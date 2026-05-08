"""
Automatisation LinkedIn via Playwright + playwright-stealth.
Envoie des invitations et messages aux leads.
"""
import asyncio
import time
import random
from datetime import date
from modules.config import LINKEDIN_EMAIL, LINKEDIN_PASSWORD, MAX_LINKEDIN_PER_MONTH
from modules.leads_csv import count_linkedin_sent_this_month, update_lead
from modules.logger import log_error

from modules.llm import invoke_llm

LINKEDIN_MSG_TEMPLATE = (
    "Salut {prenom}, je fais des visuels 3D pour les biotech — "
    "分子 mechanisms, dispositifs, procédures. 5 jours. Tu团队的 besoin ?"
)

def generate_linkedin_message(prenom: str, company_name: str = "", sector: str = "") -> str:
    """Génère un message LinkedIn plus humain via LLM."""
    system = """Tu es Edgar. Message LinkedIn court (max 280 caractères).

RÈGLES:
- Format: "Salut [prénom], [ce que tu fais] en [délai]. [question]
- Pas de liste de services
- Pas de "Bonjour"
- Pas de "Ça pourrait vous être utile ?" (trop faible)
- Ton naturel, direct, sans blabla"""

    context = f"Prénom: {prenom}, Boîte: {company_name}, Secteur: {sector}"
    result = invoke_llm(system, context, max_tokens=100).strip()

    if result and len(result) <= 300:
        return result

    return LINKEDIN_MSG_TEMPLATE.format(prenom=prenom)

async def _send_invitation_async(linkedin_url: str, prenom: str, message: str) -> bool:
    try:
        from playwright.async_api import async_playwright
        from playwright_stealth import stealth_async

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            await stealth_async(page)

            # Login
            await page.goto("https://www.linkedin.com/login", timeout=30000)
            await page.fill("#username", LINKEDIN_EMAIL)
            await page.fill("#password", LINKEDIN_PASSWORD)
            await page.click('[type="submit"]')
            await page.wait_for_timeout(3000)

            # Check login success
            if "challenge" in page.url or "checkpoint" in page.url:
                print("[LinkedIn] Vérification de sécurité détectée — arrêt")
                await browser.close()
                return False

            # Navigate to profile
            await page.goto(linkedin_url, timeout=30000)
            await page.wait_for_timeout(2000 + random.randint(500, 1500))

            # Find and click Connect button
            connect_btn = await page.query_selector('button[aria-label*="Connect"], button[aria-label*="Se connecter"]')
            if not connect_btn:
                # Try More button
                more_btn = await page.query_selector('button[aria-label*="More"]')
                if more_btn:
                    await more_btn.click()
                    await page.wait_for_timeout(1000)
                    connect_btn = await page.query_selector('div[aria-label*="Connect"]')

            if not connect_btn:
                print(f"[LinkedIn] Bouton Connect non trouvé pour {linkedin_url}")
                await browser.close()
                return False

            await connect_btn.click()
            await page.wait_for_timeout(1500)

            # Add note if possible
            add_note_btn = await page.query_selector('button[aria-label*="Add a note"]')
            if add_note_btn:
                await add_note_btn.click()
                await page.wait_for_timeout(1000)
                msg = message
                textarea = await page.query_selector('textarea[name="message"]')
                if textarea:
                    await textarea.fill(msg[:300])

            # Confirm send
            send_btn = await page.query_selector('button[aria-label*="Send"]')
            if send_btn:
                await send_btn.click()
                await page.wait_for_timeout(2000)

            await browser.close()
            return True

    except Exception as e:
        log_error("linkedin_outreach", e, f"send_invitation {linkedin_url}")
        return False

def send_invitation(lead: dict) -> bool:
    """Send a LinkedIn connection request to a lead."""
    if count_linkedin_sent_this_month() >= MAX_LINKEDIN_PER_MONTH:
        print(f"[LinkedIn] Limite mensuelle atteinte ({MAX_LINKEDIN_PER_MONTH})")
        return False

    linkedin_url = lead.get("linkedin_url", "")
    if not linkedin_url:
        print(f"[LinkedIn] Pas de profil URL pour {lead.get('email', '')}")
        return False

    prenom = lead.get("prenom", "")
    email = lead.get("email", "")
    boite = lead.get("boite", "")
    sector = lead.get("sector", "")

    message = generate_linkedin_message(prenom, boite, sector)

    try:
        success = asyncio.run(_send_invitation_async(linkedin_url, prenom, message))
    except Exception as e:
        log_error("linkedin_outreach", e, f"asyncio.run {linkedin_url}")
        success = False

    if success:
        today = date.today().isoformat()
        update_lead(email, {
            "date_linkedin": today,
            "statut": "LinkedIn envoyé",
        })
        print(f"[LinkedIn] Invitation envoyée à {prenom} — {linkedin_url}")
        # Random delay between 30s and 2min to avoid detection
        time.sleep(random.randint(30, 120))

    return success

def send_invitations_batch(leads: list[dict]) -> int:
    """Send LinkedIn invitations to a batch of leads. Returns count sent."""
    sent = 0
    for lead in leads:
        if count_linkedin_sent_this_month() >= MAX_LINKEDIN_PER_MONTH:
            break
        if send_invitation(lead):
            sent += 1
    return sent
