# XAUUSD Wick Zones — Audit Pro global post-validation Z4

**Date d'audit :** 2026-08-24  
**Dépôt :** `iagency971/twilio-voice-gateway`  
**Branche :** `agent/xau-wick-zone-pro-dev`  
**Périmètre :** conclusions scientifiques Z4, bridge Python → Pine, versions Pine v2.0.1 à v2.0.8, Replay, disparition des zones, MEMORY, transfert FOREXCOM, UI et expérimentations hors périmètre.  
**Règle :** aucune optimisation, aucun nouveau seuil sélectionné à partir des résultats ou des captures.

---

## 1. Verdict exécutif

### 1.1 Statut scientifique Z4

**GO — inchangé, mais uniquement pour le claim étroit suivant :**

> Sur XAUUSD M1 Dukascopy, les variables de géométrie Z4 et de lignée/stabilité du modèle M0GL ajoutent une information prédictive reproductible, par rapport au modèle causal M0 figé, pour la revisite d'une zone dans les 240 prochaines M1 actives.

Le claim a passé :

- DEV janvier–juillet 2024 ;
- Validation indépendante août 2024–juillet 2025 ;
- OOS figé août 2025–juillet 2026 ;
- BID primaire ;
- ASK secondaire cohérent.

Le claim **ne couvre pas** :

- réaction/rejet/reversal ;
- support ou résistance ;
- rentabilité ;
- entrée, stop, objectif ;
- FOREXCOM ;
- M5/M15/H1 ;
- BODY ou BODY-vs-WICK.

### 1.2 Statut du Pine actuellement utilisé

**NO-GO pour le label `VALIDATED_PROXY`.**

La version actuelle auditée est :

- `XAUUSD_Z4_Revisit_Score_QA_v2_0_8_M1_CYAN_LAST3.pine`
- SHA-256 : `7f67fdeb03b1b612462a9df05fee4c4feffee0302594b2ee9825b4448e74f333`

Elle contient une modification de classe **C** dans le détecteur / modèle :

```pine
int side = center >= close ? -1 : 1
```

Cette ligne est doublement incompatible avec Z4 :

1. elle **inverse la convention de side** pour toutes les zones non chevauchantes :
   - zone au-dessus du cours → `-1`, alors que Z4 exige `+1` ;
   - zone en dessous du cours → `+1`, alors que Z4 exige `-1` ;
2. elle conserve les zones dont l'intervalle P50 chevauche le cours, alors que Z4 les exclut du jeu de zones éligibles.

Les `R` affichés par v2.0.2 à v2.0.8 ne sont donc pas interprétables comme le Revisit Score Z4 validé.

### 1.3 Dernière version Pine scientifiquement fidèle

La dernière version existante dont le cœur scientifique correspond au proxy Z4 audité est :

- `XAUUSD_Z4_Revisit_Score_QA_v2_0_1_M1_VALIDATED_PROXY.pine`
- SHA-256 : `55737ed18eec86642663214860db8be33c9087382d3a52caf2dded7819b3f4fb`

**Statut : GO conditionnel** pour des snapshots M1 confirmés en historique / Replay, dans l'enveloppe de parité déjà acceptée, avec la réserve de transfert de feed.

Elle n'est toutefois pas encore une version live finale sans réserve, car deux défauts engineering de classe B subsistent :

- calcul possible sur une M1 temps réel non confirmée ;
- récupération après `GRID_LIMIT` pouvant réafficher trop tôt `VALIDATED_PROXY` avec une lignée remise à zéro.

---

## 2. Revalidation des conclusions scientifiques

## 2.1 DEV et architecture figée

L'addendum Z4 v0.5 a figé avant Validation :

- M1 actif : `high > low` ;
- mémoire de 1 440 M1 actives ;
- grille absolue 0,01 USD ;
- lower wick / body / upper wick séparés ;
- `v60` = médiane du True Range sur 60 M1 actives ;
- `vseg` = médiane du True Range sur 1 440 M1 actives ;
- Gaussian exact Python aux échelles 0,25 / 0,50 / 1,00 × `vseg` ;
- familles coarse ;
- meilleur pic medium par famille ;
- confirmation fine ;
- prominence medium ;
- limites P50 ;
- lignée one-to-one ;
- 34 features M0GL ;
- endpoint `REVISIT_240` ;
- aucun Top N.

