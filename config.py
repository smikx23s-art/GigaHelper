import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

GIGAPUB_TOKEN = os.getenv("GIGAPUB_TOKEN")
PARTNER_ID = os.getenv("PARTNER_ID", "100")
PROJECT_ID = int(os.getenv("PROJECT_ID"))

# Пороги для алерта об аномалии CTR/CPM (в процентах)
CPM_ALERT_THRESHOLD = float(os.getenv("CPM_ALERT_THRESHOLD", "15"))
CTR_ALERT_THRESHOLD = float(os.getenv("CTR_ALERT_THRESHOLD", "20"))

# AI-советник (Google Gemini — бесплатный API-ключ на aistudio.google.com/apikey)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
