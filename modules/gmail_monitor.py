"""
Surveille la boîte Gmail pour détecter les réponses aux emails de prospection.
"""
import imaplib
import email
from email.header import decode_header
from datetime import datetime, date, timedelta
from modules.config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, NEGATIVE_KEYWORDS
from modules.leads_csv import update_lead, load_leads, save_leads
from modules.logger import log_error

IMAP_HOST = "imap.gmail.com"
BOUNCE_SENDER_MARKERS = ("mail delivery subsystem", "mailer-daemon", "postmaster")
BOUNCE_SUBJECT_MARKERS = (
    "delivery status notification",
    "adresse introuvable",
    "message non distribué",
    "message non distribue",
    "address not found",
    "undeliver",
    "delivery incomplete",
    "delivery failure",
)

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


def _append_note(email_addr: str, note: str):
    try:
        df = load_leads()
        mask = df["email"].fillna("").astype(str).str.strip().str.lower() == str(email_addr or "").strip().lower()
        if not mask.any():
            return
        existing = str(df.loc[mask, "notes"].iloc[0] or "").strip()
        parts = [part.strip() for part in existing.split(" | ") if part.strip()]
        if note not in parts:
            parts.append(note)
        df.loc[mask, "notes"] = " | ".join(parts)
        save_leads(df)
    except Exception as e:
        log_error("gmail_monitor", e, f"append_note {email_addr}")


def _extract_known_emails(text: str, known_emails: set[str]) -> list[str]:
    lowered = (text or "").lower()
    matches = []
    for email_addr in known_emails:
        if email_addr and email_addr.lower() in lowered:
            matches.append(email_addr)
    return matches


def _looks_like_bounce(from_header: str, subject: str, body: str) -> bool:
    haystack = " ".join([from_header or "", subject or "", body or ""]).lower()
    return any(marker in haystack for marker in BOUNCE_SENDER_MARKERS + BOUNCE_SUBJECT_MARKERS)


def check_bounces(days: int = 7) -> list[dict]:
    """
    Scan Gmail for delivery failures affecting known prospect emails.
    Returns list of {email, subject, body} dicts.
    """
    bounces = []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        mail.select("INBOX")

        since = (date.today() - timedelta(days=days)).strftime("%d-%b-%Y")
        _, data = mail.search(None, f'(SINCE {since})')
        if not data[0]:
            mail.logout()
            return []

        df = load_leads()
        known_emails = {
            str(value).strip().lower()
            for value in df["email"].dropna().values
            if str(value).strip()
        }
        already_bounced = {
            str(value).strip().lower()
            for value in df[df["statut"].fillna("").astype(str).str.strip().str.lower() == "bounce"]["email"].dropna().values
            if str(value).strip()
        }
        seen = set()

        for num in data[0].split():
            try:
                _, msg_data = mail.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                from_header = _decode_str(msg.get("From", ""))
                subject = _decode_str(msg.get("Subject", ""))
                body = _get_body(msg)
                if not _looks_like_bounce(from_header, subject, body):
                    continue

                matched_emails = _extract_known_emails(" ".join([from_header, subject, body]), known_emails)
                for matched in matched_emails:
                    if matched in already_bounced or matched in seen:
                        continue
                    seen.add(matched)
                    bounces.append({
                        "email": matched,
                        "subject": subject,
                        "body": body[:1000],
                    })
            except Exception as e:
                log_error("gmail_monitor", e, "parse bounce message")

        mail.logout()
    except Exception as e:
        log_error("gmail_monitor", e, "check_bounces")

    return bounces

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


def process_bounces(bounces: list[dict]):
    """Marque automatiquement les emails en échec de livraison."""
    from modules.notion_crm import update_status, log_action

    for bounce in bounces:
        email_addr = bounce["email"]
        print(f"[GmailMonitor] Bounce détecté pour {email_addr}")
        update_lead(email_addr, {"dnc": "true", "statut": "Bounce", "reponse": "bounce", "contact_decision": "dnc"})
        _append_note(email_addr, "Bounce detected from Gmail delivery failure")
        try:
            update_status(email_addr, "DNC")
            log_action(email_addr, "Bounce détecté", bounce.get("subject", ""))
        except Exception as e:
            log_error("gmail_monitor", e, f"notion bounce {email_addr}")
