#!/usr/bin/env python3
"""
Scrape ~50 nouveaux leads biotech/medtech français.
Sources : liste curatée + France Biotech API + Maddyness.
Écrit dans data/leads.csv avec déduplication (ne jamais écraser les existants).
"""
import re
import time
import sys
import requests
from pathlib import Path
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
FIELDS = ["nom", "prenom", "boite", "domaine", "email", "linkedin_url",
          "statut", "canal", "date_email", "date_linkedin",
          "relance_j3", "relance_j7", "relance_j14", "reponse", "dnc", "notes"]

SKIP = {
    "france biotech", "femtech france", "femtech française",
    "dassault systèmes medidata", "banque populaire",
    "servier", "ipsen", "l'oréal", "sanofi", "roche", "novartis", "amgen",
    "les laboratoires pierre fabre",
    "cellprothera", "cardiawave", "everzom",
}
BAD_PATTERNS = re.compile(
    r"^((la|le|les|un|une|de|l')\s|\s+et\s|\s+&\s)|"
    r"^(puis|trois|nouveau|administrateur|bilan|rapport|assemblée|communiqué"
    r"|presse|dossier|projet|inserm|résah|réseau|dresse|annonce|annoncé"
    r"|inaugure|lance|lancement|ouvre|organise|start[\-\s]?up"
    r"|communiqué|inaugure|l'appui|\s+CV$|\s+BCV$|^BCV$)", re.IGNORECASE
)


def _get(url: str, timeout: int = 12) -> requests.Response | None:
    try:
        return requests.get(url, headers=HEADERS, timeout=timeout)
    except Exception:
        return None


def _post(url: str, data: dict, timeout: int = 12) -> requests.Response | None:
    try:
        return requests.post(url, data=data, headers=HEADERS, timeout=timeout)
    except Exception:
        return None


def extract_domain(url: str) -> str:
    m = re.search(r"https?://(?:www\.)?([^/?#]+)", url)
    return m.group(1).lower() if m else ""


def is_company(name: str) -> bool:
    nl = name.lower().strip()
    if nl in SKIP:
        return False
    if BAD_PATTERNS.search(nl):
        return False
    if len(name) < 3 or len(name) > 30:
        return False
    if " et " in name or " & " in name:
        return False
    if not re.match(r"^[A-Za-zÀ-ÿ]", name):
        return False
    if re.search(r"^[A-Z][a-zà-ÿ]+\s+[A-Z][a-zà-ÿ]+$", name.strip()):
        return False
    if len(name.split()) > 3:
        return False
    return True


# ─── Liste curatée de vraies boîtes ──────────────────────────────────────

