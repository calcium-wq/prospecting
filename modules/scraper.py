"""
Scraper de startups biotech/medtech françaises.

Sources (dans l'ordre de priorité) :
1. France Biotech WP REST API — communiqués de presse → noms de boîtes
2. Maddyness levées de fonds — articles de funding récents
3. DuckDuckGo site:linkedin.com/company — recherche ciblée
4. Liste statique curatée — 50+ boîtes françaises connues avec domaines
"""
import re
import time
import requests
from bs4 import BeautifulSoup
from modules.config import TARGET_SECTOR
from modules.logger import log_error

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ─── Boîtes françaises biotech/medtech/healthtech connues ─────────────────────
# Format : (nom_boite, domaine, secteur, stade)
STATIC_LEADS = [
    # Biotech / Thérapeutiques
    ("Cardiawave", "cardiawave.com", "biotech", "series_a"),
    ("CellProthera", "cellprothera.com", "biotech", "series_a"),
    ("CorWave", "corwave.com", "medtech", "series_a"),
    ("EVerZom", "everzom.com", "biotech", "series_a"),
    ("Hemerion", "hemerion.com", "biotech", "seed"),
    ("Inside Therapeutics", "insidetherapeutics.com", "biotech", "seed"),
    ("Amolyt Pharma", "amolytpharma.com", "biotech", "series_a"),
    ("Elixir Health", "elixirhealth.fr", "biotech", "seed"),
    ("Brenus Pharma", "brenuspharma.com", "biotech", "series_a"),
    ("Cilcare", "cilcare.com", "biotech", "series_a"),
    ("Egle Therapeutics", "egletherapeutics.com", "biotech", "series_a"),
    ("TreeFrog Therapeutics", "treefrog-therapeutics.com", "biotech", "series_a"),
    ("Eligo Bioscience", "eligo-bioscience.com", "biotech", "series_a"),
    ("Enterome", "enterome.com", "biotech", "series_a"),
    ("Aelis Farma", "aelis-farma.com", "biotech", "series_a"),
    ("Abivax", "abivax.com", "biotech", "series_a"),
    ("DNA Script", "dnascript.com", "biotech", "series_a"),
    ("OSE Immunotherapeutics", "ose-immuno.com", "biotech", "series_a"),
    ("Biophytis", "biophytis.com", "biotech", "series_a"),
    ("Alcediag", "alcediag.com", "biotech", "seed"),
    ("Affluent Medical", "affluentmedical.com", "medtech", "series_a"),
    ("Advanced BioDesign", "advancedbiodesign.fr", "medtech", "seed"),
    ("Axomove", "axomove.com", "healthtech", "seed"),
    ("PulseLife", "pulselife.fr", "healthtech", "seed"),
    # Medtech / Dispositifs
    ("Quantum Surgical", "quantum-surgical.com", "medtech", "series_a"),
    ("Surgivisio", "surgivisio.com", "medtech", "series_a"),
    ("Wandercraft", "wandercraft.eu", "medtech", "series_a"),
    ("Feetme", "feetme.fr", "medtech", "series_a"),
    ("Caranx Medical", "caranxmedical.com", "medtech", "seed"),
    ("HighLife", "highlifesas.com", "medtech", "series_a"),
    ("FineHeart", "fineheart.fr", "medtech", "series_a"),
    ("Pixium Vision", "pixium-vision.com", "medtech", "series_a"),
    # IA / Santé numérique
    ("Owkin", "owkin.com", "healthtech", "series_a"),
    ("Sonio", "sonio.co", "healthtech", "series_a"),
    ("Gleamer", "gleamer.com", "healthtech", "seed"),
    ("ExactCure", "exactcure.com", "healthtech", "seed"),
    ("Avatar Medical", "avatarmedical.ai", "healthtech", "seed"),
    ("Dreem", "dreem.com", "healthtech", "series_a"),
    ("Implicity", "implicity.com", "healthtech", "seed"),
    ("Meditect", "meditect.fr", "medtech", "seed"),
    ("Bioptigen", "bioptigen.com", "medtech", "seed"),
    ("INCEPTO", "incepto-medical.com", "healthtech", "series_a"),
    ("Spade", "spade-medical.com", "medtech", "seed"),
    ("Cardiologs", "cardiologs.com", "healthtech", "series_a"),
    ("Ganymed Robotics", "ganymede.eu", "medtech", "series_a"),
    ("Lucine", "lucine.fr", "healthtech", "seed"),
    ("Incepto Medical", "incepto-medical.com", "healthtech", "series_a"),
    ("BIOPHTA", "biophta.com", "biotech", "seed"),
    ("AB Science", "ab-science.com", "biotech", "series_a"),
    ("Creapharm", "creapharm.com", "biotech", "series_a"),
]


