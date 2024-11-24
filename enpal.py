import os
import time
import requests
import pandas as pd
from io import StringIO
import logging
from flask import Flask, jsonify
from dotenv import load_dotenv
from threading import Timer
from datetime import datetime, timedelta
import pytz
from itertools import cycle

# Load environment variables from .env file
load_dotenv()

# Configure logging to log to stdout and stderr
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Read environment variables
INFLUX_HOSTS = os.getenv("INFLUX_HOSTS")
logging.info(f"INFLUX_HOSTS: {INFLUX_HOSTS}")

if INFLUX_HOSTS:
    INFLUX_HOSTS = INFLUX_HOSTS.split(",")  # Multiple IPs separated by commas
else:
    logging.error("INFLUX_HOSTS environment variable is not set or empty.")
    raise ValueError("INFLUX_HOSTS environment variable is not set or empty.")

INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")
INFLUX_ORG_ID = os.getenv("INFLUX_ORG_ID")
QUERY_RANGE_START = os.getenv("QUERY_RANGE_START", "-5m")  # Default to -5m if not set
HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("HTTP_PORT", 5000))
START_TIME = os.getenv("START_TIME", "05:00")  
END_TIME = os.getenv("END_TIME", "22:00")  
TIMEZONE = os.getenv("TIMEZONE", "CET")  

# Cycle through the IP addresses
influx_hosts_cycle = cycle(INFLUX_HOSTS)

# Global variables to store the cached data and health status
cached_solar_generation = None
cached_grid_power = None
cached_battery_data = None
data_fetch_successful = False

# Global variable to store the last known working IP
last_working_ip = None

# Global variable to track if no working IP was found
no_working_ip_found = False

# Global variables to store the last 10 values and their timestamps
solar_generation_history = []
grid_power_history = []
battery_data_history = []
fetch_timestamps = []

# Global variable to track the initialization phase
initialization_phase = True

# Global variable to track the number of data fetches
fetch_count = 0

def get_influx_api():
    """Get the next INFLUX_API URL from the cycle of IP addresses."""
    global last_working_ip
    if last_working_ip:
        return f"http://{last_working_ip}:8086/api/v2/query?orgID={INFLUX_ORG_ID}"
    else:
        current_host = next(influx_hosts_cycle)
        return f"http://{current_host}:8086/api/v2/query?orgID={INFLUX_ORG_ID}"

# Log the environment variables for debugging
logging.info(f"INFLUX_HOSTS: {INFLUX_HOSTS}")
logging.info(f"INFLUX_TOKEN: {INFLUX_TOKEN}")
logging.info(f"INFLUX_BUCKET: {INFLUX_BUCKET}")
logging.info(f"INFLUX_ORG_ID: {INFLUX_ORG_ID}")
logging.info(f"QUERY_RANGE_START: {QUERY_RANGE_START}")
logging.info(f"HTTP_HOST: {HTTP_HOST}")
logging.info(f"HTTP_PORT: {HTTP_PORT}")
logging.info(f"START_TIME: {START_TIME}")
logging.info(f"END_TIME: {END_TIME}")
logging.info(f"TIMEZONE: {TIMEZONE}")

app = Flask(__name__)

