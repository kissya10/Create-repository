import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///orion.db")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
SUPERADMIN_ID = int(os.getenv("SUPERADMIN_ID", "1070889762"))
try:
    MAIN_CHAT_ID = int(os.getenv("MAIN_CHAT_ID")) if os.getenv("MAIN_CHAT_ID") else None
except ValueError:
    MAIN_CHAT_ID = None

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment or .env file")
