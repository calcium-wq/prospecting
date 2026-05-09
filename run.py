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
import json
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

_GENERIC_EMAIL_PREFIXES = {
    "contact", "hello", "info", "bonjour", "contact-us", "admin",
    "support", "noreply", "no-reply", "sales", "marketing", "service",
    "team", "equipe",
}
_BAD_PRENOM_VALUES = {
    "fondateur", "founder", "contact", "support", "admin", "ceo",
    "directeur", "hello", "marketing", "sales", "service", "team",
}


def is_generic_email(email: str) -> bool:
    prefix = email.split("@")[0].lower()
    return prefix in _GENERIC_EMAIL_PREFIXES


PRENOM_CORRECTIONS: dict[str, tuple[str, str]] = {
    "cd@hemerion.com":             ("Clement", "Dupont"),
    "prinaudo@enterome.com":       ("Philippe", "Rinaudo"),
    "ofriedrich@cellprothera.com": ("Olivier", "Friedrich"),
    "jhutin@steminov.com":         ("Jean", "Hutin"),
    "rbarbaras@abionyx.com":       ("Ronald", "Barbaras"),
    "c.estrella@alzprotect.com":   ("Cecilia", "Estrella"),
    "wentworth@transgene.fr":      ("James", "Wentworth"),
    "lsabbagh@domaintherapeutics.com": ("Laurent", "Sabbagh"),
}

NOTIFY_PRENOM = {}

_pending_emails: list[dict] = []
PENDING_EMAILS_PATH = DATA_DIR / "pending_emails.json"

