import os
import requests
import pandas as pd
from io import StringIO
import logging
from flask import Flask, jsonify
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging to log to stdout and stderr
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(message)s')

# Read environment variables
INFLUX_HOST = os.getenv("INFLUX_HOST")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")
INFLUX_ORG_ID = os.getenv("INFLUX_ORG_ID")
QUERY_RANGE_START = os.getenv("QUERY_RANGE_START", "-5m")  # Default to -5m if not set
HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("HTTP_PORT", 5000))
BATTERY_STATE_OF_CHARGE_THRESHOLD = int(os.getenv("BATTERY_STATE_OF_CHARGE_THRESHOLD", 50))  # Default to 50 if not set
BATTERY_WATT_ADDER = int(os.getenv("BATTERY_WATT_ADDER", 2000))  # Default to 2000 if not set

# Construct the INFLUX_API URL
INFLUX_API = f"http://{INFLUX_HOST}:8086/api/v2/query?orgID={INFLUX_ORG_ID}"

# Log the environment variables for debugging
logging.debug(f"INFLUX_API: {INFLUX_API}")
logging.debug(f"INFLUX_TOKEN: {INFLUX_TOKEN}")
logging.debug(f"INFLUX_BUCKET: {INFLUX_BUCKET}")
logging.debug(f"INFLUX_ORG_ID: {INFLUX_ORG_ID}")
logging.debug(f"QUERY_RANGE_START: {QUERY_RANGE_START}")
logging.debug(f"HTTP_HOST: {HTTP_HOST}")
logging.debug(f"HTTP_PORT: {HTTP_PORT}")
logging.debug(f"BATTERY_STATE_OF_CHARGE_THRESHOLD: {BATTERY_STATE_OF_CHARGE_THRESHOLD}")
logging.debug(f"BATTERY_WATT_ADDER: {BATTERY_WATT_ADDER}")

app = Flask(__name__)

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

    response = requests.post(INFLUX_API, headers=headers, data=query)
    logging.debug(f"Curl status: {response.status_code}")
    logging.debug(f"Curl output: {response.text}")

    if response.status_code == 200:
        data = StringIO(response.text)
        df = pd.read_csv(data)
        if not df.empty:
            solar_generation = df[df['_field'] == 'Power.Production.Total']['_value'].iloc[-1]
            return {"solar_power_generation": float(solar_generation)}
        else:
            logging.error("DataFrame is empty or required columns are missing.")
            return None
    else:
        logging.error(f"Data query failed with status {response.status_code}.")
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

    response = requests.post(INFLUX_API, headers=headers, data=query)
    logging.debug(f"Curl status: {response.status_code}")
    logging.debug(f"Curl output: {response.text}")

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
            return None
    else:
        logging.error(f"Data query failed with status {response.status_code}.")
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

    response = requests.post(INFLUX_API, headers=headers, data=query)
    logging.debug(f"Curl status: {response.status_code}")
    logging.debug(f"Curl output: {response.text}")

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
            return None
    else:
        logging.error(f"Data query failed with status {response.status_code}.")
        return None

@app.route('/solar_generation', methods=['GET'])
def get_solar_generation():
    data = fetch_solar_generation()
    if data is not None:
        return jsonify(data)
    else:
        return jsonify({"error": "Failed to fetch data"}), 500

@app.route('/grid_power', methods=['GET'])
def get_grid_power():
    data = fetch_grid_power()
    if data is not None:
        return jsonify(data)
    else:
        return jsonify({"error": "Failed to fetch data"}), 500

@app.route('/battery_data', methods=['GET'])
def get_battery_data():
    data = fetch_battery_data()
    if data is not None:
        return jsonify(data)
    else:
        return jsonify({"error": "Failed to fetch data"}), 500

if __name__ == "__main__":
    logging.debug("Script started")
    app.run(host=HTTP_HOST, port=HTTP_PORT, debug=True)
