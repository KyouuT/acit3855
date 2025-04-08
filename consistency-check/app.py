import requests, json, time, logging
from datetime import datetime
from flask import Flask, jsonify
import os
import yaml
import logging.config
import connexion
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

def fetch_json(url):
    res = requests.get(url)
    res.raise_for_status()
    return res.json()

def run_check():
    logger.info("Starting consistency check...")
    start = time.time()

    # Fetch data from all services
    processing_counts = fetch_json(f"{APP_CONFIG['url']['processing']}")
    analyzer_counts = fetch_json(f"{APP_CONFIG['url']['analyzer_counts']}")
    analyzer_ids = fetch_json(f"{APP_CONFIG['url']['analyzer_ids']}")
    storage_counts = fetch_json(f"{APP_CONFIG['url']['storage_counts']}")
    storage_ids = fetch_json(f"{APP_CONFIG['url']['storage_ids']}")

    # Build dictionaries for comparison
    analyzer_set = {(x["event_id"], x["trace_id"]) for x in analyzer_ids}
    storage_set = {(x["event_id"], x["trace_id"]) for x in storage_ids}

    check_file = "./data/consistency/check.json"

    missing_in_db = []
    for eid, tid in analyzer_set - storage_set:
        found = next((x for x in analyzer_ids if x["event_id"] == eid and x["trace_id"] == tid), None)
        if found: missing_in_db.append(found)

    missing_in_queue = []
    for eid, tid in storage_set - analyzer_set:
        found = next((x for x in storage_ids if x["event_id"] == eid and x["trace_id"] == tid), None)
        if found: missing_in_queue.append(found)

    results = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "counts": {
            "processing": processing_counts,
            "queue": analyzer_counts,
            "db": storage_counts
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

def get_last_check():
    try:
        with open(CHECK_PATH, "r") as f:
            return jsonify(json.load(f)), 200
    except FileNotFoundError:
        return jsonify({"message": "No checks have been run yet"}), 404

if __name__ == '__main__':
    app.run(port=8120, host="0.0.0.0")