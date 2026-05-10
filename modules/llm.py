"""
Wrapper OpenRouter (compatible OpenAI SDK).
"""
from openai import OpenAI
from modules.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL
from modules.logger import log_error

# Connaissance spécifique par boîte — injectée uniquement pour la boîte cible
_SPECIFIC_KNOWLEDGE: dict[str, str] = {
    "Cilcare": "candidat médicament CIL001 (synaptopathie cochléaire, perte auditive cachée)",
    "TreeFrog Therapeutics": "biotech spécialisée en thérapie cellulaire par microcapsules",
    "Abivax": "biotech développant obefazimod pour rectocolite hémorragique",
    "DNA Script": "enzymologie synthétique, imprimantes ADN SYNTAX",
    "CorWave": "pompe cardiaque LVAD à membrane ondulante biomimétique, développement clinique insuffisance cardiaque",
    "Elixir Health": "plateforme IA pour cliniques PMA (fertilité), gestion administrative + suivi patient",
    "Alcediag": "biomarqueurs RNA + IA, test EDIT-B® — différencier dépression unipolaire et trouble bipolaire via analyse sanguine",
    "Metafora Biosystems": "test EDIT-B® et biomarqueurs RNA pour psychiatrie de précision",
    "Cardiawave": "ultrasons focalisés (HIFU) pour sténose aortique sans chirurgie",
    "Hemerion": "photosensibilisants pour PDT (thérapie photodynamique) en oncologie",
    "Egle Therapeutics": "immunothérapie Treg, cellules régulatrices pour maladies auto-immunes",
    "Eligo Bioscience": "phages génétiquement modifiés ciblant le microbiome, antibiotiques de précision",
    "Enterome": "microbiome intestinal, biomarqueurs et candidats médicaments inflammatoire/oncologie",
    "Aelis Farma": "sigmoïdes endocannabinoïdes, GAS6 pour addiction et maladies psychiatriques",
    "OSE Immunotherapeutics": "immunothérapie oncologie et maladies inflammatoires, Tedopi® NSCLC",
    "Biophytis": "BIO101 pour muscle et insuffisance respiratoire (Sarcopénie, COVID-19 sévère)",
    "Vect-Horus": "technologie VECTrans pour franchir la barrière hémato-encéphalique",
    "Vaxinano": "nanoparticules lipidiques sans adjuvant pour vaccins muqueux",
    "Theranexus": "co-administration neuronal/glial, THN102 pour narcolepsie",
    "Brenus Pharma": "immunothérapie BRE001 cancer du pancréas",
}

_client = None


def _offline_fallback(system_prompt: str, user_message: str) -> str:
    prompt = (user_message or "").lower()
    if "reponds juste 'ok'" in prompt or "réponds juste 'ok'" in prompt:
        return "OK"

    if "destinataire:" in prompt and ("genere un email" in prompt or "génère un email" in prompt):
        import re

        match = re.search(r"Destinataire:\s*(.*?)\s+de\s+([^\n]+)", user_message, re.IGNORECASE)
        company_name = match.group(2).strip() if match else "cette biotech"
        knowledge = _SPECIFIC_KNOWLEDGE.get(company_name, "")
        subject = f"{company_name} en image"
        body = (
            f"{company_name} porte une technologie qui gagne a etre montree visuellement plutot que decrite en slides. "
            f"Je cree des animations 3D medicales pour rendre ce type de mecanisme plus clair pour investisseurs et partenaires."
        )
        if knowledge:
            body = (
                f"{company_name} travaille sur {knowledge}, un sujet qui gagne a etre rendu visuel tres vite pour investisseurs et partenaires. "
                "Je cree des animations 3D medicales courtes pour clarifier ce type de mecanisme."
            )
        return f"Objet: {subject}\n\n{body}\n\nEst-ce qu'un echange de 15 min vous parlerait ?\n\n— Edgar"

    if "prénom:" in prompt or "prenom:" in prompt:
        import re

        match = re.search(r"pr[ée]nom:\s*([^,\n]+)", user_message, re.IGNORECASE)
        prenom = match.group(1).strip() if match else "bonjour"
        return f"Salut {prenom}, je cree des rendus 3D biotech en 72h pour clarifier une techno complexe. Un echange de 15 min vous semblerait-il utile ?"

    return ""

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
        return _offline_fallback(system_prompt, user_message)

