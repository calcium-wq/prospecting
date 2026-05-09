# Sales Playbook - Prospection biotech 3D

Objectif : transformer une reponse positive en call, puis en devis simple a 3000-5000 euros.

## Contrainte de disponibilite

Edgar est etudiant.

Disponibilites par defaut a proposer pour un call :
- lundi matin ;
- lundi apres 17h30 ;
- mardi a vendredi apres 18h30 ;
- week-end.

Fuseau horaire : Europe/Paris.

Regle absolue :
- ne pas proposer par defaut un call en pleine journee de semaine.
- si possible, proposer "fin de journee en semaine ou week-end" plutot que "jeudi/vendredi fin de matinee".

---

## 1. Quand un prospect repond positivement

**Repondre dans les 2h.** Delai plus long = perte de momentum.

### Template reponse positive

```
Objet: Re: [sujet original]

Bonjour [Prenom],

Merci pour votre retour, ravi que ca resonne.

Je vous propose un appel de 15 min cette semaine pour comprendre votre technologie, voir ou une animation 3D peut aider, et vous dire franchement si je peux vous etre utile.

Vous auriez un creneau en fin de journee cette semaine, ou sinon ce week-end ?

-- Edgar
```

### Mise a jour Notion

| Champ | Valeur |
|-------|--------|
| Statut | `Call propose` |
| Notes | Copier la reponse exacte du prospect |
| Reponse | `Oui` |

---

## 2. Reponses aux objections courantes

### 2.1 "Montrez-moi un exemple"

**Jamais envoyer de fichier sans cadrage.** Repondre d'abord :

```
Objet: Re: [sujet original]

[Prenom],

Oui, je peux vous montrer un exemple de style. Voici le lien : [LIEU VERS DEMO]

Le plus pertinent reste de prendre 15 min pour comprendre votre mecanisme exact, puis je peux vous proposer un mini storyboard adapte a votre technologie. Ca vous permettrait de voir exactement ce que ca donnerait pour votre cas.

Vous auriez un creneau en fin de journee cette semaine, ou sinon ce week-end ?

-- Edgar
```

**Action immediate** : Verifier que la demo est accessible (lien WeTransfer ou page web).

### 2.2 "Quel budget ?"

**Jamais donner un prix sans contexte.** Cadrer d'abord :

```
Objet: Re: [sujet original]

[Prenom],

Le budget depende de la complexite du mecanisme et du niveau de refinment attendu. generalement entre 3000 et 5000 euros.

Pour vous donner une idee plus precise, j aurais besoin de comprendre :
- Le mecanisme a expliquer (complexite visuelle)
- L audience cible (investisseurs, partenaires, conference)
- La deadline

Ces 3 elements me permettent de you propose un scope adapte.

Un rapide echange en fin de journee cette semaine, ou ce week-end, serait-il possible ?

-- Edgar
```

**NE JAMAIS** :
- Donner un prix fixe sans comprendre le besoin
- Proposer "moins cher" si le prospect hesite
- Discuter prix avant d'avoir qualifie le besoin

### 2.3 "Pas le bon moment"

**Re-qualifier au lieu de accepter le refus. Demander une deadline :**

```
Objet: Re: [sujet original]

[Prenom],

Je comprends. Question deadline : vous auriez besoin de cette animation pour quand ? Debut de projet, conference, levée de fonds ?

Si vous me donnez une date cible, je peux vous dire si on peut s organiser.

-- Edgar
```

**Si le prospect donne une date** : Noter dans notes "Relancer le [DATE - 2 semaines]"

**Si le prospect reste vague** : Conclure

```
[Prenom],

Pas de souci. Je reviens vers vous dans quelques semaines. Bonne continuation pour [sujet en cours / levée / conference].

-- Edgar
```

---

## 3. Script de call 15 min

### Regles

- **5 questions max** — ne pas depasser 15 min
- **Ecouter 80%, parler 20%**
- **Prendre des notes** — serviront pour le suivi
- **Terminer par une proposition** — ne pas laisser le prospect sans suite

### Les 5 questions

**Q1 - Objectif**
> "Quel est l'objectif principal de cette animation ?"

*But : Savoir si levée de fonds, партнер pharma, conference, usage interne.*
*Reponse type : "Lever des fonds", "Partner avec pharma", "Congress ASCO", "Formation equipe"*

**Q2 - Audience**
> "A qui devez-vous expliquer cette technologie ?"

*But : Calibrer le niveau de detail, le style visuel.*
*Reponse type : "VCSeries A", "Pfizer/Merck", "Patients", "Equipe R&D interne"*

**Q3 - Deadline**
> "Vous avez besoin de cette animation pour quand ?"

*But : Determiner le prix (delai court = premium).*
*Reponse type : "3 semaines", "Fin du mois", "Conference en octobre"*

**Q4 - Existant**
> "Vous avez deja des visuels, un deck, un schema ?" (si non precise)

*But : Ne pas recreer ce qui existe, evaluermigration depuis PowerPoint.*
*Reponse type : "On a un schema PowerPoint", "Des slides deck", "Rien du tout"*

**Q5 - Element indispensable**
> "Si je vous fais cette animation, qu'est-ce qui doit ABSOLUMENT apparaitre ?"

