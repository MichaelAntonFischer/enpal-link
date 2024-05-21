#!/bin/bash

# Navigate to the enpal-modbus directory
cd enpal-modbus

# Pull the latest changes from the repository
git pull

# Build the Docker image
docker build -t michaelantonfischer/enpal-modbus .

# Push the Docker image to the repository
docker push michaelantonfischer/enpal-modbus

# Navigate back to the parent directory
cd ..

# Start the Docker container
./start_enpal.sh