Le modèle, le scaler, les coefficients, l'intercept, les transforms et le poids total égal par landmark ont été gelés avant ouverture de la Validation.

## 2.2 Validation indépendante

Validation primaire BID, août 2024–juillet 2025 :

- 134 272 lignes de zones ;
- 23 518 landmarks ;
- Brier M0 : 0,1394336344 ;
- Brier M0GL : 0,1372729365 ;
- ΔBrier : **+0,0021606979** ;
- ΔLogLoss : **+0,0064640617** ;
- 41 semaines positives sur 53 ;
- bootstrap hebdomadaire 95 % : **[+0,0013474159 ; +0,0030235919]** ;
- H1 : **+0,0019276763** ;
- H2 : **+0,0023973542** ;
- six gates prospectifs : PASS.

ASK secondaire :

- ΔBrier : **+0,0019110452** ;
- ΔLogLoss : **+0,0058680612**.

## 2.3 OOS figé

OOS primaire BID, août 2025–juillet 2026 :

- 132 858 lignes ;
- 23 506 landmarks ;
- Brier M0 : 0,1686448215 ;
- Brier M0GL : 0,1561993591 ;
- ΔBrier : **+0,0124454624** ;
- ΔLogLoss : **+0,0427746202** ;
- bootstrap hebdomadaire 95 % : **[+0,0100846293 ; +0,0146934804]** ;
- H1 : **+0,0091764172** ;
- H2 : **+0,0157083941** ;
- six gates : PASS.

ASK secondaire :

- ΔBrier : **+0,0120343044**.

Le run OOS original a subi un conflit de publication GitHub après les calculs. Une reconstruction déterministe a reproduit les métriques primaires bit-for-bit. Le conflit de publication ne réduit donc pas le claim scientifique.

## 2.4 Calibration

Un défaut a été documenté dans l'agrégation ECE de la Validation v0.1. Il ne touchait ni :

- les prédictions brutes ;
- Brier ;
- LogLoss ;
- bootstrap ;
- résultats par moitié ;
- décision PASS ;
- coefficients Platt.

L'OOS a calculé l'ECE avec les poids globaux corrects ; `ECE10 = 0,0757288`. La calibration absolue reste insuffisante pour afficher une probabilité honnête.

## 2.5 Réaction

**NO-GO confirmé.**

Les endpoints directionnels, MFE/violation, sweep, reclaim et retest ont produit des résultats mixtes selon les folds, BUY/SELL et sessions. Certains sous-tests sont positifs, d'autres négatifs ; ils ne satisfont pas le standard de stabilité requis.

Conséquences :

- aucun `P_REACTION` ;
- aucun score combiné revisit × réaction ;
- aucun claim de support/résistance ;
- `R` ne doit jamais guider seul une entrée, un SL ou un TP.

---

## 3. Audit du bridge Python scientifique → Pine v2.0.1

## 3.1 Résultat général

La v2.0.1 reproduit correctement l'architecture du **proxy Pine approuvé**, et non l'exact Python 0,01/SciPy/Hungarian.

Les approximations engineering autorisées ont été sélectionnées outcome-blind :

- grille 0,05 USD ;
- Gaussian 3-box ;
- peak/prominence/P50 explicites ;
- lineage greedy ;
- warm-up 96 landmarks.

Les gates de parité ont passé avant création de l'indicateur.

## 3.2 Matrice de conformité

