import os
import requests
import pandas as pd
from io import StringIO
import time
import logging
from flask import Flask, jsonify

# Configure logging
logging.basicConfig(filename='/var/log/enpal.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Read environment variables
INFLUX_HOST = os.getenv("INFLUX_HOST")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")
INFLUX_ORG_ID = os.getenv("INFLUX_ORG_ID")
QUERY_RANGE_START = os.getenv("QUERY_RANGE_START", "-5m")  # Default to -5m if not set
HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("HTTP_PORT", 5000))

# Construct the INFLUX_API URL
INFLUX_API = f"http://{INFLUX_HOST}:8086/api/v2/query?orgID={INFLUX_ORG_ID}"

# Log the environment variables for debugging
logging.info(f"INFLUX_API: {INFLUX_API}")
logging.info(f"INFLUX_TOKEN: {INFLUX_TOKEN}")
logging.info(f"INFLUX_BUCKET: {INFLUX_BUCKET}")
logging.info(f"INFLUX_ORG_ID: {INFLUX_ORG_ID}")
logging.info(f"QUERY_RANGE_START: {QUERY_RANGE_START}")
logging.info(f"HTTP_HOST: {HTTP_HOST}")
logging.info(f"HTTP_PORT: {HTTP_PORT}")

app = Flask(__name__)

def fetch_solar_power_surplus():
    logging.info("Starting data query...")
    logging.debug(f"INFLUX_API: {INFLUX_API}")
    logging.debug(f"INFLUX_TOKEN: {INFLUX_TOKEN}")
    logging.debug(f"INFLUX_BUCKET: {INFLUX_BUCKET}")
    logging.debug(f"INFLUX_ORG_ID: {INFLUX_ORG_ID}")
    logging.debug(f"QUERY_RANGE_START: {QUERY_RANGE_START}")

    query = f"""
    {{
      "type": "flux",
      "query": "from(bucket: \\"{INFLUX_BUCKET}\\") |> range(start: {QUERY_RANGE_START}) |> filter(fn: (r) => r._field == \\"PowerToGrid\\") |> last()",
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
        logging.info("Data query successful.")
        # Parse the CSV response
        data = StringIO(response.text)
        df = pd.read_csv(data)

        # Extract the latest value (assuming it's the solar power surplus)
        latest_value = df['_value'].iloc[-1]
        logging.info(f"Latest solar power surplus: {latest_value}")
        return latest_value
    else:
        logging.error(f"Data query failed with status {response.status_code}.")
        return None

@app.route('/solar_power_surplus', methods=['GET'])
def get_solar_power_surplus():
    latest_value = fetch_solar_power_surplus()
    if latest_value is not None:
        return jsonify({"solar_power_surplus": latest_value})
    else:
        return jsonify({"error": "Failed to fetch data"}), 500

if __name__ == "__main__":
    logging.info("Script started")
    app.run(host=HTTP_HOST, port=HTTP_PORT)