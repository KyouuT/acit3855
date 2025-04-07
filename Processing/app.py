import connexion
from datetime import datetime
from connexion import NoContent
import httpx
import uuid
import yaml
import logging
import logging.config
from apscheduler.schedulers.background import BackgroundScheduler
import os
import json
from connexion.middleware import MiddlewarePosition 
from starlette.middleware.cors import CORSMiddleware 

# API Setup
app = connexion.FlaskApp(__name__, specification_dir='.')
app.add_api('aquarium.yml', base_path="/processing", strict_validation=True, validate_responses=True)
if "CORS_ALLOW_ALL" in os.environ and os.environ["CORS_ALLOW_ALL"] == "yes": 
    app.add_middleware( 
        CORSMiddleware, 
        position=MiddlewarePosition.BEFORE_EXCEPTION, 
        allow_origins=["*"], 
        allow_credentials=True, 
        allow_methods=["*"], 
        allow_headers=["*"], 
    )

STORAGE_URL = "http://localhost:8090"

SERVICE_NAME = "processing"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_CONFIG_PATH = os.path.join(BASE_DIR, "config", "test", "log_conf.yml")
APP_CONFIG_PATH = os.path.join(BASE_DIR, "config", "test", "processing_conf.yml")
STATS_PATH = os.path.join(BASE_DIR, "data", "processing", "stats.json")

with open(APP_CONFIG_PATH, "r") as f:
    APP_CONFIG = yaml.safe_load(f.read())

with open(LOG_CONFIG_PATH, "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    
LOG_CONFIG["handlers"]["file"]["filename"] = f"../logs/{SERVICE_NAME}.log"
logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger("basicLogger")

# with open("log_conf.yml", "r") as f:
#     log_config = yaml.safe_load(f.read())
#     logging.config.dictConfig(log_config)

# def update_event_data(event_type, body):
#     logger = logging.getLogger("basicLogger")

#     timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
#     msg_data = f"ID: {body.get('id', 'N/A')}, People: {body.get('num_people', 'N/A')}"
#     trace_id = str(uuid.uuid4())
#     body["trace_id"] = trace_id

#     event = {
#         "received_timestamp": timestamp,
#         "msg_data": msg_data,
#         "trace_id": trace_id
#     }

#     logger.info(f"Received event {event_type} with a trace id of {trace_id}")

#     if event_type == "ticket":
#         # url = f"{STORAGE_URL}/buy/tickets"
#         url = app_config["ticket"]["url"]
#     elif event_type == "event":
#         # url = f"{STORAGE_URL}/booking/attraction"
#         url = app_config["attraction"]["url"]

#     response = httpx.post(url, json=body, headers={"Content-Type": "application/json"})
#     logger.info(f"Response for event {event_type} (id:{trace_id}) has status {response.status_code}")

#     return NoContent, response.status_code

# def post_booking_tickets(body):
#     return update_event_data("ticket", body)

# def post_booking_events(body):
#     return update_event_data("event", body)

def populate_stats():
    logger.info("Periodic processing has started")

    stats_file = "./data/processing/stats.json"
    default_stats = {
        "num_tickets_readings": 0,
        "max_people_tickets": 0,
        "num_event_readings": 0,
        "max_people_events": 0,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if os.path.exists(stats_file):
        with open(stats_file, 'r') as f:
            stats = json.load(f)
    else:
        stats = default_stats

    current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    last_updated=stats["last_updated"]

    try:
        response_tickets = httpx.get(APP_CONFIG["ticket"]["url"], params={"start_timestamp": last_updated, "end_timestamp": current_time})
        response_events = httpx.get(APP_CONFIG["attraction"]["url"], params={"start_timestamp": last_updated, "end_timestamp": current_time})

        if response_tickets.status_code == 200 and response_events.status_code == 200:
            tickets = response_tickets.json()
            events = response_events.json()

            logger.info(f"Received {len(tickets)} ticket events")
            logger.info(f"Received {len(events)} attraction events")
            print(tickets)
            print(events)

            stats["num_tickets_readings"] += len(tickets)
            stats["num_event_readings"] += len(events)
            if len(tickets) > 0:
                stats["max_people_tickets"] = max(stats["max_people_tickets"], max(ticket["num_people"] for ticket in tickets))

            if len(events) > 0:
                stats["max_people_events"] = max(stats["max_people_events"], max(event["num_people"] for event in events))

            stats["last_updated"] = current_time

            with open(stats_file, 'w') as file:
                json.dump(stats, file, indent=4)
        else:
            if response_tickets.status_code != 200:
                logger.error(f"Failed to retrieve ticket events: {response_tickets.status_code}")
            if response_events.status_code != 200:
                logger.error(f"Failed to retrieve attraction events: {response_events.status_code}")
    except Exception as e:
        logger.error(f"Error during periodic processing: {e}")

    logger.info("Periodic processing has ended")

def get_stats():
    logger.info("Request Received for statistics")
    stats_file = STATS_PATH

    if os.path.exists(stats_file):
        with open(stats_file, 'r') as f:
            stats = json.load(f)
    else:
        logger.error("Statistics do not exist")
        return {"message": "Statistics do not exist"}, 404
    
    logger.debug(f"Statistics: {stats}")
    logger.info("Request for statistics completed")

    return stats, 200

def init_scheduler():
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats, 'interval', seconds=APP_CONFIG['scheduler']['interval'])
    sched.start()

if __name__ == '__main__':
    init_scheduler()
    app.run(port=8100, host="0.0.0.0")