*But : Identifier le "hero shot", le moment cle du mecanisme.*
*Reponse type : "Le recepteur", "La molecule qui se fixe", "La cascade de signalisation"*

### Sortie attendue du call

A la fin du call, tu dois avoir :

| Element | Note |
|---------|------|
| Objectif | ______________ |
| Audience | ______________ |
| Deadline | ______________ |
| Existant | ______________ |
| Element indispensable | ______________ |
| Prix propose | 3000 / 5000 euros |

**Si tous les champs sont remplis** → Proposer le devis.

**Si champs manquants** → "Pour finaliser ma proposition, j'ai besoin de [element manquant]. On reprend 5 min ?"

---

## 4. Logique de pricing 3000 vs 5000 euros

### 3000 euros (offre de base)

Quand AU MOINS 3 de ces conditions sont remplies :

- [ ] Mecanisme simple (A -> B, pas de cascade complexe)
- [ ] Deadline flexible (7+ jours)
- [ ] Pas de revisions demandees (1 round prevu)
- [ ] Pas de client existing (premier contact)
- [ ] Audience technique (chercheurs, pas pitch investors)

### 5000 euros (offre premium)

Quand AU MOINS 3 de ces conditions sont remplies :

- [ ] Mecanisme complexe (multiples etapes, boucles, signaux croises)
- [ ] Deadline courte (5 jours ou moins)
- [ ] Revisions prevues (2+ rounds)
- [ ] Audience non-technique (investisseurs, patients, board)
- [ ] Usage en conference ou lever de fonds (high stakes)
- [ ] Deja un client existant (relation etablie)

### Phrase de cadrage a utiliser

```
Pour ce type de besoin, je travaille generalement entre 3000 et 5000 euros selon :
- La complexite du mecanisme a visualiser
- Le niveau de revision attendu
- La deadline

L'objectif est de vous livrer un support clair, exploitable rapidement, sans partir sur une production lourde de plusieurs semaines.
```

---

## 5. Envoi du devis apres call

**Delai max : 2h apres le call.**

## Doctrine business

- Automatiser toute la prospection jusqu'a la premiere reponse du prospect.
- Ne jamais envoyer de reponse commerciale chaude a la place d'Edgar.
- Le systeme peut envoyer emails initiaux, relances, monitoring et notifications.
- Des qu'un prospect repond, Edgar reprend la main.

```
Objet: Proposition animation 3D - [Nom de la boite]

Bonjour [Prenom],

Merci pour l'echange.

Voici ce que j'ai compris :
- Objectif : [objecti]
- Audience : [audience]
- Deadline : [delai]
- Element cle : [element]

Proposition :
- Animation 3D de [20-45] secondes
- Storyboard valide avant production
- 1 round de revisions
- Rendu final MP4
- Delai : [X] jours ouvrables

Budget : [3000/5000] euros

Si ca vous va, je vous envoie le brief de demarrage pour validation.

-- Edgar
```

---

## 6. Si le prospect demande un exemple

### Phrase de cadrage AVANT d'envoyer quoi que ce soit

```
[Prenom],

Oui, je peux vous montrer un exemple de style.

Le plus pertinent reste de prendre 15 min pour comprendre votre mecanisme exact, puis je peux vous proposer un mini storyboard adapte a votre technologie. Ca vous permettrait de voir exactement ce que ca donnerait pour votre cas.

Vous avez 15 min cette semaine ?
```

**Action urgente** : La demo doit etre prete. Voir PORTFOLIO_DEMO_BRIEF.md.

### Definition de "suffisant" pour la demo

La demo n'a pas besoin d'etre parfaite. Elle doit seulement prouver :

- [ ] Le rendu est propre et professionnel
- [ ] Tu peux expliquer un mecanisme complexe visuellement
- [ ] Le prospect peut se projeter sur sa propre technologie
- [ ] Le style est adapt au secteur medical/biotech

---

## 7. Regles absolues

1. **Repondre dans les 2h** — pas d'excuse
2. **Ne jamais promettre une expertise scientifique** que tu n'as pas
3. **Toujours demander les documents existants** avant de produire
4. **Vendre la clarte et l'impact business**, pas juste la 3D
5. **Si le prospect est flou**, proposer un mini storyboard avant devis final
6. **Si le prospect demande trop pour trop peu**, reduire le scope au lieu de baixar le prix
7. **Jamais discuter prix sans avoir qualifie le besoin** (Q1-Q5)
8. **Ne jamais envoyer de demo sans cadrage** (cf 2.1)
9. **Pas de prix sans contexte** (cf 2.2)
10. **Toujours proposer une prochaine etape concrete** a la fin de chaque echange

---

## 8. Checklist avant de proposer un devis

- [ ] J'ai recapitule l'objectif (Q1)
- [ ] J'ai compris l'audience (Q2)
- [ ] Je connais la deadline (Q3)
- [ ] Je sais s'il y a deja des visuels (Q4)
- [ ] Je sais ce qui doit apparaitre absolument (Q5)
- [ ] J'ai decide 3000 ou 5000 euros en fonction des criteres
- [ ] J'ai propose une prochaine etape concrete
- [ ] J'ai envoye dans les 2h suivant le call
