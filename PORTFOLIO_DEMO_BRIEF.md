# Portfolio demo - Animation 3D medicale

Objectif : produire un exemple montrable rapidement si un prospect demande un portfolio.

---

## 1. Spécifications techniques

| Parametre | Valeur |
|-----------|--------|
| Duree | 20-30 secondes |
| Resolution | 1920x1080 (Full HD) |
| Frame rate | 30 fps |
| Codec | H.264 |
| Bitrate | 8-12 Mbps |
| Container | MP4 |
| Audio | Aucun (mute par defaut) |

---

## 2. Sujet recommandé

**Mecanisme generique** : molecule therapeutique qui se fixe a un recepteur cellulaire et bloque une cascade inflammatoire.

**Pourquoi ce sujet** :
- Applicable a beaucoup de biotechs (immunologie, oncologie, metabolisme)
- Facile a comprendre visuellement
- Combine molecule + cellule + signalisation
- Ne depend pas d'un prospect specifique
- Valorise le potentiel "storytelling" de la 3D

---

## 3. Palette couleurs

| Element | Couleur | Hex |
|---------|---------|-----|
| Fond | Noir profond | #0A0A0F |
| Cellule (membrane) | Bleu transparent | #2A4B7C (alpha 0.3) |
| Recepteur | Bleu electrique | #4A90D9 |
| Molecule therapeutique | Vert/blanc nacre | #E8F4EC |
| Signal inflammatoire | Orange/rouge | #FF6B4A |
| Signal bloque | Bleu pale | #7BAFD4 |
| Labels | Blanc | #FFFFFF |

---

## 4. Storyboard detaille

### Scene 1 - Contexte biologique (0-5s)

**Description** : Vue large d'une cellule avec signaux inflammatoires qui approchent.

**Composition** :
- Cellule centree, occupe 60% du cadre
- Membrane visible, semi-transparente
- 3-5 recepteurs visibles sur le contour
- Particules oranges (signaux) en mouvement vers la cellule

**Camera** :
- Static ou lent dolly backward
- Profondeur de champ moyenne (tout net)

**Texte ecran** : "Signal inflammatoire actif"

**Rendu attendu** : Debut de tension visuelle, couleurtiere rouge/orange.

---

### Scene 2 - Cible therapeutique (5-10s)

**Description** : Zoom sur un recepteur. Molecule therapeutique arrive et se fixe.

**Composition** :
- Zoom progressif sur un recepteur
- Molecule en approche depuis la gauche
- Fixation visible (interaction molecule-recepteur)

**Camera** :
- Smooth zoom in (2-3 secondes)
- Rotation legere autour du complexe (15-20 degres)

**Texte ecran** : "Fixation selective"

**Rendu attendu** : Moment de connexion, changement de couleur sur le recepteur (bleu -> vert).

---

### Scene 3 - Blocage du signal (10-18s)

**Description** : Les signaux inflammatoires sont bloques. La cascade interne diminue.

**Composition** :
- Particules oranges qui ralentissent et s'arretent
- Signal intracellulaire passe de rouge a bleu
- Effet de "mur" visible entre signaux et cellule

**Camera** :
- Reveal progressif (les particules se figent une par une)
- Reveil de la cascade intracellulaire en bleu

**Texte ecran** : "Signal bloque"

**Rendu attendu** : Sensation de controle, changement de palette (chaud -> froid).

---

### Scene 4 - Resultat (18-25s)

**Description** : Vue large de la cellule stabilisee.

**Composition** :
- Retour sur cellule entiere
- Environment calme, colores en bleu
- Plus de signaux inflammatoires
- Membrane en Bleu electrique stable

**Camera** :
- Pull back progressif
- Fin sur pose stable

**Texte ecran** : "Mecanisme rendu clair"

**Rendu attendu** : Resolution, stabilite, professionnalisme.

---

## 5. Prompt de production pour Blender / Claude