| Composant | Référence Z4 | v2.0.1 | Statut |
|---|---|---|---|
| Timeframe | M1 actif seulement | garde `timeframe.in_seconds() == 60` | Conforme |
| Activité | `high > low` | `activeBar = high > low` | Conforme |
| Mémoire | 1 440 actives | ring buffer 1 440 actives | Conforme |
| TR | précédent close actif | précédent close actif | Conforme |
| `v60` | médiane TR 60 | médiane des 60 derniers TR du ring | Conforme |
| `vseg` | médiane TR 1 440 | médiane des 1 440 TR | Conforme |
| Champ | lower/body/upper séparés, wick = lower+upper | identique | Conforme |
| Origine grille | multiples absolus de 0,00 | bins absolus à pas 0,05 | Conforme au proxy |
| Pas grille | exact 0,01 | proxy 0,05 | B approuvé |
| Smoothing | SciPy Gaussian | trois box passes | B approuvé |
| Peaks/minima | SciPy | formules explicites Pine | B approuvé |
| Familles | coarse | coarse | Conforme |
| Pic central | meilleur medium | meilleur medium | Conforme |
| Confirmation | fine proche | fine proche | Conforme |
| Prominence | medium | medium | Conforme au proxy |
| Bornes | P50 | P50 interpolé | Conforme au proxy |
| `side` | bornes entièrement sous/au-dessus du close | formule exacte Z4 | Conforme |
| Exclusion zone au prix | oui | oui | Conforme |
| Lineage | Hungarian one-to-one | greedy one-to-one | B approuvé |
| Gap | snapshot éligible sans zone termine la lignée | arrays précédents vidés | Conforme |
| Âge/stabilité | features figées | mêmes transforms et ordre | Conforme |
| Modèle | 34 features BID M0GL | 34 moyennes, scales et coefficients | Conforme |
| Intercept | -2,1980240456517803 | identique | Conforme |
| R map | 101 seuils DEV + interpolation | 101 seuils + interpolation | Conforme |
| Cadence | landmark 15 min UTC | `time % 900000 == 0` | Conforme |
| Top N | interdit | absent | Conforme |
| Lookahead historique | interdit | aucune référence future / security lookahead | Conforme |
| Feed | Dukascopy BID | feed du graphique | transfert non validé |

## 3.3 Parité engineering déjà établie

### 3-box seul

- exact-zone match : 92,41 % ;
- proxy-zone match : 99,25 % ;
- IoU médiane : 0,9876 ;
- score Spearman : 0,99895 ;
- top-1 : 89,27 %.

### Pas de grille

Candidats pré-enregistrés :

- 0,02 : PASS ;
- 0,05 : PASS ;
- 0,10 : FAIL.

Règle figée : plus grand pas qui passe toutes les gates.  
Résultat : **0,05 USD**.

### Peak/prominence/P50 explicites

- exact-zone match : 99,50 % par rapport à la référence 3-box/0,05 ;
- proxy-zone match : 99,88 % ;
- IoU médiane : 1,00 ;
- score Spearman : 0,99999 ;
- top-1 : 99,83 %.

### Greedy lineage

- accord de lien précédent : 99,9776 % ;
- score Spearman : 0,999959 ;
- top-1 : 99,9562 %.

### Combinaison complète

- exact-zone match : 92,2441 % ;
- proxy-zone match : 98,8002 % ;
- IoU médiane : 0,973891 ;
- score Spearman : 0,998415 ;
- top-1 : 86,9937 %.

### Label R

- erreur médiane `R_float` : 0,2825 ;
- erreur p95 : 2,9742 ;
- affichage à ±2 points : 93,45 % ;
- affichage à ±5 points : 98,10 % ;
- Spearman : 0,998415.

## 3.4 Deux défauts engineering dans v2.0.1

### B1 — M1 temps réel non confirmée

La mise à jour du ring et le snapshot 15 minutes ne sont pas conditionnés par `barstate.isconfirmed`.

Sur historique et en Replay, les barres exécutées sont confirmées. En temps réel, un indicateur Pine s'exécute à chaque tick de la M1 ouverte ; `high`, `low` et `close` sont provisoires jusqu'au tick de clôture. Le rollback empêche normalement une accumulation permanente multiple, mais la minute landmark peut afficher plusieurs snapshots provisoires avant la clôture.

