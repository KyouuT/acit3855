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

# API Setup
app = connexion.FlaskApp(__name__, specification_dir='.')
app.add_api('consistency_check.yaml', base_path="/consistency", strict_validation=True, validate_responses=True)
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
APP_CONFIG_PATH = os.path.join(BASE_DIR, "config", "test", "consistency_conf.yml")
CHECK_PATH = os.path.join(BASE_DIR, "data", "consistency", "check.json")

SERVICE_NAME = "consistency_check"

# Load configurations
with open(APP_CONFIG_PATH, "r") as f:
    APP_CONFIG = yaml.safe_load(f.read())

with open(LOG_CONFIG_PATH, "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    
LOG_CONFIG["handlers"]["file"]["filename"] = f"../logs/{SERVICE_NAME}.log"
logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger("basicLogger")

def run_consistency_checks():
    logger.info("Starting consistency check...")
    start = time.time()

    # Fetch data from all services
    processing_counts = httpx.get(f"{APP_CONFIG['url']['processing']}")
    analyzer_counts = httpx.get(f"{APP_CONFIG['url']['analyzer_counts']}")
    analyzer_ids = httpx.get(f"{APP_CONFIG['url']['analyzer_ids']}")
    storage_counts = httpx.get(f"{APP_CONFIG['url']['storage_counts']}")
    storage_ids = httpx.get(f"{APP_CONFIG['url']['storage_ids']}")

    # Build dictionaries for comparison
    if analyzer_ids.status_code == 200:
        a_ids = analyzer_ids.json()
    if storage_ids.status_code == 200:
        s_ids = storage_ids.json()
    processing_data = processing_counts.json() if processing_counts.status_code == 200 else {"error": "unavailable"}
    analyzer_count_data = analyzer_counts.json() if analyzer_counts.status_code == 200 else {"error": "unavailable"}
    storage_count_data = storage_counts.json() if storage_counts.status_code == 200 else {"error": "unavailable"}
    
    analyzer_set = {(x["event_id"], x["trace_id"]) for x in a_ids}
    storage_set = {(x["event_id"], x["trace_id"]) for x in s_ids}

    check_file = "./data/consistency/check.json"
    default_check = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "counts": {
            "db": {},
            "queue": {},
            "processing": {}
        },
        "missing_in_db": [],
        "missing_in_queue": []
    }

    if os.path.exists(check_file):
        with open(check_file, 'r') as f:
            results = json.load(f)
    else:
        results = default_check

    missing_in_db = []
    for eid, tid in analyzer_set - storage_set:
        found = next((x for x in a_ids if x["event_id"] == eid and x["trace_id"] == tid), None)
        if found: missing_in_db.append(found)

    missing_in_queue = []
    for eid, tid in storage_set - analyzer_set:
        found = next((x for x in s_ids if x["event_id"] == eid and x["trace_id"] == tid), None)
        if found: missing_in_queue.append(found)

    results = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "counts": {
            "processing": processing_data,
            "queue": analyzer_count_data,
            "db": storage_count_data
        },
        "missing_in_db": missing_in_db,
        "missing_in_queue": missing_in_queue
    }

    
    with open(check_file, 'w') as file:
        json.dump(results, file, indent=4)

    processing_time_ms = int((time.time() - start) * 1000)
    logger.info(f"Consistency check completed | processing_time_ms={processing_time_ms} | "
             f"missing_in_db={len(missing_in_db)} | missing_in_queue={len(missing_in_queue)}")

    return jsonify({"processing_time_ms": processing_time_ms}), 200

def get_checks():
    logger.info("Request Received for consistency check")
    check_file = CHECK_PATH

    if os.path.exists(check_file):
        with open(check_file, 'r') as f:
            stats = json.load(f)
    else:
        logger.error("consistency check do not exist")
        return {"message": "consistency check do not exist"}, 404
    
    logger.debug(f"consistency check: {stats}")
    logger.info("Request for consistency check completed")

    return stats, 200

if __name__ == '__main__':
    app.run(port=8120, host="0.0.0.0")