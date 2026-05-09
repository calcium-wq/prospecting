# Workflows GitHub Actions - Prospecting Pipeline

Ce fichier explique chaque workflow automatis.

---

## Tableau recapitulatif

| Workflow | Heure (Paris) | Jours | Fonction |
|----------|---------------|-------|----------|
| `prospecting-enrich` | 12:30 | Lun-Sam | Enrichit les emails |
| `prospecting-auto-send` | 18:05 | Lun-Sam | Envoie les emails |
| `prospecting-followups` | 18:35 | Lun-Sam | Envoie les relances |
| `prospecting-daily-summary` | 20:15 | Lun-Sam | Rapport quotidien |
| `prospecting-monitor` | :07 chaque heure | Tous les jours | Surveille les reponses |

---

## Detail par workflow

### 1. prospecting-enrich

**Ce qu'il fait** : Cherche les emails manquants pour les leads "Nouveau" via Hunter.io et scraping de site.

**Heure** : 12:30 (Paris), du lundi au samedi

**Ce qu'il modifie** :
- `data/leads.csv` (ajout colonne `email`)
- Commit automatique si changement

**Ce qu'il ne fait jamais** :
- N'envoi pas d'emails
- Ne modifie pas le statut des leads
- Ne touche pas a Notion
- Ne scrape pas de nouveaux leads

**Comment savoir si ca marche** :
- Voir les commits dans GitHub avec message "chore: sync enrich updates"
- Checker `data/leads.csv` : colonne `email` doit avoir plus de valeurs

---

### 2. prospecting-auto-send

**Ce qu'il fait** : Envoie les emails initiaux aux leads qui ont un email et qui sont en statut "Nouveau" (valides, prets a envoyer).

**Heure** : 18:05 (Paris), du lundi au samedi

**Ce qu'il modifie** :
- `data/leads.csv` (statut -> "Email envoye", colonne `date_email`)
- Envoie des vrais emails aux prospects

**Ce qu'il ne fait jamais** :
- N'ajoute pas de nouveaux leads
- Ne repond pas aux receptions
- Ne fait pas de relances
- N'envoie que des emails "validated" (pas de spam)

**Comment savoir si ca marche** :
- Commit "chore: sync auto-send updates"
- Emails recus par les prospects (si tu es en copie ou via notification Telegram)
- colonne `date_email` remplies

---

### 3. prospecting-followups

**Ce qu'il fait** : Envoie les relances automatiques (J+3, J+7, J+14) aux leads qui ont recu un email initial.

**Heure** : 18:35 (Paris), du lundi au samedi

**Ce qu'il modifie** :
- `data/leads.csv` (colonnes `relance_j3`, `relance_j7`, `relance_j14`)
- Envoie des emails de relance

**Ce qu'il ne fait jamais** :
- N'ajoute pas de nouveaux leads
- Ne scrape pas
- N'envoie pas d'email initial (que des relances)

**Comment savoir si ca marche** :
- Commit "chore: sync followup updates"
- Colonnes de relance remplies dans leads.csv

---

### 4. prospecting-daily-summary

**Ce qu'il fait** : Genere et envoie un rapport quotidien (nombre emails envoyes, taux de reponse, leads en cours).

**Heure** : 20:15 (Paris), du lundi au samedi

**Ce qu'il modifie** : **RIEN** (lecture seule)

**Ce qu'il ne fait jamais** :
- N'envoi pas d'emails aux prospects
- Ne modifie pas leads.csv
- N'enrichit pas les leads

**Comment savoir si ca marche** :
- Workflow apparait dans "Actions" GitHub
- Regarder les logs pour voir le rapport genere

---

### 5. prospectus-monitor

**Ce qu'il fait** : Verifie la boites Gmail toutes les heures pour detecter les reponses des prospects. Met a jour les statuts (DNC, Intéressé, etc.) et envoie une notification Telegram en cas de reponse positive.

**Heure** : :07 chaque heure (donc 00:07, 01:07, 02:07, ...)

**Ce qu'il modifie** :
- `data/leads.csv` (statut, colonne `reponse`, colonne `dnc`)
- Envoie des notifications Telegram

**Ce qu'il ne fait jamais** :
- N'envoi pas d'emails aux prospects
- Ne scrape pas
- N'ajoute pas de nouveaux leads

**Comment savoir si ca marche** :
- Notification Telegram recue avec "Nouveau lead chaud"
- Mise a jour du statut dans leads.csv

---

## Comment verifier que tout marche

### 1. Voir les dernieres executions

Aller sur : `https://github.com/[ton-compte]/prospecting/actions`

Verifier que tous les workflows sont "green" (cercle vert).

### 2. Voir les commits recents

```bash
git log --oneline -10
```

Les commits automatiquement par les workflows sont :
- "chore: sync enrich updates"
- "chore: sync auto-send updates"
- "chore: sync followup updates"
- "chore: sync monitor updates"

### 3. Verifier les donnees

```bash
python3 -c "
import pandas as pd
df = pd.read_csv('data/leads.csv')
print(f'Total: {len(df)}')
print(f'Emails envoyes: {len(df[df[\"statut\"]==\"Email envoye\"])}')
print(f'DNC: {len(df[df[\"dnc\"]==True])}')
print(f'Nouveau: {len(df[df[\"statut\"]==\"Nouveau\"])}')
"
```

### 4. Recevoir les notifications

- Verifier que Telegram Bot est configure
- Tu devrais recevoir une notification a chaque reponse positive detectee

---

## Declencher un workflow manuellement

Si un workflow ne s'est pas execute ou si tu veux forcer une execution :

1. Aller sur `https://github.com/[ton-compte]/prospecting/actions`
2. Cliquer sur le workflow desire
3. Bouton "Run workflow" en haut a droite

Cela declenchera le workflow meme en dehors de l'heure planifiee.

---

## Troubleshooting

| Probleme | Solution |
|----------|----------|
| Workflow echoue | Voir les logs dans l'onglet "Actions" |
| Emails pas envoyes | Verifier que les leads ont un email (enrich doit avoir fonctionne) |
| Statuts pas mis a jour | Verifier que le monitor s'est execute recemment |
|rien ne se passe |Verifier les secrets GitHub sont configures (OPENROUTER_API_KEY, etc.) |

---

## Ordonnancement quotidien type

| Heure | Action |
|-------|--------|
| 12:30 | Enrichir les nouveaux leads |
| 18:05 | Envoyer les emails initiaux |
| 18:35 | Envoyer les relances |
| 20:15 | Rapport quotidien |
| :07 / heure | Surveiller les reponses |

**Note** : Aucun workflow ne tourne le dimanche.