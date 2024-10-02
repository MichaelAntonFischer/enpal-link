#!/bin/bash

HEALTH_URL="http://localhost:5000/health"
EMAIL="your_email@example.com"
RETRY_COUNT=5
SLEEP_INTERVAL=60

log() {
    echo "$(date) - $1"
}

check_health() {
    log "Starting health check..."
    for ((i=1; i<=RETRY_COUNT; i++)); do
        log "Attempt $i: Checking health at $HEALTH_URL"
        response=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)
        log "Response code: $response"
        if [ "$response" -eq 200 ]; then
            log "Server is healthy"
            return 0
        fi
        log "Server not healthy, sleeping for $SLEEP_INTERVAL seconds"
        sleep $SLEEP_INTERVAL
    done
    log "Server is down after $RETRY_COUNT attempts"
    echo "Server is down after $RETRY_COUNT attempts" | mail -s "Server Down Alert" $EMAIL
    return 1
}

check_enpal_data() {
    log "Checking Enpal data..."
    # Add logic to check if new values are received from enpal
    # This is a placeholder and should be replaced with actual implementation
    new_values_received=true

    if [ "$new_values_received" = false ]; then
        log "No new values received from enpal"
        echo "No new values received from enpal" | mail -s "Enpal Data Alert" $EMAIL
    else
        log "New values received from enpal"
    fi
}

check_health && check_enpal_data
log "Health check script completed"