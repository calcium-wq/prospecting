"""
Gestion de la séquence de relances email J+3 / J+7 / J+14.
Les relances sont générées par le LLM (pas de templates hardcodés).
"""
from modules.leads_csv import get_leads_due_for_followup, update_lead, load_leads
from modules.email_sender import _send_smtp
from modules.llm import generate_followup_j3, generate_followup_j7, generate_followup_j14
from modules.logger import log_error
from modules.notion_crm import log_action
from modules.gmail_monitor import check_replies, process_replies
from datetime import date


def validate_followup(body: str) -> tuple[bool, str, str]:
    """
    Valide une relance avant envoi.
    Retourne (is_valid, error_message, corrected_body).
    """
    if not body or not body.strip():
        return False, "Corps vide", body

    words = body.split()
    word_count = len(words)
    if word_count > 60:
        return False, f" Trop de mots ({word_count}/60)", body

    body_lower = body.lower()
    forbidden_phrases = [
        "je reste disponible",
        "je ferme le dossier",
        "avez-vous déjà envisagé",
    ]
    for phrase in forbidden_phrases:
        if phrase in body_lower:
            return False, f"Contient interdit: '{phrase}'", body

    question_count = body.count("?")
    if question_count > 1:
        return False, f"Plusieurs questions ({question_count})", body

    corrected = body
    if "-- Edgar" not in body and "— Edgar" not in body:
        corrected = body.rstrip() + "\n\n— Edgar"

    return True, "", corrected


def get_followups_due_today() -> dict[int, list[dict]]:
    """
    Retourne un dict {day: [lead_dict]} des relances dues aujourd'hui.
    Sans envoyer, sans vérifier Gmail.
    """
    result = {3: [], 7: [], 14: []}
    for day in [3, 7, 14]:
        due = get_leads_due_for_followup(day)
        if not due.empty:
            result[day] = due.to_dict("records")
    return result


def _send_llm_followup(lead: dict, day: int) -> bool:
    email_addr = lead.get("email", "")
    if not email_addr:
        return False

    prenom = lead.get("prenom", "")
    boite = lead.get("boite", "")

    if day == 3:
        content = generate_followup_j3(boite, prenom)
    elif day == 7:
        content = generate_followup_j7(boite, prenom)
    elif day == 14:
        content = generate_followup_j14(boite, prenom)
    else:
        return False

    body = content.get("body", "")
    is_valid, error, corrected_body = validate_followup(body)
    if not is_valid:
        log_error("followup", Exception(error), f"Validation échouée pour {email_addr} J+{day}")
        print(f"[Followup] VALIDATION ÉCHOUÉE J+{day} {email_addr}: {error}")
        return False

    success = _send_smtp(email_addr, content["subject"], corrected_body)
    if success:
        updates = {"statut": "Relancé"}
        if day == 14:
            updates["statut"] = "Froid"
        update_lead(email_addr, updates)
        print(f"[Followup] Relance J+{day} envoyée à {email_addr}")
    return success


def run_followups():
    """Run all pending follow-ups for today."""
    print("[Followup] Vérification des réponses Gmail...")
    try:
        replies = check_replies()
        if replies:
            print(f"[Followup] {len(replies)} réponse(s) traitée(s)")
            process_replies(replies)
    except Exception as e:
        log_error("followup", e, "check_replies au début des relances")

    df = load_leads()
    responded_emails = set(df[df["reponse"].fillna("").astype(str).str.strip() != ""]["email"].dropna().values)
    dnc_emails = set(df[df["dnc"].fillna("").astype(str).str.strip().lower() == "true"]["email"].dropna().values)

    total_sent = 0
    for day in [3, 7, 14]:
        due = get_leads_due_for_followup(day)
        if due.empty:
            print(f"[Followup] J+{day} : aucune relance à envoyer")
            continue

        print(f"[Followup] J+{day} : {len(due)} relance(s) à envoyer")
        for _, row in due.iterrows():
            lead = row.to_dict()
            email_addr = lead.get("email", "")

            if email_addr in responded_emails:
                print(f"[Followup] SKIP {email_addr}: a déjà répondu")
                continue
            if email_addr in dnc_emails:
                print(f"[Followup] SKIP {email_addr}: DNC")
                continue

            try:
                sent = _send_llm_followup(lead, day)
                if sent:
                    total_sent += 1
                    try:
                        log_action(lead["email"], f"Relance J+{day} envoyée")
                    except Exception:
                        pass
            except Exception as e:
                log_error("followup", e, f"J+{day} {row.get('email', '')}")

    print(f"[Followup] Total relances envoyées : {total_sent}")
    return total_sent