```
Create a 20-30 second premium medical 3D animation.

SUBJECT: Generic therapeutic molecule binds to cell membrane receptor and blocks inflammatory signaling cascade.

TECHNICAL SPECS:
- Resolution: 1920x1080
- Frame rate: 30fps
- Duration: 25 seconds
- No audio

COLOR PALETTE:
- Background: #0A0A0F (deep black)
- Cell membrane: #2A4B7C (translucent blue, alpha 0.3)
- Receptor: #4A90D9 (electric blue)
- Therapeutic molecule: #E8F4EC (pearl white/green)
- Inflammatory signal: #FF6B4A (orange-red)
- Blocked signal: #7BAFD4 (pale blue)
- Labels: #FFFFFF (white)

SCENE BREAKDOWN:

Scene 1 (0-5s) - PROBLEM:
- Wide shot of cell, 60% of frame
- Semi-transparent membrane visible
- 3-5 receptors on membrane perimeter
- 3-5 orange particles moving toward cell
- Text overlay: "Signal inflammatoire actif"
- Camera: static or slow dolly back
- Lighting: 3-point, soft key from top-left

Scene 2 (5-10s) - TARGET:
- Smooth zoom to one receptor on membrane
- Therapeutic molecule enters from left
- Molecule binds to receptor
- Color shift on receptor (blue to green)
- Text overlay: "Fixation selective"
- Camera: 2-3s zoom in + 15-20 degree orbit

Scene 3 (10-18s) - SOLUTION:
- Orange particles slow down and stop
- Intracellular signals fade from red to blue
- Visible "wall" effect between signals and cell
- Text overlay: "Signal bloque"
- Camera: progressive reveal, particles freeze one by one

Scene 4 (18-25s) - RESULT:
- Pull back to wide cell view
- Calm blue environment, no orange signals
- Membrane now electric blue stable
- Text overlay: "Mecanisme rendu clair"
- Camera: slow pull back, stable final pose

LIGHTING:
- Key light: top-left, soft warm (intensity 0.8)
- Fill light: right side, cool blue (intensity 0.3)
- Rim light: behind subject, white (intensity 0.4)
- No harsh shadows

MATERIALS:
- Cell: subsurface scattering, translucent
- Receptor: glossy, slight emission
- Molecule: glass-like, slight refraction
- Particles: emissive glow on orange

OUTPUT:
- Format: MP4, H.264, 8-12 Mbps
- No audio track
- Smooth 30fps, no stuttering
- Clean render, no artifacts
```

---

## 6. Checklist production

Avant de considerer la demo comme terminee :

- [ ] Duree entre 20 et 30 secondes
- [ ] Resolution 1920x1080
- [ ] 30 fps constant
- [ ] 4 scenes distinctes avec texte overlay
- [ ] Palette couleurs respectee
- [ ] Camera movements fluides (pas de jump cuts)
- [ ] Fond sombre (#0A0A0F)
- [ ] Molecule visible et distincte du recepteur
- [ ] Transition rouge -> bleu visible dans scene 3
- [ ] Export en MP4 H.264
- [ ] Fichier inferieur a 100 Mo
- [ ] Pas de artefacts de rendu visibles

---

## 7. Fallback si generation echoue

Si la generation automatique echoue :

1. **Option A** : Utiliser un modele pre-existant type "medical explainer" et adapter le storyboard
2. **Option B** : Generer une sequence plus courte (15s) avec moins de details
3. **Option C** : Utiliser un style different (flat 2D vectoriel au lieu de 3D)

**En cas d'impossibilite totale** : Signaler que la demo est en cours de production et proposer un call pour montrer des references visuelles via partage d'ecran.

---

## 8. Phrase a envoyer si prospect demande un exemple

**NE JAMAIS** envoyer le fichier directement sans cadrage.

```
Objet: Re: [sujet original]

[Prenom],

Oui, je peux vous montrer un exemple de style.

Le plus pertinent reste de prendre 15 min pour comprendre votre mecanisme exact, puis je peux vous proposer un mini storyboard adapte a votre technologie. Ca vous permettrait de voir exactement ce que ca donnerait pour votre cas.

Vous avez 15 min cette semaine ?

-- Edgar
```

---

## 9. Definition de "suffisant"

Cette demo n'a pas besoin d'etre parfaite. Elle doit seulement prouver :

- [ ] Le rendu est propre et professionnel
- [ ] Tu peux expliquer un mecanisme complexe visuellement
- [ ] Le prospect peut se projeter sur sa propre technologie
- [ ] Le style est adapt au secteur medical/biotech
- [ ] La palette couleurs est coherente et premium

**Si tous les points sont verifies** : la demo est suffisante.

**Si 1-2 points manquent** : Corriger le point manquant avant de montrer.

**Si plus de 2 points manquants** : Ne pas montrer, regenerer ou utiliser le fallback.