import os
import requests
import pandas as pd
from io import StringIO
import time
import logging
from pymodbus.server.sync import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import sunspec2.mdef as mdef
import sunspec2.device as device

# Configure logging
logging.basicConfig(filename='/var/log/enpal.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Read environment variables
INFLUX_HOST = os.getenv("INFLUX_HOST")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")
INFLUX_ORG_ID = os.getenv("INFLUX_ORG_ID")
QUERY_RANGE_START = os.getenv("QUERY_RANGE_START", "-5m")  # Default to -5m if not set
MODBUS_HOST = os.getenv("MODBUS_HOST", "0.0.0.0")
MODBUS_PORT = int(os.getenv("MODBUS_PORT", 502))

# Construct the INFLUX_API URL
INFLUX_API = f"http://{INFLUX_HOST}:8086/api/v2/query?orgID={INFLUX_ORG_ID}"

# Log the environment variables for debugging
logging.info(f"INFLUX_API: {INFLUX_API}")
logging.info(f"INFLUX_TOKEN: {INFLUX_TOKEN}")
logging.info(f"INFLUX_BUCKET: {INFLUX_BUCKET}")
logging.info(f"INFLUX_ORG_ID: {INFLUX_ORG_ID}")
logging.info(f"QUERY_RANGE_START: {QUERY_RANGE_START}")
logging.info(f"MODBUS_HOST: {MODBUS_HOST}")
logging.info(f"MODBUS_PORT: {MODBUS_PORT}")

# SunSpec model for a power meter (model 1)
model_id = 1
model_def = mdef.get_model_def(model_id)
model = device.Model(model_def)

# Initialize the model with some example values
model.points['ID'].value = model_id
model.points['L'].value = 66  # Length of the model
model.points['A'].value = 123.45  # Example value for current
model.points['PhV'].value = 230.0  # Example value for voltage
model.points['W'].value = 5000  # Example value for power

# Create a Modbus data block with the SunSpec model
data_block = ModbusSequentialDataBlock(40001, model.to_list())

# Create a Modbus slave context
store = ModbusSlaveContext(hr=data_block, zero_mode=True)
context = ModbusServerContext(slaves=store, single=True)

# Create Modbus device identification
identity = ModbusDeviceIdentification()
identity.VendorName = 'Your Company'
identity.ProductCode = 'SunSpec Power Meter'
identity.VendorUrl = 'http://yourcompany.com'
identity.ProductName = 'SunSpec Power Meter'
identity.ModelName = 'SunSpec Power Meter'
identity.MajorMinorRevision = '1.0'

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

        # Extract the latest value (assuming it's the solar power surplus)
        latest_value = df['_value'].iloc[-1]
        logging.info(f"Latest solar power surplus: {latest_value}")
        return latest_value
    else:
        logging.error(f"Data query failed with status {response.status_code}.")
        return None

def update_sunspec_model(latest_value):
    if latest_value is not None:
        # Update the SunSpec model with the latest value
        model.points['W'].value = latest_value
        # Update the Modbus data block
        data_block.setValues(40001, model.to_list())
        logging.info(f"Updated SunSpec model with value: {latest_value}")
    else:
        logging.warning("No value to update SunSpec model.")

def run_server():
    logging.info(f"Starting Modbus SunSpec server on {MODBUS_HOST}:{MODBUS_PORT}")
    StartTcpServer(context, identity=identity, address=(MODBUS_HOST, MODBUS_PORT))

if __name__ == "__main__":
    logging.info("Script started")
    # Start the Modbus server in a separate thread
    from threading import Thread
    server_thread = Thread(target=run_server)
    server_thread.start()

    while True:
        latest_value = fetch_solar_power_surplus()
        update_sunspec_model(latest_value)
        time.sleep(60)  # Wait for 1 minute before the next iteration