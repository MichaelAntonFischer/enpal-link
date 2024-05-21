#!/bin/bash

# Set environment variables
export INFLUX_HOST="YOUR_INFLUX_HOST"
export INFLUX_ORG_ID="YOUR_INFLUX_ORG_ID"
export INFLUX_BUCKET="YOUR_INFLUX_BUCKET"
export INFLUX_TOKEN="YOUR_INFLUX_TOKEN"
export POWERFOX_USERNAME="YOUR_POWERFOX_USERNAME"
export POWERFOX_PASSWORD="YOUR_POWERFOX_PASSWORD"
export POWERFOX_DEVICE_ID="YOUR_POWERFOX_DEVICE_ID"

# Navigate to the enpal-modbus directory
cd enpal-modbus

# Run docker-compose up in detached mode
docker-compose up -d