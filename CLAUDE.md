# CLAUDE.md — Prospecting Pipeline

## Contexte
Pipeline de prospection B2B automatisé pour vendre des animations 3D médicales
à des startups biotech/medtech françaises (Seed/Series A).
Le système trouve des leads, enrichit leurs emails, envoie un email personnalisé,
et contacte sur LinkedIn — sans intervention manuelle après setup.

## Stack
- OS : WSL2 Ubuntu sur Windows 11
- Python 3.x
- LLM : OpenRouter (modèle openrouter/auto, base URL https://openrouter.ai/api/v1, compatible OpenAI SDK)
- Email : Gmail SMTP (smtp.gmail.com, port 587, App Password)
- CRM : Notion
- Pivot entre repos : data/leads.csv

## Architecture réelle

Les 5 repos sont clonés dans `~/prospecting/` mais **ne sont pas utilisés**.
Toute la logique est réécrite dans `modules/`.

| Repo clone | Utilisé ? | Raison |
|------------|-----------|--------|
| crunchbase-scraper | ❌ | Remplacé par scraper.py (liste curatée + France Biotech API + Maddyness) |
| fire-enrich | ❌ | Remplacé par email_enricher.py (Hunter, site, theHarvester, SMTP) |
| theHarvester | ⚠️ Fallback | Appelé via subprocess dans email_enricher.py (pas le repo complet) |
| OpenOutreach | ❌ | Remplacé par linkedin_outreach.py (Playwright + stealth) |
| kaymen99/sales-outreach | ❌ | Remplacé par llm.py (OpenRouter) et modules.email_sender |

## Structure des dossiers
```
~/prospecting/
├── .env                    ← toutes les clés API, ne jamais hardcoder
├── CLAUDE.md               ← ce fichier
├── run.py                  ← orchestrateur principal
├── scrape_pipeline.py      ← script de scraping autonome → leads.csv
├── setup_notion.py         ← setup + test Notion
├── test_notion.py          ← test CRUD Notion complet
├── modules/                ← TOUTE la logique du pipeline
│   ├── config.py
│   ├── llm.py
│   ├── scraper.py
│   ├── email_enricher.py
│   ├── email_sender.py
│   ├── leads_csv.py
│   ├── notion_crm.py
│   ├── followup.py
│   ├── gmail_monitor.py
│   ├── linkedin_outreach.py
│   ├── telegram_notif.py
│   └── logger.py
└── data/
    ├── leads.csv           ← fichier pivot central (20 leads)
    ├── errors.log          ← journal des erreurs
    └── monitor.log         ← journal surveillance Gmail
```

## Les 14 modules — rôle exact

| Fichier | Rôle | Dépendances |
|---------|------|-------------|
| `config.py` | Charge .env, définit constantes (rate-limits, keywords DNC) | python-dotenv |
| `llm.py` | Wrapper OpenRouter, génération emails initiaux + 3 relances (J+3/J+7/J+14) | openai (OpenAI SDK) |
| `scraper.py` | Scraping startups FR (liste curatée, France Biotech API, Maddyness, DuckDuckGo) + news 2026 + LinkedIn URL | requests, BeautifulSoup |
| `email_enricher.py` | Multi-source cascade : Hunter.io → scraping site → theHarvester (subprocess) → /team → patterns + SMTP vérif | requests, smtplib, subprocess |
| `email_sender.py` | Envoi Gmail SMTP. Relances passent PAR llm.py (templates LLM), pas hardcodés ici | smtplib, email.mime |
| `leads_csv.py` | CRUD pivot CSV, déduplication email/LinkedIn, compteurs rate-limit | pandas |
| `notion_crm.py` | API Notion via httpx (contournement bug notion-client), upsert/page, log_action | httpx |
| `followup.py` | Orchestrateur relances : appelle leads_csv.get_leads_due_for_followup + email_sender | leads_csv, email_sender, notion_crm |
| `gmail_monitor.py` | IMAP lecture INBOX, détection réponsesknown leads, DNC keywords, notify Telegram | imaplib, email |
| `linkedin_outreach.py` | Playwright + stealth_async, login, invitations, message généré par LLM | playwright, playwright_stealth |
| `telegram_notif.py` | Notifications hot lead sur réponse positive | requests |
| `logger.py` | Logging erreurs → errors.log + stdout | logging |
| `leads_csv.py` | Toutes les ops CSV (load, add, update, is_duplicate, compteurs) | pandas |
| `__init__.py` | Vide |

## Variables d'environnement (.env)

```
=== LLM ===
OPENROUTER_API_KEY
OPENROUTER_MODEL=openrouter/auto

=== EMAIL ===
GMAIL_ADDRESS
GMAIL_APP_PASSWORD

=== LINKEDIN ===
LINKEDIN_EMAIL
LINKEDIN_PASSWORD

=== CIBLE ===
TARGET_SECTOR=healthtech,medtech,biotech
TARGET_COUNTRY=France
TARGET_STAGE=seed,series_a
TARGET_ROLES=CMO,Head of Marketing,Founder,CEO
MY_SERVICE=3D medical animation delivered in 5 days for biotech fundraising and medical conferences

=== NOTIFICATIONS ===
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID

=== NOTION ===
NOTION_TOKEN
NOTION_DATABASE_ID

=== ENRICHISSEMENT ===
HUNTER_API_KEY
```

## Rate limits réels

- **100 emails/jour** (pas 50 comme souvent mentionné)
- **130 invitations LinkedIn/mois** (pas 80)
- Si un repo échoue → logger dans data/errors.log et continuer
- Ne jamais contacter deux fois le même lead (déduplication via email + linkedin_url)

## run.py — Flags disponibles

```bash
python3 run.py                  # Pipeline complet (scrape → enrich → followup → preview → send → linkedin → monitor)
python3 run.py --scrape         # Scraping startups uniquement
python3 run.py --enrich         # Enrichissement emails + LinkedIn URL uniquement
python3 run.py --preview        # Génère + affiche les emails (NE LES ENVOIT PAS — attend confirmation)
python3 run.py --send           # Envoie les emails pending (après --preview, confirmation interactive)
python3 run.py --followup       # Relances J+3/J+7/J+14 uniquement
python3 run.py --linkedin       # Invitations LinkedIn uniquement
python3 run.py --monitor        # Surveillance réponses Gmail uniquement
python3 run.py --test           # Test de tous les composants (8/8)
python3 run.py --max-leads N    # Nombre max de leads à scraper (défaut: 9999)
```

### Étapes du pipeline (ordre d'exécution pour run complet)

```
step_scrape         → Scraping startups FR → ajoute à leads.csv
step_enrich         → Enrichit emails (Hunter + site + theHarvester + SMTP) + LinkedIn URL
step_followups      → Envoie les relances en retard (J+3/J+7/J+14)
step_preview_emails → Génère emails LLM + affiche pour validation
step_send_emails   → Envoie les emails validés (confirmation interactive)
step_linkedin      → Invitations aux leads éligibles (email 3+ jours avant)
step_monitor_replies→ Vérifie Gmail IMAP, traite réponses, notifie Telegram
```

## Gestion des réponses et relances

### Séquence de relances email automatique
- J+3 : relance courte via LLM (`llm.generate_followup_j3`)
- J+7 : nouvel angle via LLM (`llm.generate_followup_j7`)
- J+14 : break-up email via LLM (`llm.generate_followup_j14`)
- Après J+14 : statut "Froid" dans Notion, stop contact
- Si réponse détectée à n'importe quelle étape → stopper toutes les relances

### Détection des réponses Gmail
- Script qui surveille GMAIL_ADDRESS toutes les heures (cron `--monitor`)
- Si nouvelle réponse : mettre à jour colonne "Statut" dans Notion
- Si mots-clés négatifs détectés (pas intéressé, no thanks, unsubscribe, stop) → marquer "DNC"
- Si réponse positive → marquer "Intéressé" et envoyer notification Telegram

### Notifications Telegram
- Token dans .env sous TELEGRAM_BOT_TOKEN
- Chat ID dans .env sous TELEGRAM_CHAT_ID
- Format : "🔥 Nouveau lead chaud : [Prénom] de [Boîte] a répondu !"

### Déduplication cross-canal
- Si un lead est contacté par email : attendre 3 jours avant d'envoyer l'invitation LinkedIn
- Ne jamais contacter deux fois le même email ou profil LinkedIn

## CRM — Notion

- Token et ID dans .env sous NOTION_TOKEN et NOTION_DATABASE_ID
- Utiliser la librairie `httpx` (API directe, contournement bug notion-client)
- Colonnes dans la base Notion :
  Nom | Prénom | Boîte | Domaine | Email | LinkedIn_URL |
  Statut | Canal | Date_Email | Date_LinkedIn |
  Relance_J3 | Relance_J7 | Relance_J14 | Réponse | DNC | Notes
- Statuts : Nouveau → Email envoyé → LinkedIn envoyé → Relancé → Intéressé → Call planifié → Froid → DNC
- Chaque action loggée dans Notion avec timestamp
- Si Notion échoue : fallback sur leads.csv et continuer

## Personnalisation des emails (règles strictes)

### Email initial (60-80 mots)
- Généré par `llm.py` → `generate_email()`
- Jamais "Bonjour" en début d'email (utiliser "Salut" ou ouvrir directement)
- Jamais "mon message vous est bien parvenu" (daté)
- Jamais "Un exemple vous intéressant ?" (script de vente)
- Jamais énumérer tous les cas d'usage ("levée ou congrès")
- Jamais "Je reste disponible" (cliché)
- Jamais "Je ferme le dossier" (robotique)
- Jamais "pour être concret" (daté) dans les relances
- Toujours signer "— Edgar"
- Scraper le site web + DuckDuckGo news 2026 pour personnaliser

### Relance J+3 (15-20 mots) — via LLM
- Courte, directe, pas de culpabilisation
- Pas de "j'espère que vous allez bien"

### Relance J+7 (40-50 mots) — via LLM
- Nouvel angle avec micro-résultat concret
- Termine par une question ouverte

### Relance J+14 (10-15 mots) — via LLM
- Break-up email, naturel, court, bienveillant

### Message LinkedIn (280 caractères max)
- Généré via LLM par `generate_linkedin_message()`
- Jamais "Bonjour"
- Jamais lister tous les services

## Bugs actifs connus

| Bug | Fichier | Impact | Statut |
|-----|---------|--------|--------|
| `smtplib.SMTPRejectError` n'existe pas dans Python | `email_enricher.py:317` | L'enrichissement SMTP crash si l'exception est levée | À corriger : remplacer par `smtplib.SMTPSenderRefused` ou `Exception` générique |
| Notion database introuvable | `notion_crm.py` | Pas de sync Notion | Vérifier que la DB est partagée avec l'intégration "Propects" — lancer `python3 setup_notion.py` |
| `NameError: 'email' is not defined` au preview | `run.py` ligne ~259 | Les emails ne peuvent pas être pré-générés en bloc | À corriger : vérifier le parsing de l f-string dans log_error |
| Templates relances hardcodés dans email_sender.py | `email_sender.py` | Les fonctions `_build_relance_j3/j7/j14` ne sont PLUS appelées par run.py mais le code reste là | Danger de confusion — à supprimer ou documenter comme legacy |
| La limite email affichée dit 100/jour | `run.py:284` | Affiche 100, CLAUDE.md disait 50 | Limite réelle = 100 (config.py) — à jour |

## Fichier pivot : data/leads.csv

16 colonnes :
```
nom, prenom, boite, domaine, email, linkedin_url,
statut, canal, date_email, date_linkedin,
relance_j3, relance_j7, relance_j14,
reponse, dnc, notes
```

Tous les leads sont à "Nouveau" — aucune action encore envoyée.

## scrape_pipeline.py — Script autonome

Écrit dans `data/leads.csv` avec **déduplication** :
- Ne jamais écraser les leads existants (vérifie par email ET domaine)
- Ajoute uniquement les nouveaux leads
- Sources : liste curatée (56 boîtes) + France Biotech API + Maddyness

```bash
python3 scrape_pipeline.py   # Scrape et ajoute à leads.csv (dédupliqué)
```

## Cron jobs actifs

```
# Pipeline complet — lundi 9h UTC
0 9 * * 1 /usr/bin/python3 /home/mbped/prospecting/run.py >> .../prospecting.log 2>&1

# Surveillance Gmail — toutes les heures
0 * * * * cd /home/mbped/prospecting && /usr/bin/python3 ...run.py --monitor >> .../monitor.log 2>&1

# Relances — 9h30 UTC chaque jour
30 9 * * * cd /home/mbped/prospecting && /usr/bin/python3 ...run.py --followup >> .../followup.log 2>&1
```

## Règles absolues

- Ne jamais hardcoder de credentials — toujours lire depuis .env
- Si un composant échoue, logger l'erreur dans data/errors.log et continuer
- Ne jamais contacter deux fois le même lead (vérifier leads.csv avant d'envoyer)
- Respecter les rate limits : 100 emails/jour, 130 LinkedIn/mois
- Tout ce qui est envoyé doit être loggé dans Notion avec timestamp
- Les relances passent toujours par llm.py (génération LLM), pas par des templates hardcodés