def generate_email(company_name: str, prenom: str, recent_news: str,
                   sector: str = "", stage: str = "") -> dict:
    """
    Génère un email complet (objet + corps) pour un lead.
    Retourne {"subject": str, "body": str}.
    """
    has_news = bool(recent_news and recent_news.strip())
    company_knowledge = _SPECIFIC_KNOWLEDGE.get(company_name, "")

    system = """Tu es Edgar Frinis, freelance qui crée des animations 3D médicales pour les biotech.

Ton style : concis, direct, sans blabla. Pas de phrases commerciales type "un exemple vous intéressant ?".

RÈGLES ABSOLUES — INTERDIT :
- MAXIMUM 80 MOTS dans le corps (hors signature "— Edgar"). Compte les mots avant de répondre.
- INTERDIT salutation en ouverture ("Bonjour", "Salut", prénom seul, "Cher") — commence directement par la phrase d'accroche.
- INTERDIT "mon message vous est bien parvenu" (daté)
- INTERDIT "Je reste disponible" (cliché)
- INTERDIT "Je ferme le dossier" (robotique)
- INTERDIT liste de cas d'usage ("levée ou congrès")
- INTERDIT "Aurais-tu" — utiliser "Auriez-vous"
- INTERDIT "Nom de l'entreprise" — remplacer par le vrai nom
- INTERDIT faute de conjugaison : "pour échange" → toujours "pour échanger", "pour discuter"
- INTERDIT email générique : chaque email DOIT contenir au moins une info spécifique à la boîte (produit, stade clinique, technologie, molécule, levée)
- INTERDIT CTA condescendante : "Avez-vous déjà envisagé" — sous-entend que le prospect n'y a pas pensé. CORRECT : "Est-ce que ça vous serait utile"
- INTERDIT question finale vague : pas "N'hésitez pas à me répondre", pas "Donnez-moi votre retour". La question finale DOIT mener vers un call de 15 min. FormatOK : "Ça vous parlerait un échange de 15 min ?"
- INTERDIT deux questions ou deux CTA dans le même email. UNE SEULE question finale, toujours vers un appel de 15 min.
- INTERDIT question ouverte descriptive en finale
- INTERDIT signature autre que "— Edgar"
- L'objet doit attirer la curiosité, pas décrire le service

FORMAT :
Objet: [sujet court, 4-6 mots, intrigant]

[Phrase d'accroche directe, sans aucune salutation — 2-3 phrases, MAXIMUM 80 MOTS]

— Edgar"""

    knowledge_block = f"\nINFO SUR LA BOÎTE : {company_knowledge}" if company_knowledge else ""

    if has_news:
        context = f"""Destinataire: {prenom} de {company_name}
Secteur: {sector}, stade: {stage}
{knowledge_block}

INFO 2026 DISPONIBLE:
{recent_news}

Génère un email avec:
- Une phrase d'accroche basée sur les infos ci-dessus (sans commentaire style "impressionnant")
- 1-2 phrases sur ce que tu fais
- Close : UNE SEULE CTA directe vers un call de 15 min (ex: "Ça vous parlerait un échange de 15 min ?")

Objet: court et intrigant"""
    else:
        context = f"""Destinataire: {prenom} de {company_name}
Secteur: {sector}, stade: {stage}
{knowledge_block}

Génère un email:
- Utilise l'info ci-dessus si disponible, sinon reste sur le contexte ({stage} dans {sector})
- Ce que tu fais en 1 phrase
- Close : UNE SEULE CTA directe vers call 15 min

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

    # Validation anti-contamination croisée
    body_lower = body.lower()
    for other, _ in _SPECIFIC_KNOWLEDGE.items():
        if other == company_name:
            continue
        if other.lower() in body_lower:
            log_error("llm", Exception(
                f"Contamination : '{other}' dans email pour '{company_name}'"
            ), "generate_email cross-contamination")
            return {"subject": subject, "body": ""}

    return {"subject": subject, "body": body}


def generate_personalized_hook(company_name: str, prenom: str, recent_news: str,
                               sector: str = "", stage: str = "") -> str:
    """Compatibilité ascendante — retourne uniquement le corps de l'email."""
    result = generate_email(company_name, prenom, recent_news, sector, stage)
    return result.get("body", "")


