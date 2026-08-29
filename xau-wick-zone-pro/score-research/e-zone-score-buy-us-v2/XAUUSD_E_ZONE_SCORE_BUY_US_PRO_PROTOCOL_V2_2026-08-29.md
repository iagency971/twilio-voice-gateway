# XAUUSD M1 — BUY US — validation des zones E1/E2/E3 et score V2

**Date de gel méthodologique :** 29 août 2026  
**Mode :** Pro  
**Dépôt :** `iagency971/twilio-voice-gateway`  
**Branche :** `agent/xau-wick-zone-pro-dev`  
**Périmètre exclusif :** XAUUSD M1, BUY, session US 08:00–17:00 New York, zones affichées E1/E2/E3

# Décision

## `GO_E_ZONE_SCORE_BUY_US_V2_SEQUENTIAL_HISTORICAL_EXECUTION`

La méthode est suffisamment définie pour lancer une exécution historique complète en mode Très élevé, sans nouvelle interruption Pro avant le package final.

Le prochain et unique checkpoint Pro doit être :

`READY_FOR_PRO_E_ZONE_SCORE_BUY_US_V2_FINAL_GATE`

Cette étude n’attend pas le 31 août 2026. Le collecteur prospectif V1 est une recherche parallèle et ne bloque ni les données historiques ni la validation demandée ici.

# Ce que le travail antérieur établit déjà

Le travail V1 n’est pas perdu. Il a établi sur deux périodes séparées qu’un classement des épisodes E affichés existe :

- DEV : 16 461 contacts, AUC 0,57569, Q4−Q1 +16,45 points ;
- réplication : 17 454 contacts, AUC 0,56577, Q4−Q1 +14,76 points ;
- le classement s’est maintenu sans refit du modèle.

Mais le V1 ne répond pas proprement à la question de l’utilisateur pour deux raisons :

1. il ne compare pas les zones E à des niveaux neutres appariés ;
2. son outcome donne davantage de marge aux zones larges, et son score est corrélé à environ 0,995 à sa composante largeur.

Le gain du modèle complet sur la largeur seule n’était que d’environ +0,00143 d’AUC en DEV et +0,00073 en réplication. Le V1 constitue donc une preuve qu’un classement reproductible existe, mais pas encore la validation d’un score de qualité propre aux zones.

# Questions scientifiques V2

L’étude V2 doit rendre des réponses distinctes et non ambiguës :

1. **Les zones E affichées sont-elles de meilleurs lieux de réaction BUY que des niveaux neutres comparables ?**
2. **E1, E2 et E3 sont-elles chacune statistiquement soutenues ?**
3. **Peut-on classer leur qualité sans transformer la largeur, la proximité ou le numéro du slot en fausse force ?**
4. **Les caractéristiques intrinsèques ou historiques de la zone ajoutent-elles réellement quelque chose au-delà du contexte de marché ?**
5. **Une formule unique et interprétable peut-elle ensuite être transposée dans Pine ?**

# Périmètre gelé

L’étude porte uniquement sur :

- XAUUSD BID M1 ;
- BUY ;
- 08:00–17:00 `America/New_York` ;
- présence d’au moins une Z4 causale strictement au-dessus du prix ;
- trois slots d’affichage originaux du moteur v0.4 sticky ;
- familles E suivantes :
  - `ESM_BOTH_G120M` ;
  - `EPM_M1_R2_A8H` ;
  - `EWM_G60M` ;
  - `ES_M1_8H_R2_T0.50`.

Les lignes Z4 ne font pas partie de la population E scorée. Le numéro E1/E2/E3 reste le slot original du v0.4. Il ne doit jamais être interprété comme une qualité. Lorsqu’une Z4 occupe un slot du display, elle est exclue sans renuméroter artificiellement les E restantes.

Sont exclus : SELL, autres sessions, autres timeframes, profit factor, expectancy, stratégie d’entrée, optimisation de stop/target et toute modification Pine pendant l’étude.

# Autorité du détecteur

La géométrie reste celle du moteur v0.4 sticky :

`Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`

Le nouveau code pourra ajouter des colonnes de provenance et d’évidence causale, mais ne pourra modifier aucune zone affichée.

Avant d’ouvrir un outcome V2, une gate de parité doit vérifier, sur tout le chevauchement août 2024 → juillet 2026, une égalité exacte de :

- timestamp ;
- slot original ;
- famille ;
- centre ;
- borne basse ;
- borne haute.

Une seule différence invalide le package pré-outcome.

# Périodes historiques

Les outcomes exacts V2 doivent être ouverts séquentiellement :

| Période | Fenêtre UTC | Rôle |
|---|---|---|
| DEVELOPMENT_V2 | 2020-01-01 inclus → 2022-01-01 exclu | Ajustement unique et gel du modèle |
| VALIDATION_V2 | 2022-01-01 inclus → 2023-01-01 exclu | Première validation chronologique |
| REPLICATION_V2 | 2023-01-01 inclus → 2024-01-01 exclu | Seconde validation chronologique |
| Robustesse non-gating | 2024-01-01 inclus → 2024-08-01 exclu | Rapport après réplication uniquement |

