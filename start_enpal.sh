#!/bin/bash

# Set environment variables
INFLUX_HOST="YOUR_INFLUX_HOST"
INFLUX_ORG_ID="YOUR_INFLUX_ORG_ID"
INFLUX_BUCKET="YOUR_INFLUX_BUCKET"
INFLUX_TOKEN="YOUR_INFLUX_TOKEN"
MODBUS_HOST="0.0.0.0"
MODBUS_PORT="502"

# Create an .env file for Docker Compose
cat <<EOF > enpal-modbus/.env
INFLUX_HOST=${INFLUX_HOST}
INFLUX_ORG_ID=${INFLUX_ORG_ID}
INFLUX_BUCKET=${INFLUX_BUCKET}
INFLUX_TOKEN=${INFLUX_TOKEN}
EOF

# Navigate to the enpal-modbus directory
cd enpal-modbus

# Run docker-compose up in detached mode
docker-compose up -d