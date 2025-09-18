import time
import json
import requests
import paho.mqtt.client as mqtt
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# Load config from file
with open("config.json", "r") as f:
    config = json.load(f)

HOMEVOLT_URL = config.get("homevolt_url", "http://example.com/data.json")
ENABLE_MQTT = config.get("enable_mqtt", True)
ENABLE_PROMETHEUS = config.get("enable_prometheus", True)
MQTT_BROKER = config.get("mqtt_broker", "localhost")
MQTT_PORT = config.get("mqtt_port", 1883)
UPDATE_INTERVAL = config.get("update_interval", 5)
MQTT_TOPICS = config.get("mqtt_topics", {})

MQTT_TOPIC_RAW = MQTT_TOPICS.get("raw", "homevolt/data/raw")
MQTT_TOPIC_SOC = MQTT_TOPICS.get("soc_avg", "homevolt/data/soc_avg")
MQTT_TOPIC_POWER = MQTT_TOPICS.get("power_output", "homevolt/data/power_output")
MQTT_TOPIC_GRID = MQTT_TOPICS.get("grid_power", "homevolt/data/grid_power")
MQTT_TOPIC_SOLAR = MQTT_TOPICS.get("solar_power", "homevolt/data/solar_power")
MQTT_TOPIC_LOAD = MQTT_TOPICS.get("load_power", "homevolt/data/load_power")
MQTT_TOPIC_FREQUENCY = MQTT_TOPICS.get("frequency", "homevolt/data/frequency")
MQTT_TOPIC_ENERGY_PRODUCED = MQTT_TOPICS.get("energy_produced", "homevolt/data/energy_produced")
MQTT_TOPIC_ENERGY_CONSUMED = MQTT_TOPICS.get("energy_consumed", "homevolt/data/energy_consumed")
MQTT_TOPIC_CYCLE_COUNT = MQTT_TOPICS.get("cycle_count", "homevolt/data/cycle_count")

# Initialize MQTT client if enabled
mqtt_client = None
if ENABLE_MQTT:
    mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")
        exit(1)

metrics = {}

def extract_relevant_metrics(data):
    try:
        ems = data.get("ems", [])[0]
        ems_data = ems.get("ems_data", {})
        sensors = data.get("sensors", [])
        bms_data = ems.get("bms_data", [])

        avg_cycle_count = sum(bms.get("cycle_count", 0) for bms in bms_data) / max(len(bms_data), 1)

        extracted = {
            "soc_avg": ems_data.get("soc_avg", 0) / 100,
            "power_output": ems_data.get("power", 0),
            "grid_power": next((s.get("total_power", 0) for s in sensors if s.get("type") == "grid"), 0),
            "solar_power": next((s.get("total_power", 0) for s in sensors if s.get("type") == "solar"), 0),
            "load_power": next((s.get("total_power", 0) for s in sensors if s.get("type") == "load"), 0),
            "frequency": ems_data.get("frequency", 0) / 1000,
            "energy_produced": ems_data.get("energy_produced", 0),
            "energy_consumed": ems_data.get("energy_consumed", 0),
            "cycle_count": avg_cycle_count
        }

        global metrics
        metrics = extracted
        return extracted
    except Exception as e:
        print(f"Error extracting metrics: {e}")
        return {}

def fetch_and_publish():
    try:
        response = requests.get(HOMEVOLT_URL)
        response.raise_for_status()
        json_data = response.json()

        extracted_data = extract_relevant_metrics(json_data)

        if ENABLE_MQTT and mqtt_client:
            mqtt_client.publish(MQTT_TOPIC_RAW, json.dumps(json_data))
            mqtt_client.publish(MQTT_TOPIC_SOC, json.dumps(extracted_data["soc_avg"]))
            mqtt_client.publish(MQTT_TOPIC_POWER, json.dumps(extracted_data["power_output"]))
            mqtt_client.publish(MQTT_TOPIC_GRID, json.dumps(extracted_data["grid_power"]))
            mqtt_client.publish(MQTT_TOPIC_SOLAR, json.dumps(extracted_data["solar_power"]))
            mqtt_client.publish(MQTT_TOPIC_LOAD, json.dumps(extracted_data["load_power"]))
            mqtt_client.publish(MQTT_TOPIC_FREQUENCY, json.dumps(extracted_data["frequency"]))
            mqtt_client.publish(MQTT_TOPIC_ENERGY_PRODUCED, json.dumps(extracted_data["energy_produced"]))
            mqtt_client.publish(MQTT_TOPIC_ENERGY_CONSUMED, json.dumps(extracted_data["energy_consumed"]))
            mqtt_client.publish(MQTT_TOPIC_CYCLE_COUNT, json.dumps(extracted_data["cycle_count"]))

            print("Published extracted metrics")
    except requests.RequestException as e:
        print(f"HTTP Request failed: {e}")
    except json.JSONDecodeError:
        print("Failed to decode JSON response")

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            response = ""
            for key, value in metrics.items():
                response += f"{key} {value}\n"
            self.wfile.write(response.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def run_http_server():
    server = HTTPServer(('0.0.0.0', 8000), MetricsHandler)
    print("Starting HTTP server on port 8000")
    server.serve_forever()

if __name__ == "__main__":
    if ENABLE_PROMETHEUS:
        server_thread = threading.Thread(target=run_http_server)
        server_thread.daemon = True
        server_thread.start()

    while True:
        fetch_and_publish()
        time.sleep(UPDATE_INTERVAL)
