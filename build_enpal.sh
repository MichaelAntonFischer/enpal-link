#!/bin/bash

# Navigate to the enpal-modbus directory
cd enpal-link

# Pull the latest changes from the repository
git pull

# Build the Docker image
docker build -t michaelantonfischer/enpal-link:latest .

# Push the Docker image to the repository
docker push michaelantonfischer/enpal-link:latest

# Navigate back to the parent directory
cd ..

# Start the Docker container
./start_enpal.sh