#!/usr/bin/env python3
"""
Pipeline de prospection B2B — Edgar Frinis
Animations 3D médicales pour startups biotech/medtech françaises.

Usage:
    python3 run.py                  # Pipeline complet
    python3 run.py --scrape         # Scraping uniquement
    python3 run.py --enrich         # Enrichissement emails uniquement
    python3 run.py --send           # Envoi emails uniquement
    python3 run.py --followup       # Relances uniquement
    python3 run.py --linkedin       # LinkedIn uniquement
    python3 run.py --monitor        # Vérification réponses Gmail
    python3 run.py --test           # Test de tous les composants
"""
import sys
import argparse
import time
from pathlib import Path
from datetime import date

# Ensure we load from the right directory
sys.path.insert(0, str(Path(__file__).parent))

from modules.config import (
    LEADS_CSV, DATA_DIR, OPENROUTER_API_KEY,
    GMAIL_ADDRESS, NOTION_TOKEN, NOTION_DATABASE_ID,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
)
from modules.logger import logger, log_error
from modules.leads_csv import (
    load_leads, add_lead, update_lead, is_duplicate,
    get_leads_for_linkedin, count_emails_sent_today, count_linkedin_sent_this_month
)

_GENERIC_EMAIL_PREFIXES = {"contact", "hello", "info", "bonjour", "contact-us", "admin"}

PRENOM_CORRECTIONS: dict[str, tuple[str, str]] = {
    "cd@hemerion.com":             ("Clement", "Dupont"),
    "prinaudo@enterome.com":       ("Philippe", "Rinaudo"),
    "ofriedrich@cellprothera.com": ("Olivier", "Friedrich"),
}

NOTIFY_PRENOM = {}

_pending_emails: list[dict] = []


def step_scrape(max_leads: int = 9999) -> list[dict]:
    """Étape 1 : Scrape les startups françaises biotech/medtech."""
    from modules.scraper import search_french_biotech_startups
    print("\n" + "="*60)
    print("ÉTAPE 1 — SCRAPING STARTUPS")
    print("="*60)
    try:
        leads = search_french_biotech_startups(max_results=max_leads)
        new_count = 0
        for lead in leads:
            if add_lead(lead):
                new_count += 1
        print(f"[Scraper] {new_count} nouveaux leads ajoutés dans leads.csv")
        return leads
    except Exception as e:
        log_error("run.py", e, "step_scrape")
        print(f"[Scraper] ERREUR : {e} — continuation...")
        return []


def step_enrich():
    """Étape 2 : Enrichissement emails + scraping LinkedIn URL."""
    from modules.email_enricher import enrich_lead, extract_prenom_from_email
    from modules.scraper import find_linkedin_url
    from modules.leads_csv import save_leads
    print("\n" + "="*60)
    print("ÉTAPE 2 — ENRICHISSEMENT EMAILS + LINKEDIN")
    print("="*60)
    try:
        df = load_leads()

        to_enrich = df[df["email"] == ""]
        if to_enrich.empty:
            print("[Enricher] Aucun lead sans email")
        else:
            print(f"[Enricher] {len(to_enrich)} leads à enrichir...")
            for idx, row in to_enrich.iterrows():
                lead = row.to_dict()
                try:
                    enriched = enrich_lead(lead)
                    if enriched.get("email"):
                        found_email = enriched["email"]
                        current_prenom = row.get("prenom", "")
                        placeholder = current_prenom.lower() in {"fondateur", "founder", "", "ceo", "directeur"}
                        new_prenom = extract_prenom_from_email(found_email, current_prenom) if placeholder else current_prenom

                        df.loc[idx, "email"] = found_email
                        if new_prenom and new_prenom != current_prenom:
                            df.loc[idx, "prenom"] = new_prenom
                            print(f"[Enricher] {row.get('boite', '')} → {found_email} (prénom: {new_prenom})")
                        else:
                            print(f"[Enricher] {row.get('boite', '')} → {found_email}")
                except Exception as e:
                    log_error("run.py", e, f"enrich {row.get('domaine', '')}")

        print(f"\n[LinkedIn] Scraping URLs pour {len(df)} leads...")
        for idx, row in df.iterrows():
            current_url = str(row.get("linkedin_url", "")).strip()
            if current_url:
                continue

            email = str(row.get("email", "")).strip()
            boite = str(row.get("boite", "")).strip()

            if not email:
                continue

            email_prefix = email.split("@")[0].lower()
            is_generic = email_prefix in _GENERIC_EMAIL_PREFIXES or "contact@" in email

            if is_generic:
                continue

            correction = PRENOM_CORRECTIONS.get(email)
            if correction:
                prenom, nom = correction
            else:
                prenom = str(row.get("prenom", "")).strip()
                nom = str(row.get("nom", "")).strip()
                if prenom.lower() in {"fondateur", "founder", "contact", "ceo", ""}:
                    continue

            if not nom:
                nom = ""

            print(f"[LinkedIn] {boite}: {prenom} {nom}...")
            li_url = find_linkedin_url(prenom, nom, boite)
            if li_url:
                df.loc[idx, "linkedin_url"] = li_url
                print(f"         → {li_url}")
            else:
                print(f"         → non trouvé")

            import time
            time.sleep(1)

        save_leads(df)
    except Exception as e:
        log_error("run.py", e, "step_enrich")
        print(f"[Enricher] ERREUR : {e} — continuation...")


