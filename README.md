# homevolt
# Homevolt MQTT & Prometheus Exporter

This project provides a small Python service to fetch state data from a **Homevolt** residential grid battery and publish it to **MQTT** and **Prometheus**. 

> ℹ️ The Homevolt must have its **local management web server enabled** for this to work. If you’re unsure, let me know and I can provide more details about the setup.

## Purpose

- Polls the Homevolt battery via its local HTTP API.
- Extracts relevant metrics (e.g., SoC, power, frequency, energy produced/consumed, cycle count).
- Publishes the raw JSON and extracted metrics to **MQTT** topics.
- Exposes metrics via an HTTP endpoint (`/metrics`) for **Prometheus** scraping.

This makes it easy to integrate Homevolt telemetry into home automation systems, dashboards, and monitoring tools.

## Configuration

All configuration is done via a `config.json` file placed next to the script. Example:

```json
{
  "homevolt_url": "http://192.168.1.50/data.json",
  "update_interval": 5,
  "enable_mqtt": true,
  "enable_prometheus": true,
  "mqtt_broker": "localhost",
  "mqtt_port": 1883,
  "mqtt_topics": {
    "raw": "homevolt/data/raw",
    "soc_avg": "homevolt/data/soc_avg",
    "power_output": "homevolt/data/power_output",
    "grid_power": "homevolt/data/grid_power",
    "solar_power": "homevolt/data/solar_power",
    "load_power": "homevolt/data/load_power",
    "frequency": "homevolt/data/frequency",
    "energy_produced": "homevolt/data/energy_produced",
    "energy_consumed": "homevolt/data/energy_consumed",
    "cycle_count": "homevolt/data/cycle_count"
  }
}
```

## Building the Docker Image

Build the image locally with:

```bash
docker build -t homevolt-mqtt-prom .
```

## Running the Container

Run with MQTT and Prometheus enabled:

```bash
docker run -d \
  --name homevolt-mqtt-prom \
  -p 8000:8000 \
  -v $(pwd)/config.json:/app/config.json:ro \
  homevolt-mqtt-prom
```

- Port `8000` is used for Prometheus scraping (`/metrics`).
- MQTT topics will be published to the configured broker if `enable_mqtt` is `true`.
- Both MQTT and Prometheus can be disabled via `config.json`.

## Prometheus Configuration

Add the following scrape job to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'homevolt'
    metrics_path: /metrics
    static_configs:
      - targets: ['localhost:8000']
```

## Notes

- This project is tailored for **Homevolt** residential batteries.
- It requires the **local HTTP API** to be enabled on the battery.
