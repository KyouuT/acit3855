from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker
import yaml
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_CONFIG_PATH = os.path.join(BASE_DIR, "config", "test", "storage_conf.yml")

with open(APP_CONFIG_PATH, "r") as f:
    APP_CONFIG = yaml.safe_load(f.read())

data=APP_CONFIG["datastore"]

engine = create_engine(f'mysql://{data["user"]}:{data["password"]}@{data["hostname"]}/{data["db"]}') 

def make_session(): 
    return sessionmaker(bind=engine)() 