def _get_corrected_lead(row: dict) -> dict:
    """Applique les corrections de prénom/nom avant génération d'email."""
    lead = dict(row)
    email = str(lead.get("email", "")).strip()

    correction = PRENOM_CORRECTIONS.get(email)
    if correction:
        lead["prenom"] = correction[0]
        lead["nom"] = correction[1]

    prenom = str(lead.get("prenom", "")).strip().lower()
    email_prefix = email.split("@")[0].lower() if "@" in email else ""

    is_generic = (
        email_prefix in _GENERIC_EMAIL_PREFIXES or
        "contact@" in email or
        prenom in {"fondateur", "founder", "contact", "ceo", ""}
    )
    lead["_use_bonjour_only"] = is_generic

    return lead


def _build_email_for_lead(lead: dict) -> dict:
    """Génère l'email personnalisé pour un lead. Retourne {to, subject, body}."""
    from modules.llm import generate_email
    from modules.scraper import get_recent_news_for_company

    boite = lead.get("boite", "")
    corrected = _get_corrected_lead(lead)
    prenom = corrected.get("prenom", "")
    use_generic = corrected.get("_use_bonjour_only", False)

    news = get_recent_news_for_company(boite, lead.get("domaine", ""))

    email_content = generate_email(
        company_name=boite,
        prenom=prenom,
        recent_news=news,
        sector="biotech/medtech",
        stage="Seed/Series A"
    )

    body = email_content["body"]

    # Supprimer toute salutation résiduelle que le LLM aurait pu générer malgré les instructions
    for stray in [f"{prenom},", f"Bonjour {prenom},", f"Salut {prenom},",
                  "Bonjour,", "Salut,", f"{prenom} ,"]:
        if body.startswith(stray):
            body = body[len(stray):].lstrip()
            break

    # Ajouter la salutation une seule fois, depuis le code
    greeting = "Bonjour," if use_generic else f"{prenom},"
    body = f"{greeting}\n\n{body}"

    return {
        "to": lead.get("email", ""),
        "subject": email_content["subject"],
        "body": body,
        "lead": corrected,
    }