La période août 2024 → juillet 2026, déjà utilisée dans V1, est interdite pour le fit, la sélection des features, les seuils et la décision V2.

Chaque fenêtre doit recevoir au moins 35 jours calendaires de warm-up antérieur. Les contacts du warm-up ne comptent pas.

# Outcome primaire neutralisé de la largeur

L’épisode s’arme seulement après `feature_available_time` et après un close M1 strictement au-dessus de la borne haute courante. La bougie d’armement ne peut pas être la bougie de contact.

Le premier contact est la première M1 disponible ultérieure dont l’intervalle `[low, high]` intersecte la zone causale encore vivante.

Au contact :

- `v0` = volatilité gelée du dernier snapshot causal disponible avant le contact ;
- `A` = close de la bougie de contact ;
- niveau favorable = `A + 0,50 × v0` ;
- niveau adverse = `A − 0,50 × v0`.

Le high et le low de la bougie de contact sont ignorés pour le résultat. La recherche commence à la M1 disponible suivante.

Dans les 30 M1 disponibles suivantes, limitées à 17:00 New York :

- favorable touché en premier → `FAVORABLE_FIRST = 1` ;
- adverse touché en premier → `ADVERSE_FIRST = 0` ;
- les deux dans la même M1 → `AMBIGUOUS_SAME_BAR = 0` ;
- aucun → `NEITHER = 0`.

L’utilisation du close de contact comme ancre et de distances symétriques élimine l’avantage mécanique procuré auparavant par une borne basse plus éloignée. La largeur ne participe ni au target ni à l’adverse threshold.

# Validation des zones contre témoins neutres

## Principe

Pour chaque épisode E réel, cinq épisodes placebo sont construits avant outcome par transplantation de son chemin géométrique normalisé dans d’autres sessions comparables de la même période.

La transplantation conserve exactement :

- la famille ;
- le slot ;
- les offsets C5 de l’épisode ;
- la distance au prix en unités de volatilité ;
- les demi-largeurs inférieure et supérieure en unités de volatilité ;
- la persistance observée du chemin donneur.

À chaque snapshot receveur :

- `center_placebo = close_receveur − distance_v_donneur × v_receveur` ;
- les demi-largeurs normalisées du donneur sont multipliées par `v_receveur`.

## Appariement

Le snapshot receveur doit avoir :

- le même créneau NY de cinq minutes ;
- le même jour de semaine NY ;
- le même slot E1/E2/E3 ;
- le même bucket de nombre de Z4 supérieures : 1, 2 ou 3+ ;
- un ratio de volatilité dans un caliper logarithmique de 0,20 ;
- une distance à la Z4 supérieure la plus proche dans un caliper de 0,25v.

Le choix des cinq voisins utilise uniquement les tendances causales 15/60/240 M1, la volatilité et la distance à la Z4. Il est déterministe, sans outcome, avec départage SHA-256. Une session receveuse doit être différente et distante d’au moins dix sessions représentées.

## Neutralité des placebos

Un placebo est censuré dès que son intervalle :

- chevauche une vraie E ou Z4 du pool causal complet ;
- ou se situe à moins de 0,20v du centre d’une vraie E ou Z4 ;
- ou ne peut plus être reconstruit sur un snapshot receveur disponible et éligible.

Ainsi, le témoin reproduit la géométrie, la position et la persistance du donneur sans être lui-même un niveau détecté.

Le placebo est ensuite soumis exactement aux mêmes règles d’armement, de contact et d’outcome symétrique.

## Estimand primaire

Un set apparié primaire comprend :

- une vraie E ayant eu un contact ;
- au moins deux des cinq placebos ayant également eu un contact.

Chaque vraie E pèse un. Son comparateur est la moyenne de ses placebos contactés.

Effet primaire :

`moyenne(Y_E_reelle − moyenne(Y_placebos))`

L’inférence emploie 5 000 tirages bootstrap multiway cluster par sessions donneuses et receveuses, seed figée, avec au moins 4 750 tirages valides.

Pour valider globalement les zones, l’effet pooled doit être positif avec borne basse IC95 % strictement supérieure à zéro dans VALIDATION_V2 et REPLICATION_V2. Il faut aussi :

- au moins 1 000 contacts réels appariés ;
- au moins 90 sessions donneuses ;
- au moins 70 % des contacts réels avec deux placebos contactés ou plus ;
- SMD absolue ≤ 0,10 sur largeur, distance, volatilité, minute de session, Z4 supérieure et tendances.

Si le matching ou l’équilibre échoue, il est interdit de redessiner les placebos après lecture des outcomes.

# Verdicts E1, E2 et E3

Le pooled est l’estimand principal du détecteur. Mais chaque slot reçoit aussi un verdict propre en réplication.

Un slot est déclaré `VALIDATED` uniquement avec :

