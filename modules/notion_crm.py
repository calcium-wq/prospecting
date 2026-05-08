"""
CRM Notion — appels API directs (notion-client v3 a supprimé databases.query).
"""
import httpx
from datetime import datetime
from modules.config import NOTION_TOKEN, NOTION_DATABASE_ID
from modules.logger import log_error

_NOTION_VERSION = "2022-06-28"
_BASE = "https://api.notion.com/v1"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": _NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _query(filter_body: dict) -> list[dict]:
    """POST /databases/{id}/query"""
    try:
        resp = httpx.post(
            f"{_BASE}/databases/{NOTION_DATABASE_ID}/query",
            headers=_headers(),
            json={"filter": filter_body},
            timeout=15,
        )
        if resp.is_success:
            return resp.json().get("results", [])
    except Exception as e:
        log_error("notion_crm", e, "query")
    return []


def _create_page(properties: dict) -> dict | None:
    try:
        resp = httpx.post(
            f"{_BASE}/pages",
            headers=_headers(),
            json={"parent": {"database_id": NOTION_DATABASE_ID}, "properties": properties},
            timeout=15,
        )
        if resp.is_success:
            return resp.json()
        log_error("notion_crm", Exception(resp.text[:200]), "create_page")
    except Exception as e:
        log_error("notion_crm", e, "create_page")
    return None


def _update_page(page_id: str, properties: dict) -> bool:
    try:
        resp = httpx.patch(
            f"{_BASE}/pages/{page_id}",
            headers=_headers(),
            json={"properties": properties},
            timeout=15,
        )
        return resp.is_success
    except Exception as e:
        log_error("notion_crm", e, f"update_page {page_id}")
        return False


def _archive_page(page_id: str):
    try:
        httpx.patch(
            f"{_BASE}/pages/{page_id}",
            headers=_headers(),
            json={"archived": True},
            timeout=15,
        )
    except Exception as e:
        log_error("notion_crm", e, f"archive_page {page_id}")


def _find_page_by_email(email: str) -> dict | None:
    if not email:
        return None
    pages = _query({"property": "Email", "email": {"equals": email}})
    return pages[0] if pages else None


def _build_properties(lead: dict) -> dict:
    # Titre = Boîte si nom vide (Notion exige un titre non vide)
    title_val = lead.get("nom") or lead.get("boite") or lead.get("email") or "—"
    props: dict = {
        "Nom": {"title": [{"text": {"content": title_val}}]},
    }
    if lead.get("prenom"):
        props["Prénom"] = {"rich_text": [{"text": {"content": lead["prenom"]}}]}
    if lead.get("boite"):
        props["Boîte"] = {"rich_text": [{"text": {"content": lead["boite"]}}]}
    if lead.get("domaine"):
        props["Domaine"] = {"rich_text": [{"text": {"content": lead["domaine"]}}]}
    if lead.get("email"):
        props["Email"] = {"email": lead["email"]}
    if lead.get("linkedin_url"):
        props["LinkedIn_URL"] = {"url": lead["linkedin_url"]}
    if lead.get("statut"):
        props["Statut"] = {"select": {"name": lead["statut"]}}
    if lead.get("canal"):
        props["Canal"] = {"rich_text": [{"text": {"content": lead["canal"]}}]}
    if lead.get("date_email"):
        props["Date_Email"] = {"date": {"start": lead["date_email"]}}
    if lead.get("date_linkedin"):
        props["Date_LinkedIn"] = {"date": {"start": lead["date_linkedin"]}}
    for day in ["Relance_J3", "Relance_J7", "Relance_J14"]:
        key = day.lower()
        if lead.get(key):
            props[day] = {"date": {"start": lead[key]}}
    if lead.get("reponse"):
        props["Réponse"] = {"rich_text": [{"text": {"content": lead["reponse"]}}]}
    if lead.get("dnc"):
        props["DNC"] = {"checkbox": True}
    if lead.get("notes"):
        props["Notes"] = {"rich_text": [{"text": {"content": str(lead["notes"])[:2000]}}]}
    return props


def upsert_lead(lead: dict):
    try:
        email = lead.get("email", "")
        props = _build_properties(lead)
        existing = _find_page_by_email(email) if email else None
        if existing:
            _update_page(existing["id"], props)
        else:
            _create_page(props)
    except Exception as e:
        log_error("notion_crm", e, f"upsert_lead {lead.get('email', '')}")


def update_status(email: str, statut: str, extra: dict = None):
    try:
        page = _find_page_by_email(email)
        if not page:
            return
        props = {"Statut": {"select": {"name": statut}}}
        if extra:
            props.update(_build_extra_props(extra))
        _update_page(page["id"], props)
    except Exception as e:
        log_error("notion_crm", e, f"update_status {email}")


def log_action(email: str, action: str, notes: str = ""):
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        page = _find_page_by_email(email)
        if not page:
            return
        current_notes = ""
        try:
            current_notes = page["properties"]["Notes"]["rich_text"][0]["plain_text"]
        except (KeyError, IndexError):
            pass
        new_notes = f"[{ts}] {action}\n{notes}\n{current_notes}".strip()[:2000]
        _update_page(page["id"], {"Notes": {"rich_text": [{"text": {"content": new_notes}}]}})
    except Exception as e:
        log_error("notion_crm", e, f"log_action {email}")


def _build_extra_props(extra: dict) -> dict:
    result = {}
    if "date_email" in extra:
        result["Date_Email"] = {"date": {"start": extra["date_email"]}}
    if "date_linkedin" in extra:
        result["Date_LinkedIn"] = {"date": {"start": extra["date_linkedin"]}}
    if "notes" in extra:
        result["Notes"] = {"rich_text": [{"text": {"content": str(extra["notes"])[:2000]}}]}
    return result


def ensure_database_schema() -> bool:
    try:
        resp = httpx.get(
            f"{_BASE}/databases/{NOTION_DATABASE_ID}",
            headers=_headers(),
            timeout=15,
        )
        if resp.is_success:
            data = resp.json()
            title = data.get("title", [{}])
            name = title[0].get("plain_text", "unknown") if title else "unknown"
            print(f"[Notion] Connecté à la base : {name}")
            return True
        print(f"[Notion] ERREUR : {resp.status_code}")
        return False
    except Exception as e:
        log_error("notion_crm", e, "ensure_database_schema")
        print(f"[Notion] ERREUR connexion : {e}")
        return False
