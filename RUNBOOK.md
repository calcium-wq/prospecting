# Runbook Prospecting — Edgar Frinis

**Dernière mise à jour :** Mai 2026
**Pipeline :** Animations 3D médicales pour biotechs françaises

---

## 1. Lancer un cycle complet de prospection

```bash
cd ~/prospecting
python3 run.py
```

**Ce que ça fait (dans l'ordre) :**
1. Scrape de nouvelles startups FR (leads.csv)
2. Enrichit les emails manquants (Hunter + site + theHarvester)
3. Génère les relances en retard (J+3/J+7/J+14)
4. Génère les emails initiaux pour validation
5. Envoie les emails (après confirmation)
6. Envoie les invitations LinkedIn (si 3+ jours depuis l'email)
7. Vérifie les réponses Gmail

**Sortie normale :**
```
============================================================
PIPELINE PROSPECTION B2B — Edgar Frinis
Date : 2026-05-08
============================================================
[Scraper] 3 nouveaux leads ajoutés dans leads.csv
[Enricher] 2 leads → emails trouvés
[Followup] Total relances envoyées : 1
PRÉVIEW — GÉNÉRATION DES 16 EMAILS
...
============================================================
Pipeline terminé.
============================================================
```

Si tu veux limiter le nombre de leads scrapés :
```bash
python3 run.py --max-leads 20
```

---

## 2. Vérifier que tout fonctionne

```bash
python3 run.py --test
```

**Ce que ça teste (8 composants) :**

| # | Composant | Ce qu'on vérifie |
|---|-----------|-----------------|
| 1/8 | Config .env | Toutes les clés API sont chargées |
| 2/8 | leads.csv | Le fichier existe et contient des leads |
| 3/8 | OpenRouter LLM | L'IA répond correctement |
| 4/8 | Gmail SMTP | Connexion sortante (envoi) |
| 5/8 | Gmail IMAP | Connexion entrante (lecture) |
| 6/8 | Notion CRM | La base de données est accessible |
| 7/8 | Telegram | Le bot peut envoyer des messages |
| 8/8 | theHarvester | L'outil de recherche d'emails fonctionne |

**Résultat attendu :** `8/8 composants OK`

Si un composant échoue, le runbook (sections 6 et 7) explique quoi faire.

---

## 3. Valider les emails avant envoi

**Jamais d'envoi automatique.** Toujours valider avant.

```bash
python3 run.py --preview
```

**Ce que ça fait :**
- Génère un email personnalisé pour chaque lead "Nouveau" avec email
- Affiche chaque email avec objet + corps
- **N'envoie rien** — affiche uniquement

**Exemple de sortie :**
```
============================================================
PRÉVIEW — GÉNÉRATION DES 16 EMAILS
============================================================
[Preview] 16 leads à générer

------------------------------------------------------------
[1/16] mathieu.schue@cilcare.com
Objet : La visibilité de CIL001
Salutation : Bonjour Mathieu,
Corps :
------------------------------------------------------------
L'entrée en Phase 2a pour traiter la synaptopathie cochléaire...
...
------------------------------------------------------------
[2/16] contact@treefrog-therapeutics.com
...
```

**Si un email ne te plaît pas :**
- Édite `modules/llm.py` pour ajuster les règles
- Relance `--preview` pour voir le nouveau résultat

**Pour envoyer après validation :**
```bash
python3 run.py --send
```
Le script demandera confirmation :
```
16 emails sont prêts.
Tapez 'oui' pour envoyer, 'non' pour annuler :
> _
```

Tape `oui` (ou `o`) pour envoyer.

---

## 4. Répondre à un lead chaud

Un lead chaud = quelqu'un qui a répondu positivement (notifié par Telegram ou détecté dans Gmail).

### Étape A : Identifier le lead

```bash
python3 run.py --monitor
```

Cela lit la boîte Gmail et affiche les réponses des leads connus. Les réponses positives sont envoyées sur Telegram.

### Étape B : Mettre à jour le lead

Quand tu as une réponse, mets à jour manuellement dans leads.csv :

| Champ | Valeur | Signification |
|-------|--------|---------------|
| `statut` | `Intéressé` | Le lead a répondu positivement |
| `statut` | `DNC` | Le lead ne veut pas être recontacté |
| `reponse` | `2026-05-08` | Date de la réponse |
| `notes` | `Veut un call` | Action à faire |

**Méthode directe (fichier CSV) :**
```bash
nano ~/prospecting/data/leads.csv
# Cherche le lead par email, modifie les champs
```

**Méthode via Notion :**
```bash
python3 setup_notion.py
# Recrée le schéma de la base si besoin
```

### Étape C : Notifier sur Telegram (si pas déjà fait)

```bash
cd ~/prospecting
python3 -c "
from modules.telegram_notif import notify_hot_lead
notify_hot_lead('Jean', 'Biotech XYZ', 'Réponse positive')
"
```

---

## 5. Ajouter manuellement un lead dans leads.csv

Ouvre le fichier et ajoute une ligne :

```bash
nano ~/prospecting/data/leads.csv
```

**Format d'une ligne (21 colonnes, séparées par des virgules) :**

```
nom,prenom,boite,domaine,email,linkedin_url,statut,canal,date_email,date_linkedin,relance_j3,relance_j7,relance_j14,reponse,dnc,notes
```

**Exemple minimal :**
```
,Marc,NomDeLaBoite,nomdelaboite.com,marc@nomdelaboite.com,https://fr.linkedin.com/in/marc,ouveau,,,,,,,,,
```

| Champ | Obligatoire | Notes |
|-------|-------------|-------|
| `prenom` | Oui | Premier prénom |
| `boite` | Oui | Nom de la boîte |
| `domaine` | Oui | Site web (sans https://) |
| `email` | Recommandé | Email si connu, sinon vide |
| `linkedin_url` | Recommandé | URL LinkedIn si connue |
| `statut` | Oui | Mettre `Nouveau` pour un nouveau lead |
| Tous les autres | Non | Vides (laisses les virgules) |

**Règles de déduplication :**
- Si l'email existe déjà → le lead est ignoré
- Si le domaine existe déjà → le lead est ignoré

**Méthode alternative (via script Python) :**
```bash
cd ~/prospecting
python3 -c "
from modules.leads_csv import add_lead
add_lead({
    'prenom': 'Marc',
    'boite': 'NomDeLaBoite',
    'domaine': 'nomdelaboite.com',
    'email': 'marc@nomdelaboite.com',
    'linkedin_url': 'https://fr.linkedin.com/in/marc',
    'statut': 'Nouveau'
})
print('Lead ajouté')
"
```

---

## 6. Que faire si Notion ne répond pas

**Symptômes :**
- `ensure_database_schema` échoue
- Les leads ne sont pas synchronisés
- Erreur `database not found` ou `401 Unauthorized`

### Checklist diagnostique

```bash
cd ~/prospecting
python3 -c "
from modules.notion_crm import ensure_database_schema
ok = ensure_database_schema()
print('OK' if ok else 'ECHEC')
"
```

### Solution 1 : Vérifier les credentials

```bash
grep NOTION ~/prospecting/.env
```

Tu dois voir :
```
NOTION_TOKEN=secret_...
NOTION_DATABASE_ID=...
```

**Si vide :**
1. Va sur https://www.notion.so/my-integrations
2. Crée une nouvelle intégration (ou réutilise "Propects")
3. Copie le token dans `.env`
4. Dans Notion, partage la base avec l'intégration

### Solution 2 : Vérifier que la base est partagée

1. Ouvre la base Notion
2. Clique sur les 3 points (⋯) en haut à droite
3. "Connections" → vérifie que ton intégration y est
4. Si non, ajoute-la

### Solution 3 : Recréer le schéma

```bash
cd ~/prospecting
python3 setup_notion.py
```

Cela recrée les colonnes attendues dans la base.

### Solution 4 : Fallback sur leads.csv seulement

Si Notion est HS, le pipeline fonctionne quand même — leads.csv est le fichier pivot. Les actions sont logguées dans `data/errors.log` au lieu de Notion.

**Commande pour forcer le mode sans Notion :**
```bash
# Pas de flag spécial — le pipeline continue automatiquement
# Ajoute --scrape --enrich --preview pour éviter le step Notion
python3 run.py --scrape --enrich --preview
```

---

## 7. Que faire si Gmail bloque l'envoi

**Symptômes :**
- Erreur `Authentication failed` ou `535 5.7.8`
- Les emails n'arrivent pas
- Erreur `SMTPRecipientsRefused`

### Checklist diagnostique

```bash
cd ~/prospecting
python3 run.py --test
# Regarde le test [4/8] Gmail SMTP
```

### Cause 1 : App Password expiré ou invalide

1. Va sur https://myaccount.google.com/security
2. "Mots de passe des applications" (2-Step Verification requis)
3. Génère un nouveau mot de passe de 16 caractères
4. Mets à jour dans `.env` :
   ```
   GMAIL_APP_PASSWORD=nouveau_mot_de_passe
   ```

### Cause 2 : Trop d'emails envoyés (rate limit)

- **Limite :** 100 emails/jour
- Le script refuse d'envoyer au-delà et affiche :
  ```
  [EmailSender] Limite journalière atteinte (100)
  ```

**Solution :** Attend le lendemain ou réduis le nombre de leads contactés.

### Cause 3 : Le compte est bloqué par Google

Google peut temporairement bloquer l'envoi si :
- Trop de tentatives de connexion échouées
- Activité inhabituelle
- 2FA non activé

**Solution :**
1. Connecte-toi manuellement sur https://gmail.com
2. Vérifie les alertes de sécurité
3. Active la validation en 2 étapes si pas fait
4. Génère un nouveau App Password

### Cause 4 : Email rejeté par le destinataire

- Adresse inexistante → `SMTPRecipientsRefused`
- Boîte pleine → légère attente

Le script log dans `data/errors.log`. Vérifie :
```bash
tail -20 ~/prospecting/data/errors.log
```

---

## 8. Comment relancer les crons si le PC redémarre

### Vérifier que les crons sont actifs

```bash
crontab -l
```

**Devrait afficher :**
```
# Pipeline complet — lundi 9h UTC
0 9 * * 1 /usr/bin/python3 /home/mbped/prospecting/run.py >> /home/mbped/prospecting/data/prospecting.log 2>&1

# Surveillance Gmail — toutes les heures
0 * * * * cd /home/mbped/prospecting && /usr/bin/python3 /home/mbped/prospecting/run.py --monitor >> /home/mbped/prospecting/data/monitor.log 2>&1

# Relances — 9h30 UTC chaque jour
30 9 * * * cd /home/mbped/prospecting && /usr/bin/python3 /home/mbped/prospecting/run.py --followup >> /home/mbped/prospecting/data/followup.log 2>&1
```

### Réinstaller les crons (si manquants)

```bash
cd ~/prospecting
python3 -c "
cron_jobs = '''0 9 * * 1 /usr/bin/python3 /home/mbped/prospecting/run.py >> /home/mbped/prospecting/data/prospecting.log 2>&1
0 * * * * cd /home/mbped/prospecting && /usr/bin/python3 /home/mbped/prospecting/run.py --monitor >> /home/mbped/prospecting/data/monitor.log 2>&1
30 9 * * * cd /home/mbped/prospecting && /usr/bin/python3 /home/mbped/prospecting/run.py --followup >> /home/mbped/prospecting/data/followup.log 2>&1'''
with open('/tmp/crontab.txt', 'w') as f:
    f.write(cron_jobs)
"
crontab /tmp/crontab.txt
echo "Crons réinstallés"
```

### Vérifier que Python est accessible

```bash
which python3
# Devrait retourner /usr/bin/python3
```

### Après un redémarrage Windows

WSL2 ne démarre pas automatiquement. Pour lancer le pipeline manuellement :

```bash
# 1. Démarrer WSL (si pas déjà fait)
wsl

# 2. Aller dans le dossier
cd ~/prospecting

# 3. Lancer le pipeline
python3 run.py
```

### Vérifier les logs après un redémarrage

```bash
# Log principal
tail -30 ~/prospecting/data/prospecting.log

# Log erreurs
tail -20 ~/prospecting/data/errors.log

# Log surveillance Gmail
tail -10 ~/prospecting/data/monitor.log

# Log relances
tail -10 ~/prospecting/data/followup.log
```

---

## Aide-mémoire

| Action | Commande |
|--------|----------|
| Cycle complet | `python3 run.py` |
| Test rapide | `python3 run.py --test` |
| Valider emails | `python3 run.py --preview` |
| Envoyer emails | `python3 run.py --send` |
| Voir crons | `crontab -l` |
| Vérifier logs | `tail -20 data/*.log` |
| Ajouter lead | `nano data/leads.csv` |
| Vérifier Notion | `python3 test_notion.py` |

---

## Contacts de référence

- **OpenRouter API** : https://openrouter.ai/keys
- **Gmail** : https://myaccount.google.com/security
- **Notion** : https://www.notion.so/my-integrations
- **Telegram Bot** : https://t.me/{bot_name}