CURATED_LEADS = [
    ("StemInov", "steminov.com", "biotech", "seed"),
    ("Metafora Biosystems", "metafora-biosystems.com", "biotech", "seed"),
    ("Alcediag", "alcediag.com", "biotech", "seed"),
    ("Dessintey", "dessintey.com", "medtech", "seed"),
    ("Vect-Horus", "vect-horus.com", "biotech", "series_a"),
    ("Vaxinano", "vaxinano.com", "biotech", "seed"),
    ("Theranexus", "theranexus.com", "biotech", "series_a"),
    ("CorWave", "corwave.com", "medtech", "series_a"),
    ("BioMAdvanced Diagnostics", "biomadvanced.com", "medtech", "seed"),
    ("NATEOSANTE", "nateosante.com", "healthtech", "seed"),
    ("Lovaltech", "lovaltech.com", "biotech", "series_a"),
    ("FineHeart", "fineheart.fr", "medtech", "series_a"),
    ("ABIONYX Pharma", "abionyx.com", "biotech", "series_a"),
    ("Affluent Medical", "affluentmedical.com", "medtech", "series_a"),
    ("SURGAR", "surgar.fr", "medtech", "seed"),
    ("PDCline Pharma", "pdc-line.com", "biotech", "seed"),
    ("Sensorion", "sensorion.com", "biotech", "series_a"),
    ("POXEL", "poxelinc.com", "biotech", "series_a"),
    ("BIOPHTA", "biophta.com", "biotech", "seed"),
    ("Pharnext", "pharnext.com", "biotech", "series_a"),
    ("ERYTECH", "erytech.com", "biotech", "series_a"),
    ("OSE Immunotherapeutics", "ose-immuno.com", "biotech", "series_a"),
    ("KAIROS DISCOVERY", "kairos-discovery.com", "biotech", "seed"),
    ("Axomove", "axomove.com", "healthtech", "seed"),
    ("SMART IMMUNE", "smartimmune.com", "biotech", "seed"),
    ("CARMAT", "carmat.com", "medtech", "series_a"),
    ("Biophytis", "biophytis.com", "biotech", "series_a"),
    ("THERACLION", "theraclion.com", "medtech", "series_a"),
    ("PulseLife", "pulselife.fr", "healthtech", "seed"),
    ("HighLife", "highlifesas.com", "medtech", "series_a"),
    ("Advanced BioDesign", "advancedbiodesign.fr", "medtech", "seed"),
    ("GeNeuro", "gneuro.com", "biotech", "series_a"),
    ("XENOTHERA", "xenothera.com", "biotech", "series_a"),
    ("DBV Technologies", "dbvtechnologies.com", "biotech", "series_a"),
    ("Oncovita", "oncovita.com", "biotech", "seed"),
    ("Alzprotect", "alzprotect.com", "biotech", "seed"),
    ("LinKinVax", "linkinvax.com", "biotech", "seed"),
    ("Transgene", "transgene.fr", "biotech", "series_a"),
    ("SEABELIFE", "seabelife.com", "biotech", "seed"),
    ("DOMAIN Therapeutics", "domaintherapeutics.com", "biotech", "series_a"),
    ("Brenus Pharma", "brenuspharma.com", "biotech", "series_a"),
    ("Amolyt Pharma", "amolytpharma.com", "biotech", "series_a"),
    ("Inside Therapeutics", "insidetherapeutics.com", "biotech", "seed"),
    ("EVerZom", "everzom.com", "biotech", "series_a"),
    ("Avatar Medical", "avatarmedical.ai", "healthtech", "seed"),
    ("Hemerion", "hemerion.com", "biotech", "seed"),
    ("VALBIOTIS", "valbiotis.com", "biotech", "series_a"),
    ("Elixir Health", "elixirhealth.fr", "biotech", "seed"),
    ("Caranx Medical", "caranxmedical.com", "medtech", "seed"),
    ("Qubit Pharmaceuticals", "qubitpharma.com", "biotech", "seed"),
    ("AB SCIENCE", "ab-science.com", "biotech", "series_a"),
    ("Cilcare", "cilcare.com", "biotech", "series_a"),
    ("TreeFrog Therapeutics", "treefrog-therapeutics.com", "biotech", "series_a"),
    ("Enterome", "enterome.com", "biotech", "series_a"),
    ("Aelis Farma", "aelis-farma.com", "biotech", "series_a"),
    ("DNA Script", "dnascript.com", "biotech", "series_a"),
    ("Alcediag", "alcediag.com", "biotech", "seed"),
    ("Axomove", "axomove.com", "healthtech", "seed"),
    ("Lattice Medical", "latticemedical.com", "medtech", "seed"),
    ("Incepto Medical", "incepto-medical.com", "healthtech", "series_a"),
    ("Cardiologs", "cardiologs.com", "healthtech", "series_a"),
    ("Ganymed Robotics", "ganymede.eu", "medtech", "series_a"),
    ("ExactCure", "exactcure.com", "healthtech", "seed"),
    ("Implicity", "implicity.com", "healthtech", "seed"),
    ("Spade", "spade-medical.com", "medtech", "seed"),
    ("Dreem", "dreem.com", "healthtech", "series_a"),
    ("Owkin", "owkin.com", "healthtech", "series_a"),
    ("Sonio", "sonio.co", "healthtech", "series_a"),
    ("Gleamer", "gleamer.com", "healthtech", "seed"),
    ("FineHeart", "fineheart.fr", "medtech", "series_a"),
    ("Quantum Surgical", "quantum-surgical.com", "medtech", "series_a"),
    ("Surgivisio", "surgivisio.com", "medtech", "series_a"),
    ("Wandercraft", "wandercraft.eu", "medtech", "series_a"),
    ("Feetme", "feetme.fr", "medtech", "seed"),
    ("HighLife", "highlifesas.com", "medtech", "series_a"),
    ("Pixium Vision", "pixium-vision.com", "medtech", "series_a"),
    ("Meditect", "meditect.fr", "medtech", "seed"),
    ("Bioptigen", "bioptigen.com", "medtech", "seed"),
    ("INCEPTO", "incepto-medical.com", "healthtech", "series_a"),
    ("AB Science", "ab-science.com", "biotech", "series_a"),
    ("Creapharm", "creapharm.com", "biotech", "series_a"),
    ("Biophytis", "biophytis.com", "biotech", "series_a"),
]


