"""
Wrapper OpenRouter (compatible OpenAI SDK).
"""
from openai import OpenAI
from modules.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL
from modules.logger import log_error

_client = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
        )
    return _client

def invoke_llm(system_prompt: str, user_message: str, model: str = None, max_tokens: int = 1024) -> str:
    model = model or OPENROUTER_MODEL
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log_error("llm", e, f"invoke_llm model={model}")
        return ""

def generate_email(company_name: str, prenom: str, recent_news: str,
                   sector: str = "", stage: str = "") -> dict:
    """
    Génère un email complet (objet + corps) pour un lead.
    Retourne {"subject": str, "body": str}.
    """
    has_news = bool(recent_news and recent_news.strip())

system = """Tu es Edgar Frinis, freelance qui crée des animations 3D médicales pour les biotech.

Ton style : concis, direct, sans blabla. Pas de phrases commerciales type "un exemple vous intéressant ?".

RÈGLES ABSOLUES — INTERDIT :
- MAXIMUM 80 MOTS dans le corps (hors signature "— Edgar"). Compte les mots avant de répondre.
- PAS de salutation en ouverture (pas de "Bonjour", "Salut", prénom seul, "Cher"). Commence directement par la phrase d'accroche.
- JAMAIS "mon message vous est bien parvenu" (c'est daté)
- JAMAIS "Je reste disponible" (cliché)
- JAMAIS "Je ferme le dossier" (robotique)
- JAMAIS de liste de cas d'usage ("levée ou congrès")
- JAMAIS "Aurais-tu" (utiliser "Auriez-vous")
- JAMAIS "Nom de l'entreprise" — remplacer par le vrai nom
- JAMAIS "Nom de la molérence" — remplacer par le vrai nom du candidat médicament
- JAMAIS faute de conjugaison : "pour échange" → INTERDIT. Toujours vérifier les terminaisons ("pour échanger", "pour discuter")
- JAMAIS email générique : chaque email DOIT contenir au moins une info spécifique à la boîte (produit, stade clinique, technologie) — jamais de remplissage générique type "je comprends votre secteur"
- JAMAIS CTA condescendant : INTERDIT "Avez-vous déjà envisagé" — cela sous-entend que le prospect n'y a pas pensé. Utiliser "Est-ce que ça vous serait utile" ou question similaire sans jugement
- JAMAIS question de clotûre vague : la question finale DOIT mener vers un call de 15 min. Pas de "N'hésitez pas à me répondre" ou "Donnez-moi votre retour". FormatOK: "Ça vous parlerait un échange de 15 min ?"
- L'objet doit attirer la curiosité, pas décrire le service

FORMAT :
Objet: [sujet court, 4-6 mots, intrigant]

[Phrase d'accroche directe, sans aucune salutation — 2-3 phrases, MAXIMUM 80 MOTS]

— Edgar"""

    if has_news:
        context = f"""Destinataire: {prenom} de {company_name}
Secteur: {sector}, stade: {stage}

INFO 2026 DISPONIBLE:
{recent_news}

SPECIFIC KNOWLEDGE — à utiliser dans l'email si pertinent:
- Cilcare: candidat médicament CIL001 (synaptopathie cochléaire, perte auditive cachée)
- TreeFrog Therapeutics: biotech spécialisée en thérapie cellulaire par microcapsules
- Abivax: biotech développant obefazimod pour rectocolite hémorragique
- DNA Script: enzymologie synthétique, imprimantes ADN

Génère un email avec:
- Une phrase de transition basique basée sur l'info (sans commentaire style "impressionnant")
- 1-2 phrases sur ce que tu fais (pas de "je crée des animations 3D de mécanismes d'action", plutôt "je fais des visuels 3D pour les biotech")
- Close avec une question ouverte (pas de "un exemple vous intéressant")

Objet: court et intrigant"""
    else:
        context = f"""Destinataire: {prenom} de {company_name}
Secteur: {sector}, stade: {stage}

PAS D'INFO SUR LA BOÎTE.

Génère un email:
- Sans rien inventer
- 1 phrase qui montre que tu comprends leur contexte ({stage} dans {sector})
- Ce que tu fais en 1 phrase
- Question directe

Objet: court et intrigant"""

    result = invoke_llm(system, context, max_tokens=250)

    # Parser objet et corps
    subject = ""
    body = result
    if result.startswith("Objet:"):
        lines = result.split("\n", 1)
        subject = lines[0].replace("Objet:", "").strip()
        body = lines[1].strip() if len(lines) > 1 else result
    elif "Objet :" in result:
        parts = result.split("Objet :", 1)
        rest = parts[1].split("\n", 1)
        subject = rest[0].strip()
        body = rest[1].strip() if len(rest) > 1 else result

    if not subject:
        subject = f"Visuel 3D pour {company_name} ?"

    return {"subject": subject, "body": body}


