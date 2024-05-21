# Use a lightweight base image
FROM alpine:latest

# Install necessary packages
RUN apk add --no-cache bash curl jq

# Copy the script into the container
COPY enpal.sh /usr/local/bin/enpal.sh

# Make the script executable
RUN chmod +x /usr/local/bin/enpal.sh

# Expose port 502 for Modbus communication
EXPOSE 502

# Set the entrypoint to the script and redirect output to a log file
ENTRYPOINT ["/usr/local/bin/enpal.sh whole_bucket"]