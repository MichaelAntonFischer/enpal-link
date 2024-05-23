# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 502 available to the world outside this container
EXPOSE 5000

# Define environment variables
ENV INFLUX_API=""
ENV INFLUX_TOKEN=""
ENV INFLUX_BUCKET=""
ENV INFLUX_ORG_ID=""
ENV QUERY_RANGE_START="-5m"
ENV HTTP_HOST="0.0.0.0"
ENV HTTP_PORT="5000"
ENV BATTERY_STATE_OF_CHARGE_THRESHOLD="50"
ENV BATTERY_WATT_ADDER="2000"

# Run app.py when the container launches
CMD ["python", "./enpal.py"]