# Enpal Solar Surplus Integration with cFos Charging Manager

This repository contains a Python script that fetches solar power surplus data from an Enpal InfluxDB and serves it via an HTTP endpoint. This data can be used to integrate with the cFos Charging Manager to enable surplus charging.

## Prerequisites
Raspberry Pi (or any other Linux-based system) with:<br />
Docker<br />
Docker-Compose<br />
Git<br />

## Installation

### Step 1: Clone the Repository
Clone this repository to your local machine:

```bash
git clone https://github.com/MichaelAntonFischer/enpal-link
```

### Step 2: Copy and Configure the Start Script
Copy the start_enpal.sh script to a directory above the cloned repository:

```bash
cp enpal-link/start_enpal.sh .
```
This step is recommended to not overwrite your config when pulling new updates from the git repo and not expose your data to the git directory.

### Make the script executable:

```bash
chmod +x ./start_enpal.sh
```

### Edit the start_enpal.sh script to add the necessary environment variables:

```bash
nano ./start_enpal.sh
```

#### Add the following environment variables to the script:

INFLUX_HOST="YOUR_INFLUX_HOST" (You can get this info from Enpal customer service)<br />
INFLUX_ORG_ID="YOUR_INFLUX_ORG_ID" (You can get this info from Enpal customer service)<br />
INFLUX_BUCKET="YOUR_INFLUX_BUCKET" (Default: solar)<br />
INFLUX_TOKEN="YOUR_INFLUX_TOKEN" (You can get this info from Enpal customer service)<br />
HTTP_HOST="0.0.0.0" (You can leave as is, if running in docker)<br />
HTTP_PORT="5000" (You can leave as is, if running in docker)<br />
BATTERY_STATE_OF_CHARGE_THRESHOLD="50" (This sets the battery percentage over which battery should supplement the solar surplus)<br />
BATTERY_WATT_ADDER="2000" (This sets the battery wattage with which battery should supplement the solar surplus)<br />

### Step 3: Build and Run the Docker Container (Optional)
Navigate to the cloned repository directory and build the Docker container:

```bash
cd enpal-link
docker build -t enpal-link .
docker run -d -p 5000:5000 --name enpal-link enpal-link
```

This will build and start the Docker container, running the Flask application that serves the solar power surplus data.

### Step 3: Use prebuilt docker image via docker-compose (Alternative)
```bash
./start_enpal.sh
```

### Step 4: Configure cFos Charging Manager
#### Access the cFos Charging Manager Configuration:

Navigate to the cFos Charging Manager web interface.
Go to the "Configuration" section.
Add the User-Defined Meter:

Select "User-defined meters" from the configuration options.
Click on "Add new meter" and choose "HTTP/JSON" as the meter type.
Upload the Enpal_Surplus_Meter.json file from this repo.

#### Set Up a Solar Surplus Charging Rule:

Go to the "Charging Rules" section in the cFos Charging Manager.
Add a new rule and select "Surplus Charging" as the mode.
Configure the rule to use the "Enpal Solar Surplus Meter" you just created.
Example Configuration for Surplus Charging Rule:

Meter: Enpal Solar Surplus Meter
Start Current: 6A (or your desired start current)
Stop Current: 0A (or your desired stop current)
Priority: High
Testing the Endpoint

### You can test the endpoint using the curl command:

```bash
curl http//:[INFLUX_HOST]:5000/solar_power_surplus
```

The expected response should reflect the calculated solar power surplus considering the battery status.

## Troubleshooting

Ensure the Flask application is running and check the logs for any errors.
```bash
docker logs -f enpal-link
```
Ensure the server running the Flask application is accessible from the device running the cFos Charging Manager.
Ensure the JSON response from the Flask endpoint matches the expected format.
If the script says "Organisation not found" or something like this, Enpal might have given you the ClientID instead of OrgID. You can find the correct ID in the InfluxDB.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

By following these steps, you can integrate the solar power surplus data from your Enpal InfluxDB with your cFos Charging Manager to enable surplus charging.
