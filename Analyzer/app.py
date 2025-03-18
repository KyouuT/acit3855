import connexion
from datetime import datetime
from connexion import NoContent
import uuid
import yaml
import logging
import logging.config
from pykafka import KafkaClient
import json
import os

SERVICE_NAME = "analyzer"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_CONFIG_PATH = os.path.join(BASE_DIR, "config", "prod", "log_conf.yml")
APP_CONFIG_PATH = os.path.join(BASE_DIR, "config", "prod", "analyzer_conf.yml")

# Load configurations
with open(APP_CONFIG_PATH, "r") as f:
    APP_CONFIG = yaml.safe_load(f.read())

with open(LOG_CONFIG_PATH, "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    
LOG_CONFIG["handlers"]["file"]["filename"] = f"../logs/{SERVICE_NAME}.log"
logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger("basicLogger")

# Kafka Setup (Reuse client instead of recreating for each request)
KAFKA_HOST = f"{APP_CONFIG['events']['hostname']}:{APP_CONFIG['events']['port']}"
KAFKA_TOPIC = APP_CONFIG["events"]["topic"]
client = KafkaClient(hosts=KAFKA_HOST)
topic = client.topics[KAFKA_TOPIC.encode('utf-8')]

def get_booking_events(index):
    """Retrieve a specific event from Kafka by index"""
    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
    
    event_counter = 0

    for msg in consumer:
        data = json.loads(msg.value.decode("utf-8"))
        if data["type"] == "ticket":
            if event_counter == index:
                return data, 200
            event_counter += 1

    logger.error(f"No ticket_event found at index {index}!")

    return {"message": f"No ticket_event found at index {index}!"}, 404


def get_booking_tickets(index):
    """Retrieve a specific ticket booking event from Kafka by index"""
    logger.info("Retrieving ticket booking event at index %d", index)
    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)

    ticket_counter = 0

    for msg in consumer:
        data = json.loads(msg.value.decode("utf-8"))
        if data["type"] == "event":
            if ticket_counter == index:
                return data, 200
            ticket_counter += 1

    logger.error(f"No event found at index {index}!")

    return {"message": f"No event found at index {index}!"}, 404


def get_stats():
    """Retrieve statistics for event1 and event2 counts"""
    logger.info("Retrieving stats")
    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
    
    num_event1 = 0
    num_event2 = 0

    for msg in consumer:
        data = json.loads(msg.value.decode("utf-8"))
        if data["type"] == "ticket":
            num_event1 += 1
        elif data["type"] == "event":
            num_event2 += 1

    return {"num_ticket": num_event1, "num_event": num_event2}, 200


# API Setup
app = connexion.FlaskApp(__name__, specification_dir='.')
app.add_api('aquarium.yml', strict_validation=True, validate_responses=True)

if __name__ == '__main__':
    app.run(port=8110, host="0.0.0.0")
