import os

PARNET_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PARNET_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
SQLITE_DIR = os.path.join(DATA_DIR, "sqlite_db")
os.makedirs(SQLITE_DIR, exist_ok=True)
SQLITE_FILEPATH = os.path.join(SQLITE_DIR, "thread_db.sqlite")