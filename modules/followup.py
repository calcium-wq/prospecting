"""
Gestion de la séquence de relances email J+3 / J+7 / J+14.
Les relances sont générées par le LLM (pas de templates hardcodés).
"""
from modules.leads_csv import get_leads_due_for_followup, update_lead
from modules.email_sender import _send_smtp
from modules.llm import generate_followup_j3, generate_followup_j7, generate_followup_j14
from modules.logger import log_error
from modules.notion_crm import log_action
from datetime import date


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

    success = _send_smtp(email_addr, content["subject"], content["body"])
    if success:
        updates = {"statut": "Relancé"}
        if day == 14:
            updates["statut"] = "Froid"
        update_lead(email_addr, updates)
        print(f"[Followup] Relance J+{day} envoyée à {email_addr}")
    return success


def run_followups():
    """Run all pending follow-ups for today."""
    total_sent = 0
    for day in [3, 7, 14]:
        due = get_leads_due_for_followup(day)
        if due.empty:
            print(f"[Followup] J+{day} : aucune relance à envoyer")
            continue

        print(f"[Followup] J+{day} : {len(due)} relance(s) à envoyer")
        for _, row in due.iterrows():
            lead = row.to_dict()
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
