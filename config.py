import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Telegram Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_PROXY = os.getenv("TELEGRAM_PROXY", "").strip() or None

# Server configuration
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("PORT", os.getenv("WEB_PORT", "8080")))

# Base URL for the WebApp (e.g. https://yourdomain.com or ngrok URL)
WEB_APP_URL = os.getenv("WEB_APP_URL", f"http://localhost:{WEB_PORT}")

# Database path
DB_PATH = BASE_DIR / "casino.db"

# House edge & Game configs
HOUSE_EDGE = 0.10  # 10%
INITIAL_DEMO_BALANCE = 0  # 0 starting stars

# Required Telegram Channel for mandatory subscription
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "").strip() or None  # e.g. "@CosmoStars_Channel"
REQUIRED_CHANNEL_URL = os.getenv("REQUIRED_CHANNEL_URL", "https://t.me/Cosm0Casino_channel")