# ─── France Biotech API ────────────────────────────────────────────────────

def scrape_france_biotech() -> list[dict]:
    companies = set()
    pattern = re.compile(
        r"^([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\s\-\.]{2,40}?)\s+"
        r"(?:lève|annonce|lance|obtient|reçoit|signe|publie|présente|devient"
        r"|rejoint|finalise|complète|conclut|intègre|décroche|remporte|acquiert)",
        re.IGNORECASE,
    )

    print("[FB] Scraping France Biotech...")
    for page in range(1, 8):
        resp = _get(
            f"https://france-biotech.fr/wp-json/wp/v2/posts"
            f"?per_page=100&page={page}&_fields=title,link"
        )
        if not resp or resp.status_code != 200:
            break
        posts = resp.json()
        if not posts:
            break
        for p in posts:
            title = re.sub(r"<[^>]+>", "", p.get("title", {}).get("rendered", "")).strip()
            m = pattern.match(title)
            if not m:
                continue
            raw = m.group(1).strip()
            if not is_company(raw):
                continue
            link = p.get("link", "")
            domain = extract_domain(link)
            bad = {"france-biotech.fr", "linkedin.com", "twitter.com",
                   "facebook.com", "google.com"}
            if domain and not any(b in domain for b in bad):
                companies.add((raw, domain))
            else:
                companies.add((raw, ""))
        if len(posts) < 100:
            break
        time.sleep(0.5)

    print(f"[FB]   -> {len(companies)} boxes trouvees")
    return [{"boite": n, "domaine": d} for n, d in companies]


# ─── Maddyness ──────────────────────────────────────────────────────────────

def scrape_maddyness() -> list[dict]:
    leads = []
    article_pattern = re.compile(
        r"https://www\.maddyness\.com/\d{4}/\d{2}/\d{2}/[\w\-]+"
    )
    bad_slug = re.compile(
        r"^(levées?[\-]?de[\-]?fonds|financement|investissement|startup|start"
        r"|seed|series|round|fonds?|capital|business|plan|rapport|actualités?"
        r"|news|brevets?|licence|partenariat|accord|resultats?|compte"
        r"|assemblées?|agm|bilan|communiqué|presse|inauguration|ouverture"
        r"|lancement|événement|événementiel|conférence|congres|congrès"
        r"|forum|salon|challenge|appel|edition|levee)", re.IGNORECASE
    )
    sector_map = {
        "biotech": "biotech",
        "medtech": "medtech",
        "healthtech": "healthtech",
        "sante": "healthtech",
        "levees-de-fonds": "biotech",
    }

    print("[Maddy] Scraping Maddyness...")
    for url in [
        "https://www.maddyness.com/levees-de-fonds/",
        "https://www.maddyness.com/tag/biotech/",
        "https://www.maddyness.com/tag/medtech/",
        "https://www.maddyness.com/tag/healthtech/",
        "https://www.maddyness.com/tag/sante/",
    ]:
        resp = _get(url)
        if not resp or resp.status_code != 200:
            continue
        soup = BeautifulSoup(resp.text, "html.parser")
        sector = sector_map.get(url.split("maddyness.com/")[-1].split("/")[0], "biotech")

        seen_urls = set()
        for a in soup.find_all("a", href=article_pattern):
            href = a["href"]
            if href in seen_urls:
                continue
            seen_urls.add(href)

            parent = a.find_parent(["h2", "h3", "li", "article"])
            text = parent.get_text(strip=True) if parent else ""

            m = re.search(
                r"^([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\s\-\.]{2,40}?)\s+(?:lève|lancement|annonce|lance)",
                text, re.IGNORECASE,
            )
            if m:
                name = m.group(1).strip()
                if is_company(name):
                    leads.append({"boite": name, "domaine": "", "secteur": sector})
            else:
                slug_m = re.search(r"/(\d{4}/\d{2}/\d{2}/)([\w\-]+)/?$", href)
                if slug_m:
                    slug = slug_m.group(2)
                    name = re.sub(r"[\-_]", " ", slug).title()
                    nl = name.lower()
                    if is_company(name) and not bad_slug.search(nl):
                        leads.append({"boite": name, "domaine": "", "secteur": sector})
        time.sleep(1)

    seen = set()
    uniq = []
    for l in leads:
        if l["boite"].lower() not in seen:
            seen.add(l["boite"].lower())
            uniq.append(l)
    print(f"[Maddy]   -> {len(uniq)} boxes uniques trouvees")
    return uniq


