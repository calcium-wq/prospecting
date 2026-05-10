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
]

_FUNCTIONAL_PATTERNS = [
    "investors@{domain}",
    "ir@{domain}",
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

_SOURCE_PRIORITIES = {
    "current": 100,
    "hunter_finder": 95,
    "hunter_domain": 88,
    "site_named": 86,
    "site_explicit": 78,
    "team_pattern": 70,
    "harvester": 60,
    "functional_pattern": 40,
}

_DOMAIN_OVERRIDES = {
    "HighLife": "highlifemedical.com",
    "Oncovita": "oncovita.fr",
    "Qubit Pharmaceuticals": "qubit-pharmaceuticals.com",
    "Advanced BioDesign": "a-biodesign.com",
    "Sonio": "sonio.app",
}

_BAD_NAME_TOKENS = {
    "admin", "board", "bonjour", "ceo", "chief", "clinical", "cofounder", "co-founder",
    "cnrs", "contact", "decouvrir", "discover", "doctor", "dr", "executive", "finance",
    "founder", "hello", "info", "investor", "investors", "ir", "marketing",
    "investigator", "join", "medical", "numerique", "officer", "oncologist", "partner", "partnership",
    "phd", "pharmd", "president", "prof", "professor", "research", "sales", "scientific",
    "service", "support", "team", "technology", "university", "us", "welcome", "jumeau",
}

_BAD_ROLE_TEXT_FRAGMENTS = {
    "join us", "technology", "scientific board", "advisory board", "president of",
    "university", "professor", "23rd", "november", "october", "december", "january",
    "february", "march", "april", "may ", "june", "july", "august", "september",
}


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


def _hunter_candidates(domain: str, first: str = "", last: str = "") -> list[dict]:
    if not HUNTER_API_KEY:
        return []

    candidates = []
    seen = set()

    def add_candidate(email: str, first_name: str = "", last_name: str = "", position: str = "", confidence: str = "", source: str = "hunter_domain"):
        email = (email or "").lower().strip()
        if not email or email in seen or not _is_domain_email(email, domain):
            return
        seen.add(email)
        role = _role_from_text(position)
        notes = _merge_notes(
            "Hunter",
            f"position: {position}" if position else "",
            f"confidence: {confidence}" if confidence else "",
        )
        candidates.append(_make_candidate(
            email=email,
            domain=domain,
            first=first_name,
            last=last_name,
            contact_role=role,
            contact_origin="interne_probable",
            proof_level="coherent",
            notes=notes,
            source=source,
        ))

    try:
        resp = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "api_key": HUNTER_API_KEY, "limit": 15},
            timeout=_HTTP_TIMEOUT,
        )
        if resp.ok:
            data = resp.json().get("data", {})
            for entry in data.get("emails", []):
                add_candidate(
                    entry.get("value", ""),
                    entry.get("first_name", "") or "",
                    entry.get("last_name", "") or "",
                    entry.get("position", "") or "",
                    str(entry.get("confidence", "") or ""),
                    "hunter_domain",
                )

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
                data = resp2.json().get("data", {})
                add_candidate(
                    data.get("email", ""),
                    data.get("first_name", "") or first,
                    data.get("last_name", "") or last,
                    data.get("position", "") or "",
                    str(data.get("confidence", "") or ""),
                    "hunter_finder",
                )
    except Exception as e:
        log_error("email_enricher", e, f"hunter_candidates {domain}")

    return candidates


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


def _site_candidates(domain: str) -> list[dict]:
    candidates = []
    seen = set()

    team_contacts = scrape_team_contacts(domain)
    for contact in team_contacts:
        first, last = _split_name_parts(contact.get("first", ""), contact.get("last", ""))
        if not first or not last:
            continue
        role_text = contact.get("role_text", "")
        role = _role_from_text(role_text)
        for email in _generate_patterns(first, last, domain):
            if email in seen:
                continue
            seen.add(email)
            candidates.append(_make_candidate(
                email=email,
                domain=domain,
                first=first.capitalize(),
                last=" ".join(part.capitalize() for part in last.split()),
                contact_role=role,
                contact_origin="interne_confirme",
                proof_level="pattern",
                notes=_merge_notes("Official team page", role_text),
                source="team_pattern",
            ))

    for email in scrape_emails_from_site(domain):
        if email in seen:
            continue
        seen.add(email)
        local = email.split("@")[0].lower()
        role = "generique" if local.split(".")[0] in _GENERIC_PREFIXES else ""
        candidates.append(_make_candidate(
            email=email,
            domain=domain,
            contact_role=role,
            contact_origin="interne_confirme",
            proof_level="officiel",
            notes="Official site email",
            source="site_explicit",
        ))

    return candidates


