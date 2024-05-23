#!/bin/bash

# Set environment variables
INFLUX_HOST="YOUR_INFLUX_HOST"
INFLUX_ORG_ID="YOUR_INFLUX_ORG_ID"
INFLUX_BUCKET="YOUR_INFLUX_BUCKET"
INFLUX_TOKEN="YOUR_INFLUX_TOKEN"
HTTP_HOST="0.0.0.0"
HTTP_PORT="5000"
BATTERY_STATE_OF_CHARGE_THRESHOLD="50"
BATTERY_WATT_ADDER="2000"

# Create an .env file for Docker Compose
cat <<EOF > enpal-link/.env
INFLUX_HOST=${INFLUX_HOST}
INFLUX_ORG_ID=${INFLUX_ORG_ID}
INFLUX_BUCKET=${INFLUX_BUCKET}
INFLUX_TOKEN=${INFLUX_TOKEN}
EOF

# Navigate to the enpal-modbus directory
cd enpal-link

# Run docker-compose up in detached mode
docker-compose up -d