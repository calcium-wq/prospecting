"""
Notifications Telegram sur réponse positive d'un lead.
"""
import requests
from modules.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from modules.logger import log_error

def send_telegram(message: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] Token ou Chat ID manquant dans .env")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        log_error("telegram_notif", e, "send_telegram")
        return False

def notify_hot_lead(prenom: str, boite: str, email: str = ""):
    msg = f"🔥 Nouveau lead chaud : {prenom} de {boite} a répondu !"
    if email:
        msg += f"\n📧 {email}"
    success = send_telegram(msg)
    if success:
        print(f"[Telegram] Notification envoyée pour {prenom} ({boite})")
    return success

def test_connection() -> bool:
    """Test Telegram bot connectivity."""
    return send_telegram("✅ Bot Telegram connecté — pipeline prospection actif.")
