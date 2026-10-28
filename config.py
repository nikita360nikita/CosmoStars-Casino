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

# Base URL for the WebApp
DEFAULT_WEB_APP_URL = "https://bot-1793026316-6064-anki.bothost.tech"
render_external = os.getenv("RENDER_EXTERNAL_URL", "").strip()
env_web_app = os.getenv("WEB_APP_URL", "").strip()

if env_web_app and "localhost" not in env_web_app:
    WEB_APP_URL = env_web_app
elif render_external:
    WEB_APP_URL = render_external
else:
    WEB_APP_URL = DEFAULT_WEB_APP_URL

# Database path
DB_PATH = BASE_DIR / "casino.db"

# Admin & Support configuration
ADMIN_USERNAMES = [
    u.strip().lstrip("@").lower()
    for u in os.getenv("ADMIN_USERNAMES", "ankisolom,child_trauma").split(",")
    if u.strip()
]
ADMIN_USERNAME = ADMIN_USERNAMES[0] if ADMIN_USERNAMES else "ankisolom"
ADMIN_SUPPORT_URL = f"https://t.me/{ADMIN_USERNAME}"
ADMIN_CHAT_IDS = [
    int(cid.strip())
    for cid in os.getenv("ADMIN_CHAT_IDS", "6200135659").split(",")
    if cid.strip().isdigit()
]

# House edge & Game configs
HOUSE_EDGE = 0.10  # 10%
INITIAL_DEMO_BALANCE = 0  # 0 starting stars

# Required Telegram Channel for mandatory subscription
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "").strip() or None  # e.g. "@CosmoStars_Channel"
REQUIRED_CHANNEL_URL = os.getenv("REQUIRED_CHANNEL_URL", "https://t.me/Cosm0Casino_channel")
