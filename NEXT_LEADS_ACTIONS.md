# Actions leads suivants - Priorisation enrichment

**Date**: 2026-05-09
**Objectif**: Augmenter le nombre de prospects avec email valide

---

## Statistiques leads.csv

| Métrique | Nombre |
|----------|--------|
| Total leads | 85 |
| Emails envoyés | 45 |
| DNC (bloqués) | 21 |
| Sans email (Nouveau) | 19 |

---

## Classification des 19 leads sans email

### 🔴 HORS SCOPE / MORT (6)

| Entreprise | Raison |
|------------|--------|
| **Amolyt Pharma** | ACQUISE par AstraZeneca en juillet 2024 ($1.05B) |
| CREAPHARM BIOSERVICES | Pas de domaine, impossible à tracer |
| Avatar Medical Vision | Pas de domaine, impossible à tracer |
| NATÉOSANTÉ | Pas de domaine, impossible à tracer |
| Walid S. Kamoun | Individu sans structure identifiable |
| EVERZOM et OmniSpirant | Pas de domaine, nom composite flou |

→ **Action**: Marquer "hors scope" dans leads.csv, ne plus prospecter

---

### 🔵 RECHERCHE MANUELLE PRIORITAIRE (3)

| # | Entreprise | Pourquoi | Source |
|---|------------|----------|--------|
| 1 | **DBV Technologies** | Phase 3 VITESSE positive déc 2025, BLA soumis H1 2026, cotée Nasdaq+Euronext, levée $116M | Site corporate, LinkedIn CEO Daniel Tassé, relations investisseurs |
| 2 | **HighLife** | CE mark obtenu janvier 2026, FDA Breakthrough Device avril 2025, marché $10B valve mitrale | Site, LinkedIn CEO Stefan Pilz, congrès cardiologie |
| 3 | **Oncovita** | FDA Orphan Drug Designation juin 2025, essais cliniques 2026, spin-off Institut Pasteur | LinkedIn CEO Stéphane Altaba, Institut Pasteur |

→ **Action**: Recherche manuelle agressive (LinkedIn, site corporate, presse)

---

### 🟡 RÉSULTATS RECHERCHE MANUELLE (2026-05-10)

#### DBV Technologies ✅ EMAIL TROUVÉ
| Champ | Valeur |
|-------|--------|
| Contact | Katie Matthews |
| Poste | Senior Director, Investor Relations & Strategy |
| Email | katie.matthews@dbvtechnologies.com |
| Source | Communiqué presse officiel Nasdaq, site corporate |
| Confiance | **Haute** - contact IR officiel, répond aux questions investisseurs |
| Pattern email | `{prenom.nom}@dbv-technologies.com` |

Autres contacts identifiés (non utilisés) :
- brett.whelan@dbv-technologies.com (Media)
- angela.marcucci@dbv-technologies.com (Media)
- jonathan.neely@dbv-technologies.com (IR)

#### HighLife ⚠️ SANS EMAIL CONFIANT
| Champ | Valeur |
|-------|--------|
| Contact | Stefan Pilz |
| Poste | CEO (depuis août 2024) |
| Domaine | highlifemedical.com |
| Email trouvés | info@highlifemed.com (générique mentions légales) |
| Source | Site mentions légales |
| Confiance | **Faible** - email générique, pas de contact direct |
| Pattern probable | stefan.pilz@highlifemedical.com |

**Note** : CEO avec profil commercial fort (ex-Abiomed, J&J). Privilégier LinkedIn DM plutôt qu'email.

#### Oncovita ⚠️ SANS EMAIL CONFIANT
| Champ | Valeur |
|-------|--------|
| Contact | Stéphane Altaba |
| Poste | CEO (depuis octobre 2024) |
| Domaine | oncovita.fr |
| Email trouvés | contact@oncovita.fr (générique) |
| Source | Site contact |
| Confiance | **Faible** - email générique, pas de contact direct |
| Pattern probable | stephane.altaba@oncovita.fr |

**Note** :CEO avec historique Sanofi/Nordic Pharma. Email IR possible mais non publié.

---

### 🟡 RÉSULTATS RECHERCHE 5 LEADSSUPPLEMENTAIRES (2026-05-10)

| # | Entreprise | Résultat | Contact | Email | Confiance |
|---|------------|----------|---------|-------|-----------|
| 1 | **POXEL** | ✅ Trouvé | Investor Relations | investors@poxelpharma.com | Haute |
| 2 | **Qubit Pharmaceuticals** | ⚠️ Possible | Robert Marino (CEO) | robermarino@qubit-pharma.com (probable) | Moyenne |
| 3 | **PDCline Pharma** | ❌ Générique | Eric Halioua (CEO) | contact@pdc-line-pharma.com | Faible |
| 4 | **Advanced BioDesign** | ❌ Générique | Contact form | contact@a-biodesign.com | Faible |
| 5 | **Lovaltech** | ✅ Trouvé | Alix Lassin (Com) | alix.lassin.cnum@lovaltechnology.com | Moyenne |