Impact :

- pas de corruption durable attendue après clôture ;
- possibilité de zones et de `R` qui bougent pendant la M1 landmark ;
- le texte `VALIDATED_PROXY` peut apparaître avant que la donnée de la M1 soit confirmée.

Classe : **B**.

Correction minimale :

```pine
bool confirmedActive = isM1 and activeBar and barstate.isconfirmed
```

et utiliser `confirmedActive` pour la mise à jour du ring et le landmark.

### B2 — récupération après `GRID_LIMIT`

Le compteur `eligibleWarmup` est incrémenté avant la validation de `nLevels`. En cas de `GRID_LIMIT`, l'état de lignée est effacé, mais le compteur n'est pas remis à zéro.

Si le grid redevient calculable :

- les lignées repartent à froid ;
- le script peut néanmoins réafficher immédiatement `VALIDATED_PROXY`.

Ce cas n'explique pas les captures actuelles : les grids observés sont très inférieurs à 12 000. Il reste néanmoins incompatible avec un comportement fail-closed strict.

Classe : **B**.

Correction minimale :

- compteur de warm-up d'état séparé ;
- remise à zéro après `GRID_LIMIT` ;
- 96 landmarks valides requis avant de réafficher `VALIDATED_PROXY`.

---

## 4. Diff sémantique v2.0.1 → v2.0.8

## 4.1 Défaut critique de `side`

### Z4 / v2.0.1

```pine
int side =
     zhi < close - STEP * 0.5 ? -1 :
     zlo > close + STEP * 0.5 ? 1 :
     0

if side != 0
    // zone éligible
```

Convention figée :

- `-1` : zone sous le cours, candidate BUY/support-side ;
- `+1` : zone au-dessus, candidate SELL/resistance-side ;
- zone qui chevauche le prix : exclue.

### v2.0.2 à v2.0.8

```pine
int side = center >= close ? -1 : 1
```

Cette variante :

- assigne `-1` aux zones au-dessus : **signe inversé** ;
- assigne `+1` aux zones en dessous : **signe inversé** ;
- n'exclut plus les zones chevauchant le prix.

### Effets en cascade

Le changement touche :

1. la population de zones ;
2. la feature `side` ;
3. la feature `same_share_center` ;
4. la feature `same_minus_body_center` ;
5. le choix lower-wick vs upper-wick comme interaction « same side » ;
6. les correspondances de lignée, car des zones supplémentaires participent au matching ;
7. l'âge, les changements, les streaks et les statistiques de stabilité ;
8. le raw score ;
9. le label R.

Il ne s'agit pas d'une petite divergence d'affichage. C'est une modification du modèle/détecteur non validée.

Classe : **C — bloquant**.

## 4.2 Classification par version

| Version | Modification nouvelle | Classe | Verdict |
|---|---|---:|---|
| v2.0.1 | proxy initial | — | dernière architecture fidèle ; B live à réparer |
| v2.0.2 | side inversé + zones chevauchantes incluses | C | NO-GO |
| v2.0.2 | boîtes ancrées à droite de la barre actuelle, R déplacé, bord gauche supprimé | A | visuel |
| v2.0.3 | halo du pic | A | visuel |
| v2.0.4 | cyan / contraste du pic | A | visuel |
| v2.0.5 | bande de pic et label PEAK | A | visuel |
| v2.0.6 | épaisseurs / transparences | A | visuel |
| v2.0.7 | ligne cyan normale, halo conservé | A | visuel |
| v2.0.8 | ligne cyan prolongée sur les trois dernières bougies | A | visuel |

Les versions v2.0.3–v2.0.8 héritent toutes du changement C introduit en v2.0.2.

## 4.3 UI : ce qui peut être conservé

Les changements suivants peuvent être réappliqués à une base v2.0.1 restaurée, sans changer la science :

- projection des boîtes à droite ;
- R placé dans la boîte ;
- couleur cyan du pic ;
- halo ;
- ligne du pic dépassant sur les trois dernières bougies ;
- suppression de la bordure verticale gauche ;
- transparence heatmap ;
- épaisseur des bornes.