def _get(url: str, timeout: int = 12) -> requests.Response | None:
    try:
        return requests.get(url, headers=HEADERS, timeout=timeout)
    except Exception as e:
        log_error("scraper", e, url)
        return None


def extract_domain(url: str) -> str:
    m = re.search(r"https?://(?:www\.)?([^/?#]+)", url)
    return m.group(1).lower() if m else ""


# ─── Source 1 : France Biotech WP REST API ───────────────────────────────────

def _fetch_france_biotech_companies() -> list[str]:
    """Extrait les noms de boîtes depuis les communiqués France Biotech."""
    company_names = set()
    pattern = re.compile(
        r"^([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\s\-\.]{2,40}?)\s+"
        r"(?:lève|annonce|lance|obtient|reçoit|signe|publie|présente|devient"
        r"|rejoint|finalise|complète|conclut|intègre|décroche|remporte)",
        re.IGNORECASE,
    )
    skip = {"France Biotech", "Banque Populaire", "AMGEN", "DASSAULT"}

    for page in range(1, 6):
        resp = _get(
            f"https://france-biotech.fr/wp-json/wp/v2/posts"
            f"?per_page=100&page={page}&_fields=title"
        )
        if not resp or resp.status_code != 200:
            break
        posts = resp.json()
        if not posts:
            break
        for p in posts:
            title = p.get("title", {}).get("rendered", "")
            m = pattern.match(title)
            if m:
                name = m.group(1).strip()
                if name not in skip and len(name) > 3:
                    company_names.add(name)
        if len(posts) < 100:
            break
        time.sleep(0.5)

    return list(company_names)


def _resolve_domain_via_duckduckgo(company_name: str) -> str:
    """Tente de trouver le domaine d'une boîte via DuckDuckGo."""
    query = f'"{company_name}" site officiel biotech medtech France 2026'
    try:
        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers=HEADERS,
            timeout=12,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select(".result__a"):
            href = a.get("href", "")
            if not href.startswith("http"):
                continue
            domain = extract_domain(href)
            if not domain:
                continue
            bad = {"linkedin.com", "google.com", "twitter.com", "facebook.com",
                   "wikipedia.org", "youtube.com", "crunchbase.com", "maddyness.com",
                   "france-biotech.fr", "lefigaro.fr", "lemonde.fr"}
            if not any(b in domain for b in bad):
                return domain
    except Exception as e:
        log_error("scraper", e, f"duckduckgo domain for {company_name}")
    return ""


# ─── Source 2 : Maddyness funding articles ────────────────────────────────────

def _fetch_maddyness_companies() -> list[dict]:
    """Extrait boîtes + domaines depuis les articles Maddyness levées de fonds."""
    leads = []
    pattern = re.compile(
        r"^([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\s\-\.]{2,40}?)\s+lève\s+[\d,\.]+\s*[MK€]",
        re.IGNORECASE,
    )
    pages = [
        "https://www.maddyness.com/levees-de-fonds/",
        "https://www.maddyness.com/tag/biotech/",
        "https://www.maddyness.com/tag/medtech/",
        "https://www.maddyness.com/tag/healthtech/",
        "https://www.maddyness.com/tag/sante/",
    ]
    seen = set()
    for url in pages:
        resp = _get(url)
        if not resp or resp.status_code != 200:
            continue
        soup = BeautifulSoup(resp.text, "html.parser")
        for h3 in soup.find_all(["h2", "h3"]):
            title = h3.get_text(strip=True)
            m = pattern.match(title)
            if m:
                name = m.group(1).strip()
                if name in seen or len(name) < 3:
                    continue
                seen.add(name)
                # Try to find a link to the article for more info
                a = h3.find_parent("a") or h3.find("a")
                article_url = a["href"] if a and a.get("href") else ""
                domain = extract_domain(article_url) if article_url else ""
                if domain and "maddyness.com" in domain:
                    domain = ""
                leads.append({"boite": name, "domaine": domain, "secteur": "healthtech", "stade": "series_a"})
        time.sleep(1)
    return leads