# ─── Enrichissement domaine ─────────────────────────────────────────────────

def enrich_domain_ddg(company_name: str) -> str:
    query = f'"{company_name}" biotech OR medtech OR healthtech France site officiel'
    try:
        resp = _post("https://html.duckduckgo.com/html/", {"q": query}, timeout=12)
        if not resp:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select(".result__a"):
            href = a.get("href", "")
            domain = extract_domain(href)
            bad = {"linkedin.com", "google.com", "twitter.com", "facebook.com",
                   "wikipedia.org", "youtube.com", "crunchbase.com",
                   "maddyness.com", "france-biotech.fr", "lesechos.fr",
                   "lefigaro.fr", "lemonde.fr", "latribune.fr"}
            if domain and not any(b in domain for b in bad):
                return domain
    except Exception:
        pass
    return ""


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    out_path = Path("/home/mbped/prospecting/data/leads.csv")
    sys.path.insert(0, str(Path(__file__).parent))
    from modules.leads_csv import load_leads, add_lead, save_leads

    print("=== Scraping → leads.csv ===\n")

    # Load existing leads
    existing_df = load_leads()
    existing_emails = set(existing_df["email"].dropna().values)
    existing_boites = set(existing_df["boite"].str.lower().dropna().values)
    existing_domaines = set(existing_df["domaine"].str.lower().dropna().values)
    existing_linkedin = set(existing_df["linkedin_url"].dropna().values)

    def is_duplicate(lead: dict) -> bool:
        email = lead.get("email", "").strip().lower()
        boite = lead.get("boite", "").strip().lower()
        domaine = lead.get("domaine", "").strip().lower()
        li_url = lead.get("linkedin_url", "").strip()
        if email and email in existing_emails:
            return True
        if boite and boite in existing_boites:
            return True
        if domaine and domaine in existing_domaines:
            return True
        if li_url and li_url in existing_linkedin:
            return True
        return False

    # Curated
    curated = [{"boite": b, "domaine": d} for b, d, _, _ in CURATED_LEADS]

    # Live sources
    fb_leads = scrape_france_biotech()
    maddy_leads = scrape_maddyness()

    # Merge & deduplicate
    seen = set()
    new_leads = []
    for l in curated + fb_leads + maddy_leads:
        key = l["boite"].lower().strip()
        if key in seen:
            continue
        seen.add(key)
        lead = {
            "nom": "",
            "prenom": "Fondateur",
            "boite": l["boite"],
            "domaine": l.get("domaine", ""),
            "email": "",
            "linkedin_url": "",
            "statut": "Nouveau",
            "canal": "",
            "date_email": "",
            "date_linkedin": "",
            "relance_j3": "",
            "relance_j7": "",
            "relance_j14": "",
            "reponse": "",
            "dnc": "",
            "notes": "",
        }
        if not is_duplicate(lead):
            new_leads.append(lead)
            existing_boites.add(lead["boite"].lower().strip())
            existing_domaines.add(lead["domaine"].lower().strip())

    print(f"\n[Total] {len(new_leads)} nouveaux leads à ajouter")

    enriched = 0
    for lead in new_leads:
        if not lead.get("domaine"):
            lead["domaine"] = enrich_domain_ddg(lead["boite"])
            existing_domaines.add(lead["domaine"].lower().strip())
            enriched += 1
            time.sleep(1.5)
            if enriched >= 20:
                print(f"[DDG] Limite: 20 domaines enrichis")
                break

    print(f"[DDG] {enriched} domaines enrichis")

    added = 0
    for lead in new_leads[:50]:
        if add_lead(lead):
            added += 1

    print(f"\n✅ {added} leads ajoutés dans {out_path}")
    print(f"   ({len(new_leads[:50]) - added} déjà existants, ignorés)")


if __name__ == "__main__":
    main()
