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

  var=$(curl -f -s "${INFLUX_API}" \
    --header "Authorization: Token ${INFLUX_TOKEN}" \
    --header "Accept: application/json" \
    --header "Content-type: application/vnd.flux" \
    --data "from(bucket: \"$INFLUX_BUCKET\")
            |> range(start: $QUERY_RANGE_START)")
  status="$?"
  echo "Curl status: $status"  # Debug statement
  echo "Curl output: $var"  # Debug statement
  if [ "$status" -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Data query successful." >> /var/log/enpal.log
  else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Data query failed with status $status." >> /var/log/enpal.log
  fi
  echo "$var"
  return "$status"
}

# Debug: Print a message indicating the script has started
echo "Script started"

# Run the script continuously
while true; do
  output_whole_bucket
  sleep 60  # Wait for 1 minute before the next iteration
done