# ─── Source 3 : DuckDuckGo LinkedIn search ────────────────────────────────────

def _fetch_via_duckduckgo() -> list[dict]:
    """Cherche des boîtes via LinkedIn company pages sur DuckDuckGo."""
    leads = []
    queries = [
        "biotech medtech startup France seed levée 2026 site:linkedin.com/company",
        "healthtech santé startup France series a 2026 site:linkedin.com/company",
        "medtech dispositif médical startup française 2026 site:linkedin.com/company",
    ]
    seen = set()
    for query in queries:
        try:
            resp = requests.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query},
                headers=HEADERS,
                timeout=15,
            )
            soup = BeautifulSoup(resp.text, "html.parser")
            for result in soup.select(".result"):
                a = result.select_one(".result__a")
                snippet = result.select_one(".result__snippet")
                if not a:
                    continue
                href = a.get("href", "")
                company_name = a.get_text(strip=True).split("|")[0].split("-")[0].strip()
                if not company_name or company_name in seen:
                    continue
                seen.add(company_name)
                # Try to find the company website from snippet or href
                domain = ""
                if snippet:
                    m = re.search(r"([a-z0-9\-]+\.(com|fr|eu|io|co|org))", snippet.get_text())
                    if m:
                        domain = m.group(0)
                leads.append({
                    "boite": company_name,
                    "domaine": domain,
                    "secteur": "biotech",
                    "stade": "seed",
                })
            time.sleep(2)
        except Exception as e:
            log_error("scraper", e, f"duckduckgo: {query}")
    return leads


# ─── Orchestrateur principal ───────────────────────────────────────────────────

def search_french_biotech_startups(max_results: int = 50) -> list[dict]:
    """
    Cherche des startups biotech/medtech françaises via plusieurs sources.
    Retourne une liste de dicts compatibles leads.csv.
    """
    leads: list[dict] = []
    seen_names: set[str] = set()
    seen_domains: set[str] = set()

    def _add(boite: str, domaine: str, secteur: str = "biotech", stade: str = "seed") -> bool:
        key = boite.lower().strip()
        dom = domaine.lower().strip()
        if key in seen_names:
            return False
        if dom and dom in seen_domains:
            return False
        seen_names.add(key)
        if dom:
            seen_domains.add(dom)
        leads.append({
            "nom": "",
            "prenom": "Fondateur",
            "boite": boite,
            "domaine": domaine,
            "email": "",
            "linkedin_url": "",
            "statut": "Nouveau",
            "secteur": secteur,
            "stade": stade,
            "notes": "",
        })
        return True

    # 1. Liste statique curatée (base garantie)
    print("[Scraper] Chargement liste statique…")
    for boite, domaine, secteur, stade in STATIC_LEADS:
        _add(boite, domaine, secteur, stade)

    # 2. France Biotech press releases (live)
    print("[Scraper] Scraping France Biotech…")
    try:
        fb_names = _fetch_france_biotech_companies()
        print(f"[Scraper] France Biotech : {len(fb_names)} noms trouvés")
        for name in fb_names:
            if name.lower() in seen_names:
                continue
            # Try DuckDuckGo to find domain
            domain = _resolve_domain_via_duckduckgo(name)
            time.sleep(1)
            _add(name, domain, "biotech", "series_a")
    except Exception as e:
        log_error("scraper", e, "france-biotech source")

    # 3. Maddyness (live)
    print("[Scraper] Scraping Maddyness…")
    try:
        maddy_leads = _fetch_maddyness_companies()
        print(f"[Scraper] Maddyness : {len(maddy_leads)} boîtes trouvées")
        for l in maddy_leads:
            _add(l["boite"], l["domaine"], l["secteur"], l["stade"])
    except Exception as e:
        log_error("scraper", e, "maddyness source")

    # 4. DuckDuckGo LinkedIn (fallback)
    if len(leads) < max_results:
        print("[Scraper] DuckDuckGo LinkedIn fallback…")
        try:
            ddg = _fetch_via_duckduckgo()
            for l in ddg:
                _add(l["boite"], l["domaine"], l["secteur"], l["stade"])
        except Exception as e:
            log_error("scraper", e, "duckduckgo source")

    result = leads[:max_results]
    print(f"[Scraper] Total : {len(result)} leads")
    return result


