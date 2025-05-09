import requests, json, time, logging
from datetime import datetime
from flask import Flask, jsonify
import os
import yaml
import logging.config
import connexion
import httpx
from connexion.middleware import MiddlewarePosition 
from starlette.middleware.cors import CORSMiddleware 
from pykafka import KafkaClient
from pykafka.common import OffsetType

# API Setup
app = connexion.FlaskApp(__name__, specification_dir='.')
app.add_api('anomaly.yaml', base_path="/anomaly", strict_validation=True, validate_responses=True)
if "CORS_ALLOW_ALL" in os.environ and os.environ["CORS_ALLOW_ALL"] == "yes": 
    app.add_middleware( 
        CORSMiddleware, 
        position=MiddlewarePosition.BEFORE_EXCEPTION, 
        allow_origins=["*"], 
        allow_credentials=True, 
        allow_methods=["*"], 
        allow_headers=["*"], 
    )

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_CONFIG_PATH = os.path.join(BASE_DIR, "config", "test", "log_conf.yml")
APP_CONFIG_PATH = os.path.join(BASE_DIR, "config", "test", "anomaly_conf.yml")
ANOMALY_PATH = os.path.join(BASE_DIR, "data", "anomaly", "anomaly.json")

SERVICE_NAME = "anomaly_detector"

# Load configurations
with open(APP_CONFIG_PATH, "r") as f:
    APP_CONFIG = yaml.safe_load(f.read())

with open(LOG_CONFIG_PATH, "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    
LOG_CONFIG["handlers"]["file"]["filename"] = f"../logs/{SERVICE_NAME}.log"
logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger("basicLogger")

KAFKA_HOST = f"{APP_CONFIG['events']['hostname']}:{APP_CONFIG['events']['port']}"
KAFKA_TOPIC = APP_CONFIG["events"]["topic"]
client = KafkaClient(hosts=KAFKA_HOST)
topic = client.topics[KAFKA_TOPIC.encode('utf-8')]

def update_anomalies():
    logger.info("Starting anomaly detector...")
    start = time.time()
    ticket_threshold = APP_CONFIG["threshold"]["ticket"]
    event_threshold = APP_CONFIG["threshold"]["attraction"]

    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)

    anomaly_file = "./data/anomaly/anomaly.json"
    default_anomaly = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "UID": "",
        "TID": "",
        "Type": "",
        "Description": ""
    }

    if os.path.exists(anomaly_file):
        with open(anomaly_file, 'r') as f:
            results = json.load(f)
    else:
        results = default_anomaly

    for msg in consumer:
        msg_str = msg.value.decode('utf-8')
        msg = json.loads(msg_str)
        logger.info(f"Received Kafka message: {msg}")
        payload = msg["payload"]
        if msg["type"] == "ticket":
            if payload["num_people"] > ticket_threshold:
                logger.warning(f"Anomaly detected: {payload['num_people']} people in ticket {payload['ticket_id']}")
                results = {
                    "last_updated": datetime.utcnow().isoformat() + "Z",
                    "event_id": payload["ticket_id"],
                    "trace_id": payload["trace_id"],
                    "event_type": msg["type"],
                    "anomaly_type": "High People Count",
                    "description": f"Anomaly detected with {payload['num_people']} people."
                }
        elif msg["type"] == "event":
            if payload["num_people"] > event_threshold:
                logger.warning(f"Anomaly detected: {payload['num_people']} people in event {payload['attraction_id']}")
                results = {
                    "last_updated": datetime.utcnow().isoformat() + "Z",
                    "event_id": payload["attraction_id"],
                    "trace_id": payload["trace_id"],
                    "event_type": msg["type"],
                    "anomaly_type": "High People Count",
                    "description": f"Anomaly detected with {payload['num_people']} people."
                }

            with open(ANOMALY_PATH, 'w') as file:
                json.dump(results, file, indent=4)

        logger.info("Message processed and committed.")

    return jsonify({}), 200

def get_anomalies(event_type):
    logger.info("Request Received for listing anomalies")
    logger.debug(f"Request for anomalies of type: {event_type}")
    check_file = ANOMALY_PATH

    if os.path.exists(check_file):
        with open(check_file, 'r') as f:
            anomaly = json.load(f)
    else:
        logger.error("anomaly list do not exist")
        return {"message": "anomaly list do not exist"}, 404
    
    filter_anomaly = []
    if event_type is None:
        filter_anomaly = [anomaly]
    elif event_type == "ticket":
        filter_anomaly = [anomaly] if anomaly["event_type"] == "ticket" else []
    elif event_type == "event":
        filter_anomaly = [anomaly] if anomaly["event_type"] == "event" else []

    logger.debug(f"Filtered anomalies: {filter_anomaly}")
    logger.info(f"Anomalies of type {event_type}: {filter_anomaly}")

    return filter_anomaly, 200

if __name__ == '__main__':
    app.run(port=8130, host="0.0.0.0")