def generate_personalized_hook(company_name: str, prenom: str, recent_news: str,
                               sector: str = "", stage: str = "") -> str:
    """Compatibilité ascendante — retourne uniquement le corps de l'email."""
    result = generate_email(company_name, prenom, recent_news, sector, stage)
    return result.get("body", "")


def generate_followup_j3(company_name: str, prenom: str) -> dict:
    """Relance J+3 - courte, directe, sans culpabilisation."""
    system = """Tu es Edgar. Relance concise, 1-2 phrases, 15-20 mots.
RÈGLES ABSOLUES — INTERDIT :
- Pas de "j'espère que vous allez bien"
- Pas de "vous n'avez peut-être pas eu le temps"
- Pas de faute de conjugaison ("pour échange" → INTERDIT, utiliser "pour échanger")
- Pas de question condescendante type "Avez-vous déjà envisagé"
- La question finale DOIT mener vers un call de 15 min.
OK: phrase directe + question vers un call."""

    context = f"Destinataire: {prenom},entreprise: {company_name}\n\nGénère une relance courte et naturelle."

    result = invoke_llm(system, context, max_tokens=80)
    subject = f"Re: {company_name}"
    return {"subject": subject, "body": result.strip()}


def generate_followup_j7(company_name: str, prenom: str, sector: str = "") -> dict:
    """Relance J+7 - nouvel angle avec cas concret."""
    system = """Tu es Edgar. Relance avec un exemple concret, 40-50 mots.
RÈGLES ABSOLUES — INTERDIT :
- PAS "pour être concret" (daté)
- PAS de liste de références
- Pas de faute de conjugaison
- Pas de question condescendante
- La question finale DOIT mener vers un call de 15 min
NARRATIF: raconte un micro-résultat (pas "j'ai animé", plutôt "j'ai fait un visuel...")."""

    context = f"Destinataire: {prenom},entreprise: {company_name},secteur: {sector}\n\nGénère une relance avec un mini-cas client, sans nommer le client."

    result = invoke_llm(system, context, max_tokens=150)
    return {"subject": f"Re: {company_name}", "body": result.strip()}


def generate_followup_j14(company_name: str, prenom: str) -> dict:
    """Break-up email J+14 - derniers mots, sans pression."""
    system = """Tu es Edgar. Dernier email, 1 phrase, 10-15 mots max.
RÈGLES ABSOLUES — INTERDIT :
- Pas "je ferme le dossier" (robotique)
- Pas "je reste disponible" (cliché)
- Pas de faute de conjugaison
- La question finale DOIT mener vers un call de 15 min
Ton naturel: court et bienveillant, genre "ok, on se refuse. Je suis là si besoin."""

    context = f"Destinataire: {prenom},entreprise: {company_name}\n\nGénère un message de clôture hyper-court."

    result = invoke_llm(system, context, max_tokens=50)
    return {"subject": f"Re: {company_name}", "body": result.strip()}