- au moins 300 contacts réels appariés ;
- au moins 60 sessions ;
- effet positif ;
- p-value bootstrap unilatérale ajustée Holm < 0,05 parmi E1/E2/E3.

Un slot qui ne passe pas ne pourra pas être présenté comme statistiquement validé, même si l’effet pooled passe.

# Construction du score V2

## Features de force autorisées

Le score n’utilise que :

1. **évidence native normalisée par famille**, après retrait du facteur de distance ;
2. **persistance d’affichage** en `log1p` ;
3. **confluence de familles E** avant déduplication, de 1 à 4 ;
4. **stabilité du centre sur trois C5** ;
5. **famille courante**.

L’évidence native est définie sans ambiguïté :

- EWM : contraste de densité de mèches ;
- ES : nombre causal de pivots dans le cluster ;
- EPM : décroissance causale avec l’âge du pivot ;
- ESM : valeur constante 1, donc aucune fausse variation interne.

Chaque évidence native devient un percentile empirique au sein de sa famille, construit sur DEV puis figé.

## Variables de nuisance

La largeur, la distance, le slot, la volatilité, l’heure, le contexte Z4, les tendances et le jour de semaine doivent être contrôlés dans le modèle, mais leur contribution est retirée du score affiché.

Le score ne doit donc jamais attribuer des points parce qu’une zone est simplement plus large, plus proche, E1 plutôt que E3, ou située à une heure historiquement plus favorable.

## Modèle unique

Deux régressions logistiques L2 sont gelées :

- nuisance-only ;
- full = mêmes nuisances + features de force.

Paramètres : `C=1`, `lbfgs`, `max_iter=5000`, aucune pondération de classes, aucune recherche d’hyperparamètre.

Le score brut affiché est uniquement la somme des contributions des features de force du modèle full. L’intercept et toutes les contributions de nuisance sont exclus.

Le score 0–100 est le percentile midrank DEV du score brut. Le mapping est figé après DEV et appliqué sans refit à validation et réplication.

La formule doit être identique pour E1, E2 et E3.

# Gates du score

Dans VALIDATION_V2 et REPLICATION_V2, toutes les conditions suivantes sont obligatoires :

- au moins 1 000 contacts et 90 sessions ;
- AUC du score brut > 0,5 avec borne basse IC95 % > 0,5 ;
- quartiles DEV figés dans l’ordre Q1 ≤ Q2 ≤ Q3 ≤ Q4 ;
- Q4−Q1 positif avec borne basse IC95 % > 0 ;
- gain d’AUC full − nuisance-only positif avec borne basse IC95 % > 0 ;
- exclusions ≤ 2 % ;
- famille inconnue ≤ 5 % ;
- corrélation de Spearman absolue score-largeur ≤ 0,20 au total ;
- corrélation absolue ≤ 0,30 dans chaque famille suffisamment représentée ;
- Q4−Q1 positif dans au moins quatre des cinq quintiles de largeur DEV figés ;
- aucun quintile de largeur avec effet inférieur à −2 points ;
- aucune modification de méthode.

Le résultat doit également être ventilé par E1/E2/E3 sans modèle ou seuil spécifique au slot.

# Arbre de décision final

- **Zones pooled échouent :** aucune validation statistique des zones E ; aucun score Pine.
- **Pooled passe mais certains slots échouent :** seuls les slots passant leur gate propre sont déclarés validés.
- **Zones passent, score échoue :** zones retenues, mais aucun score 0–100 de qualité n’est autorisé.
- **Zones et score passent :** retour en Pro pour figer la formule Pine, le breakdown des points et les libellés.

Même un double PASS ne prouve pas une stratégie profitable : il valide une localisation de réaction et un rang relatif, pas une expectancy nette de spread, slippage ou gestion de trade.

# Séquence d’exécution autorisée

Le mode Très élevé doit :

1. coder la génération Z4 geometry-only, l’instrumentation V2, les placebos, le labeler, les modèles et le QA indépendant ;
2. prouver la parité v0.4 et l’absence de lookahead ;
3. geler et hasher tout le package pré-outcome ;
4. ouvrir DEV, ajuster une fois, puis geler le modèle et le mapping ;
5. ouvrir validation sans refit ;
6. ouvrir réplication uniquement si la gate de continuation validation est complète ;
7. geler tous les résultats, contrôles, hashes, artefacts et commits ;
8. s’arrêter uniquement au checkpoint final Pro.

Aucune étape Pro intermédiaire n’est requise. En cas d’échec de validation, le mode Très élevé doit tout de même produire le package final avec le verdict mécanique, sans ouvrir la réplication.

# Statut

**Gate méthodologique ciblée : PASS**  
**Token autorisé :** `GO_E_ZONE_SCORE_BUY_US_V2_SEQUENTIAL_HISTORICAL_EXECUTION`  
**Prochaine étape :** Très élevé  
**Prochain checkpoint :** `READY_FOR_PRO_E_ZONE_SCORE_BUY_US_V2_FINAL_GATE`  
**Pine :** interdit jusqu’au verdict Pro final  
**Production :** aucune autorisation
