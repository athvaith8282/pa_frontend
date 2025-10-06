import os

PARNET_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PARNET_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
SQLITE_DIR = os.path.join(DATA_DIR, "sqlite_db")
os.makedirs(SQLITE_DIR, exist_ok=True)
SQLITE_FILEPATH = os.path.join(SQLITE_DIR, "thread_db.sqlite")

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REFRESH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_TOKEN_URL = "https://oauth2.googleapis.com/revoke"

REDIRECT_URI = "http://localhost:8501/component/streamlit_oauth.authorize_button"
SCOPES= "https://www.googleapis.com/auth/gmail.modify"