# Set the werkzeug logger level to WARNING
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def is_within_time_range():
    """Check if the current time is within the specified start and end time in the given timezone."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).time()
    start_time = datetime.strptime(START_TIME, "%H:%M").time()
    end_time = datetime.strptime(END_TIME, "%H:%M").time()
    return start_time <= now <= end_time

def verify_working_ip():
    """Verify the last known working IP or find a new one."""
    global last_working_ip, no_working_ip_found
    no_working_ip_found = False  # Reset the flag at the start of each verification

    query = f"""
    {{
      "type": "flux",
      "query": "from(bucket: \\"{INFLUX_BUCKET}\\") |> range(start: {QUERY_RANGE_START}) |> limit(n:1)",
      "orgID": "{INFLUX_ORG_ID}"
    }}
    """

    headers = {
        "Authorization": f"Token {INFLUX_TOKEN}",
        "Accept": "application/json",
        "Content-type": "application/json"
    }

    # Try the last known working IP first
    if last_working_ip:
        INFLUX_API = f"http://{last_working_ip}:8086/api/v2/query?orgID={INFLUX_ORG_ID}"
        try:
            response = requests.post(INFLUX_API, headers=headers, data=query)
            if response.status_code == 200:
                logging.info(f"Verified working IP: {last_working_ip}")
                return True
            else:
                logging.error(f"Verification failed with status {response.status_code}.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Verification request failed: {e}")
            last_working_ip = None  # Reset last working IP if it fails

    # If the last known IP fails, cycle through the list
    for _ in range(len(INFLUX_HOSTS)):
        INFLUX_API = get_influx_api()
        try:
            response = requests.post(INFLUX_API, headers=headers, data=query)
            if response.status_code == 200:
                last_working_ip = INFLUX_API.split("//")[1].split(":")[0]  # Update last working IP
                logging.info(f"New working IP found: {last_working_ip}")
                return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Verification request failed: {e}")

    logging.error("No working IP found.")
    no_working_ip_found = True  # Set the flag if no IP is found
    return False

def update_history(history_list, new_value):
    """Update the history list with the new value and current timestamp."""
    current_time = datetime.now()
    if len(history_list) >= 60:  # Increased from 10 to 60
        history_list.pop(0)
    history_list.append((current_time, new_value))

def get_delay_until_start():
    """Calculate the delay in seconds until the next start time."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    start_time = datetime.strptime(START_TIME, "%H:%M").replace(
        year=now.year, month=now.month, day=now.day, tzinfo=tz
    )
    
    # If start time is earlier than current time, add one day
    if start_time <= now:
        start_time = start_time + timedelta(days=1)
    
    delay = (start_time - now).total_seconds()
    logging.info(f"Calculated delay until next start: {delay} seconds")
    return delay

def fetch_data():
    global cached_solar_generation, cached_grid_power, cached_battery_data, data_fetch_successful, fetch_count, initialization_phase
    
    if not is_within_time_range():
        # Set all values to 0 during off-hours
        cached_solar_generation = {"solar_power_generation": 0.0}
        cached_grid_power = {"grid_power": 0.0}
        cached_battery_data = {
            "battery_charge_discharge": 0.0,
            "battery_charge_level": 0.0
        }
        data_fetch_successful = True  # Set to true so health check returns 200
        
        # Schedule next fetch at start time
        logging.warning("Outside specified time range. Scheduling next fetch at start time.")
        delay = get_delay_until_start()
        Timer(delay, fetch_data).start()
        return

    if initialization_phase:
        logging.info("Application is in the initialization phase.")

    if not verify_working_ip():
        logging.error("Data fetch aborted due to no working IP.")
        Timer(10, fetch_data).start()  
        return

    data_fetch_successful = False 
    
    logging.info("Within time range, fetching data...")
    # Fetch solar generation data
    cached_solar_generation = fetch_solar_generation()
    update_history(solar_generation_history, cached_solar_generation)
    logging.debug(f"Cached Solar Generation Data: {cached_solar_generation}")

    # Fetch grid power data
    cached_grid_power = fetch_grid_power()
    update_history(grid_power_history, cached_grid_power)
    logging.debug(f"Cached Grid Power Data: {cached_grid_power}")

    # Fetch battery data
    cached_battery_data = fetch_battery_data()
    if cached_battery_data:
        # Create a combined battery data dictionary with both power and level
        battery_history_data = {
            'battery_charge_level': cached_battery_data['battery_charge_level'],
            'battery_power': cached_battery_data['battery_charge_discharge']
        }
        update_history(battery_data_history, battery_history_data)
    logging.debug(f"Cached Battery Data: {cached_battery_data}")

    # Record the timestamp of this fetch
    fetch_timestamps.append(datetime.now())
    if len(fetch_timestamps) > 10:
        fetch_timestamps.pop(0)

    # Increment the fetch count
    fetch_count += 1

    # Check if we need to exit the initialization phase
    if fetch_count >= 10 and initialization_phase:
        logging.info("Exiting initialization phase.")
        initialization_phase = False
        # Only change to WARNING if not in DEBUG mode
        if logging.getLogger().getEffectiveLevel() != logging.DEBUG:
            logging.getLogger().setLevel(logging.WARNING)

    # Check if all data fetches were successful
    if cached_solar_generation and cached_grid_power and cached_battery_data:
        data_fetch_successful = True
        logging.info("Data fetch successful.")
    else:
        logging.error("Data fetch failed for one or more components.")

    # Schedule the next fetch in 10 seconds
    logging.info("Scheduling the next data fetch in 10 seconds.")
    Timer(10, fetch_data).start()