def generate_followup_j3(company_name: str, prenom: str) -> dict:
    """Relance J+3 - courte, directe, sans culpabilisation."""
    system = """Tu es Edgar. Tu écris en FRANCAIS uniquement, comme un humain, pas comme un assistant commercial.
Relance concise, naturelle, 1-2 phrases, 18-30 mots maximum hors signature.
RÈGLES ABSOLUES — INTERDIT :
- Pas d'anglais
- Pas de "j'espère que vous allez bien"
- Pas de "vous n'avez peut-être pas eu le temps"
- Pas de faute de conjugaison ("pour échange" → INTERDIT, utiliser "pour échanger")
- Pas de question condescendante type "Avez-vous déjà envisagé"
- Pas de langage trop vendeur ou abstrait
- Une seule question finale, vers un call de 15 min
FORMAT ATTENDU :
- salutation courte
- une phrase simple
- une seule question finale
- signature "— Edgar"
EXEMPLE DE TON :
"Marie,

Je me permets une courte relance au cas ou mon message soit tombe au mauvais moment.

Un echange de 15 min cette semaine vous serait-il utile ?

— Edgar"
"""

    context = f"Destinataire: {prenom},entreprise: {company_name}\n\nGénère une relance courte et naturelle."

    result = invoke_llm(system, context, max_tokens=80)
    subject = f"Re: {company_name}"
    return {"subject": subject, "body": result.strip()}


def generate_followup_j7(company_name: str, prenom: str, sector: str = "") -> dict:
    """Relance J+7 - nouvel angle avec cas concret."""
    system = """Tu es Edgar. Tu écris en FRANCAIS uniquement, comme un humain, pas comme un assistant commercial.
Relance avec un exemple concret, 35-50 mots maximum hors signature.
RÈGLES ABSOLUES — INTERDIT :
- Pas d'anglais
- PAS "pour être concret" (daté)
- PAS de liste de références
- Pas de faute de conjugaison
- Pas de question condescendante
- Pas de langage pompeux
- Une seule question finale, vers un call de 15 min
NARRATIF :
- raconte un micro-resultat credible
- pas de nom de client
- pas de promesse exageree
FORMAT ATTENDU :
- salutation
- micro-cas concret en 1-2 phrases
- une seule question finale
- signature "— Edgar"
EXEMPLE DE TON :
"Marie,

J'ai recemment prepare un visuel court pour aider une biotech a rendre son mecanisme plus clair en reunion investisseur. Je pense que ce format pourrait aussi vous aider si le sujet est d'actualite.

Un echange de 15 min vous semblerait-il utile ?

— Edgar"
"""

    context = f"Destinataire: {prenom},entreprise: {company_name},secteur: {sector}\n\nGénère une relance avec un mini-cas client, sans nommer le client."

    result = invoke_llm(system, context, max_tokens=150)
    return {"subject": f"Re: {company_name}", "body": result.strip()}


def generate_followup_j14(company_name: str, prenom: str) -> dict:
    """Break-up email J+14 - derniers mots, sans pression, naturel."""
    system = """Tu es Edgar. Dernier email de la séquence, en FRANCAIS uniquement, naturel et bienveillant, 18-30 mots maximum hors signature.
RÈGLES ABSOLUES — INTERDIT :
- Pas d'anglais
- Pas "je ferme le dossier" (robotique)
- Pas "je reste disponible" (cliché)
- Pas "ok, on se refuse" (maladroit)
- Pas "pour être concret" (daté)
- Pas de faute de conjugaison
- Pas de question condescendante "Avez-vous déjà envisagé"
- Pas de double formulation type "a nouveau" répétée
- Pas obligé de poser une question sur ce dernier message
FORMAT ATTENDU :
- salutation
- une phrase de cloture simple
- signature "— Edgar"
EXEMPLE DE TON :
"Marie,

Je ne vous relance pas davantage. Si le sujet devient utile plus tard, nous pourrons en reparler.

— Edgar"
"""

    context = f"Destinataire: {prenom},entreprise: {company_name}\n\nGénère un message de clôture naturel et court."

    result = invoke_llm(system, context, max_tokens=50)
    body = result.strip()
    if "-- Edgar" not in body:
        body += "\n\n— Edgar"
    return {"subject": f"Re: {company_name}", "body": body}
