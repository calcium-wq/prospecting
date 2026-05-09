# GitHub Actions Setup - Prospecting

Objectif : faire tourner la prospection automatiquement meme quand le PC de Rudeus est eteint.

## Principe

Le repo peut rester public.
Les secrets restent prives dans GitHub Actions.
Les workflows ne sont declenches que par `schedule` ou `workflow_dispatch`.

## Secrets GitHub a configurer

Dans `Settings -> Secrets and variables -> Actions`, ajouter :

- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `GMAIL_ADDRESS`
- `GMAIL_APP_PASSWORD`
- `LINKEDIN_EMAIL`
- `LINKEDIN_PASSWORD`
- `HUNTER_API_KEY`
- `NOTION_TOKEN`
- `NOTION_DATABASE_ID`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Workflows installes

- `prospecting-monitor.yml`
  - toutes les heures
  - lit Gmail
  - met a jour `leads.csv`
  - notifie si un prospect repond

- `prospecting-enrich.yml`
  - tous les jours
  - enrichit les leads sans email
  - commit `leads.csv` si changement

- `prospecting-auto-send.yml`
  - tous les jours
  - envoie automatiquement les leads juges surs
  - commit `leads.csv` si changement

- `prospecting-followups.yml`
  - tous les jours
  - envoie les relances automatiques
  - commit `leads.csv` si changement

- `prospecting-daily-summary.yml`
  - tous les jours
  - envoie le resume Telegram

## Horaires

Les cron GitHub sont en UTC.
Les horaires choisis privilegient la fin de journee Europe/Paris.

## Notes importantes

- Le mode `--auto-send-safe` n'envoie que les leads :
  - `statut == Nouveau`
  - avec email
  - non `DNC`
  - non generiques
  - sans prenom suspect
- Le monitor ne repond jamais a la place d'Edgar.
- Les relances sont securisees et passent par des fallbacks humains si le LLM genere quelque chose de faible.
- `theHarvester` est optionnel sur GitHub Actions. Si absent, le pipeline continue sans lui.

## Premier ordre de lancement conseille

1. Configurer les secrets.
2. Passer le repo en public si necessaire.
3. Activer les workflows.
4. Lancer manuellement une fois :
   - `Prospecting Monitor`
   - `Prospecting Enrich`
   - `Prospecting Auto Send Safe`
   - `Prospecting Followups`
5. Verifier dans GitHub Actions que `leads.csv` est bien mis a jour par commit automatique.

## Limites de la version 0 euro

- GitHub Actions n'est pas une vraie VM persistante.
- C'est tres bien pour des taches cron et des batchs.
- Ce n'est pas ideal pour du navigateur persistant ou du LinkedIn lourd.
- Quand on pourra, l'etape suivante sera une machine always-on type Oracle Always Free.
