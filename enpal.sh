#!/bin/sh
# Zugangsdaten InfluxDB
INFLUX_API="${INFLUX_HOST}/api/v2/query?orgID=${INFLUX_ORG_ID}"
QUERY_RANGE_START="-5m"

# Function to output the whole bucket
output_whole_bucket() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting data query..." >> /var/log/enpal.log
  echo "INFLUX_API: ${INFLUX_API}"  # Debug statement
  echo "INFLUX_TOKEN: ${INFLUX_TOKEN}"  # Debug statement
  echo "INFLUX_BUCKET: ${INFLUX_BUCKET}"  # Debug statement
  echo "QUERY_RANGE_START: ${QUERY_RANGE_START}"  # Debug statement

  # Perform the curl request and capture the HTTP response headers
  response=$(curl -i -s -w "%{http_code}" "${INFLUX_API}" \
    --header "Authorization: Token ${INFLUX_TOKEN}" \
    --header "Accept: application/json" \
    --header "Content-type: application/vnd.flux" \
    --data-binary @- <<EOF
from(bucket: "${INFLUX_BUCKET}")
  |> range(start: ${QUERY_RANGE_START})
  |> filter(fn: (r) => r._measurement == "numberDataPoints")
  |> filter(fn: (r) => r._field == "Power.Production.Total" or r._field == "Energy.Production.Total.Day" or r._field == "Power.External.Total" or r._field == "Energy.External.Total.Out.Day" or r._field == "Energy.External.Total.In.Day" or r._field == "Energy.Consumption.Total.Day" or r._field == "Power.Consumption.Total" or r._field == "Power.Storage.Total" or r._field == "Energy.Storage.Total.In.Day" or r._field == "Energy.Storage.Total.Out.Day" or r._field == "Energy.Storage.Level" or r._field == "Percent.Storage.Level")
  |> keep(columns: ["_time", "_value", "_field"])
EOF
)
  status="$?"
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')

  echo "Curl status: $status"  # Debug statement
  echo "HTTP code: $http_code"  # Debug statement
  echo "Curl output: $body"  # Debug statement

  if [ "$status" -eq 0 ] && [ "$http_code" -eq 200 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Data query successful." >> /var/log/enpal.log
  else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Data query failed with status $status and HTTP code $http_code." >> /var/log/enpal.log
  fi
  echo "$body"
  return "$status"
}

# Debug: Print a message indicating the script has started
echo "Script started"

# Run the script continuously
while true; do
  output_whole_bucket
  sleep 60  # Wait for 1 minute before the next iteration
done