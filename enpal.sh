#!/bin/sh
# Zugangsdaten InfluxDB
# @ see https://github.com/weldan84/enpal-influx-evcc
INFLUX_HOST="YOUR_INFLUX_HOST"
INFLUX_ORG_ID="YOUR_INFLUX_ORG_ID"
INFLUX_BUCKET="YOUR_INFLUX_BUCKET"
INFLUX_TOKEN="YOUR_INFLUX_TOKEN"
INFLUX_API="${INFLUX_HOST}/api/v2/query?orgID=${INFLUX_ORG_ID}"
QUERY_RANGE_START="-5m"

case $1 in
# Output the whole bucket
whole_bucket)
  var=$(curl -f -s "${INFLUX_API}" \
    --header "Authorization: Token ${INFLUX_TOKEN}" \
    --header "Accept: application/json" \
    --header "Content-type: application/vnd.flux" \
    --data "from(bucket: \"$INFLUX_BUCKET\")
            |> range(start: $QUERY_RANGE_START)")
  status="$?"
  echo "$var"
  exit "$status"
  ;;
# Other cases remain unchanged
# Gesamtverbrauch
consumption)
  var=$(curl -f -s "${INFLUX_API}" \
    --header "Authorization: Token ${INFLUX_TOKEN}" \
    --header "Accept: application/json" \
    --header "Content-type: application/vnd.flux" \
    --data "from(bucket: \"$INFLUX_BUCKET\")
            |> range(start: $QUERY_RANGE_START)
            |> filter(fn: (r) => r._measurement == \"Gesamtleistung\")
            |> filter(fn: (r) => r._field == \"Verbrauch\")
            |> keep(columns: [\"_value\"])
            |> last()")
  status="$?"
  var="${var##*,}"
  ;;
# Netzbezug/Einspeisung Enpal InfluxDB (Errechneter Wert)
grid_enpal)
  pv=$(enpal pv)
  consumption=$(enpal consumption)
  battery=$(enpal battery)
  # shellcheck disable=SC2004
  echo $(($consumption - $pv - $battery))
  exit 0
  ;;
# Netzbezug/Einspeisung Powerfox Poweropti (Tatsächlicher Wert)
grid_powerfox)
  # Um das API-Aufrufkontingent nicht zu überschreiten wird hier 3 Sekunden lang pausiert! (Maximal zugelassen 1 pro 3s)
  sleep 3
  var=$(curl -f -s -G "https://backend.powerfox.energy/api/2.0/my/$POWERFOX_DEVICE_ID/current" \
    -u "$POWERFOX_USERNAME:$POWERFOX_PASSWORD")
  status="$?"
  var=$(echo "$var" | jq '.Watt // empty')
  if [ "$var" = "empty" ]; then
    echo >&2 "Der Poweropti liefert keine aktuellen Werte. Hier wird dir geholfen https://poweropti.powerfox.energy/faq/"
    exit 1
  fi
  echo "$var"
  exit "$status"
  ;;
# Aktuelle Solarproduktion / DC-Erzeugungsleistung
pv)
  var=$(curl -f -s "${INFLUX_API}" \
    --header "Authorization: Token ${INFLUX_TOKEN}" \
    --header "Accept: application/json" \
    --header "Content-type: application/vnd.flux" \
    --data "from(bucket: \"$INFLUX_BUCKET\")
            |> range(start: $QUERY_RANGE_START)
            |> filter(fn: (r) => r._measurement == \"LeistungDc\")
            |> filter(fn: (r) => r._field == \"Total\")
            |> keep(columns: [\"_value\"])
            |> last()")
  status="$?"
  var="${var##*,}"
  ;;
# Kumulierte Solarproduktion / DC-Erzeugungsleistung
energy)
  var=$(curl -f -s "${INFLUX_API}" \
    --header "Authorization: Token ${INFLUX_TOKEN}" \
    --header "Accept: application/json" \
    --header "Content-type: application/vnd.flux" \
    --data "from(bucket: \"$INFLUX_BUCKET\")
            |> range(start: $QUERY_RANGE_START)
            |> filter(fn: (r) => r._measurement == \"EnergieDc\")
            |> filter(fn: (r) => r._field == \"Total\")
            |> keep(columns: [\"_value\"])
            |> last()")
  status="$?"
  var="${var##*,}"
  ;;
# Aktueller Ladezustand der Batterie
battery)
  var=$(curl -f -s "${INFLUX_API}" \
    --header "Authorization: Token ${INFLUX_TOKEN}" \
    --header "Accept: application/json" \
    --header "Content-type: application/vnd.flux" \
    --data "from(bucket: \"$INFLUX_BUCKET\")
            |> range(start: $QUERY_RANGE_START)
            |> filter(fn: (r) => r._measurement == \"Batterie\")
            |> filter(fn: (r) => r._field == \"Ladezustand\")
            |> keep(columns: [\"_value\"])
            |> last()")
  status="$?"
  var="${var##*,}"
  ;;
*)
  echo "Usage: $0 {whole_bucket|consumption|grid_enpal|grid_powerfox|pv|energy|battery}"
  exit 1
  ;;
esac

echo "$var"
exit "$status"