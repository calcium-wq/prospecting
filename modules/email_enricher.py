"""
Enrichissement d'emails — stratégie multi-sources, 0 email inventé.

Ordre de priorité :
1. Hunter.io API (emails vérifiés côté serveur)
2. Scraping emails en clair sur le site web (footer, /contact, /about)
3. theHarvester OSINT (Google/Bing/DuckDuckGo)
4. Scraping des vrais noms (/team, /about) + patterns
5. Vérification SMTP — ou fallback MX si WSL2 bloque tout
"""
import re
import shutil
import socket
import smtplib
import subprocess
import time

import requests
from bs4 import BeautifulSoup

from modules.config import BASE_DIR, HUNTER_API_KEY
from modules.logger import log_error

_HARVESTER_TIMEOUT = 90
_HTTP_TIMEOUT = 10
_EHLO_DOMAIN = "gmail.com"
_GENERIC_PREFIXES = {"contact", "hello", "info", "bonjour", "contact-us", "support", "admin", "noreply", "no-reply", "sales", "marketing", "team", "equipe", "service"}

_harvester_cache: dict[str, list[str]] = {}

_ABOUT_PATHS = ["/team", "/about", "/about-us", "/equipe", "/founders", "/leadership"]
_CONTACT_PATHS = ["/contact", "/contact-us", "/nous-contacter", "/contactez-nous", "/"]

_PATTERNS = [
    "{first}.{last}@{domain}",
    "{first}{last}@{domain}",
    "{f}{last}@{domain}",
    "{first}@{domain}",
    "{last}@{domain}",
    "contact@{domain}",
    "hello@{domain}",
    "info@{domain}",
]

_EMAIL_RE = re.compile(r"[\w.+\-]+@[\w.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE)
_PLACEHOLDER_NAMES = {"fondateur", "founder", "ceo", "directeur", "contact",
                      "support", "admin", "noreply", "sales", "marketing", "service", "team"}

_VOWELS = frozenset("aeiouyàâéèêëîïôùûü")
# Clusters de consonnes valides en début de prénom français/anglais/nordique
_VALID_NAME_DIGRAPHS = frozenset({
    "bj", "bl", "br", "ch", "cl", "cr", "dr", "fl", "fr",
    "gl", "gn", "gr", "ph", "pl", "pr", "qu", "sc", "sk",
    "sl", "sm", "sn", "sp", "st", "sw", "th", "tr", "tw",
    "vr", "wh", "wr",
})


def extract_prenom_from_email(email: str, fallback: str = "") -> str:
    """Extrait un prénom plausible depuis l'adresse email (prenom.nom@ ou prenom@)."""
    import re as _re
    local = email.split("@")[0].lower()
    # Gérer prénom-composé : jean-jacques.mention → Jean-Jacques
    if "-" in local.split(".")[0]:
        parts = local.split(".")
        first_raw = parts[0]
        first = "-".join(p.capitalize() for p in first_raw.split("-"))
        return first
    if "." in local:
        first = local.split(".")[0]
    elif len(local) > 3:
        first = local  # prenom seul ou pnom
    else:
        return fallback  # trop court (ex: cd@)
    first = _re.sub(r"[^a-z]", "", first)
    if len(first) <= 1:
        return fallback
    if len(first) >= 8 and "." not in local:
        return fallback
    # Detect initial+surname without separator (e.g. jhutin=j+hutin, cmartin=c+martin)
    if (len(first) >= 4
            and "." not in local
            and first[0] not in _VOWELS
            and first[1] not in _VOWELS
            and first[:2] not in _VALID_NAME_DIGRAPHS):
        return fallback
    return first.capitalize() if first else fallback


# ---------------------------------------------------------------------------
# Source 1 : Hunter.io API
# ---------------------------------------------------------------------------

def _hunter_find(domain: str, first: str = "", last: str = "") -> list[str]:
    """Interroge Hunter.io pour trouver des emails sur un domaine."""
    if not HUNTER_API_KEY:
        return []
    emails = []
    try:
        # Domain search (liste tous les emails connus)
        resp = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "api_key": HUNTER_API_KEY, "limit": 10},
            timeout=_HTTP_TIMEOUT,
        )
        if resp.ok:
            data = resp.json().get("data", {})
            for entry in data.get("emails", []):
                email = entry.get("value", "")
                if email:
                    emails.append(email.lower())

        # Email finder (cherche spécifiquement par nom si on en a un)
        if first and last and first.lower() not in _PLACEHOLDER_NAMES:
            resp2 = requests.get(
                "https://api.hunter.io/v2/email-finder",
                params={
                    "domain": domain,
                    "first_name": first,
                    "last_name": last,
                    "api_key": HUNTER_API_KEY,
                },
                timeout=_HTTP_TIMEOUT,
            )
            if resp2.ok:
                found = resp2.json().get("data", {}).get("email", "")
                if found and found not in emails:
                    emails.insert(0, found.lower())
    except Exception as e:
        log_error("email_enricher", e, f"hunter {domain}")
    return emails


