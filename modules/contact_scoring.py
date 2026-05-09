import re
from typing import Any

import pandas as pd

ROLE_SCORES = {
    "CEO / Founder": 35,
    "CBO / BD / Partnerships": 33,
    "CFO / IR interne": 30,
    "CSO / CMO": 24,
    "Product / Clinical Marketing / Comms interne": 20,
    "IR externe / agence": 12,
    "generique": 4,
}

ORIGIN_SCORES = {
    "interne_confirme": 25,
    "interne_probable": 18,
    "externe_officiel": 10,
    "externe_flou": 0,
}

CHANNEL_SCORES = {
    "email_nominatif": 20,
    "email_fonctionnel_interne": 12,
    "email_externe_agence": 6,
    "email_generique": 2,
}

PROOF_SCORES = {
    "officiel": 15,
    "coherent": 10,
    "pattern": 5,
    "none": 0,
}

ABSOLUTE_DNC_PREFIXES = {
    "support", "admin", "noreply", "no-reply", "contact", "hello", "info",
    "bonjour", "contact-us", "sales", "marketing", "service", "team", "equipe",
}

GENERIC_BUT_NOT_ABSOLUTE_PREFIXES = {"investor", "investors", "ir"}

BAD_ROLE_KEYWORDS = {
    "support", "admin", "noreply", "no-reply", "contact", "hello", "info",
    "bonjour", "contact-us", "sales", "marketing", "service", "team", "equipe",
    "investor", "investors", "ir",
}