def fetch_solar_generation():
    logging.debug("Fetching solar generation data...")
    query = f"""
    {{
      "type": "flux",
      "query": "from(bucket: \\"{INFLUX_BUCKET}\\") |> range(start: {QUERY_RANGE_START}) |> filter(fn: (r) => r._field == \\"Power.Production.Total\\") |> last()",
      "orgID": "{INFLUX_ORG_ID}"
    }}
    """

    headers = {
        "Authorization": f"Token {INFLUX_TOKEN}",
        "Accept": "application/json",
        "Content-type": "application/json"
    }

    for _ in range(len(INFLUX_HOSTS)):
        INFLUX_API = get_influx_api()
        try:
            response = requests.post(INFLUX_API, headers=headers, data=query)
            logging.debug(f"Response status: {response.status_code} from {INFLUX_API}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'numberDataPoints' in data:
                        # New format
                        solar_generation = data['numberDataPoints'].get('Power.Production.Total', {}).get('value', 0.0)
                        last_working_ip = INFLUX_API.split("//")[1].split(":")[0]
                        return {"solar_power_generation": float(solar_generation)}
                    else:
                        # Try old format with CSV
                        data_csv = StringIO(response.text)
                        df = pd.read_csv(data_csv)
                        if not df.empty:
                            solar_generation = df[df['_field'] == 'Power.Production.Total']['_value'].iloc[-1]
                            last_working_ip = INFLUX_API.split("//")[1].split(":")[0]
                            return {"solar_power_generation": float(solar_generation)}
                except Exception as e:
                    logging.error(f"Error parsing response: {str(e)}")
                    continue
            else:
                logging.error(f"Data query failed with status {response.status_code}.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            last_working_ip = None
        except Exception as e:
            logging.error(f"Unexpected error while fetching solar data: {str(e)}")
            continue

    return None

def fetch_grid_power():
    logging.debug("Fetching grid import/export data...")
    query = f"""
    {{
      "type": "flux",
      "query": "from(bucket: \\"{INFLUX_BUCKET}\\") |> range(start: {QUERY_RANGE_START}) |> filter(fn: (r) => r._field == \\"Power.Grid.Export\\" or r._field == \\"Power.Grid.Import\\") |> last()",
      "orgID": "{INFLUX_ORG_ID}"
    }}
    """

    headers = {
        "Authorization": f"Token {INFLUX_TOKEN}",
        "Accept": "application/json",
        "Content-type": "application/json"
    }

    for _ in range(len(INFLUX_HOSTS)):
        INFLUX_API = get_influx_api()
        logging.debug(f"Trying INFLUX_API: {INFLUX_API}")
        try:
            response = requests.post(INFLUX_API, headers=headers, data=query)
            logging.debug(f"Response status: {response.status_code} from {INFLUX_API}")
            logging.debug(f"Response output: {response.text}")

            if response.status_code == 200:
                data = StringIO(response.text)
                df = pd.read_csv(data)
                if not df.empty:
                    grid_export = df[df['_field'] == 'Power.Grid.Export']['_value'].iloc[-1] if 'Power.Grid.Export' in df['_field'].values else 0
                    grid_import = df[df['_field'] == 'Power.Grid.Import']['_value'].iloc[-1] if 'Power.Grid.Import' in df['_field'].values else 0
                    grid_power = float(grid_export) - float(grid_import)
                    last_working_ip = INFLUX_API.split("//")[1].split(":")[0]  # Update last working IP
                    return {"grid_power": grid_power}
                else:
                    logging.error("DataFrame is empty or required columns are missing.")
            else:
                logging.error(f"Data query failed with status {response.status_code}.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            # Move to the next IP in the cycle
            last_working_ip = None

    return None

def fetch_battery_data():
    logging.debug("Fetching battery data...")
    query = f"""
    {{
      "type": "flux",
      "query": "from(bucket: \\"{INFLUX_BUCKET}\\") |> range(start: {QUERY_RANGE_START}) |> filter(fn: (r) => r._field == \\"Power.Battery.Charge.Discharge\\" or r._field == \\"Energy.Battery.Charge.Level\\" or r._field == \\"Percent.Storage.Level\\") |> last()",
      "orgID": "{INFLUX_ORG_ID}"
    }}
    """

    headers = {
        "Authorization": f"Token {INFLUX_TOKEN}",
        "Accept": "application/json",
        "Content-type": "application/json"
    }

    for _ in range(len(INFLUX_HOSTS)):
        INFLUX_API = get_influx_api()
        logging.debug(f"Trying INFLUX_API: {INFLUX_API}")
        try:
            response = requests.post(INFLUX_API, headers=headers, data=query)
            logging.debug(f"Response status: {response.status_code} from {INFLUX_API}")
            logging.debug(f"Response output: {response.text}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'numberDataPoints' in data:
                        # New format
                        battery_charge_discharge = data['numberDataPoints'].get('Power.Storage.Total', {}).get('value', 0.0)
                        battery_charge_level = data['numberDataPoints'].get('Energy.Storage.Level', {}).get('value', 0.0)
                        last_working_ip = INFLUX_API.split("//")[1].split(":")[0]
                        return {
                            "battery_charge_discharge": float(battery_charge_discharge),
                            "battery_charge_level": float(battery_charge_level)
                        }
                    else:
                        # Try old format with CSV
                        data_csv = StringIO(response.text)
                        df = pd.read_csv(data_csv)
                        if not df.empty:
                            battery_charge_discharge = df[df['_field'] == 'Power.Battery.Charge.Discharge']['_value'].iloc[-1]
                            battery_charge_level = df[df['_field'] == 'Energy.Battery.Charge.Level']['_value'].iloc[-1]
                            last_working_ip = INFLUX_API.split("//")[1].split(":")[0]
                            return {
                                "battery_charge_discharge": float(battery_charge_discharge),
                                "battery_charge_level": float(battery_charge_level)
                            }
                except Exception as e:
                    logging.error(f"Error parsing response: {str(e)}")
                    continue
            else:
                logging.error(f"Data query failed with status {response.status_code}.")
                logging.error(f"Response content: {response.text}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            last_working_ip = None
        except Exception as e:
            logging.error(f"Unexpected error while fetching battery data: {str(e)}")
            continue

    return None

def check_stuck_values(history_list):
    """Check if the data is stuck based on timestamps and value consistency."""
    if len(history_list) < 10:
        logging.warning("Not enough data to determine if values are stuck.")
        return False
    
    # Log the history list for debugging
    logging.debug(f"History list for stuck check: {history_list}")
    
    if 'solar_power_generation' in history_list[0][1]:
        key = 'solar_power_generation'
    elif 'grid_power' in history_list[0][1]:
        key = 'grid_power'
    elif 'battery_charge_level' in history_list[0][1]:
        key = 'battery_charge_level'
    else:
        logging.error("Unknown data format in history list")
        return False
    
    timestamps = [entry[0] for entry in history_list]
    values = [entry[1][key] for entry in history_list]
    
    # Get the current time
    current_time = datetime.now()
    
    # Check if all timestamps are older than 2 hours
    if all(current_time - ts > timedelta(hours=2) for ts in timestamps):
        logging.warning("All timestamps are older than 2 hours. Data is stuck.")
        return True
    
    # Check if all values are the same (regardless of timestamp)
    if len(set(values)) == 1:
        logging.warning("Detected stuck values in the history list.")
        return True
    
    logging.info("Values and timestamps are not stuck.")
    return False

def check_recent_timestamps():
    """Check if the timestamps of the last 10 fetches are within the last 2 hours."""
    if len(fetch_timestamps) < 10:
        return False
    return all(datetime.now() - ts < timedelta(hours=2) for ts in fetch_timestamps)

@app.route('/solar_generation', methods=['GET'])
def get_solar_generation():
    if cached_solar_generation:
        logging.debug(f"Returning solar generation data: {cached_solar_generation}")
        return jsonify(cached_solar_generation), 200
    else:
        logging.error("Failed to fetch solar generation data")
        return jsonify({"error": "Failed to fetch data"}), 500

@app.route('/grid_power', methods=['GET'])
def get_grid_power():
    if cached_grid_power:
        logging.debug(f"Returning grid power data: {cached_grid_power}")
        return jsonify(cached_grid_power), 200
    else:
        logging.error("Failed to fetch grid power data")
        return jsonify({"error": "Failed to fetch data"}), 500

@app.route('/battery_data', methods=['GET'])
def get_battery_data():
    if cached_battery_data:
        logging.debug(f"Returning battery data: {cached_battery_data}")
        return jsonify(cached_battery_data), 200
    else:
        logging.error("Failed to fetch battery data")
        return jsonify({"error": "Failed to fetch data"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    if not is_within_time_range():
        # During off-hours, always return healthy with 0 values
        return jsonify({
            "status": "healthy",
            "message": "System in standby (outside operating hours)",
            "solar_generation": {"solar_power_generation": 0.0},
            "grid_power": {"grid_power": 0.0},
            "battery_data": {
                "battery_charge_discharge": 0.0,
                "battery_charge_level": 0.0
            },
            "initialization_phase": False
        }), 200

    if no_working_ip_found:
        logging.error("Health check failed: No working IP found, Enpal box seems down.")
        return jsonify({"status": "unhealthy", "reason": "No working IP found, Enpal box seems down."}), 500
    elif data_fetch_successful:
        solar_value = cached_solar_generation.get('solar_power_generation', 'N/A')
        grid_value = cached_grid_power.get('grid_power', 'N/A')
        battery_level = cached_battery_data.get('battery_charge_level', 'N/A')
        battery_power = cached_battery_data.get('battery_charge_discharge', 'N/A')
        logging.warning(f"Latest Values - S: {solar_value}, G: {grid_value}, B_lvl: {battery_level}, B_pwr: {battery_power}")

        # Only check for stuck values if not in initialization phase
        if not initialization_phase:
            # First check if timestamps are recent enough
            if not check_recent_timestamps():
                log_all_datasets("Data timestamps are too old")
                return jsonify({
                    "status": "warning",
                    "message": "Data timestamps are too old",
                    "solar_generation": cached_solar_generation,
                    "grid_power": cached_grid_power,
                    "battery_data": cached_battery_data,
                    "initialization_phase": initialization_phase
                }), 208

            # Then check if all datasets show the same values
            solar_values = [entry[1]['solar_power_generation'] for entry in solar_generation_history[-60:]]
            grid_values = [entry[1]['grid_power'] for entry in grid_power_history[-60:]]
            battery_level_values = [entry[1]['battery_charge_level'] for entry in battery_data_history[-60:]]
            battery_power_values = [entry[1]['battery_power'] for entry in battery_data_history[-60:]]

            if (len(set(solar_values)) == 1 and 
                len(set(grid_values)) == 1 and 
                len(set(battery_level_values)) == 1 and
                len(set(battery_power_values)) == 1):
                log_all_datasets("Stuck values detected in all data sets")
                return jsonify({
                    "status": "warning",
                    "message": "Stuck values detected in all data sets",
                    "solar_generation": cached_solar_generation,
                    "grid_power": cached_grid_power,
                    "battery_data": cached_battery_data,
                    "initialization_phase": initialization_phase
                }), 208

        return jsonify({
            "status": "healthy",
            "solar_generation": cached_solar_generation,
            "grid_power": cached_grid_power,
            "battery_data": cached_battery_data,
            "initialization_phase": initialization_phase
        }), 200
    else:
        logging.error("Health check failed")
        return jsonify({"status": "unhealthy"}), 500

def retry_ip_verification():
    """Retry IP verification every hour if no working IP is found."""
    if no_working_ip_found:
        logging.info("Retrying IP verification after an hour...")
        verify_working_ip()
    # Schedule the next retry in 1 hour (3600 seconds)
    Timer(3600, retry_ip_verification).start()

def log_all_datasets(reason):
    """Log all datasets when a warning condition is detected."""
    logging.warning(f"Warning condition detected: {reason}")
    logging.warning("Current data in memory:")
    logging.warning(f"Solar Generation History (last 60):")
    for ts, data in solar_generation_history[-60:]:
        logging.warning(f"  {ts}: {data}")
    logging.warning(f"Grid Power History (last 60):")
    for ts, data in grid_power_history[-60:]:
        logging.warning(f"  {ts}: {data}")
    logging.warning(f"Battery Data History (last 60):")
    for ts, data in battery_data_history[-60:]:
        logging.warning(f"  {ts}: {data}")

if __name__ == "__main__":
    logging.info("Script started")
    fetch_data()  # Start the initial data fetch
    retry_ip_verification()  # Start the retry mechanism
    app.run(host=HTTP_HOST, port=HTTP_PORT, debug=False)  # Set debug to False