Condition : aucun changement hors du bloc de dessin et aucune réécriture de `side`, des zones, de la lignée ou du score.

L'ancrage des boîtes à la barre courante est visuel, mais il peut donner l'impression que le score est recalculé chaque minute. Le tableau `Snapshot` doit rester visible ou le label doit indiquer l'heure du dernier snapshot confirmé.

---

## 5. GO / NO-GO du label `VALIDATED_PROXY`

| Objet | Statut |
|---|---|
| Z4 Python exact sur Dukascopy M1 | **GO** |
| Proxy engineering validé dans les gates DEV outcome-blind | **GO** |
| v2.0.1, historique / Replay, snapshot confirmé | **GO conditionnel** |
| v2.0.1, temps réel avant clôture de la M1 landmark | **NO-GO provisoire** |
| v2.0.2–v2.0.8 | **NO-GO** |
| v2.0.8 sur FOREXCOM | **NO-GO comme “validé sur ce feed”** |
| M5/M15/H1 avec R | **NO-GO** |
| BODY / BODY-vs-WICK avec claim prédictif | **NO-GO** |

### Décision

La version actuellement utilisée ne doit plus afficher `VALIDATED_PROXY`.

Dernière version fidèle existante :

`XAUUSD_Z4_Revisit_Score_QA_v2_0_1_M1_VALIDATED_PROXY.pine`

Mais la version de production recommandée doit être reconstruite à partir de v2.0.1, avec :

- side Z4 restauré ;
- uniquement les améliorations UI de classe A ;
- barres confirmées ;
- warm-up réarmé après grid failure ;
- nouveau manifest ;
- trace QA.

---

## 6. Pourquoi les zones disparaissent en Replay

## 6.1 Comportement prévu par le protocole

Le port spec dit explicitement :

- score recalculé uniquement à chaque landmark 15 min ;
- dernière photographie maintenue entre landmarks ;
- si une zone n'existe plus au snapshot suivant, elle disparaît et sa lignée se termine ;
- aucune hystérésis visuelle ne doit modifier l'état scientifique.

Z4 n'est donc pas un registre permanent de supports/résistances. C'est un détecteur causal de montagnes présentes à l'instant du snapshot.

## 6.2 Causes possibles, par ordre logique

### 1. Rolling 1 440 actives

À chaque snapshot, des M1 sortent de la fenêtre et de nouvelles M1 entrent. Le champ de comptage wick change.

### 2. `vseg`

La médiane TR 1 440 est recalculée. Les trois rayons de lissage changent. Dans le proxy Pine, le rayon 3-box est entier ; un petit mouvement de `vseg` peut faire franchir un seuil d'arrondi et changer discrètement la topologie.

### 3. Pics et minima coarse

Une petite variation du profil lissé peut :

- fusionner deux pics ;
- séparer une montagne ;
- déplacer ou supprimer un minimum ;
- modifier les limites d'un bassin coarse.

### 4. Sélection medium

Le meilleur pic medium du bassin peut changer ou ne plus être localement détecté.

### 5. Confirmation fine

Le pic medium peut cesser d'avoir un pic fine dans la tolérance.

### 6. Prominence

Si la prominence devient nulle ou non positive, la zone est rejetée.

### 7. P50

P50 déplace les limites. Dans le Z4 fidèle, ces limites peuvent ensuite chevaucher le cours et rendre la zone inéligible.

### 8. Limites du profil

Quand un extrême ancien sort du rolling range, la grille locale se resserre. L'origine reste absolue, mais le traitement des bords peut modifier une montagne située près d'un extrême.

## 6.3 Ce qui n'est pas la cause directe

### Lineage

La lignée ne crée ni ne supprime une détection courante. Elle associe les zones déjà détectées et calcule leurs features historiques.

Quand une zone disparaît en amont, la lignée se termine ; elle n'est pas la cause de cette disparition.

### Top N

Il n'existe aucun Top N.

