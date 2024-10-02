import os
import time
import requests
import pandas as pd
from io import StringIO
import logging
from flask import Flask, jsonify
from dotenv import load_dotenv
from threading import Timer
from datetime import datetime
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

def get_influx_api():
    """Get the next INFLUX_API URL from the cycle of IP addresses."""
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

def is_within_time_range():
    """Check if the current time is within the specified start and end time in the given timezone."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).time()
    start_time = datetime.strptime(START_TIME, "%H:%M").time()
    end_time = datetime.strptime(END_TIME, "%H:%M").time()
    return start_time <= now <= end_time

def fetch_data():
    global cached_solar_generation, cached_grid_power, cached_battery_data, data_fetch_successful

    data_fetch_successful = False  # Reset the flag at the start of each fetch

    if is_within_time_range():
        logging.info("Within time range, fetching data...")
        # Fetch solar generation data
        cached_solar_generation = fetch_solar_generation()
        logging.info(f"Cached Solar Generation Data: {cached_solar_generation}")

        # Fetch grid power data
        cached_grid_power = fetch_grid_power()
        logging.info(f"Cached Grid Power Data: {cached_grid_power}")

        # Fetch battery data
        cached_battery_data = fetch_battery_data()
        logging.info(f"Cached Battery Data: {cached_battery_data}")

        # Check if all data fetches were successful
        if cached_solar_generation and cached_grid_power and cached_battery_data:
            data_fetch_successful = True
            logging.info("Data fetch successful.")
        else:
            logging.error("Data fetch failed for one or more components.")
    else:
        # Set cached data to 0 when outside the specified time range
        cached_solar_generation = {"solar_power_generation": 0}
        cached_grid_power = {"grid_power": 0}
        cached_battery_data = {
            "battery_charge_discharge": 0,
            "battery_charge_level": 0
        }
        logging.info("Outside specified time range. Cached data set to 0.")
        data_fetch_successful = True  # Consider it successful since it's outside the time range

    # Schedule the next fetch in 60 seconds
    Timer(60, fetch_data).start()

def fetch_solar_generation():
    logging.info("Fetching solar generation data...")
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
        logging.info(f"INFLUX_API: {INFLUX_API}")
        response = requests.post(INFLUX_API, headers=headers, data=query)
        logging.info(f"Response status: {response.status_code} from {INFLUX_API}")
        logging.info(f"Response output: {response.text}")

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

    return None

def fetch_grid_power():
    logging.info("Fetching grid import/export data...")
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
        logging.info(f"INFLUX_API: {INFLUX_API}")
        try:
            response = requests.post(INFLUX_API, headers=headers, data=query)
            logging.info(f"Response status: {response.status_code} from {INFLUX_API}")
            logging.info(f"Response output: {response.text}")

            if response.status_code == 200:
                data = StringIO(response.text)
                df = pd.read_csv(data)
                if not df.empty:
                    grid_export = df[df['_field'] == 'Power.Grid.Export']['_value'].iloc[-1] if 'Power.Grid.Export' in df['_field'].values else 0
                    grid_import = df[df['_field'] == 'Power.Grid.Import']['_value'].iloc[-1] if 'Power.Grid.Import' in df['_field'].values else 0
                    grid_power = float(grid_export) - float(grid_import)
                    return {"grid_power": grid_power}
                else:
                    logging.error("DataFrame is empty or required columns are missing.")
            else:
                logging.error(f"Data query failed with status {response.status_code}.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")

    return None

def fetch_battery_data():
    logging.info("Fetching battery data...")
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
        logging.info(f"INFLUX_API: {INFLUX_API}")
        try:
            response = requests.post(INFLUX_API, headers=headers, data=query)
            logging.info(f"Response status: {response.status_code} from {INFLUX_API}")
            logging.info(f"Response output: {response.text}")

            if response.status_code == 200:
                data = StringIO(response.text)
                df = pd.read_csv(data)
                if not df.empty:
                    battery_charge_discharge = df[df['_field'] == 'Power.Battery.Charge.Discharge']['_value'].iloc[-1]
                    battery_charge_level = df[df['_field'] == 'Energy.Battery.Charge.Level']['_value'].iloc[-1]
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

    return None

@app.route('/solar_generation', methods=['GET'])
def get_solar_generation():
    if cached_solar_generation:
        logging.info(f"Returning solar generation data: {cached_solar_generation}")
        return jsonify(cached_solar_generation), 200
    else:
        logging.error("Failed to fetch solar generation data")
        return jsonify({"error": "Failed to fetch data"}), 500

@app.route('/grid_power', methods=['GET'])
def get_grid_power():
    if cached_grid_power:
        logging.info(f"Returning grid power data: {cached_grid_power}")
        return jsonify(cached_grid_power), 200
    else:
        logging.error("Failed to fetch grid power data")
        return jsonify({"error": "Failed to fetch data"}), 500

@app.route('/battery_data', methods=['GET'])
def get_battery_data():
    if cached_battery_data:
        logging.info(f"Returning battery data: {cached_battery_data}")
        return jsonify(cached_battery_data), 200
    else:
        logging.error("Failed to fetch battery data")
        return jsonify({"error": "Failed to fetch data"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    if data_fetch_successful:
        return jsonify({"status": "healthy"}), 200
    else:
        return jsonify({"status": "unhealthy"}), 500

if __name__ == "__main__":
    logging.info("Script started")
    fetch_data()  # Start the initial data fetch
    app.run(host=HTTP_HOST, port=HTTP_PORT, debug=True)