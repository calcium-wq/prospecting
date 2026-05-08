#!/usr/bin/env python3
"""
Setup Notion : vérifie l'accès et crée les colonnes nécessaires si manquantes.

PRÉREQUIS : La base Notion doit être partagée avec l'intégration.
1. Ouvre Notion → va sur ta base de données
2. Clique "..." (en haut à droite) → "Connections" → cherche "Propects" → connecter
3. Relance ce script
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from modules.config import NOTION_TOKEN, NOTION_DATABASE_ID
from notion_client import Client

def check_and_setup():
    notion = Client(auth=NOTION_TOKEN)

    print(f"Test connexion à la base : {NOTION_DATABASE_ID}")
    try:
        db = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
        title = db.get("title", [{}])[0].get("plain_text", "unknown")
        print(f"✓ Base trouvée : '{title}'")

        existing_props = set(db.get("properties", {}).keys())
        print(f"  Colonnes existantes : {sorted(existing_props)}")

        required_props = {
            "Prénom": {"rich_text": {}},
            "Boîte": {"rich_text": {}},
            "Domaine": {"rich_text": {}},
            "Email": {"email": {}},
            "LinkedIn_URL": {"url": {}},
            "Statut": {
                "select": {
                    "options": [
                        {"name": "Nouveau", "color": "gray"},
                        {"name": "Email envoyé", "color": "blue"},
                        {"name": "LinkedIn envoyé", "color": "purple"},
                        {"name": "Relancé", "color": "yellow"},
                        {"name": "Intéressé", "color": "green"},
                        {"name": "Call planifié", "color": "orange"},
                        {"name": "Froid", "color": "default"},
                        {"name": "DNC", "color": "red"},
                    ]
                }
            },
            "Canal": {"rich_text": {}},
            "Date_Email": {"date": {}},
            "Date_LinkedIn": {"date": {}},
            "Relance_J3": {"date": {}},
            "Relance_J7": {"date": {}},
            "Relance_J14": {"date": {}},
            "Réponse": {"rich_text": {}},
            "DNC": {"checkbox": {}},
            "Notes": {"rich_text": {}},
        }

        missing = {k: v for k, v in required_props.items() if k not in existing_props}
        if missing:
            print(f"\n  Ajout de {len(missing)} colonnes manquantes...")
            notion.databases.update(
                database_id=NOTION_DATABASE_ID,
                properties=missing
            )
            print(f"  ✓ Colonnes ajoutées : {list(missing.keys())}")
        else:
            print("  ✓ Toutes les colonnes sont présentes")

        return True

    except Exception as e:
        print(f"\n✗ ERREUR : {e}")
        print("\n--- ACTION REQUISE ---")
        print("Ta base Notion n'est pas partagée avec l'intégration.")
        print("\nÉtapes :")
        print("1. Ouvre Notion → va sur ta base de données (ID: " + NOTION_DATABASE_ID + ")")
        print("2. Clique sur '...' en haut à droite → 'Connections'")
        print("3. Cherche 'Propects' → clique 'Connect'")
        print("4. Relance : python3 setup_notion.py")
        return False

if __name__ == "__main__":
    success = check_and_setup()
    sys.exit(0 if success else 1)
