import os
import requests
import pandas as pd
from io import StringIO
import time
import logging

# Configure logging
logging.basicConfig(filename='/var/log/enpal.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Read environment variables
INFLUX_HOST = os.getenv("INFLUX_HOST")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")
INFLUX_ORG_ID = os.getenv("INFLUX_ORG_ID")
QUERY_RANGE_START = os.getenv("QUERY_RANGE_START", "-5m")  # Default to -5m if not set

# Construct the INFLUX_API URL
INFLUX_API = f"http://{INFLUX_HOST}:8086/api/v2/query?orgID={INFLUX_ORG_ID}"

# Log the environment variables for debugging
logging.info(f"INFLUX_API: {INFLUX_API}")
logging.info(f"INFLUX_TOKEN: {INFLUX_TOKEN}")
logging.info(f"INFLUX_BUCKET: {INFLUX_BUCKET}")
logging.info(f"INFLUX_ORG_ID: {INFLUX_ORG_ID}")
logging.info(f"QUERY_RANGE_START: {QUERY_RANGE_START}")

def output_whole_bucket():
    logging.info("Starting data query...")
    logging.debug(f"INFLUX_API: {INFLUX_API}")
    logging.debug(f"INFLUX_TOKEN: {INFLUX_TOKEN}")
    logging.debug(f"INFLUX_BUCKET: {INFLUX_BUCKET}")
    logging.debug(f"INFLUX_ORG_ID: {INFLUX_ORG_ID}")
    logging.debug(f"QUERY_RANGE_START: {QUERY_RANGE_START}")

    query = f"""
    {{
      "type": "flux",
      "query": "from(bucket: \\"{INFLUX_BUCKET}\\") |> range(start: {QUERY_RANGE_START}) |> last()",
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

        # Display the fields and their values with units
        for index, row in df.iterrows():
            print(f"Time: {row['_time']}")
            print(f"Value: {row['_value']}")
            print(f"Field: {row['_field']}")
            print(f"Measurement: {row['_measurement']}")
            print(f"Unit: {row['unit']}")
            print("-------------------")
    else:
        logging.error(f"Data query failed with status {response.status_code}.")

if __name__ == "__main__":
    logging.info("Script started")
    while True:
        output_whole_bucket()
        time.sleep(60)  # Wait for 1 minute before the next iteration