SENT_STATUS_PREFIXES = (
    "email envoy",
    "relanc",
    "interess",
    "int",
    "froid",
    "linkedin envoy",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    return _text(value).lower()


def _status_key(value: Any) -> str:
    lowered = _norm(value)
    return (
        lowered
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("ù", "u")
        .replace("ï", "i")
        .replace("î", "i")
        .replace("ô", "o")
        .replace("ç", "c")
    )


def _to_bool(value: Any) -> bool:
    return _norm(value) in {"1", "true", "yes", "y", "oui"}


def is_sent_status(value: Any) -> bool:
    key = _status_key(value)
    return any(key.startswith(prefix) for prefix in SENT_STATUS_PREFIXES)


def normalize_domain(value: Any) -> str:
    domain = _norm(value)
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def parse_hold_attempts(value: Any) -> int:
    try:
        return max(0, int(float(_text(value) or "0")))
    except ValueError:
        return 0


def email_parts(email: Any) -> tuple[str, str]:
    raw = _norm(email)
    if "@" not in raw:
        return "", ""
    local, domain = raw.split("@", 1)
    return local, normalize_domain(domain)


def infer_channel_type(lead: dict) -> str:
    email = _text(lead.get("email"))
    local, email_domain = email_parts(email)
    if not local or not email_domain:
        return ""

    prefix = local.split(".")[0].lower()
    origin = infer_contact_origin(lead)
    company_domain = normalize_domain(lead.get("domaine"))

    if prefix in ABSOLUTE_DNC_PREFIXES or prefix in GENERIC_BUT_NOT_ABSOLUTE_PREFIXES:
        return "email_generique"
    if origin.startswith("externe"):
        return "email_externe_agence"
    if company_domain and email_domain == company_domain and "." not in local and len(local) > 1:
        return "email_fonctionnel_interne"
    return "email_nominatif"


def infer_contact_origin(lead: dict) -> str:
    existing = _norm(lead.get("contact_origin"))
    if existing in ORIGIN_SCORES:
        return existing

    email = _text(lead.get("email"))
    local, email_domain = email_parts(email)
    if not local:
        return ""

    notes = _norm(lead.get("notes"))
    company_domain = normalize_domain(lead.get("domaine"))
    domain_match = bool(company_domain and email_domain == company_domain)

    if any(token in notes for token in ("external agency", "agence", "parent company", "parent ", "affluent", "presse", "press", "external", "externe")):
        return "externe_officiel"
    if any(token in notes for token in ("pattern", "inferred", "infere", "unconfirmed", "non verified", "not verified")):
        return "interne_probable" if domain_match else "externe_flou"
    if domain_match:
        return "interne_confirme"

    company_stem = re.sub(r"[^a-z0-9]", "", company_domain.split(".")[0]) if company_domain else ""
    email_stem = re.sub(r"[^a-z0-9]", "", email_domain.split(".")[0]) if email_domain else ""
    if company_stem and email_stem and (company_stem in email_stem or email_stem in company_stem):
        return "interne_probable"
    if any(token in notes for token in ("official", "officiel", "press release", "investors page", "corporate presentation", "team page", "official team")):
        return "externe_officiel"
    return "externe_flou"


def infer_contact_role(lead: dict) -> str:
    existing = _text(lead.get("contact_role"))
    if existing in ROLE_SCORES:
        return existing

    prenom = _norm(lead.get("prenom"))
    notes = _norm(lead.get("notes"))
    local, _ = email_parts(lead.get("email"))
    prefix = local.split(".")[0].lower() if local else ""
    origin = infer_contact_origin(lead)

    haystack = " ".join(filter(None, [notes, prenom, prefix]))
    if prefix in ABSOLUTE_DNC_PREFIXES or prenom in BAD_ROLE_KEYWORDS:
        return "generique"
    if any(token in haystack for token in ("ceo", "founder", "co-founder", "president")):
        return "CEO / Founder"
    if any(token in haystack for token in ("cbo", "business development", "bizdev", "partnership", "partnering", "commercial")):
        return "CBO / BD / Partnerships"
    if any(token in haystack for token in ("investor relations", "investor", "ir", "cfo")):
        return "CFO / IR interne" if origin.startswith("interne") else "IR externe / agence"
    if any(token in haystack for token in ("cso", "cmo", "scientific", "medical", "r&d", "research", "clinical")):
        return "CSO / CMO"
    if any(token in haystack for token in ("communication", "communications", "comms", "marketing", "media", "press")):
        return "Product / Clinical Marketing / Comms interne" if origin.startswith("interne") else "IR externe / agence"
    if prefix in GENERIC_BUT_NOT_ABSOLUTE_PREFIXES:
        return "IR externe / agence" if origin.startswith("externe") else "CFO / IR interne"
    if origin.startswith("interne"):
        return "Product / Clinical Marketing / Comms interne"
    return "IR externe / agence"


def infer_proof_level(lead: dict) -> str:
    existing = _norm(lead.get("proof_level"))
    if existing in PROOF_SCORES:
        return existing

    email = _text(lead.get("email"))
    if not email:
        return ""

    notes = _norm(lead.get("notes"))
    if any(token in notes for token in ("official", "officiel", "official team", "team page", "corporate presentation", "press release", "investors page", "verified", "official site")):
        return "officiel"
    if any(token in notes for token in ("pattern", "inferred", "infere", "unconfirmed", "not verified")):
        return "pattern"
    origin = infer_contact_origin(lead)
    if origin.startswith("interne"):
        return "coherent"
    return "none"


def infer_premium(lead: dict) -> bool:
    if _to_bool(lead.get("premium")):
        return True
    notes = _norm(lead.get("notes"))
    return "premium" in notes


def is_absolute_dnc(lead: dict) -> bool:
    email = _text(lead.get("email"))
    status = _text(lead.get("statut"))
    if _status_key(status) == "hors scope":
        return True
    if _to_bool(lead.get("dnc")):
        return True
    if not email:
        return False

    local, email_domain = email_parts(email)
    prefix = local.split(".")[0].lower() if local else ""
    if prefix in ABSOLUTE_DNC_PREFIXES:
        return True
    if not local or not email_domain or "." not in email_domain:
        return True

    notes = _norm(lead.get("notes"))
    company_domain = normalize_domain(lead.get("domaine"))
    if company_domain and email_domain != company_domain and infer_contact_origin(lead) == "externe_flou":
        return True
    if any(token in notes for token in ("manifestement faux", "fake", "invalid", "not verified - do not send")):
        return True
    return False


def compute_contact_score(lead: dict) -> int:
    email = _text(lead.get("email"))
    if not email:
        return 0
    role = infer_contact_role(lead)
    origin = infer_contact_origin(lead)
    channel = infer_channel_type(lead)
    proof = infer_proof_level(lead)
    return ROLE_SCORES.get(role, 0) + ORIGIN_SCORES.get(origin, 0) + CHANNEL_SCORES.get(channel, 0) + PROOF_SCORES.get(proof, 0)


def decide_contact(lead: dict, hold_attempts: int | None = None) -> str:
    if is_absolute_dnc(lead):
        return "dnc"

    email = _text(lead.get("email"))
    if not email:
        return ""

    score = compute_contact_score(lead)
    premium = infer_premium(lead)
    attempts = parse_hold_attempts(lead.get("hold_attempts") if hold_attempts is None else hold_attempts)

    if premium:
        if score >= 35:
            return "auto_send"
        return "dnc"

    if score >= 60:
        return "auto_send"
    if score < 35:
        return "dnc"
    if attempts >= 3:
        return "dnc"
    return "auto_hold"


def enrich_contact_fields(lead: dict, increment_hold: bool = False, mutate_status: bool = True) -> dict:
    updated = dict(lead)
    status = _text(updated.get("statut"))
    email = _text(updated.get("email"))
    previous_decision = _norm(updated.get("contact_decision"))
    hold_attempts = parse_hold_attempts(updated.get("hold_attempts"))

    updated.setdefault("premium", "")
    if email:
        updated["contact_role"] = infer_contact_role(updated)
        updated["contact_origin"] = infer_contact_origin(updated)
        updated["proof_level"] = infer_proof_level(updated)
        updated["contact_score"] = str(compute_contact_score(updated))

        decision = decide_contact(updated, hold_attempts)
        if decision == "auto_hold" and increment_hold:
            if previous_decision == "auto_hold":
                hold_attempts += 1
            else:
                hold_attempts = max(hold_attempts, 1)
            decision = decide_contact(updated, hold_attempts)
        updated["hold_attempts"] = str(hold_attempts) if hold_attempts else ""
        updated["contact_decision"] = decision
    else:
        updated["contact_role"] = ""
        updated["contact_origin"] = ""
        updated["proof_level"] = ""
        updated["contact_score"] = ""
        if _status_key(status) in {"dnc", "hors scope"} or _to_bool(updated.get("dnc")):
            updated["contact_decision"] = "dnc"
        else:
            updated["contact_decision"] = ""
        if not updated.get("hold_attempts"):
            updated["hold_attempts"] = ""
        return updated

    if not mutate_status or is_sent_status(status):
        return updated

    decision = updated.get("contact_decision", "")
    if _status_key(status) == "hors scope":
        updated["contact_decision"] = "dnc"
        return updated
    if decision == "dnc":
        updated["statut"] = "DNC"
        updated["dnc"] = "True"
    elif decision == "auto_hold":
        updated["statut"] = "Auto-hold"
    elif decision == "auto_send":
        updated["statut"] = "Nouveau"
        if _norm(updated.get("dnc")) == "true":
            updated["dnc"] = ""
    return updated


def rescore_dataframe(df: pd.DataFrame, increment_hold: bool = False, mutate_status: bool = True) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        rows.append(enrich_contact_fields(row.to_dict(), increment_hold=increment_hold, mutate_status=mutate_status))
    rescored = pd.DataFrame(rows)
    for col in df.columns:
        if col not in rescored.columns:
            rescored[col] = ""
    return rescored
