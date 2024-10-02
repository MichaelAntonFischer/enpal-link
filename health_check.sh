#!/bin/bash

HEALTH_URL="http://localhost:5000/health"
EMAIL="your_email@example.com"
RETRY_COUNT=5
SLEEP_INTERVAL=60

check_health() {
    for ((i=1; i<=RETRY_COUNT; i++)); do
        response=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)
        if [ "$response" -eq 200 ]; then
            echo "Server is healthy"
            return 0
        fi
        sleep $SLEEP_INTERVAL
    done
    echo "Server is down after $RETRY_COUNT attempts"
    echo "Server is down after $RETRY_COUNT attempts" | mail -s "Server Down Alert" $EMAIL
    return 1
}

check_enpal_data() {
    # Add logic to check if new values are received from enpal
    # This is a placeholder and should be replaced with actual implementation
    new_values_received=true

    if [ "$new_values_received" = false ]; then
        echo "No new values received from enpal"
        echo "No new values received from enpal" | mail -s "Enpal Data Alert" $EMAIL
    fi
}

check_health && check_enpal_data