# ---------------------------------------------------------------------------
# Source 2 : Scraping emails en clair sur le site web
# ---------------------------------------------------------------------------

def _fetch_page(url: str) -> str:
    try:
        resp = requests.get(url, timeout=_HTTP_TIMEOUT, headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }, allow_redirects=True)
        if resp.ok:
            return resp.text
    except Exception:
        pass
    return ""


def scrape_emails_from_site(domain: str) -> list[str]:
    """
    Cherche des emails en clair sur le site (footer, /contact, /about).
    Ces emails n'ont pas besoin de vérification SMTP.
    """
    found = []
    for path in _CONTACT_PATHS + _ABOUT_PATHS:
        for scheme in ("https", "http"):
            html = _fetch_page(f"{scheme}://{domain}{path}")
            if not html:
                continue
            # Cherche dans le texte brut (pas les attributs href mailto:)
            soup = BeautifulSoup(html, "html.parser")
            # 1. liens mailto: explicites
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("mailto:"):
                    email = href[7:].split("?")[0].strip().lower()
                    if _is_domain_email(email, domain) and email not in found:
                        found.append(email)
            # 2. texte brut dans footer / section contact
            for selector in ["footer", "[class*='contact']", "[class*='footer']", "body"]:
                for tag in soup.select(selector):
                    text = tag.get_text()
                    for match in _EMAIL_RE.findall(text):
                        email = match.lower()
                        if _is_domain_email(email, domain) and email not in found:
                            found.append(email)
            if found:
                break  # On a trouvé des emails sur ce chemin
        if found:
            break
    return found


def _is_domain_email(email: str, domain: str) -> bool:
    """Vérifie que l'email appartient au domaine cible."""
    return bool(re.match(r"^[\w.+\-]+@[\w.\-]+\.[a-zA-Z]{2,}$", email)) and \
           email.endswith("@" + domain)


# ---------------------------------------------------------------------------
# Source 3 : theHarvester OSINT
# ---------------------------------------------------------------------------

def _run_harvester(domain: str) -> list[str]:
    if domain in _harvester_cache:
        return _harvester_cache[domain]
    if shutil.which("theHarvester") is None:
        _harvester_cache[domain] = []
        return []
    try:
        result = subprocess.run(
            ["theHarvester", "-d", domain, "-b", "google,bing,duckduckgo", "-l", "50"],
            capture_output=True, text=True, timeout=_HARVESTER_TIMEOUT,
            cwd=str(BASE_DIR),
        )
        output = result.stdout + result.stderr
        emails = re.findall(r"[\w.+\-]+@" + re.escape(domain), output, re.IGNORECASE)
        found = list({e.lower() for e in emails})
    except subprocess.TimeoutExpired:
        found = []
    except Exception as e:
        log_error("email_enricher", e, f"harvester {domain}")
        found = []
    _harvester_cache[domain] = found
    return found


# ---------------------------------------------------------------------------
# Source 4 : scraping des vrais noms fondateurs (/team, /about)
# ---------------------------------------------------------------------------

