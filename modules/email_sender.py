# RÈGLES ABSOLUES — NE JAMAIS VIOLER
# 1. Format : toujours MIMEText(body, 'plain') — jamais HTML
# 2. Fautes de grammaire interdites — vérifier conjugaisons
# 3. Chaque email DOIT contenir une info spécifique à la boîte
# 4. CTA condescendante interdite ("Avez-vous déjà envisagé")
# 5. Question finale = toujours vers un call 15min
# 6. Signature toujours "— Edgar" jamais autre chose
# 7. Jamais de question ouverte descriptive en finale

"""
Envoi d'emails via Gmail SMTP + App Password.
Gère initial + relances J+3/J+7/J+14.
"""
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, timedelta
from modules.config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, MAX_EMAILS_PER_DAY
from modules.leads_csv import count_emails_sent_today, update_lead
from modules.logger import log_error

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

def _send_smtp(to: str, subject: str, body: str) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = to
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to, msg.as_string())
        return True
    except Exception as e:
        log_error("email_sender", e, f"smtp to={to}")
        return False

def _build_initial_email(prenom: str, boite: str, hook: str) -> tuple[str, str]:
    subject = f"Animation 3D — {boite}"
    body = f"""Bonjour {prenom},

{hook}

Je crée des animations 3D de mécanismes d'action pour les startups biotech qui préparent une levée ou un congrès. Livraison en 5 jours.

Un exemple vous intéresse ?

Edgar Frinis"""
    return subject, body

def _build_relance_j3(prenom: str, boite: str) -> tuple[str, str]:
    subject = f"Re: Animation 3D — {boite}"
    body = f"""Bonjour {prenom}, mon message vous est bien parvenu ?

Edgar"""
    return subject, body

def _build_relance_j7(prenom: str) -> tuple[str, str]:
    subject = "Mécanisme d'action en 48h"
    body = f"""Bonjour {prenom},

Pour être concret : j'ai animé le MoA d'un anticorps monoclonal en 48h pour une startup en pré-Series A la semaine dernière.

Utile pour votre prochain congrès ou pitch investisseur ?

Edgar"""
    return subject, body

def _build_relance_j14(prenom: str) -> tuple[str, str]:
    subject = "Je ferme le dossier"
    body = f"""Bonjour {prenom},

Dernier message — si le timing n'est pas bon, pas de problème. Je reste disponible.

Edgar"""
    return subject, body

def send_initial_email(lead: dict, subject: str = "", body: str = "", hook: str = "") -> bool:
    """
    Send initial prospecting email. Returns True on success.
    Accepte soit (subject, body) générés par generate_email,
    soit hook (legacy) pour compatibilité.
    """
    if count_emails_sent_today() >= MAX_EMAILS_PER_DAY:
        print(f"[EmailSender] Limite journalière atteinte ({MAX_EMAILS_PER_DAY})")
        return False

    email = lead.get("email", "")
    if not email:
        return False

    if not subject or not body:
        # Fallback legacy
        prenom = lead.get("prenom", "")
        boite = lead.get("boite", "votre startup")
        subject, body = _build_initial_email(prenom, boite, hook)

    success = _send_smtp(email, subject, body)
    if success:
        today = date.today().isoformat()
        followup_dates = {
            "date_email": today,
            "statut": "Email envoyé",
            "canal": "Email",
            "relance_j3": (date.today() + timedelta(days=3)).isoformat(),
            "relance_j7": (date.today() + timedelta(days=7)).isoformat(),
            "relance_j14": (date.today() + timedelta(days=14)).isoformat(),
        }
        update_lead(email, followup_dates)
        print(f"[EmailSender] Email initial envoyé à {email}")
    return success

def send_followup(lead: dict, day: int) -> bool:
    """Send a follow-up email at J+3, J+7, or J+14."""
    email = lead.get("email", "")
    if not email:
        return False

    prenom = lead.get("prenom", "")
    boite = lead.get("boite", "")

    if day == 3:
        subject, body = _build_relance_j3(prenom, boite)
    elif day == 7:
        subject, body = _build_relance_j7(prenom)
    elif day == 14:
        subject, body = _build_relance_j14(prenom)
    else:
        return False

    success = _send_smtp(email, subject, body)
    if success:
        updates = {"statut": "Relancé"}
        if day == 14:
            updates["statut"] = "Froid"
        update_lead(email, updates)
        print(f"[EmailSender] Relance J+{day} envoyée à {email}")
    return success