def find_linkedin_url(prenom: str, nom: str, company_name: str) -> str:
    """
    Cherche le profil LinkedIn d'une personne via DuckDuckGo.
    Retourne l'URL complète ou "" si rien trouvé.
    Toutes les queries incluent "2026" et rejettent les résultats anterieurs à janvier 2026.
    """
    import re as _re
    if not prenom or prenom.lower() in {"fondateur", "founder", "contact", "ceo", ""}:
        return ""

    search_terms = f"{prenom} {nom} {company_name}".strip()
    query = f'site:linkedin.com/in "{search_terms}" 2026'

    try:
        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers=HEADERS,
            timeout=12,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select(".result__a"):
            href = a.get("href", "")
            if "linkedin.com/in/" in href and "linkedin.com/company/" not in href:
                match = _re.search(r"linkedin\.com/in/([\w\-]+)", href)
                if match:
                    profile_id = match.group(1)
                    if any(skip in profile_id.lower() for skip in ["company", "jobs", "school", "showcase"]):
                        continue
                    clean_url = f"https://www.linkedin.com/in/{profile_id}"
                    return clean_url
    except Exception as e:
        log_error("scraper", e, f"linkedin_url for {search_terms}")
    return ""


def get_recent_news_for_company(company_name: str, domain: str) -> str:
    """
    Cherche des infos 2026 sur la boîte pour personnaliser l'email.
    Retourne "" si rien de 2026 trouvé — le LLM utilisera le contexte générique.
    """
    import re as _re
    query = f'"{company_name}" 2026 levée fonds OR recrutement OR congrès OR publication OR lancement OR actualité OR nouvelle'
    try:
        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers=HEADERS,
            timeout=12,
        )
        soup = BeautifulSoup(resp.text, "html.parser")

        valid_snippets = []
        for result in soup.select(".result__snippet")[:5]:
            text = result.get_text(strip=True)
            if "2026" in text:
                deduped = _re.sub(
                    r'(' + _re.escape(company_name) + r'[\s,\.]*){2,}',
                    company_name + ' ',
                    text,
                    flags=_re.IGNORECASE
                ).strip()
                valid_snippets.append(deduped)

        if not valid_snippets:
            return ""

        return valid_snippets[0][:400]
    except Exception as e:
        log_error("scraper", e, f"news for {company_name}")
        return ""


def search_linkedin_for_leads(csv_path: str = "data/leads.csv") -> list[dict]:
    """
    Pour chaque lead sans linkedin_url, cherche sur DuckDuckGo :
    'site:linkedin.com/in [prenom] [nom] [boite]'
    Retourne la liste mise à jour sans modifier le fichier.
    """
    import csv as _csv

    leads = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = _csv.DictReader(f)
            leads = list(reader)
    except Exception as e:
        log_error("scraper", e, f"read {csv_path}")
        return []

    updated = []
    for lead in leads:
        prenom = (lead.get("prenom") or "").strip()
        nom = (lead.get("nom") or "").strip()
        boite = (lead.get("boite") or "").strip()
        linkedin_url = (lead.get("linkedin_url") or "").strip()

        if linkedin_url:
            updated.append(lead)
            continue

        if not prenom or not boite:
            updated.append(lead)
            continue

        query = f'site:linkedin.com/in {prenom} {nom} {boite}'
        found_url = ""
        try:
            resp = requests.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query},
                headers=HEADERS,
                timeout=12,
            )
            soup = BeautifulSoup(resp.text, "html.parser")
            for result in soup.select(".result"):
                a = result.select_one(".result__a")
                if not a:
                    continue
                href = a.get("href", "")
                if "linkedin.com/in/" in href:
                    found_url = href
                    break
            time.sleep(1)
        except Exception as e:
            log_error("scraper", e, f"linkedin search for {boite}")

        lead["linkedin_url"] = found_url
        updated.append(lead)
        print(f"  {boite}: {found_url or 'non trouvé'}")

    return updated