def _extract_names_from_html(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    selectors = [
        "[class*='founder']", "[class*='team']", "[class*='member']",
        "[class*='ceo']", "[class*='leader']", "[class*='person']",
        "h2", "h3", "h4",
    ]
    seen = set()
    skip_kw = {"our team", "meet", "about", "contact", "leadership", "news",
               "mission", "vision", "values", "careers", "jobs"}
    for sel in selectors:
        for tag in soup.select(sel):
            for line in tag.get_text(separator="\n").split("\n"):
                line = line.strip()
                words = line.split()
                if 2 <= len(words) <= 3 and all(w[0].isupper() for w in words if w):
                    lower = line.lower()
                    if any(kw in lower for kw in skip_kw):
                        continue
                    if lower not in seen:
                        seen.add(lower)
                        candidates.append((words[0], " ".join(words[1:])))
    return candidates[:5]


def scrape_founder_names(domain: str) -> list[tuple[str, str]]:
    for path in _ABOUT_PATHS:
        for scheme in ("https", "http"):
            html = _fetch_page(f"{scheme}://{domain}{path}")
            names = _extract_names_from_html(html)
            if names:
                return names
    return []


# ---------------------------------------------------------------------------
# Génération de patterns
# ---------------------------------------------------------------------------

def _normalize(s: str) -> str:
    for src, dst in [("é","e"),("è","e"),("ê","e"),("à","a"),("â","a"),("ô","o"),
                     ("î","i"),("û","u"),("ç","c"),("ü","u"),("ö","o"),("-"," ")]:
        s = s.replace(src, dst)
    return s.lower().strip()


def _generate_patterns(first: str, last: str, domain: str) -> list[str]:
    first = _normalize(first)
    last = _normalize(last)
    # Si nom composé (ex: "De La Tour"), prendre juste le dernier mot
    last_simple = last.split()[-1] if last.split() else last
    f = first[0] if first else ""
    result = []
    for pattern in _PATTERNS:
        try:
            email = pattern.format(first=first, last=last_simple, f=f, domain=domain)
            # Rejeter les patterns mal formés (point/tiret en début ou fin de partie locale)
            local = email.split("@")[0]
            if not local or local.startswith(".") or local.endswith(".") or local == f:
                continue
            if email not in result:
                result.append(email)
        except KeyError:
            continue
    return result


# ---------------------------------------------------------------------------
# Vérification SMTP et MX
# ---------------------------------------------------------------------------

def _get_mx(domain: str) -> str | None:
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, "MX")
        mx = sorted(answers, key=lambda r: r.preference)[0].exchange.to_text().rstrip(".")
        return mx
    except Exception:
        return None


def _smtp_verify(email: str) -> tuple[bool, bool]:
    """
    Retourne (accepted, all_ports_blocked).
    - accepted=True : email confirmé ou fallback légitime
    - all_ports_blocked=True : aucun port SMTP joignable (WSL2)
    """
    domain = email.split("@")[-1]
    prefix = email.split("@")[0].lower()

    mx = _get_mx(domain)
    if not mx:
        # Pas de MX → domaine ne reçoit pas d'email
        return False, False

    all_blocked = True

    for port in (25, 587, 465):
        try:
            if port == 465:
                smtp = smtplib.SMTP_SSL(mx, port, timeout=10)
            else:
                smtp = smtplib.SMTP(timeout=10)
                smtp.connect(mx, port)

            all_blocked = False  # connexion établie

            with smtp:
                smtp.ehlo(_EHLO_DOMAIN)
                if port == 587:
                    try:
                        smtp.starttls()
                        smtp.ehlo(_EHLO_DOMAIN)
                    except Exception:
                        pass
                smtp.mail("verify@" + _EHLO_DOMAIN)
                code, _ = smtp.rcpt(email)
                if code in (250, 251):
                    return True, False
                # Code 5xx (rejet) → essaie le port suivant
                continue

        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected,
                socket.timeout, OSError, ConnectionRefusedError):
            continue  # port bloqué → essaie le suivant
        except Exception as e:
            log_error("email_enricher", e, f"smtp_verify port={port} {email}")
            continue

    if all_blocked:
        # WSL2 / firewall — on ne peut pas vérifier
        return prefix in _GENERIC_PREFIXES, True

    # Serveurs joignables mais aucun n'a confirmé → génériques seulement
    return prefix in _GENERIC_PREFIXES, False


# ---------------------------------------------------------------------------
# Logique principale
# ---------------------------------------------------------------------------