def step_preview_emails() -> list[dict]:
    """Génère et affiche les 16 emails pour validation avant envoi."""
    global _pending_emails
    _pending_emails = []

    from modules.scraper import get_recent_news_for_company
    print("\n" + "="*60)
    print("PRÉVIEW — GÉNÉRATION DES 16 EMAILS")
    print("="*60)

    df = load_leads()
    to_contact = df[
        (df["statut"] == "Nouveau") &
        (df["email"] != "") &
        (df["dnc"] == "")
    ]

    if to_contact.empty:
        print("[Preview] Aucun nouveau lead avec email à contacter")
        return []

    print(f"[Preview] {len(to_contact)} leads à générer\n")

    for i, (_, row) in enumerate(to_contact.iterrows(), 1):
        lead = row.to_dict()
        try:
            email_data = _build_email_for_lead(lead)
            _pending_emails.append(email_data)

            print(f"{'─'*60}")
            print(f"[{i}/{len(to_contact)}] {email_data['to']}")
            print(f"Objet : {email_data['subject']}")
            print(f"{'─'*60}")
            print(email_data["body"])
            print()

        except Exception as e:
            log_error("run.py", e, f"preview {lead.get('email', '')}")
            print(f"[Preview] ERREUR pour {lead.get('email', '')} — {e}")

    print(f"{'='*60}")
    print(f"RÉSUMÉ : {len(_pending_emails)} emails prêts à être envoyés")
    print(f"{'='*60}")
    return _pending_emails


def step_send_emails(dry_run: bool = False):
    """Étape 3 : Envoi des emails initiaux personnalisés (ou dry_run via preview)."""
    from modules.email_sender import send_initial_email
    from modules.notion_crm import upsert_lead, log_action
    global _pending_emails

    print("\n" + "="*60)
    print("ÉTAPE 3 — ENVOI EMAILS INITIAUX")
    print("="*60)

    if not _pending_emails:
        print("[EmailSender] Aucun email en attente. Lancez --preview d'abord.")
        return

    df = load_leads()
    daily_limit = count_emails_sent_today()
    print(f"[EmailSender] {len(_pending_emails)} emails en attente, {daily_limit}/100 envoyés aujourd'hui")

    if dry_run:
        print("[EmailSender] Mode dry-run — aucun email envoyé")
        return

    sent = 0
    for email_data in _pending_emails:
        if count_emails_sent_today() >= 100:
            print("[EmailSender] Limite journalière atteinte")
            break

        lead = email_data["lead"]
        try:
            success = send_initial_email(
                lead,
                subject=email_data["subject"],
                body=email_data["body"]
            )
            if success:
                sent += 1
                try:
                    upsert_lead({**lead, "statut": "Email envoyé"})
                    log_action(lead["email"], "Email initial envoyé", email_data["subject"])
                except Exception as e:
                    log_error("run.py", e, f"notion log {lead.get('email', '')}")

                from modules.leads_csv import update_lead
                update_lead(lead["email"], {
                    "statut": "Email envoyé",
                    "date_email": __import__("datetime").date.today().isoformat(),
                })

                time.sleep(5)

        except Exception as e:
            log_error("run.py", e, f"send_email {lead.get('email', '')}")
            print(f"[EmailSender] ERREUR pour {lead.get('email', '')} — continuation...")

    print(f"[EmailSender] {sent} emails envoyés")
    _pending_emails = []