MANUAL_EMAIL_OVERRIDES: dict[str, dict[str, str]] = {'jhutin@steminov.com': {'subject': 'StemInov en image',
                         'body': 'Vos travaux sur les cellules souches mesenchymateuses issues de la gelee de Wharton '
                                 'demandent une explication claire pour des investisseurs. Je cree des animations 3D '
                                 'medicales qui rendent visibles les mecanismes cellulaires complexes, sans jargon '
                                 'inutile.\n'
                                 '\n'
                                 'Seriez-vous disponible pour un echange de 15 min ?\n'
                                 '\n'
                                 '-- Edgar'},
 'nicolas.fournier@dessintey.com': {'subject': 'Votre IVS en mouvement',
                                    'body': "Dessintey transforme la reeducation avec l'IVS, STIIMP et SRT. Ces "
                                            'technologies sont fortes, mais leur logique neuromotrice reste difficile '
                                            'a saisir en quelques slides. Je cree des animations 3D medicales pour '
                                            'rendre ce type de mecanisme immediatement comprehensible.\n'
                                            '\n'
                                            'Seriez-vous disponible pour un echange de 15 min ?\n'
                                            '\n'
                                            '-- Edgar'},
 'jamal.temsamani@vect-horus.com': {'subject': 'VECTrans en 3D',
                                    'body': 'La technologie VECTrans a un enjeu visuel evident : faire comprendre le '
                                            'franchissement de la barriere hemato-encephalique. Je cree des animations '
                                            '3D medicales qui rendent ce type de mecanisme clair pour des '
                                            'investisseurs ou partenaires scientifiques.\n'
                                            '\n'
                                            'Seriez-vous disponible pour un echange de 15 min ?\n'
                                            '\n'
                                            '-- Edgar'},
 'angelo.scuotto@vaxinano.com': {'subject': 'Vos vaccins muqueux en image',
                                 'body': 'Votre approche autour des nanoparticules lipidiques pour vaccins muqueux '
                                         'gagne a etre vue, pas seulement decrite. Je cree des animations 3D medicales '
                                         'pour transformer des mecanismes immunologiques complexes en supports courts, '
                                         'precis et utiles en presentation.\n'
                                         '\n'
                                         'Seriez-vous disponible pour un echange de 15 min ?\n'
                                         '\n'
                                         '-- Edgar'},
 'marie.sebille@theranexus.com': {'subject': 'Le THN102 en mouvement',
                                  'body': "L'approche neuronal-glial de Theranexus demande une vraie pedagogie "
                                          'visuelle. Je cree des animations 3D medicales qui rendent lisibles les '
                                          'mecanismes cellulaires complexes, notamment quand il faut expliquer une '
                                          'differenciation scientifique a des investisseurs.\n'
                                          '\n'
                                          'Seriez-vous disponible pour un echange de 15 min ?\n'
                                          '\n'
                                          '-- Edgar'},
 'anais.david@nateosante.com': {'subject': "Rendre visible l'air traite",
                                'body': "L'EOLIS Air Manager traite un sujet invisible par nature : qualite de l'air, "
                                        'filtration, flux, particules. Je cree des animations 3D medicales et '
                                        'techniques pour rendre ce fonctionnement tangible dans des supports '
                                        'commerciaux ou investisseurs.\n'
                                        '\n'
                                        'Seriez-vous disponible pour un echange de 15 min ?\n'
                                        '\n'
                                        '-- Edgar'},
 'eric.jague@affluentmedical.com': {'subject': 'Epygon en 3D',
                                    'body': "Les dispositifs d'Affluent Medical comme Epygon ou Kalios reposent sur "
                                            'des interactions anatomiques fines. Je cree des animations 3D medicales '
                                            'pour rendre ces mecanismes immediatement comprehensibles aupres '
                                            "d'investisseurs, chirurgiens ou partenaires.\n"
                                            '\n'
                                            'Seriez-vous disponible pour un echange de 15 min ?\n'
                                            '\n'
                                            '-- Edgar'},
 'france.jean.garrec@biophta.com': {'subject': 'Vos micro-inserts en image',
                                    'body': "Les micro-inserts ophtalmiques de Biophta ont besoin d'une explication "
                                            'visuelle precise : diffusion, positionnement, liberation prolongee. Je '
                                            'cree des animations 3D medicales qui transforment ce mecanisme en '
                                            'demonstration claire et courte.\n'
                                            '\n'
                                            'Seriez-vous disponible pour un echange de 15 min ?\n'
                                            '\n'
                                            '-- Edgar'},
 'brian.schwab@erytech.com': {'subject': 'ERYCAPS en mouvement',
                              'body': "La plateforme ERYCAPS, avec l'encapsulation de substances actives dans les "
                                      'globules rouges, devient tres visuelle quand elle est bien modelisee. Je cree '
                                      'des animations 3D medicales pour rendre ce mecanisme cellulaire clair en '
                                      'quelques secondes.\n'
                                      '\n'
                                      'Seriez-vous disponible pour un echange de 15 min ?\n'
                                      '\n'
                                      '-- Edgar'},
 'boris.leveque@axomove.com': {'subject': 'La reeducation Axomove en 3D',
                               'body': "Axomove rend la reeducation plus accessible, mais l'impact d'un protocole "
                                       'therapeutique reste parfois abstrait pour des decideurs. Je cree des '
                                       'animations 3D medicales pour visualiser mouvement, articulation et benefice '
                                       'patient avec un rendu clair.\n'
                                       '\n'
                                       'Seriez-vous disponible pour un echange de 15 min ?\n'
                                       '\n'
                                       '-- Edgar'},
 'steve@smartimmune.com': {'subject': 'ProTcell en image',
                           'body': 'La plateforme ProTcell touche a une mecanique immunitaire difficile a vulgariser : '
                                   'progeniteurs, lymphocytes T, restauration immunitaire. Je cree des animations 3D '
                                   'medicales pour transformer cette science en support clair pour investisseurs et '
                                   'partenaires.\n'
                                   '\n'
                                   'Seriez-vous disponible pour un echange de 15 min ?\n'
                                   '\n'
                                   '-- Edgar'},
 'bjoern.gerold@theraclion.com': {'subject': 'SONOVEIN en mouvement',
                                  'body': "SONOVEIN rend l'echotherapie non invasive tres concrete, mais l'action des "
                                          'ultrasons focalises reste invisible sans visualisation. Je cree des '
                                          'animations 3D medicales pour expliquer cette interaction tissu-dispositif '
                                          'avec precision.\n'
                                          '\n'
                                          'Seriez-vous disponible pour un echange de 15 min ?\n'
                                          '\n'
                                          '-- Edgar'},
 'celine.breda@xenothera.com': {'subject': 'Vos anticorps en 3D',
                                'body': 'Les anticorps polyclonaux glyco-humanises de Xenothera demandent une '
                                        'pedagogie claire pour etre compris vite hors cercle scientifique. Je cree des '
                                        'animations 3D medicales qui rendent ces mecanismes biologiques lisibles pour '
                                        'investisseurs, partenaires et cliniciens.\n'
                                        '\n'
                                        'Seriez-vous disponible pour un echange de 15 min ?\n'
                                        '\n'
                                        '-- Edgar'},
 'romain.lucas@seabelife.com': {'subject': 'Vos inhibiteurs de necrose en image',
                                'body': "Les travaux de SEABELIFE sur l'inhibition de la necrose cellulaire touchent a "
                                        'des mecanismes difficiles a expliquer rapidement. Je cree des animations 3D '
                                        'medicales pour visualiser ces interactions moleculaires et les rendre '
                                        'comprehensibles en presentation.\n'
                                        '\n'
                                        'Seriez-vous disponible pour un echange de 15 min ?\n'
                                        '\n'
                                        '-- Edgar'},
 'pauline@avatarmedical.ai': {'subject': 'Avatar Medical en image',
                              'body': "Avatar Medical transforme deja l'imagerie medicale en experience 3D "
                                      'exploitable. Je cree des animations medicales cinematiques pour montrer la '
                                      "valeur d'une technologie complexe, avec un rendu clair pour investisseurs, "
                                      'chirurgiens ou partenaires.\n'
                                      '\n'
                                      'Seriez-vous disponible pour un echange de 15 min ?\n'
                                      '\n'
                                      '-- Edgar'},
 'pascal.sirvent@valbiotis.com': {'subject': 'TOTUM-63 en mouvement',
                                  'body': 'Les actifs de Valbiotis, comme TOTUM-63, reposent sur des mecanismes '
                                          'metaboliques qui gagnent a etre visualises. Je cree des animations 3D '
                                          "medicales pour rendre ces modes d'action plus clairs dans des supports "
                                          'investisseurs ou scientifiques.\n'
                                          '\n'
                                          'Seriez-vous disponible pour un echange de 15 min ?\n'
                                          '\n'
                                          '-- Edgar'},
 'colin.mansfield@ab-science.com': {'subject': 'Le masitinib en image',
                                    'body': "Le masitinib repose sur des mecanismes d'inhibition difficiles a "
                                            'vulgariser sans support visuel. Je cree des animations 3D medicales pour '
                                            'transformer cette interaction moleculaire en demonstration claire, utile '
                                            'en pitch investisseur ou presentation scientifique.\n'
                                            '\n'
                                            'Seriez-vous disponible pour un echange de 15 min ?\n'
                                            '\n'
                                            '-- Edgar'},
 'clemence.morillot@incepto-medical.com': {'subject': 'Vos algorithmes en image',
                                           'body': "Incepto rend l'IA medicale plus accessible aux equipes de "
                                                   'radiologie. Je cree des animations 3D medicales pour rendre '
                                                   "visibles des flux d'analyse, algorithmes ou parcours diagnostics "
                                                   'qui restent souvent abstraits dans un deck classique.\n'
                                                   '\n'
                                                   'Seriez-vous disponible pour un echange de 15 min ?\n'
                                                   '\n'
                                                   '-- Edgar'},
 'mathieu@cardiologs.com': {'subject': "L'ECG augmente en 3D",
                            'body': "L'analyse ECG par IA de Cardiologs est puissante, mais son fonctionnement reste "
                                    'difficile a montrer simplement. Je cree des animations 3D medicales pour '
                                    "transformer ce type d'analyse invisible en demonstration claire et memorable.\n"
                                    '\n'
                                    'Seriez-vous disponible pour un echange de 15 min ?\n'
                                    '\n'
                                    '-- Edgar'},
 'frederic.dayan@exactcure.com': {'subject': 'Le jumeau numerique en image',
                                  'body': 'ExactCure rend la reponse medicamenteuse plus personnalisee grace au jumeau '
                                          'numerique. Je cree des animations 3D medicales pour rendre cette simulation '
                                          "concrete et comprehensible aupres d'investisseurs ou partenaires sante.\n"
                                          '\n'
                                          'Seriez-vous disponible pour un echange de 15 min ?\n'
                                          '\n'
                                          '-- Edgar'},
 'nathan.burnel-hauteville@implicity.com': {'subject': 'Implicity en image',
                                            'body': "La telesurveillance cardiaque d'Implicity repose sur des signaux, "
                                                    'alertes et algorithmes difficiles a visualiser dans un support '
                                                    'classique. Je cree des animations 3D medicales pour rendre ce '
                                                    'parcours clinique clair en quelques secondes.\n'
                                                    '\n'
                                                    'Seriez-vous disponible pour un echange de 15 min ?\n'
                                                    '\n'
                                                    '-- Edgar'},
 'andy.karabajakian@owkin.com': {'subject': "L'IA d'Owkin en image",
                                 'body': "Les modeles d'Owkin relient donnees medicales, biologie et decouverte "
                                         'therapeutique. Je cree des animations 3D medicales pour rendre ces '
                                         'mecanismes complexes plus visibles et plus convaincants dans des supports '
                                         'investisseurs ou partenaires.\n'
                                         '\n'
                                         'Seriez-vous disponible pour un echange de 15 min ?\n'
                                         '\n'
                                         '-- Edgar'},
 'david.armand@surgivisio.com': {'subject': 'Surgivisio en 3D',
                                 'body': 'Le guidage 2D/3D de Surgivisio merite une demonstration visuelle aussi '
                                         'precise que la technologie elle-meme. Je cree des animations 3D medicales '
                                         'pour rendre la navigation chirurgicale et le geste assiste immediatement '
                                         'comprehensibles.\n'
                                         '\n'
                                         'Seriez-vous disponible pour un echange de 15 min ?\n'
                                         '\n'
                                         '-- Edgar'},
 'maria.iacono@wandercraft.eu': {'subject': 'Atalante en mouvement',
                                 'body': "L'exosquelette Atalante parle immediatement quand on voit sa stabilisation "
                                         'et sa biomecanique en action. Je cree des animations 3D medicales pour '
                                         "rendre cette technologie robotique claire aupres d'investisseurs, centres de "
                                         'soins ou partenaires.\n'
                                         '\n'
                                         'Seriez-vous disponible pour un echange de 15 min ?\n'
                                         '\n'
                                         '-- Edgar'},
 'leila.farid@feetme.fr': {'subject': 'FeetMe en mouvement',
                           'body': 'Les semelles connectees FeetMe produisent des donnees de marche utiles, mais '
                                   'difficiles a rendre tangibles. Je cree des animations 3D medicales pour '
                                   'transformer ces flux biomecaniques en visuels clairs pour investisseurs, '
                                   'cliniciens ou partenaires.\n'
                                   '\n'
                                   'Seriez-vous disponible pour un echange de 15 min ?\n'
                                   '\n'
                                   '-- Edgar'},
 'sandra.moriceau@metafora-biosystems.com': {'subject': 'Metafora en image',
                                             'body': 'Metafora biosystems travaille sur la caracterisation du metabolisme cellulaire, un sujet puissant mais difficile a expliquer vite. Je cree des animations 3D medicales pour rendre ces flux biologiques plus clairs dans un deck investisseur ou partenaire.\n\nSeriez-vous disponible pour un echange de 15 min ?\n\n-- Edgar'},
 'rbarbaras@abionyx.com': {'subject': 'ABIONYX en mouvement',
                           'body': 'ABIONYX developpe des therapies pour les maladies renales et ophtalmologiques, avec une expertise forte autour des vecteurs HDL. Je cree des animations 3D medicales pour rendre ces mecanismes biologiques visibles et plus faciles a comprendre en presentation.\n\nSeriez-vous disponible pour un echange de 15 min ?\n\n-- Edgar'},
 'c.estrella@alzprotect.com': {'subject': 'AZP2006 en image',
                               'body': 'AZP2006 et la voie progranuline touchent a des mecanismes neurodegeneratifs complexes : tauopathies, inflammation, survie neuronale. Je cree des animations 3D medicales pour transformer ce type de mecanisme en support clair pour investisseurs ou partenaires.\n\nSeriez-vous disponible pour un echange de 15 min ?\n\n-- Edgar'},
 'wentworth@transgene.fr': {'subject': 'Transgene en image',
                            'body': 'Les plateformes myvac et Invir.IO de Transgene reposent sur une science tres visuelle : vecteurs viraux, neoantigenes, immunotherapie personnalisee. Je cree des animations 3D medicales pour rendre ces mecanismes comprehensibles en quelques secondes.\n\nSeriez-vous disponible pour un echange de 15 min ?\n\n-- Edgar'},
 'lsabbagh@domaintherapeutics.com': {'subject': 'Vos GPCR en mouvement',
                                     'body': 'Domain Therapeutics avance sur des programmes GPCR en immuno-oncologie et inflammation, avec des mecanismes difficiles a vulgariser simplement. Je cree des animations 3D medicales pour rendre ces interactions receptorales claires dans un support investisseur ou partenaire.\n\nSeriez-vous disponible pour un echange de 15 min ?\n\n-- Edgar'}}

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
    """Étape 2 : Enrichissement emails."""
    from modules.email_enricher import enrich_lead, extract_prenom_from_email
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
                        save_leads(df)
                except Exception as e:
                    log_error("run.py", e, f"enrich {row.get('domaine', '')}")

        # LinkedIn scraping désactivé — 0 résultats en pratique, ralentit massivement le pipeline
        # Réactiver quand linkedin_url sera disponible directement dans les leads scrappés
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

    is_generic = is_generic_email(email) or prenom in _BAD_PRENOM_VALUES or prenom == ""
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

    manual = MANUAL_EMAIL_OVERRIDES.get(str(corrected.get("email", "")).strip().lower())
    if manual:
        email_content = manual
    else:
        news = get_recent_news_for_company(boite, lead.get("domaine", ""))

        email_content = generate_email(
        company_name=boite,
        prenom=prenom,
        recent_news=news,
        sector="biotech/medtech",
        stage="Seed/Series A"
        )

    body = email_content["body"]
    subject = email_content["subject"]
    import re as _re
    body = _re.sub(r"(Est-ce que\s+)?[\u00c7\u00e7Cc]a vous parlerait un .change de 15 min\s*\?",
                   "Est-ce qu'un \u00e9change de 15 min vous parlerait ?", body, flags=_re.IGNORECASE)
    body = body.replace("\u00c7a vous parlerait un \u00e9change de 15 min ?", "Est-ce qu'un \u00e9change de 15 min vous parlerait ?")
    body = body.replace("Est-ce que \u00e7a vous parlerait un \u00e9change de 15 min ?", "Est-ce qu'un \u00e9change de 15 min vous parlerait ?")
    body = body.replace("Ca vous parlerait un echange de 15 min ?", "Est-ce qu'un echange de 15 min vous parlerait ?")
    body = body.replace("Est-ce que ca vous parlerait un echange de 15 min ?", "Est-ce qu'un echange de 15 min vous parlerait ?")
    body = body.replace("animations 3D chirurgicales et anatomiques", "animations 3D medicales et anatomiques")
    body = body.replace("animations 3D chirurgicales", "animations 3D medicales")


    raw = f"{subject}\n{body}".lower()
    forbidden_fragments = [
        "[", "]", "nom de la technologie", "nom de la mol",
        "nom de l'entreprise", "cela vous parlerait un", "vous parlerait un",
    ]
    if not body.strip():
        raise ValueError("Email LLM vide ou bloque par validation qualite")
    raw_norm = raw.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    if ("edit-b" in raw_norm or "edit b" in raw_norm) and str(boite).strip().lower() != "alcediag":
        raise ValueError(f"Contamination croisee detectee: EDIT-B pour {boite}")
    if any(fragment in raw for fragment in forbidden_fragments):
        raise ValueError(f"Email bloque par validation qualite: {subject}")
    word_count = len(body.split())
    if word_count > 85:
        raise ValueError(f"Email trop long: {word_count} mots")


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
        "subject": subject,
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
        (df["dnc"] == "") &
        (~df["email"].apply(is_generic_email)) &
        (~df["prenom"].fillna("").str.lower().isin(_BAD_PRENOM_VALUES))
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
    if _pending_emails:
        PENDING_EMAILS_PATH.write_text(
            json.dumps(_pending_emails, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"[Preview] Emails sauvegardes pour validation : {PENDING_EMAILS_PATH}")

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
    if not _pending_emails and PENDING_EMAILS_PATH.exists():
        try:
            _pending_emails = json.loads(PENDING_EMAILS_PATH.read_text(encoding="utf-8"))
            print(f"[Send] Emails charg?s depuis la preview valid?e : {PENDING_EMAILS_PATH}")
        except Exception as e:
            log_error("run.py", e, "load pending emails")

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
    """Étape 6 : Vérification des réponses Gmail + résumé quotidien Telegram."""
    from modules.gmail_monitor import check_replies, process_replies
    from modules.telegram_notif import notify_hot_lead, send_daily_summary
    from modules.leads_csv import load_leads
    print("\n" + "="*60)
    print("ÉTAPE 6 — SURVEILLANCE RÉPONSES GMAIL")
    print("="*60)
    hot_count = 0
    try:
        replies = check_replies()
        if not replies:
            print("[GmailMonitor] Aucune nouvelle réponse détectée")
        else:
            print(f"[GmailMonitor] {len(replies)} réponse(s) détectée(s)")
            hot_count = process_replies(replies, notify_fn=notify_hot_lead) or 0
    except Exception as e:
        log_error("run.py", e, "step_monitor_replies")
        print(f"[GmailMonitor] ERREUR : {e} — continuation...")

    try:
        df = load_leads()
        stats = {
            "sent": int((df["statut"] == "Email envoyé").sum()),
            "replies": int(df["reponse"].notna().sum()),
            "followups_due": int((df["statut"] == "Relancé").sum()),
            "no_email": int((df["email"].fillna("") == "").sum()),
            "hot": hot_count,
        }
        send_daily_summary(stats)
    except Exception as e:
        log_error("run.py", e, "send_daily_summary")


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