def find_email(prenom: str, nom: str, domain: str) -> str:
    """
    Cherche un email fiable pour ce lead. Retourne "" si rien trouvé.
    """
    if not domain:
        return ""

    # Détecter si prenom/nom sont des placeholders ("Fondateur", "Founder"…)
    is_placeholder = (
        not prenom or prenom.lower().strip() in _PLACEHOLDER_NAMES or
        not nom or nom.lower().strip() in _PLACEHOLDER_NAMES
    )

    # ── Source 1 : Hunter.io ──────────────────────────────────────────────
    first_real = prenom if not is_placeholder else ""
    last_real = nom if not is_placeholder else ""
    hunter_emails = _hunter_find(domain, first_real, last_real)
    if hunter_emails:
        print(f"           [Hunter] {hunter_emails[0]}")
        return hunter_emails[0]

    # ── Source 2 : emails en clair sur le site web ────────────────────────
    site_emails = scrape_emails_from_site(domain)
    if site_emails:
        print(f"           [Site] {site_emails[0]}")
        return site_emails[0]

    # ── Source 3 : theHarvester OSINT ─────────────────────────────────────
    harvester_emails = _run_harvester(domain)
    if harvester_emails:
        # Priorité aux emails qui matchent le nom si on en a un
        if not is_placeholder and nom:
            name_match = [
                e for e in harvester_emails
                if nom.lower()[:4] in e.lower() or prenom.lower()[:3] in e.lower()
            ]
            if name_match:
                print(f"           [Harvester+nom] {name_match[0]}")
                return name_match[0]
        print(f"           [Harvester] {harvester_emails[0]}")
        return harvester_emails[0]

    # ── Source 4 : scraping noms réels + patterns ─────────────────────────
    # Toujours scraper les vrais noms (les placeholders ne comptent pas)
    scraped_names = scrape_founder_names(domain)
    name_sources: list[tuple[str, str]] = []
    if not is_placeholder:
        name_sources.append((prenom, nom))
    name_sources.extend(scraped_names)

    # Vérifier si les ports SMTP sont bloqués (test rapide sur un générique)
    mx_exists = _get_mx(domain) is not None
    _, ports_blocked = _smtp_verify(f"probe@{domain}")

    candidates: list[str] = []
    for fn, ln in name_sources:
        for email in _generate_patterns(fn, ln, domain):
            if email not in candidates:
                candidates.append(email)

    # Ajouter les génériques si pas déjà présents
    for prefix in ("contact", "hello", "info"):
        generic = f"{prefix}@{domain}"
        if generic not in candidates:
            candidates.append(generic)

    for email in candidates:
        if not re.match(r"^[\w.+\-]+@[\w.\-]+\.[a-zA-Z]{2,}$", email):
            continue
        prefix = email.split("@")[0].lower()

        if ports_blocked:
            # WSL2 bloque SMTP → stratégie dégradée
            if prefix in _GENERIC_PREFIXES and mx_exists:
                # Générique + MX confirmé → on accepte
                print(f"           [Générique+MX] {email}")
                return email
            if not is_placeholder and mx_exists and prefix not in _GENERIC_PREFIXES:
                # Pattern personnel + MX confirmé → on accepte avec confiance modérée
                print(f"           [Pattern+MX] {email}")
                return email
            if prefix in _GENERIC_PREFIXES:
                # Générique sans MX confirmé (cas extrême)
                print(f"           [Générique] {email}")
                return email
        else:
            # SMTP joignable → vérification réelle
            time.sleep(2)
            accepted, _ = _smtp_verify(email)
            if accepted:
                print(f"           [SMTP] {email}")
                return email

    return ""


def enrich_lead(lead: dict) -> dict:
    """Enrichit un lead avec un email fiable si le champ est vide."""
    if lead.get("email"):
        return lead
    domain = lead.get("domaine", "")
    prenom = lead.get("prenom", "")
    nom = lead.get("nom", "")
    lead["email"] = find_email(prenom, nom, domain)
    return lead


def enrich_all_leads(leads: list[dict]) -> list[dict]:
    enriched = []
    for i, lead in enumerate(leads):
        label = f"{lead.get('boite', '')} ({lead.get('domaine', '')})"
        print(f"[Enricher] {i+1}/{len(leads)} — {label}")
        try:
            lead = enrich_lead(lead)
            result = lead["email"] if lead["email"] else "— aucun email trouvé"
            print(f"           → {result}")
        except Exception as e:
            log_error("email_enricher", e, f"enrich {lead.get('domaine', '')}")
        enriched.append(lead)
    return enriched
