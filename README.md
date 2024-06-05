# Enpal Solar Integration with cFos Charging Manager

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
This step is recommended to not overwrite your config when pulling new updates from the git repo.

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

### Step 3.1: Build and Run the Docker Container (Alternative to 3.2)
Navigate to the cloned repository directory and build the Docker container:

```bash
cd enpal-link
docker build -t enpal-link .
docker run -d -p 5000:5000 --name enpal-link enpal-link
```

This will build and start the Docker container, running the Flask application that serves the solar power surplus data.

### Step 3.2: Use prebuilt docker image via docker-compose (Alternative to 3.1)
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
Upload the Enpal_Solar_Generation.json (repeat with other desired meters) file from this repo.

#### Set Up a Solar Surplus Charging Rule:

Go to the "Charging Rules" section in the cFos Charging Manager.
Add a new rule and select "Surplus Charging" as the mode.
Configure the rule to use the "Enpal Solar Generation Meter" you just created.
Example Configuration for Surplus Charging Rule:

Meter: Enpal Solar Meter
Start Current: 6A (or your desired start current)
Stop Current: 0A (or your desired stop current)

Example Meters and Config:
![C5E933B3-BEF1-47C2-BEEC-2A6BCA6B790B](https://github.com/MichaelAntonFischer/enpal-link/assets/93607398/b6a0688f-075f-4ba8-8b62-b2e5247ece27)

![17C70A87-CC9D-4CAF-8BE7-8690A8F003A6](https://github.com/MichaelAntonFischer/enpal-link/assets/93607398/0f45e0ac-276c-40e2-ac22-56fe7732cd82)

![F8DCC261-719B-4233-B216-49EE3B75FBC3](https://github.com/MichaelAntonFischer/enpal-link/assets/93607398/0b213aea-8797-456a-a3b2-dce3fc153183)

![662C2D54-7295-43DB-93D7-34459769D416](https://github.com/MichaelAntonFischer/enpal-link/assets/93607398/d9c02426-fb3e-487f-ba8e-23739b82eb98)

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

IMPORTANT:
At the time of this writing the enpal box reboots during the night and doesn't react kindly to requests during boot. It is recommended to shutdown the virtual meters from 11p.m. to 5a.m.

```bash
crontab -e
```
Add the following lines:
```bash
0 5 * * * cd /home/[USER_NAME]/enpal-link && /usr/local/bin/docker-compose up -d >>>
0 22 * * * cd /home/[USER_NAME]/enpal-link && /usr/local/bin/docker-compose down >>>
```

Replace [USER_NAME] with your username. If you didn't clone the repo to home dir, please adjust the full path. Same for docker-compose.


## License

This project is licensed under the MIT License. See the LICENSE file for details.

By following these steps, you can integrate the solar power surplus data from your Enpal InfluxDB with your cFos Charging Manager to enable surplus charging.