# ---------------------------------------------------------------------------
# Génération de patterns
# ---------------------------------------------------------------------------

def _normalize(s: str) -> str:
    for src, dst in [("é","e"),("è","e"),("ê","e"),("à","a"),("â","a"),("ô","o"),
                     ("î","i"),("û","u"),("ç","c"),("ü","u"),("ö","o"),("-"," ")]:
        s = s.replace(src, dst)
    return s.lower().strip()


def _clean_name_token(value: str) -> str:
    token = _normalize(value or "")
    token = re.sub(r"[^a-z0-9\s-]", "", token)
    return " ".join(token.split())


def _looks_like_person_token(token: str) -> bool:
    token = _clean_name_token(token)
    if not token or len(token) < 2:
        return False
    if any(char.isdigit() for char in token):
        return False
    if token in _BAD_NAME_TOKENS:
        return False
    return True


def _split_name_parts(first: str, last: str) -> tuple[str, str]:
    title_tokens = {"dr", "doctor", "prof", "professor", "md", "phd", "pharmd", "pr"}
    first_parts = [part for part in _clean_name_token(first).split() if part and part not in title_tokens]
    last_parts = [part for part in _clean_name_token(last).split() if part and part not in title_tokens]
    if not first_parts and last_parts:
        first_parts = last_parts[:1]
        last_parts = last_parts[1:]
    return " ".join(first_parts), " ".join(last_parts)


def _merge_notes(*parts: str) -> str:
    cleaned = []
    seen = set()
    for part in parts:
        text = str(part or "").strip().strip(",")
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return " | ".join(cleaned)


def _role_from_text(value: str) -> str:
    text = _normalize(value)
    if any(token in text for token in ("ceo", "chief executive", "founder", "co-founder", "president")):
        return "CEO / Founder"
    if any(token in text for token in ("cbo", "business development", "bizdev", "partnership", "partnering", "commercial")):
        return "CBO / BD / Partnerships"
    if any(token in text for token in ("cfo", "investor relations", "investor", "finance", "financial")):
        return "CFO / IR interne"
    if any(token in text for token in ("cso", "cmo", "scientific", "medical", "clinical", "r&d", "research")):
        return "CSO / CMO"
    if any(token in text for token in ("communication", "communications", "marketing", "press", "media", "product", "clinical marketing")):
        return "Product / Clinical Marketing / Comms interne"
    return ""


def _make_candidate(
    *,
    email: str,
    domain: str,
    first: str = "",
    last: str = "",
    contact_role: str = "",
    contact_origin: str = "",
    proof_level: str = "",
    notes: str = "",
    source: str = "",
) -> dict:
    return {
        "email": email.lower().strip(),
        "domaine": domain,
        "prenom": first.strip(),
        "nom": last.strip(),
        "contact_role": contact_role,
        "contact_origin": contact_origin,
        "proof_level": proof_level,
        "notes": notes,
        "_candidate_source": source,
    }


def _candidate_has_bad_local_tokens(email: str, source: str) -> bool:
    if source == "functional_pattern":
        return False
    local = email.split("@")[0].lower()
    parts = [part for part in re.split(r"[._-]+", local) if part]
    functional_ok = {"investor", "investors", "ir"}
    suspicious_substrings = {
        "jumeau", "numerique", "privacy", "message", "your", "join", "scientific",
        "board", "pharmd", "phd", "cnrs", "investigator",
    }
    if any(part in (_BAD_NAME_TOKENS - functional_ok) for part in parts):
        return True
    if any(len(part) < 3 and part not in functional_ok for part in parts):
        return True
    if any(fragment in local for fragment in suspicious_substrings):
        return True
    return False


