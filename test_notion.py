#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not NOTION_TOKEN or not NOTION_DATABASE_ID:
    print("ERREUR: Variables NOTION_TOKEN et NOTION_DATABASE_ID requises")
    sys.exit(1)

notion = Client(auth=NOTION_TOKEN)

lead_data = {
    "nom": "Maurice",
    "prenom": "",
    "boite": "Cardiawave",
    "domaine": "cardiawave.com",
    "email": "maurice.delplanque@cardiawave.com",
    "linkedin_url": "",
    "statut": "Nouveau",
    "canal": "Email",
    "notes": "Test de création depuis test_notion.py"
}

properties = {
    "Nom": {"title": [{"text": {"content": lead_data["nom"] or "Cardiawave"}}]},
    "Prénom": {"rich_text": [{"text": {"content": lead_data["prenom"]}}]},
    "Boîte": {"rich_text": [{"text": {"content": lead_data["boite"]}}]},
    "Domaine": {"rich_text": [{"text": {"content": lead_data["domaine"]}}]},
    "Email": {"email": lead_data["email"]},
    "LinkedIn_URL": {"url": lead_data["linkedin_url"]} if lead_data["linkedin_url"] else None,
    "Statut": {"select": {"name": lead_data["statut"]}},
    "Canal": {"rich_text": [{"text": {"content": lead_data["canal"]}}]} if lead_data["canal"] else None,
    "Notes": {"rich_text": [{"text": {"content": lead_data["notes"]}}]},
}

properties = {k: v for k, v in properties.items() if v is not None}

print("=== CRÉATION DE LA LIGNE DANS NOTION ===")
new_page = notion.pages.create(
    parent={"database_id": NOTION_DATABASE_ID},
    properties=properties
)
page_id = new_page["id"]
print(f"✓ Page créée: {page_id}")

print("\n=== LECTURE DE LA LIGNE CRÉÉE ===")
retrieved = notion.pages.retrieve(page_id=page_id)
props = retrieved["properties"]

for key in ["Nom", "Prénom", "Boîte", "Domaine", "Email", "LinkedIn_URL", "Statut", "Canal", "Notes"]:
    if key in props:
        prop = props[key]
        if prop["type"] == "title":
            val = prop["title"][0]["text"]["content"] if prop["title"] else ""
        elif prop["type"] == "rich_text":
            val = prop["rich_text"][0]["text"]["content"] if prop["rich_text"] else ""
        elif prop["type"] == "email":
            val = prop["email"] or ""
        elif prop["type"] == "url":
            val = prop["url"] or ""
        elif prop["type"] == "select":
            val = prop["select"]["name"] if prop["select"] else ""
        print(f"  {key}: {val}")

print("\n=== MISE À JOUR DU STATUT ===")
notion.pages.update(
    page_id=page_id,
    properties={
        "Statut": {"select": {"name": "Email envoyé"}}
    }
)
print("✓ Statut mis à jour → 'Email envoyé'")

print("\n=== VÉRIFICATION FINALE ===")
final = notion.pages.retrieve(page_id=page_id)
final_status = final["properties"]["Statut"]["select"]["name"]
print(f"✓ Statut final: {final_status}")

print("\n=== RÉSUMÉ ===")
print(f"  Page ID: {page_id}")
print(f"  Entreprise: Cardiawave")
print(f"  Email: maurice.delplanque@cardiawave.com")
print(f"  Statut: {final_status}")
print("\n✓ TEST RÉUSSI - La ligne est dans Notion")