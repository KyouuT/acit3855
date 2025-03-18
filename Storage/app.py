import connexion
import json
from datetime import datetime
from connexion import NoContent
import functools
from events import Base, TicketBooking, EventBooking, create as create_tables, drop as drop_tables
from storage import make_session
import yaml
import logging
import logging.config
from sqlalchemy import select
from pykafka import KafkaClient
from pykafka.common import OffsetType
from threading import Thread
import json
import os

MAX_EVENTS = 5
EVENT_FILE = 'events.json'

SERVICE_NAME = "storage"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_CONFIG_PATH = os.path.join(BASE_DIR, "config", "test", "log_conf.yml")
APP_CONFIG_PATH = os.path.join(BASE_DIR, "config", "prod", "storage_conf.yml")

with open(LOG_CONFIG_PATH, 'r') as f:
    LOG_CONFIG = yaml.safe_load(f.read())

with open(APP_CONFIG_PATH, "r") as f:
    APP_CONFIG = yaml.safe_load(f.read())
    
LOG_CONFIG["handlers"]["file"]["filename"] = f"../logs/{SERVICE_NAME}.log"
logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger("basicLogger")

def initialize_event_file():
    data = {
        "ticket_count": 0,
        "event_count": 0,
        "ticket_events": [],
        "event_events": []
    }
    with open(EVENT_FILE, 'w') as file:
        json.dump(data, file, indent=4)

def use_db_session(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        session = make_session()
        try:
            return func(session, *args, **kwargs)
        finally:
            session.close()
    return wrapper

@use_db_session
def update_event_data(session, event_type, body):
    timestamp = datetime.now()

    if event_type == "ticket":
        event = TicketBooking(
            ticket_id=body.get('ticket_id'),
            num_people=body.get('num_people'),
            date=datetime.strptime(body.get('date'), '%Y-%m-%d %H:%M:%S'),
            attraction=body.get('attraction'),
            date_created=timestamp,
            trace_id=body.get('trace_id')
        )
        data_key = "ticket_events"
        count_key = "ticket_count"
    elif event_type == "event":
        event = EventBooking(
            attraction_id=body.get('attraction_id'),
            num_people=body.get('num_people'),
            start_date=datetime.strptime(body.get('start_date'), '%Y-%m-%d %H:%M:%S'),
            end_date=datetime.strptime(body.get('end_date'), '%Y-%m-%d %H:%M:%S'),
            date_created=timestamp,
            trace_id=body.get('trace_id')
        )
        data_key = "event_events"
        count_key = "event_count"

    session.add(event)
    session.commit()

    trace_id = body.get('trace_id')
    logger.debug(f"Stored event {event_type} with a trace id of {trace_id}")

@use_db_session
def get_booking_tickets(session, start_timestamp:str, end_timestamp:str):
    start = datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M:%S")
    end = datetime.strptime(end_timestamp, "%Y-%m-%d %H:%M:%S") 
    statement = select(TicketBooking).where(
        TicketBooking.date_created >= start,
        TicketBooking.date_created < end
    ) 
    results = [ 
        result.to_dict() 
        for result in session.execute(statement).scalars().all() 
    ] 
    # logger.info("Found %d ticket bookings (start: %s, end: %s)", len(results),start,end)
    return results 

@use_db_session
def get_booking_events(session, start_timestamp:str, end_timestamp:str):
    start = datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M:%S") 
    end = datetime.strptime(end_timestamp, "%Y-%m-%d %H:%M:%S") 
    statement = select(EventBooking).where(
        EventBooking.date_created >= start,
        EventBooking.date_created < end
        ) 
    results = [ 
        result.to_dict() 
        for result in session.execute(statement).scalars().all() 
    ] 
    # logger.info("Found %d event bookings (start: %s, end: %s)", len(results),start,end)
    return results

def process_messages():
    KAFKA_HOST = f"{APP_CONFIG['events']['hostname']}:{APP_CONFIG['events']['port']}"
    client = KafkaClient(hosts=KAFKA_HOST)
    topic = client.topics[str.encode(f"{APP_CONFIG['events']['topic']}")]

    logger.info("Starting Kafka consumer...")

    consumer = topic.get_simple_consumer(
        consumer_group=b'event_group', 
        reset_offset_on_start=False,
        auto_offset_reset=OffsetType.LATEST
    )

    for msg in consumer:
        msg_str = msg.value.decode('utf-8')
        msg = json.loads(msg_str)
        logger.info(f"Received Kafka message: {msg}")
        payload = msg["payload"]

        if msg["type"] == "ticket":
            logger.info("Processing ticket event...")
            update_event_data("ticket", payload)
        elif msg["type"] == "event":
            logger.info("Processing event booking...")
            update_event_data("event", payload)

        consumer.commit_offsets() 
        logger.info("Message processed and committed.")

# @use_db_session
# def post_booking_tickets(session, body):
#     update_event_data("ticket", body)
#     return body, 200

# @use_db_session
# def post_booking_events(session, body):
#     update_event_data("event", body)
#     return NoContent, 201

def setup_kafka_thread(): 
    logger.info("Starting Kafka thread...")
    t1 = Thread(target=process_messages) 
    t1.setDaemon(True) 
    t1.start()

app = connexion.FlaskApp(__name__, specification_dir='.')
app.add_api('aquarium.yml', strict_validation=True, validate_responses=True)

if __name__ == '__main__':
    create_tables()
    setup_kafka_thread()
    app.run(port=8090, host="0.0.0.0")