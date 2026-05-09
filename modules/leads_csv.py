import csv

import pandas as pd
from datetime import date

from modules.config import LEADS_CSV
from modules.logger import log_error

COLUMNS = [
    "nom", "prenom", "boite", "domaine", "email", "linkedin_url",
    "statut", "canal", "date_email", "date_linkedin",
    "relance_j3", "relance_j7", "relance_j14", "reponse", "dnc", "notes",
    "contact_role", "contact_origin", "proof_level", "contact_score",
    "contact_decision", "premium", "hold_attempts",
]


def _status_key(value: str) -> str:
    lowered = str(value or "").strip().lower()
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


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[COLUMNS].fillna("")


def _load_csv_rows() -> pd.DataFrame:
    with open(LEADS_CSV, newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        rows = list(reader)

    if not rows:
        return pd.DataFrame(columns=COLUMNS)

    header = rows[0]
    data_rows = []
    width = len(header)
    for row in rows[1:]:
        if len(row) < width:
            row = row + [""] * (width - len(row))
        elif len(row) > width:
            row = row[: width - 1] + [",".join(row[width - 1 :])]
        data_rows.append(row)

    return pd.DataFrame(data_rows, columns=header)


def load_leads() -> pd.DataFrame:
    if not LEADS_CSV.exists() or LEADS_CSV.stat().st_size == 0:
        df = pd.DataFrame(columns=COLUMNS)
        df.to_csv(LEADS_CSV, index=False)
        return df
    df = _load_csv_rows().fillna("")
    return _ensure_columns(df)


def save_leads(df: pd.DataFrame):
    _ensure_columns(df).to_csv(LEADS_CSV, index=False)


def is_duplicate(df: pd.DataFrame, email: str = "", linkedin_url: str = "") -> bool:
    if email and email in df["email"].values:
        return True
    if linkedin_url and linkedin_url in df["linkedin_url"].values:
        return True
    return False


def add_lead(row: dict) -> bool:
    """Add a new lead. Returns False if duplicate."""
    try:
        df = load_leads()
        if is_duplicate(df, row.get("email", ""), row.get("linkedin_url", "")):
            return False
        row.setdefault("statut", "Nouveau")
        row.setdefault("dnc", "")
        row.setdefault("reponse", "")
        row.setdefault("contact_role", "")
        row.setdefault("contact_origin", "")
        row.setdefault("proof_level", "")
        row.setdefault("contact_score", "")
        row.setdefault("contact_decision", "")
        row.setdefault("premium", "")
        row.setdefault("hold_attempts", "")
        new_row = {col: row.get(col, "") for col in COLUMNS}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_leads(df)
        return True
    except Exception as e:
        log_error("leads_csv", e, f"add_lead {row.get('email', '')}")
        return False


def update_lead(email: str, updates: dict):
    try:
        df = load_leads()
        mask = df["email"] == email
        if not mask.any():
            return
        for key, val in updates.items():
            if key in df.columns:
                df.loc[mask, key] = str(val)
        save_leads(df)
    except Exception as e:
        log_error("leads_csv", e, f"update_lead {email}")


def get_leads_due_for_followup(day: int) -> pd.DataFrame:
    """Return leads where followup at day J+day is due today."""
    df = load_leads()
    today = date.today().isoformat()
    col_map = {3: "relance_j3", 7: "relance_j7", 14: "relance_j14"}
    col = col_map.get(day, "")
    if not col:
        return pd.DataFrame()
    due = df[
        (df["statut"].apply(_status_key).str.startswith("email envoy")) &
        (df["contact_decision"].fillna("").astype(str).str.strip() == "auto_send") &
        (df["dnc"] == "") &
        (df["reponse"] == "") &
        (df[col] == today)
    ]
    return due


def get_leads_for_linkedin() -> pd.DataFrame:
    """Leads where date_email was 3+ days ago and no LinkedIn yet."""
    df = load_leads()
    today = date.today()
    eligible = []
    for _, row in df.iterrows():
        if row["dnc"] or row["date_linkedin"]:
            continue
        if not row["date_email"]:
            continue
        try:
            email_date = date.fromisoformat(row["date_email"])
            if (today - email_date).days >= 3:
                eligible.append(row)
        except ValueError:
            continue
    return pd.DataFrame(eligible)


def count_emails_sent_today() -> int:
    df = load_leads()
    today = date.today().isoformat()
    return len(df[df["date_email"] == today])


def count_linkedin_sent_this_month() -> int:
    df = load_leads()
    this_month = date.today().strftime("%Y-%m")
    return len(df[df["date_linkedin"].str.startswith(this_month, na=False)])
