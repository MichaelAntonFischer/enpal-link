#!/bin/bash

# Set environment variables
INFLUX_ORG_ID="YOUR_INFLUX_ORG_ID"
INFLUX_BUCKET="YOUR_INFLUX_BUCKET"
INFLUX_TOKEN="YOUR_INFLUX_TOKEN"
HTTP_HOST="0.0.0.0"
HTTP_PORT="5000"

# Set multiple IP addresses for INFLUX_HOSTS
os.environ["INFLUX_HOSTS"] = "192.168.1.10,192.168.1.11,192.168.1.12"

# Create an .env file for Docker Compose
cat <<EOF > enpal-link/.env
INFLUX_HOST=${INFLUX_HOST}
INFLUX_ORG_ID=${INFLUX_ORG_ID}
INFLUX_BUCKET=${INFLUX_BUCKET}
INFLUX_TOKEN=${INFLUX_TOKEN}
HTTP_HOST=${HTTP_HOST}
HTTP_PORT=${HTTP_PORT}
BATTERY_STATE_OF_CHARGE_THRESHOLD=${BATTERY_STATE_OF_CHARGE_THRESHOLD}
BATTERY_WATT_ADDER=${BATTERY_WATT_ADDER}
EOF

# Navigate to the enpal-modbus directory
cd enpal-link

# Run docker-compose up in detached mode
docker-compose up -d