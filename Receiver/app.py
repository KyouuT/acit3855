import connexion
from datetime import datetime
from connexion import NoContent
import httpx
import uuid
import yaml
import logging
import logging.config
from pykafka import KafkaClient
import json
import os

app = connexion.FlaskApp(__name__, specification_dir='.')
if "CORS_ALLOW_ALL" in os.environ and os.environ["CORS_ALLOW_ALL"] == "yes": 
    app.add_middleware(...) # Set up '*' CORS headers when `CORS_ALLOW_ALL` is 'yes'
app.add_api('aquarium.yml', base_path="/receiver", strict_validation=True, validate_responses=True)

STORAGE_URL = "http://localhost:8090"

SERVICE_NAME = "receiver"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_CONFIG_PATH = os.path.join(BASE_DIR, "config", "test", "log_conf.yml")
APP_CONFIG_PATH = os.path.join(BASE_DIR, "config", "test", "receiver_conf.yml")

with open(APP_CONFIG_PATH, "r") as f:
    APP_CONFIG = yaml.safe_load(f.read())

with open(LOG_CONFIG_PATH, "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    
LOG_CONFIG["handlers"]["file"]["filename"] = f"../logs/{SERVICE_NAME}.log"
logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger("basicLogger")

KAFKA_HOST = f"{APP_CONFIG['events']['hostname']}:{APP_CONFIG['events']['port']}"
KAFKA_TOPIC = APP_CONFIG['events']['topic'].encode('utf-8')
client = KafkaClient(hosts=KAFKA_HOST)
topic = client.topics[KAFKA_TOPIC]
producer = topic.get_sync_producer()

def produce_kafka_event(event_type, body):
    trace_id = str(uuid.uuid4())
    body["trace_id"] = trace_id

    msg = {
        "type": event_type,
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "payload": body
    }

    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))
    logger.info(f"Produced Kafka event {event_type} with trace ID: {trace_id}")

    return NoContent, 201

def update_event_data(event_type, body):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msg_data = f"ID: {body.get('id', 'N/A')}, People: {body.get('num_people', 'N/A')}"
    trace_id = str(uuid.uuid4())
    body["trace_id"] = trace_id

    event = {
        "received_timestamp": timestamp,
        "msg_data": msg_data,
        "trace_id": trace_id
    }

    logger.info(f"Received event {event_type} with a trace id of {trace_id}")

    if event_type == "ticket":
        # url = f"{STORAGE_URL}/buy/tickets"
        url = APP_CONFIG["ticket"]["url"]
    elif event_type == "event":
        # url = f"{STORAGE_URL}/booking/attraction"
        url = APP_CONFIG["attraction"]["url"]

    response = httpx.post(url, json=body, headers={"Content-Type": "application/json"})
    logger.info(f"Response for event {event_type} (id:{trace_id}) has status {response.status_code}")

    return NoContent, response.status_code

def post_booking_tickets(body):
    # return update_event_data("ticket", body)
    return produce_kafka_event("ticket", body)


def post_booking_events(body):
    # return update_event_data("event", body)
    return produce_kafka_event("event", body)


if __name__ == '__main__':
    app.run(port=8080, host="0.0.0.0")