def _extract_team_contacts_from_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    contacts = []
    seen = set()
    selectors = [
        "[class*='team']",
        "[class*='member']",
        "[class*='founder']",
        "[class*='leadership']",
        "[class*='management']",
        "section",
        "article",
    ]
    skip_kw = {"our team", "about", "contact", "careers", "jobs", "news", "mission", "vision", "values"}
    for sel in selectors:
        for tag in soup.select(sel):
            lines = [line.strip() for line in tag.get_text(separator="\n").splitlines() if line.strip()]
            if not lines:
                continue
            for idx, line in enumerate(lines):
                words = line.split()
                if not (2 <= len(words) <= 4):
                    continue
                if not all(w[:1].isupper() for w in words if w):
                    continue
                lower = line.lower()
                if any(kw in lower for kw in skip_kw):
                    continue
                first = words[0]
                last = " ".join(words[1:])
                first_norm, last_norm = _split_name_parts(first, last)
                if not _looks_like_person_token(first_norm):
                    continue
                if not all(_looks_like_person_token(part) for part in last_norm.split() if part):
                    continue
                role_text = ""
                for next_line in lines[idx + 1 : idx + 3]:
                    if len(next_line) <= 90 and next_line != line:
                        role_text = next_line
                        break
                role_lower = _normalize(role_text)
                if any(fragment in role_lower for fragment in _BAD_ROLE_TEXT_FRAGMENTS):
                    continue
                last_parts = [part for part in last_norm.split() if part]
                if last_parts and len(last_parts[-1]) < 3:
                    continue
                key = (_normalize(first_norm), _normalize(last_norm), _normalize(role_text))
                if key in seen:
                    continue
                seen.add(key)
                contacts.append({"first": first_norm, "last": last_norm, "role_text": role_text})
    return contacts[:12]


def scrape_team_contacts(domain: str) -> list[dict]:
    for path in _ABOUT_PATHS:
        for scheme in ("https", "http"):
            html = _fetch_page(f"{scheme}://{domain}{path}")
            if not html:
                continue
            contacts = _extract_team_contacts_from_html(html)
            if contacts:
                return contacts
    return []


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


def _pattern_candidates(prenom: str, nom: str, domain: str, allow_functional: bool = False) -> list[dict]:
    candidates = []
    seen = set()
    names = []
    first, last = _split_name_parts(prenom, nom)
    if first and last and first.lower() not in _PLACEHOLDER_NAMES and last.lower() not in _PLACEHOLDER_NAMES:
        names.append((first, last, ""))
    for contact in scrape_team_contacts(domain):
        c_first, c_last = _split_name_parts(contact.get("first", ""), contact.get("last", ""))
        if c_first and c_last:
            names.append((c_first, c_last, contact.get("role_text", "")))

    dedup_names = []
    seen_names = set()
    for first_name, last_name, role_text in names:
        key = (first_name, last_name)
        if key in seen_names:
            continue
        seen_names.add(key)
        dedup_names.append((first_name, last_name, role_text))

    for first_name, last_name, role_text in dedup_names:
        role = _role_from_text(role_text)
        pretty_first = "-".join(part.capitalize() for part in first_name.split("-"))
        pretty_last = " ".join(part.capitalize() for part in last_name.split())
        for email in _generate_patterns(first_name, last_name, domain):
            if email in seen:
                continue
            seen.add(email)
            candidates.append(_make_candidate(
                email=email,
                domain=domain,
                first=pretty_first,
                last=pretty_last,
                contact_role=role,
                contact_origin="interne_probable",
                proof_level="pattern",
                notes=_merge_notes("Pattern generated", role_text),
                source="team_pattern",
            ))

    if allow_functional:
        for pattern in _FUNCTIONAL_PATTERNS:
            email = pattern.format(domain=domain)
            if email in seen:
                continue
            seen.add(email)
            candidates.append(_make_candidate(
                email=email,
                domain=domain,
                contact_role="CFO / IR interne",
                contact_origin="interne_probable",
                proof_level="pattern",
                notes="Functional investor relations pattern",
                source="functional_pattern",
            ))

    return candidates


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

