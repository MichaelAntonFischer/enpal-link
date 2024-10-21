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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Adjust Flask's logger to only show HTTP requests in debug mode
if not app.debug:
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.WARNING)  # Set to WARNING to suppress HTTP request logs

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
    """Update the history list with the new value, maintaining a maximum of 10 entries."""
    if len(history_list) >= 10:
        history_list.pop(0)
    history_list.append(new_value)

def fetch_data():
    global cached_solar_generation, cached_grid_power, cached_battery_data, data_fetch_successful, fetch_count, initialization_phase

    if not is_within_time_range():
        logging.info("Outside specified time range. Skipping data fetch.")
        return

    if not verify_working_ip():
        logging.error("Data fetch aborted due to no working IP.")
        return

    data_fetch_successful = False  # Reset the flag at the start of each fetch

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
    update_history(battery_data_history, cached_battery_data)
    logging.debug(f"Cached Battery Data: {cached_battery_data}")

    # Record the timestamp of this fetch
    fetch_timestamps.append(datetime.now())
    if len(fetch_timestamps) > 10:
        fetch_timestamps.pop(0)

    # Increment the fetch count
    fetch_count += 1

    # Exit initialization phase after 10 fetches
    if fetch_count >= 10:
        initialization_phase = False

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
    global last_working_ip
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

    # Try the last known working IP first
    if last_working_ip:
        INFLUX_API = f"http://{last_working_ip}:8086/api/v2/query?orgID={INFLUX_ORG_ID}"
        try:
            response = requests.post(INFLUX_API, headers=headers, data=query)
            logging.debug(f"Response status: {response.status_code} from {INFLUX_API}")

            if response.status_code == 200:
                data = StringIO(response.text)
                df = pd.read_csv(data)
                if not df.empty:
                    solar_generation = df[df['_field'] == 'Power.Production.Total']['_value'].iloc[-1]
                    return {"solar_power_generation": float(solar_generation)}
                else:
                    logging.error("DataFrame is empty or required columns are missing.")
            else:
                logging.error(f"Data query failed with status {response.status_code}.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            last_working_ip = None  # Reset last working IP if it fails

    # If the last known IP fails, cycle through the list
    for _ in range(len(INFLUX_HOSTS)):
        INFLUX_API = get_influx_api()
        logging.debug(f"Trying INFLUX_API: {INFLUX_API}")
        try:
            response = requests.post(INFLUX_API, headers=headers, data=query)
            logging.debug(f"Response status: {response.status_code} from {INFLUX_API}")

            if response.status_code == 200:
                data = StringIO(response.text)
                df = pd.read_csv(data)
                if not df.empty:
                    solar_generation = df[df['_field'] == 'Power.Production.Total']['_value'].iloc[-1]
                    last_working_ip = INFLUX_API.split("//")[1].split(":")[0]  # Update last working IP
                    return {"solar_power_generation": float(solar_generation)}
                else:
                    logging.error("DataFrame is empty or required columns are missing.")
            else:
                logging.error(f"Data query failed with status {response.status_code}.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")

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
      "query": "from(bucket: \\"{INFLUX_BUCKET}\\") |> range(start: {QUERY_RANGE_START}) |> filter(fn: (r) => r._field == \\"Power.Battery.Charge.Discharge\\" or r._field == \\"Energy.Battery.Charge.Level\\") |> last()",
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
                    battery_charge_discharge = df[df['_field'] == 'Power.Battery.Charge.Discharge']['_value'].iloc[-1]
                    battery_charge_level = df[df['_field'] == 'Energy.Battery.Charge.Level']['_value'].iloc[-1]
                    last_working_ip = INFLUX_API.split("//")[1].split(":")[0]  # Update last working IP
                    return {
                        "battery_charge_discharge": float(battery_charge_discharge),
                        "battery_charge_level": float(battery_charge_level)
                    }
                else:
                    logging.error("DataFrame is empty or required columns are missing.")
            else:
                logging.error(f"Data query failed with status {response.status_code}.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            # Move to the next IP in the cycle
            last_working_ip = None

    return None

def check_stuck_values(history_list):
    """Check if the last 10 values in the history list are the same."""
    return len(set(tuple(d.items()) for d in history_list)) == 1

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
    if no_working_ip_found:
        logging.error("Health check failed: No working IP found, Enpal box seems down.")
        return jsonify({"status": "unhealthy", "reason": "No working IP found, Enpal box seems down."}), 500
    elif data_fetch_successful:
        solar_value = cached_solar_generation.get('solar_power_generation', 'N/A')
        grid_value = cached_grid_power.get('grid_power', 'N/A')
        battery_discharge = cached_battery_data.get('battery_charge_discharge', 'N/A')
        battery_level = cached_battery_data.get('battery_charge_level', 'N/A')
        logging.WARNING(f"Latest Values - S: {solar_value}, G: {grid_value}, B: {battery_discharge}, BL: {battery_level}")

        # Only check for stuck values if not in initialization phase
        if not initialization_phase and check_recent_timestamps():
            solar_stuck = check_stuck_values(solar_generation_history)
            grid_stuck = check_stuck_values(grid_power_history)
            battery_stuck = check_stuck_values(battery_data_history)

            if solar_stuck and grid_stuck and battery_stuck:
                logging.warning("Stuck values detected in all data sets.")
                return jsonify({
                    "status": "warning",
                    "message": "Stuck values detected in all data sets",
                    "solar_generation": cached_solar_generation,
                    "grid_power": cached_grid_power,
                    "battery_data": cached_battery_data,
                    "initialization_phase": initialization_phase
                }), 208  # Using 208 to indicate a warning state

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

# Adjust logging configuration to suppress non-error messages after init phase
if initialization_phase:
    logging.getLogger().setLevel(logging.INFO)
else:
    logging.getLogger().setLevel(logging.WARNING)

if __name__ == "__main__":
    logging.info("Script started")
    fetch_data()  # Start the initial data fetch
    retry_ip_verification()  # Start the retry mechanism
    app.run(host=HTTP_HOST, port=HTTP_PORT, debug=False)  # Set debug to False