**Emails ajoutés à leads.csv** : POXEL, Lovaltech (confidence suffisante)
**Non ajoutés** : Qubit (trop incertain), PDCline, Advanced BioDesign (trop génériques)

---

### 🟢 ENRICHISSEMENT AUTOMATIQUE (8)

| # | Entreprise | Domaine | Statut | Source à utiliser |
|---|------------|---------|--------|-------------------|
| 1 | PDCline Pharma | pdc-line.com | Thérapies cellulaires cancer | Hunter.io + site |
| 2 | Qubit Pharmaceuticals | qubitpharma.com | Drug discovery AI | Hunter + site + Crunchbase |
| 3 | Advanced BioDesign | advancedbiodesign.fr | Anticorps thérapeutiques | Hunter + site |
| 4 | Caranx Medical | caranxmedical.com | Medtech cardiovasculaire | Hunter + site |
| 5 | BioMAdvanced Diagnostics | biomadvanced.com | Diagnostic | Hunter + site |
| 6 | SURGAR | surgar.fr | Biotech | Hunter + site |
| 7 | Spade | spade-medical.com | Medical | Hunter + site |
| 8 | Sonio | sonio.co | MedTech | Hunter + site |

→ **Action**: Lancer `--enrich` sur ces 10 en priorité

---

## Plan d'action concrètes

### IMMÉDIAT (cette semaine)

1. **Lancer enrichissement auto** sur les 10 leads du groupe vert
   ```bash
   python3 run.py --enrich
   ```

2. **Recherche manuelle DBV Technologies**
   - CEO: Daniel Tassé (LinkedIn)
   - Contact IR: investor@dbv-technologies.com
   - Contexte: BLA soumise, présentation AAAAI 2026, levée $116M en 2025

3. **Recherche manuelle HighLife**
   - CEO: Stefan Pilz (LinkedIn)
   - Contact: contact@highlifemedical.com
   - Contexte: CE mark janvier 2026, FDA IDE approved, premier commercialisation Europe

4. **Recherche manuelle Oncovita**
   - CEO: Stéphane Altaba (LinkedIn)
   - Contact: contact@oncovita.fr
   - Contexte: FDA Orphan Drug 2025, essai clinique 2026

### SI RIEN NE MARCHE (semaine 2)

- Re-scraper avec sources alternatives (Maddyness, France Biotech)
- Contact direct via LinkedIn (pas d'email, juste DM)

---

## Notes

- Les 6 leads "hors scope" doivent être exclus du pipeline de prospection active
- DBV, HighLife, Oncovita sont les 3 meilleures opportunités restantes - investir du temps manuel
- Les 10 autres sont des leads corrects mais moins stratégiques

---

## Suivi

| Date | Action | Résultat |
|------|--------|-----------|
| 2026-05-09 | Analyse classification | 6 hors scope, 3 manuels, 10 auto |
| 2026-05-10 | Recherche DBV/HighLife/Oncovita | DBV: katie.matthews@dbvtechnologies.com (IR) ✓ |
| 2026-05-10 | Recherche 5 leads supplémentaires | POXEL + Lovaltech ajoutés (2/5) |
| 2026-05-10 | Recherche 10 leads restants | Qubit + Caranx(Affluent) ajoutés (2/10) |
| 2026-05-10 | Recherche top 5 priority | PDCline: e.halioua@pdc-line-pharma.com (CEO) ✓ |

### 🟡 RÉSULTATS RECHERCHE 10 LEADSSUPPLEMENTAIRES (2026-05-10)

| # | Entreprise | Résultat | Contact | Email | Confiance |
|---|------------|----------|---------|-------|-----------|
| 1 | Qubit Pharmaceuticals | ✅ Probable | Robert Marino (CEO) | robert.marino@qubit-pharmaceuticals.com | Moyenne |
| 2 | Caranx Medical (Acquis) | ✅ Via母公司 | Jerome Geoffroy (IR Affluent) | jerome.geoffroy@affluentmedical.com | Moyenne |
| 3 | PDCline Pharma | ❌ Générique | Eric Halioua (CEO) | contact@pdc-line-pharma.com | Faible |
| 4 | Spade | ❌ Blocqué | - | spade@spade-equipements.com | Faible |
| 5 | Sonio | ❌ Blocqué | Formulaire only | - | Faible |
| 6 | BioMAdvanced Diagnostics | ❌ Pas d'info | - | - | Faible |
| 7 | SURGAR | ❌ Pas d'info | - | - | Faible |
| 8 | HighLife | ❌ Déjà fait | Stefan Pilz (CEO) | info@highlifemed.com | Faible |
| 9 | Advanced BioDesign | ❌ Déjà fait | - | contact@a-biodesign.com | Faible |
| 10 | Oncovita | ❌ Déjà fait | Stéphane Altaba (CEO) | contact@oncovita.fr | Faible |