## 6.4 Captures 5 → 4 → 4 → 3

Dans v2.0.8, le filtre `side` n'exclut plus aucune montagne. La baisse observée ne peut donc pas provenir du filtre side de la v2.0.1.

Elle vient vraisemblablement de la chaîne :

- rolling / `vseg` ;
- profil ;
- coarse basin ;
- pic medium ;
- fine confirmation ;
- prominence.

La capture seule ne permet pas d'identifier le maillon exact.

## 6.5 Bug Pine ou churn attendu ?

Aucun bug de suppression n'est démontré par les captures.

Cependant, la parité combinée indique que le proxy Pine et l'exact Python ont le même nombre de zones dans seulement environ **59,35 %** des landmarks DEV, même si leurs zones appariées et leurs scores ont une très forte parité.

Conclusion :

- le churn de zones existe par construction dans Z4 ;
- certains événements individuels d'apparition/disparition peuvent être spécifiques au proxy Pine ;
- les gates ont validé une équivalence globale, pas l'identité de chaque snapshot.

### Test minimal sans outcomes

Ajouter un mode trace sur un jeu de timestamps figé qui enregistre, pour chaque montagne potentielle :

- coarse peak présent/absent ;
- bassin ;
- medium choisi ;
- fine confirmé/non confirmé ;
- prominence ;
- P50 ;
- side éligible/non éligible ;
- match lineage.

Comparer exact Python et proxy Pine sur Dukascopy, sans lire les outcomes.

---

## 7. Nouvelle hypothèse MEMORY

## 7.1 Statut

**Expérimental — non validé.**

Question :

> Une zone Z4 qui cesse d'être détectée conserve-t-elle une information de revisite ?

Cette question n'est pas couverte par le modèle validé.

## 7.2 Définitions outcome-blind à figer

### LIVE

Zone éligible détectée au landmark confirmé, selon le side Z4 original.

### FIRST_DISAPPEARANCE

Une lignée LIVE à `t-1` n'a aucun match éligible à `t`.

### REASON

Motif déterministe à tracer :

- `PROFILE_NO_PEAK` ;
- `COARSE_FAMILY_CHANGED` ;
- `MEDIUM_MISSING` ;
- `FINE_UNCONFIRMED` ;
- `PROMINENCE_NONPOSITIVE` ;
- `SIDE_OVERLAP` ;
- `GRID_UNAVAILABLE`.

### MEMORY

Géométrie figée au dernier snapshot LIVE :

- `zlo`, `zhi`, centre ;
- raw score et R au dernier LIVE ;
- side ;
- âge ;
- stabilité ;
- distance ;
- v60 / vseg ;
- timestamp de disparition.

Aucune mise à jour de la géométrie avec des données postérieures à la disparition.

### REAPPEARANCE

Une nouvelle zone LIVE rejoint la MEMORY selon un matcher pré-enregistré et causal.

### EXPIRATION

Durée maximale pré-enregistrée avant lecture des résultats.

Candidats raisonnables à figer sans les choisir à l'œil :

- 1, 2, 4, 8 et 16 landmarks ;
- soit 15, 30, 60, 120 et 240 minutes de cadence landmark.

## 7.3 Endpoint primaire proposé

`MEMORY_REVISIT_240` :

- à partir du landmark de première disparition ;
- revisite de l'intervalle figé `[zlo_last, zhi_last]` dans les 240 prochaines M1 actives ;
- pas de comptage de la M1 déjà utilisée pour constater la disparition ;
- une seule observation primaire par épisode de disparition ;
- bootstrap groupé par semaine, et idéalement sensibilité par lineage.

## 7.4 Comparaisons

### Baseline

Distance, largeur, side, volatilité, session, âge, dernier R / raw score.

### Candidat MEMORY

Baseline + :

- temps depuis disparition ;
- raison de disparition ;
- dernier âge/stabilité ;
- historique de réapparition ;
- nombre de snapshots LIVE avant disparition.

### Contrôles

