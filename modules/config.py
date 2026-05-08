import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/auto")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")

NOTION_TOKEN = os.getenv("NOTION_TOKEN")

def _format_notion_id(raw: str | None) -> str | None:
    """Normalise un UUID Notion en format 8-4-4-4-12 avec tirets."""
    if not raw:
        return raw
    clean = raw.replace("-", "")
    if len(clean) != 32:
        return raw
    return f"{clean[0:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:32]}"

NOTION_DATABASE_ID = _format_notion_id(os.getenv("NOTION_DATABASE_ID"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TARGET_SECTOR = os.getenv("TARGET_SECTOR", "healthtech,medtech,biotech").split(",")
TARGET_COUNTRY = os.getenv("TARGET_COUNTRY", "France")
TARGET_STAGE = os.getenv("TARGET_STAGE", "seed,series_a").split(",")
TARGET_ROLES = os.getenv("TARGET_ROLES", "CMO,Head of Marketing,Founder,CEO").split(",")
MY_SERVICE = os.getenv("MY_SERVICE", "3D medical animation delivered in 5 days for biotech fundraising and medical conferences")

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LEADS_CSV = DATA_DIR / "leads.csv"
ERRORS_LOG = DATA_DIR / "errors.log"

MAX_EMAILS_PER_DAY = 100
MAX_LINKEDIN_PER_MONTH = 130

NEGATIVE_KEYWORDS = [
    "pas intéressé", "not interested", "no thanks", "unsubscribe",
    "stop", "désabonner", "remove me", "désinscription", "ne pas contacter",
    "do not contact", "désinscrivez", "arrêtez"
]
