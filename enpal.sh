#!/bin/sh
# Zugangsdaten InfluxDB
INFLUX_API="http://${INFLUX_HOST}:8086/api/v2/query?orgID=${INFLUX_ORG_ID}"
QUERY_RANGE_START="-5m"

# Function to output the whole bucket
output_whole_bucket() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting data query..." >> /var/log/enpal.log
  echo "INFLUX_API: ${INFLUX_API}"  # Debug statement
  echo "INFLUX_TOKEN: ${INFLUX_TOKEN}"  # Debug statement
  echo "INFLUX_BUCKET: ${INFLUX_BUCKET}"  # Debug statement
  echo "INFLUX_ORG_ID: ${INFLUX_ORG_ID}"  # Debug statement
  echo "QUERY_RANGE_START: ${QUERY_RANGE_START}"  # Debug statement

  # Perform the curl request and capture the HTTP response headers and body separately
  response=$(curl -s -w "\n%{http_code}" -X POST "${INFLUX_API}" \
    --header "Authorization: Token ${INFLUX_TOKEN}" \
    --header "Accept: application/json" \
    --header "Content-type: application/json" \
    --data-binary @- <<EOF
{
  "type": "flux",
  "query": "from(bucket: \\"${INFLUX_BUCKET}\\") |> range(start: ${QUERY_RANGE_START}) |> last()",
  "orgID": "${INFLUX_ORG_ID}"
}
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

    # Parse the CSV response and format the output
    echo "$body" | tail -n +2 | while IFS=, read -r result table _start _stop _time _value _field _measurement unit; do
      echo "Time: $_time"
      echo "Value: $_value"
      echo "Field: $_field"
      echo "Measurement: $_measurement"
      echo "Unit: $unit"
      echo "-------------------"
    done
  else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Data query failed with status $status and HTTP code $http_code." >> /var/log/enpal.log
  fi
  return "$status"
}

# Debug: Print a message indicating the script has started
echo "Script started"

# Run the script continuously
while true; do
  output_whole_bucket
  sleep 60  # Wait for 1 minute before the next iteration
done

# Debug: Print a message indicating the script has started
echo "Script started"

# Run the script continuously
while true; do
  output_whole_bucket
  sleep 60  # Wait for 1 minute before the next iteration
done