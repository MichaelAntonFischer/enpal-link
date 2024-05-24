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

def fetch_solar_power_surplus():
    logging.debug("Starting data query...")
    logging.debug(f"INFLUX_API: {INFLUX_API}")
    logging.debug(f"INFLUX_TOKEN: {INFLUX_TOKEN}")
    logging.debug(f"INFLUX_BUCKET: {INFLUX_BUCKET}")
    logging.debug(f"INFLUX_ORG_ID: {INFLUX_ORG_ID}")
    logging.debug(f"QUERY_RANGE_START: {QUERY_RANGE_START}")

    query = f"""
    {{
      "type": "flux",
      "query": "from(bucket: \\"{INFLUX_BUCKET}\\") |> range(start: {QUERY_RANGE_START}) |> filter(fn: (r) => r._field == \\"Power.Grid.Export\\" or r._field == \\"Power.Battery.Charge.Discharge\\" or r._field == \\"Energy.Battery.Charge.Level\\" or r._field == \\"Power.Consumption.Total\\" or r._field == \\"Power.Production.Total\\") |> last()",
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
        logging.debug("Data query successful.")
        data = StringIO(response.text)
        df = pd.read_csv(data)
        logging.debug(f"DataFrame: {df}")

        if not df.empty:
            grid_export = df[df['_field'] == 'Power.Grid.Export']['_value'].iloc[-1]
            battery_charge_discharge = df[df['_field'] == 'Power.Battery.Charge.Discharge']['_value'].iloc[-1]
            battery_charge_level = df[df['_field'] == 'Energy.Battery.Charge.Level']['_value'].iloc[-1]
            house_usage = df[df['_field'] == 'Power.Consumption.Total']['_value'].iloc[-1]
            solar_generation = df[df['_field'] == 'Power.Production.Total']['_value'].iloc[-1]

            logging.debug(f"Grid Export: {grid_export}")
            logging.debug(f"Battery Charge/Discharge: {battery_charge_discharge}")
            logging.debug(f"Battery Charge Level: {battery_charge_level}")
            logging.debug(f"House Usage: {house_usage}")
            logging.debug(f"Solar Generation: {solar_generation}")

            if battery_charge_level > BATTERY_STATE_OF_CHARGE_THRESHOLD:
                effective_surplus = grid_export + min(battery_charge_discharge, -BATTERY_WATT_ADDER)
                effective_surplus = max(effective_surplus, grid_export + BATTERY_WATT_ADDER)
            else:
                effective_surplus = grid_export

            logging.debug(f"Effective Solar Power Surplus: {effective_surplus}")

            return {
                "solar_power_surplus": float(effective_surplus),
                "house_usage": float(house_usage),
                "solar_power_generation": float(solar_generation),
                "grid_power_draw": float(grid_export)
            }
        else:
            logging.error("DataFrame is empty or required columns are missing.")
            return None
    else:
        logging.error(f"Data query failed with status {response.status_code}.")
        return None

@app.route('/solar_power_surplus', methods=['GET'])
def get_solar_power_surplus():
    data = fetch_solar_power_surplus()
    if data is not None:
        return jsonify(data)
    else:
        return jsonify({"error": "Failed to fetch data"}), 500

if __name__ == "__main__":
    logging.debug("Script started")
    app.run(host=HTTP_HOST, port=HTTP_PORT, debug=True)