- bandes témoins appariées largeur/distance/session ;
- zones LIVE ;
- MEMORY expirées comme contrôle négatif.

## 7.5 Séparation temporelle

La nouvelle hypothèse est née après lecture de Validation et OOS Z4. Ces périodes ne sont plus un holdout totalement vierge pour ce nouveau claim.

Plan honnête :

1. développement sur DEV janvier–juillet 2024 ;
2. réplication historique août 2024–juillet 2026, explicitement secondaire ;
3. vraie confirmation prospective sur une période réservée à partir du **2026-09-01**.

Tant qu'une gate prospective n'est pas passée :

- pas de `R` sur une MEMORY ;
- au maximum une zone fantôme pâle marquée `MEM — EXPERIMENTAL` ;
- aucune règle « reste valide jusqu'à cassure ».

---

## 8. Cross-feed Dukascopy → FOREXCOM

## 8.1 Statut actuel

**Non validé.**

Ce qui est établi :

- Dukascopy BID primaire ;
- Dukascopy ASK secondaire.

Ce qui n'est pas établi :

- `FOREXCOM:XAUUSD` ;
- feed TradingView générique ;
- broker CFD utilisé en exécution.

Le niveau de claim permis est :

> Modèle Z4 validé sur Dukascopy M1 ; calcul appliqué à FOREXCOM sous hypothèse de transfert non validée.

## 8.2 Gate 1 — parité de feed outcome-blind

Sur une période synchronisée et pré-enregistrée :

- timestamps UTC ;
- active-bar agreement ;
- OHLC QA ;
- offset de prix comparé en coordonnées relatives au close ;
- v60 / vseg ;
- zone count ;
- side agreement ;
- match de zones ;
- IoU ;
- erreurs centre/bornes en unités de vseg ;
- score raw ;
- R ;
- top-1.

Aucun résultat futur de revisit n'est nécessaire pour cette gate.

Les seuils doivent être figés avant calcul, idéalement en reprenant les critères de la gate Pine existante, sans les assouplir après lecture.

## 8.3 Gate 2 — transfert prédictif

Si la parité géométrique passe :

- coefficients Dukascopy gelés ;
- aucun refit sur FOREXCOM ;
- labels `REVISIT_240` calculés sur le même feed FOREXCOM ;
- M0 vs M0GL ;
- Brier, LogLoss ;
- bootstrap hebdomadaire ;
- deux moitiés ;
- QA causale ;
- BUY/SELL/US secondaires uniquement.

Pour une vraie confirmation prospective, réserver une période postérieure au prereg cross-feed.

---

## 9. Higher TF et expériences BODY

### M5/M15/H1

Les zones natives higher-TF peuvent être affichées comme descriptives ou swing.

Interdictions :

- pas de `R` Z4 M1 ;
- pas de claim de revisit validé ;
- pas de fusion arbitraire avec le score M1.

Un vrai score higher-TF exige un développement et une validation séparés.

### BODY

Le compteur de corps pur est descriptif.

### BODY-vs-WICK

La dominance corps/mèches est une nouvelle transformation non incluse dans Z4.

Ni l'un ni l'autre ne bénéficie des résultats DEV/Validation/OOS du modèle wick Z4.

---

## 10. Corrections minimales requises

Ordre obligatoire :

1. repartir de la v2.0.1 hashée ;
2. restaurer sans modification la logique side originale ;
3. ne pas conserver les zones P50 chevauchant le close ;
4. ajouter le traitement sur M1 confirmée ;
5. réarmer 96 landmarks après toute perte d'état due au grid ;
6. réappliquer seulement les changements UI de classe A ;
7. conserver le timestamp du snapshot visible ;
8. renommer temporairement le statut `QA_PROXY` pendant la vérification ;
9. produire un nouveau SHA et manifest ;
10. exécuter les gates suivantes sans outcomes :
    - diff statique du cœur scientifique ;
    - comparaison de 34 paramètres et 101 seuils ;
    - trace Python/proxy sur timestamps figés ;
    - test Replay ;
    - test live clôture landmark ;
    - test artificiel `GRID_LIMIT → recovery → 96 landmarks`.