def _confirm_and_send():
    """Attend confirmation de l'utilisateur avant d'envoyer les emails en attente."""
    global _pending_emails
    if not _pending_emails:
        print("[Send] Aucun email en attente. Lancez --preview d'abord.")
        return

    print(f"\n{len(_pending_emails)} emails sont prêts.\n")
    print("Tapez 'oui' pour envoyer, 'non' pour annuler :")
    try:
        answer = input("> ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("Annulé.")
        _pending_emails = []
        return

    if answer in ("oui", "o", "yes", "y"):
        print("\nEnvoi en cours...\n")
        step_send_emails(dry_run=False)
    else:
        print("Envoi annulé.")
        _pending_emails = []


def step_followups():
    """Étape 4 : Relances J+3 / J+7 / J+14."""
    from modules.followup import run_followups
    from modules.notion_crm import log_action
    print("\n" + "="*60)
    print("ÉTAPE 4 — RELANCES EMAIL")
    print("="*60)
    try:
        run_followups()
    except Exception as e:
        log_error("run.py", e, "step_followups")
        print(f"[Followup] ERREUR : {e} — continuation...")


def step_linkedin():
    """Étape 5 : Invitations LinkedIn (après délai de 3 jours post-email)."""
    from modules.linkedin_outreach import send_invitations_batch
    from modules.notion_crm import upsert_lead
    print("\n" + "="*60)
    print("ÉTAPE 5 — INVITATIONS LINKEDIN")
    print("="*60)

    monthly = count_linkedin_sent_this_month()
    print(f"[LinkedIn] {monthly}/130 invitations envoyées ce mois")

    if monthly >= 130:
        print("[LinkedIn] Limite mensuelle atteinte")
        return

    try:
        eligible = get_leads_for_linkedin()
        if eligible.empty:
            print("[LinkedIn] Aucun lead éligible (email 3+ jours, pas encore LinkedIn)")
            return

        print(f"[LinkedIn] {len(eligible)} leads éligibles pour LinkedIn")
        leads = eligible.to_dict("records")
        sent = send_invitations_batch(leads)

        # Update Notion
        for lead in leads[:sent]:
            try:
                upsert_lead({**lead, "statut": "LinkedIn envoyé"})
            except Exception:
                pass

        print(f"[LinkedIn] {sent} invitations envoyées")
    except Exception as e:
        log_error("run.py", e, "step_linkedin")
        print(f"[LinkedIn] ERREUR : {e} — continuation...")


def step_monitor_replies():
    """Étape 6 : Vérification des réponses Gmail."""
    from modules.gmail_monitor import check_replies, process_replies
    from modules.telegram_notif import notify_hot_lead
    print("\n" + "="*60)
    print("ÉTAPE 6 — SURVEILLANCE RÉPONSES GMAIL")
    print("="*60)
    try:
        replies = check_replies()
        if not replies:
            print("[GmailMonitor] Aucune nouvelle réponse détectée")
            return
        print(f"[GmailMonitor] {len(replies)} réponse(s) détectée(s)")
        process_replies(replies, notify_fn=notify_hot_lead)
    except Exception as e:
        log_error("run.py", e, "step_monitor_replies")
        print(f"[GmailMonitor] ERREUR : {e} — continuation...")


def test_all_components():
    """Teste chaque composant et affiche un rapport."""
    print("\n" + "="*60)
    print("TEST DE TOUS LES COMPOSANTS")
    print("="*60)

    results = {}

    # 1. Config / .env
    print("\n[1/8] Test configuration .env...")
    missing = []
    for var, val in [
        ("OPENROUTER_API_KEY", OPENROUTER_API_KEY),
        ("GMAIL_ADDRESS", GMAIL_ADDRESS),
        ("NOTION_TOKEN", NOTION_TOKEN),
        ("NOTION_DATABASE_ID", NOTION_DATABASE_ID),
        ("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN),
        ("TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID),
    ]:
        if not val:
            missing.append(var)
    results["config"] = "OK" if not missing else f"MANQUANT: {missing}"
    print(f"  → {results['config']}")

    # 2. leads.csv
    print("\n[2/8] Test leads.csv...")
    try:
        df = load_leads()
        results["leads_csv"] = f"OK ({len(df)} leads)"
    except Exception as e:
        results["leads_csv"] = f"ERREUR: {e}"
    print(f"  → {results['leads_csv']}")

    # 3. OpenRouter LLM
    print("\n[3/8] Test OpenRouter LLM...")
    try:
        from modules.llm import invoke_llm
        response = invoke_llm("Tu es un assistant.", "Réponds juste 'OK'", max_tokens=10)
        results["llm"] = "OK" if response else "ERREUR: réponse vide"
    except Exception as e:
        results["llm"] = f"ERREUR: {e}"
    print(f"  → {results['llm']}")

    # 4. Gmail SMTP
    print("\n[4/8] Test Gmail SMTP (connexion)...")
    try:
        import smtplib
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.ehlo()
            s.starttls()
            s.login(GMAIL_ADDRESS, __import__("os").getenv("GMAIL_APP_PASSWORD", ""))
        results["gmail_smtp"] = "OK"
    except Exception as e:
        results["gmail_smtp"] = f"ERREUR: {e}"
    print(f"  → {results['gmail_smtp']}")

    # 5. Gmail IMAP (lecture)
    print("\n[5/8] Test Gmail IMAP (lecture)...")
    try:
        import imaplib, os
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_ADDRESS, os.getenv("GMAIL_APP_PASSWORD", ""))
        mail.select("INBOX")
        mail.logout()
        results["gmail_imap"] = "OK"
    except Exception as e:
        results["gmail_imap"] = f"ERREUR: {e}"
    print(f"  → {results['gmail_imap']}")

    # 6. Notion
    print("\n[6/8] Test Notion CRM...")
    try:
        from modules.notion_crm import ensure_database_schema
        ok = ensure_database_schema()
        results["notion"] = "OK" if ok else "ERREUR: base inaccessible"
    except Exception as e:
        results["notion"] = f"ERREUR: {e}"
    print(f"  → {results['notion']}")

    # 7. Telegram
    print("\n[7/8] Test Telegram...")
    try:
        from modules.telegram_notif import test_connection
        ok = test_connection()
        results["telegram"] = "OK" if ok else "ERREUR: envoi échoué"
    except Exception as e:
        results["telegram"] = f"ERREUR: {e}"
    print(f"  → {results['telegram']}")

    # 8. theHarvester
    print("\n[8/8] Test theHarvester...")
    try:
        import subprocess
        r = subprocess.run(["theHarvester", "--help"], capture_output=True, timeout=10)
        results["theHarvester"] = "OK" if r.returncode == 0 else "ERREUR"
    except Exception as e:
        results["theHarvester"] = f"ERREUR: {e}"
    print(f"  → {results['theHarvester']}")

    # Summary
    print("\n" + "="*60)
    print("RÉSUMÉ DES TESTS")
    print("="*60)
    ok_count = sum(1 for v in results.values() if v.startswith("OK"))
    print(f"\n{ok_count}/{len(results)} composants OK\n")
    for component, status in results.items():
        icon = "✓" if status.startswith("OK") else "✗"
        print(f"  {icon} {component:20s} : {status}")
    print()

    return results


def main():
    parser = argparse.ArgumentParser(description="Pipeline de prospection B2B — Edgar Frinis")
    parser.add_argument("--scrape", action="store_true", help="Scraping startups uniquement")
    parser.add_argument("--enrich", action="store_true", help="Enrichissement emails uniquement")
    parser.add_argument("--preview", action="store_true", help="Génère et affiche les emails pour validation")
    parser.add_argument("--send", action="store_true", help="Envoi emails (après --preview ou seul)")
    parser.add_argument("--followup", action="store_true", help="Relances uniquement")
    parser.add_argument("--linkedin", action="store_true", help="LinkedIn uniquement")
    parser.add_argument("--monitor", action="store_true", help="Surveillance réponses Gmail")
    parser.add_argument("--test", action="store_true", help="Test tous les composants")
    parser.add_argument("--max-leads", type=int, default=9999, help="Nombre max de leads à scraper")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("PIPELINE PROSPECTION B2B — Edgar Frinis")
    print(f"Date : {date.today().isoformat()}")
    print(f"{'='*60}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if args.test:
        test_all_components()
        return

    if args.scrape:
        step_scrape(args.max_leads)
    elif args.enrich:
        step_enrich()
    elif args.preview:
        step_preview_emails()
    elif args.send:
        if not _pending_emails:
            step_preview_emails()
        _confirm_and_send()
    elif args.followup:
        step_followups()
    elif args.linkedin:
        step_linkedin()
    elif args.monitor:
        step_monitor_replies()
    else:
        # Pipeline complet
        step_scrape(args.max_leads)
        step_enrich()
        step_followups()
        step_preview_emails()
        step_send_emails()
        step_linkedin()
        step_monitor_replies()

    print(f"\n{'='*60}")
    print("Pipeline terminé.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