def _harvester_candidates(domain: str, prenom: str = "", nom: str = "") -> list[dict]:
    candidates = []
    seen = set()
    harvester_emails = _run_harvester(domain)
    first, last = _split_name_parts(prenom, nom)
    for email in harvester_emails:
        if email in seen or not _is_domain_email(email, domain):
            continue
        seen.add(email)
        role = ""
        notes = "theHarvester OSINT"
        if last and last[:4] in email.lower():
            notes = _merge_notes(notes, "lastname match")
        if first and first[:3] in email.lower():
            notes = _merge_notes(notes, "firstname match")
        candidates.append(_make_candidate(
            email=email,
            domain=domain,
            first=prenom,
            last=nom,
            contact_role=role,
            contact_origin="interne_probable",
            proof_level="coherent",
            notes=notes,
            source="harvester",
        ))
    return candidates


def _select_best_candidate(base_lead: dict, candidates: list[dict]) -> dict | None:
    from modules.contact_scoring import enrich_contact_fields

    decision_priority = {"auto_send": 3, "auto_hold": 2, "dnc": 1, "": 0}
    ranked = []
    seen = set()

    for candidate in candidates:
        email = candidate.get("email", "").lower().strip()
        if not email or email in seen:
            continue
        if _candidate_has_bad_local_tokens(email, candidate.get("_candidate_source", "")):
            continue
        seen.add(email)

        merged = dict(base_lead)
        merged.update(candidate)
        merged["notes"] = _merge_notes(base_lead.get("notes", ""), candidate.get("notes", ""))
        scored = enrich_contact_fields(merged, increment_hold=False, mutate_status=False)

        if not scored.get("contact_decision"):
            continue

        source = candidate.get("_candidate_source", "")
        ranked.append((
            decision_priority.get(scored.get("contact_decision", ""), 0),
            int(scored.get("contact_score") or 0),
            _SOURCE_PRIORITIES.get(source, 0),
            scored,
        ))

    if not ranked:
        return None

    ranked.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    return ranked[0][3]


def find_best_contact(lead: dict) -> dict | None:
    company_name = (lead.get("boite") or "").strip()
    domain = _DOMAIN_OVERRIDES.get(company_name, (lead.get("domaine") or "").strip()).lower()
    if not domain:
        return None

    prenom = lead.get("prenom", "")
    nom = lead.get("nom", "")
    candidates: list[dict] = []

    current_email = (lead.get("email") or "").strip().lower()
    if current_email.endswith("@" + domain):
        candidates.append(_make_candidate(
            email=current_email,
            domain=domain,
            first=prenom,
            last=nom,
            contact_role=lead.get("contact_role", ""),
            contact_origin=lead.get("contact_origin", ""),
            proof_level=lead.get("proof_level", ""),
            notes=lead.get("notes", ""),
            source="current",
        ))

    first_real = prenom if _clean_name_token(prenom).lower() not in _PLACEHOLDER_NAMES else ""
    last_real = nom if _clean_name_token(nom).lower() not in _PLACEHOLDER_NAMES else ""

    candidates.extend(_hunter_candidates(domain, first_real, last_real))
    candidates.extend(_site_candidates(domain))
    candidates.extend(_harvester_candidates(domain, first_real, last_real))
    allow_functional = str(lead.get("premium", "")).strip().lower() == "true"
    candidates.extend(_pattern_candidates(first_real, last_real, domain, allow_functional=allow_functional))

    best = _select_best_candidate(lead, candidates)
    if not best:
        return None
    best["domaine"] = domain
    return best


def find_email(prenom: str, nom: str, domain: str) -> str:
    lead = {"prenom": prenom, "nom": nom, "domaine": domain, "notes": "", "premium": ""}
    best = find_best_contact(lead)
    return best.get("email", "") if best else ""


def enrich_lead(lead: dict) -> dict:
    """Enrichit un lead avec le meilleur contact trouvable pour ce domaine."""
    best = find_best_contact(lead)
    if not best:
        return lead

    enriched = dict(lead)
    for key in ("email", "prenom", "nom", "notes", "contact_role", "contact_origin", "proof_level", "contact_score", "contact_decision"):
        if best.get(key):
            enriched[key] = best[key]
    if best.get("premium"):
        enriched["premium"] = best["premium"]
    return enriched


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
