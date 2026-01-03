# enpal-link MAP

This repository provides an integration between Enpal solar systems and the cFos Charging Manager.

## Architecture

The system consists of a Python Flask application (`enpal.py`) that:
1. Fetches data from an Enpal InfluxDB instance (running on the Enpal box).
2. Normalizes the data (Solar, Grid, Battery).
3. Serves the data via HTTP endpoints for cFos Charging Manager.

### Key Components

- **[enpal.py](file:///Users/michaelfischer/git/maf/enpal-link/enpal.py)**: The main application logic. It handles data fetching, caching, and the Flask API.
- **[Dockerfile](file:///Users/michaelfischer/git/maf/enpal-link/Dockerfile)** & **[docker-compose.yml](file:///Users/michaelfischer/git/maf/enpal-link/docker-compose.yml)**: Deployment configuration for containerized execution.
- **[.json meter files](file:///Users/michaelfischer/git/maf/enpal-link/)**: Configuration files for cFos Charging Manager to define how to parse the JSON responses from this service.

## Data Structure

The Enpal InfluxDB structure periodically changes. Current mapping:
- **Solar Production**: `Power.Production.Total`
- **Grid Export**: `Power.Grid.Export`
- **Grid Import**: `Power.Grid.Import` (Note: sometimes calculated from exports)
- **Battery Power**: `Power.Battery.Charge.Discharge` (Positive = Charge, Negative = Discharge)
- **Battery Level**: `Percent.Storage.Level`

## Deployment

Typically deployed on `citadel` (home automation server) using `docker-compose`. Configuration is managed via an `.env` file.
The Enpal box IP can change; the service cycles through a list of IPs defined in `INFLUX_HOSTS`.

## Workflows

- **/code-quality-checks**: Run on every commit.
- **/code-review**: Run for large changes.
