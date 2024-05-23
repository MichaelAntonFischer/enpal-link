
#Enpal Solar Surplus Integration with cFos Charging Manager
This repository contains a Python script that fetches solar power surplus data from an Enpal InfluxDB and serves it via an HTTP endpoint. This data can be used to integrate with the cFos Charging Manager to enable surplus charging.
##Prerequisites
Python 3.11 or later
Docker
Git
Raspberry Pi (or any other Linux-based system)
##Installation
Step 1: Clone the Repository
Clone this repository to your local machine:
surplus
Step 2: Copy and Configure the Start Script
Copy the start_enpal.sh script to a directory above the cloned repository:
sh
Make the script executable:
sh
Edit the start_enpal.sh script to add the necessary environment variables:
sh
Add the following environment variables to the script:
build
Step 3: Build and Run the Docker Container
Navigate back to the cloned repository directory and build the Docker container:
build
This will build and start the Docker container, running the Flask application that serves the solar power surplus data.
Step 4: Configure cFos Charging Manager
1. Access the cFos Charging Manager Configuration:
Navigate to the cFos Charging Manager web interface.
Go to the "Configuration" section.
2. Add the User-Defined Meter:
Select "User-defined meters" from the configuration options.
Click on "Add new meter" and choose "HTTP/JSON" as the meter type.
Upload the Enpal_Surplus_Meter.json file you created.
3. Set Up a Solar Surplus Charging Rule:
Go to the "Charging Rules" section in the cFos Charging Manager.
Add a new rule and select "Surplus Charging" as the mode.
Configure the rule to use the "Enpal Solar Surplus Meter" you just created.
Example Configuration for Surplus Charging Rule:
Meter: Enpal Solar Surplus Meter
Start Current: 6A (or your desired start current)
Stop Current: 0A (or your desired stop current)
Priority: High
##Testing the Endpoint
You can test the endpoint using the curl command:
curl http://yourip:5000/solar_power_surplus
The expected response should reflect the calculated solar power surplus considering the battery status.
##Troubleshooting
Ensure the Flask application is running and check the logs for any errors.
Ensure the server running the Flask application is accessible from the device running the cFos Charging Manager.
Ensure the JSON response from the Flask endpoint matches the expected format.
##License
This project is licensed under the MIT License. See the LICENSE file for details.
---
By following these steps, you can integrate the solar power surplus data from your Enpal InfluxDB with your cFos Charging Manager to enable surplus charging.