Aucune nouvelle Validation/OOS économique n'est requise si le détecteur, les features, le modèle et la map R restent identiques à v2.0.1. Une nouvelle parity gate est nécessaire seulement si une modification dépasse les classes A/B minimales ci-dessus.

---

## 11. Utilisation discrétionnaire permise aujourd'hui

### Permis

- utiliser la v2.0.1 comme information de **rang relatif de revisite H240** ;
- seulement sur M1 ;
- seulement à partir d'un snapshot 15 min confirmé ;
- avec la mention FOREXCOM = transfert ;
- observer la géométrie et l'heure du snapshot ;
- considérer qu'une zone absente au snapshot suivant n'est plus une zone LIVE validée.

### Non permis

- utiliser les R de v2.0.2–v2.0.8 ;
- lire R comme un pourcentage ;
- lire R comme force de support/résistance ;
- déduire un BUY/SELL ;
- choisir un stop ou target ;
- maintenir une zone disparue comme valide scientifiquement ;
- appliquer R aux higher TF ou aux expériences BODY.

---

## 12. Décision finale

### Science Z4

**GO.**

Le résultat P_REVISIT_240 reste valide dans son périmètre Dukascopy M1 relatif à M0.

### Pine actuel v2.0.8

**NO-GO.**

Le changement `side` inverse la convention et modifie la population de zones. Le label `VALIDATED_PROXY` doit être retiré de cette version.

### Dernière base correcte

**v2.0.1**, SHA-256 :

`55737ed18eec86642663214860db8be33c9087382d3a52caf2dded7819b3f4fb`

### Production live

**REPAIR_ENGINEERING_REQUIRED**, sans optimisation et sans réouverture des outcomes.

### MEMORY

**PREREG_REQUIRED — EXPERIMENTAL.**

### FOREXCOM

**TRANSFER_ASSUMPTION — NOT VALIDATED.**

---

## 13. Provenance de l'audit

### Artifacts scientifiques versionnés

- `xau-wick-zone-pro/XAUUSD_WICK_ZONE_PREREG_ADDENDUM_v0_5_Z4_FROZEN.md`
- `xau-wick-zone-pro/XAUUSD_WICK_ZONE_PREREG_ADDENDUM_v0_6_Z4_OOS_FROZEN.md`
- `xau-wick-zone-pro/XAUUSD_WICK_ZONE_PRO_FINAL_REPORT_v0_4_2026-08-23.md`
- `xau-wick-zone-pro/xau_zone_episode_dev_z4.py`
  - blob `a8a147615c3fd366c49e93b340fd2018b5b66e9e`
- `xau-wick-zone-pro/results/XAUUSD_Z4_FROZEN_MODEL_PARAMS_v0_1.json`
  - blob `c95fd545ec451968cb421f81ed6add0c508f387d`
- `xau-wick-zone-pro/results/XAUUSD_Z4_REVISIT_SCORE_MAP_v0_1.json`
  - blob `c3376009db6e130dc55994c1321c1d8007b8b458`
- `xau-wick-zone-pro/validation/XAUUSD_Z4_VALIDATION_RESULTS_v0_1.json`
  - blob `d7a5120e58c9fa39c78d0453c417cd0694522e05`
- attestations OOS sous `xau-wick-zone-pro/oos/`
- résultats de parité sous `xau-wick-zone-pro/parity/`

### Pine audités localement

- v2.0.1 : `55737ed18eec86642663214860db8be33c9087382d3a52caf2dded7819b3f4fb`
- v2.0.8 : `7f67fdeb03b1b612462a9df05fee4c4feffee0302594b2ee9825b4448e74f333`

Au moment de l'audit, les fichiers Pine v2.0.1–v2.0.8 ne figurent pas dans l'arborescence versionnée `xau-wick-zone-pro`; ils proviennent des artefacts de la conversation. Ils doivent être commités avec leurs manifests avant toute nouvelle itération afin de restaurer une traçabilité complète.
