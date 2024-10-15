#!/bin/bash

HEALTH_URL="http://localhost:5000/health"
EMAIL="recipient@example.com"
RETRY_COUNT=5
SLEEP_INTERVAL=60
ENPAL_LINK_DIR="./enpal-link"
DOCKER_COMPOSE_FILE="$ENPAL_LINK_DIR/docker-compose.yaml"

log() {
    echo "$(date) - $1"
}

send_email() {
    local subject="$1"
    local message="$2"
    echo -e "Subject: $subject\n\n$message" | msmtp $EMAIL
}

restart_server() {
    if [ -d "$ENPAL_LINK_DIR" ] && [ -f "$DOCKER_COMPOSE_FILE" ]; then
        log "Restarting server using Docker Compose..."
        (cd "$ENPAL_LINK_DIR" && docker-compose down && docker-compose up -d)
        log "Server restart command executed."
    else
        log "Docker Compose file not found in $ENPAL_LINK_DIR. Cannot restart server."
        send_email "Server Restart Failed" "Docker Compose file not found in $ENPAL_LINK_DIR. Cannot restart server."
    fi
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
    send_email "Server Down Alert" "Server is down after $RETRY_COUNT attempts"
    restart_server
    return 1
}

check_enpal_data() {
    log "Checking Enpal data..."
    # Add logic to check if new values are received from enpal
    # This is a placeholder and should be replaced with actual implementation
    new_values_received=true

    if [ "$new_values_received" = false ]; then
        log "No new values received from enpal"
        send_email "Enpal Data Alert" "No new values received from enpal"
    else
        log "New values received from enpal"
    fi
}

check_health && check_enpal_data
log "Health check script completed"
