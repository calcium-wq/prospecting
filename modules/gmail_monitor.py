"""
Surveille la boîte Gmail pour détecter les réponses aux emails de prospection.
"""
import imaplib
import email
from email.header import decode_header
from datetime import datetime, date, timedelta
from modules.config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, NEGATIVE_KEYWORDS
from modules.leads_csv import update_lead, load_leads
from modules.logger import log_error

IMAP_HOST = "imap.gmail.com"

def _decode_str(s) -> str:
    if isinstance(s, bytes):
        return s.decode("utf-8", errors="replace")
    return s or ""

def _get_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                try:
                    body += part.get_payload(decode=True).decode("utf-8", errors="replace")
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
        except Exception:
            pass
    return body

def _is_negative(body: str) -> bool:
    body_lower = body.lower()
    return any(kw in body_lower for kw in NEGATIVE_KEYWORDS)

def check_replies() -> list[dict]:
    """
    Check Gmail inbox for replies to prospecting emails.
    Returns list of {email, subject, body, is_negative} dicts.
    """
    replies = []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        mail.select("INBOX")

        # Search for unseen emails from the last 2 days
        since = (date.today() - timedelta(days=2)).strftime("%d-%b-%Y")
        _, data = mail.search(None, f'(UNSEEN SINCE {since})')

        if not data[0]:
            mail.logout()
            return []

        df = load_leads()
        known_emails = set(df["email"].dropna().values)
        already_processed = set(
            df[df["reponse"].fillna("").astype(str).str.strip() != ""]["email"].dropna().values
        )

        for num in data[0].split():
            try:
                _, msg_data = mail.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])

                from_header = _decode_str(msg.get("From", ""))
                subject = _decode_str(msg.get("Subject", ""))
                body = _get_body(msg)

                # Extract sender email
                sender_email = ""
                if "<" in from_header:
                    sender_email = from_header.split("<")[1].rstrip(">").strip()
                else:
                    sender_email = from_header.strip()

                # Only process if it's from a known lead, and avoid repeating the same notification.
                # Do not mark messages as read: Edgar must see prospect replies in Gmail.
                if sender_email not in known_emails:
                    continue
                if sender_email in already_processed:
                    continue

                negative = _is_negative(body + subject)
                replies.append({
                    "email": sender_email,
                    "subject": subject,
                    "body": body[:500],
                    "is_negative": negative
                })

            except Exception as e:
                log_error("gmail_monitor", e, "parse message")

        mail.logout()
    except Exception as e:
        log_error("gmail_monitor", e, "check_replies")

    return replies

def process_replies(replies: list[dict], notify_fn=None):
    """Process replies and update leads accordingly."""
    from modules.notion_crm import update_status, log_action
    from modules.leads_csv import update_lead

    for reply in replies:
        email_addr = reply["email"]
        if reply["is_negative"]:
            print(f"[GmailMonitor] DNC détecté pour {email_addr}")
            update_lead(email_addr, {"dnc": "true", "statut": "DNC", "reponse": "négative"})
            try:
                update_status(email_addr, "DNC")
                log_action(email_addr, "Réponse négative reçue", reply["subject"])
            except Exception as e:
                log_error("gmail_monitor", e, f"notion DNC {email_addr}")
        else:
            print(f"[GmailMonitor] Réponse positive de {email_addr}")
            update_lead(email_addr, {"statut": "Intéressé", "reponse": "positive"})
            try:
                update_status(email_addr, "Intéressé")
                log_action(email_addr, "Réponse positive reçue", reply["subject"])
            except Exception as e:
                log_error("gmail_monitor", e, f"notion intéressé {email_addr}")

            if notify_fn:
                try:
                    df = load_leads()
                    row = df[df["email"] == email_addr]
                    if not row.empty:
                        prenom = row.iloc[0]["prenom"]
                        boite = row.iloc[0]["boite"]
                        notify_fn(prenom, boite, email_addr)
                except Exception as e:
                    log_error("gmail_monitor", e, f"notify {email_addr}")
