# XAUUSD M1 — audit méthodologique outcome-blind du « score E » — BUY US

**Date de gel de l’audit :** 2026-08-28  
**Dépôt :** `iagency971/twilio-voice-gateway`  
**Branche :** `agent/xau-wick-zone-pro-dev`  
**Head inspecté avant rédaction :** `1308b5f7660e06c6b2df3116a28b31dd3dbee517`  
**Périmètre :** XAUUSD M1, BUY uniquement, session US 08:00–17:00 `America/New_York`  
**Statut :** **AUDIT MÉTHODOLOGIQUE TERMINÉ — VERDICT D — AUCUN SCORE INTRINSÈQUE E JUSTIFIÉ À CE STADE**  
**Autorisation production :** `NONE_METHOD_AUDIT_ONLY`  
**Modification Pine :** aucune.

---

## Frontière outcome-blind appliquée

Cet audit reconstruit uniquement :

- la génération et la localisation causales des zones E ;
- la continuité sticky et la signification des slots E1/E2/E3 ;
- le schéma de variables, leur instant de disponibilité et leur transformation ;
- la formule et la sémantique d’affichage du rang `E_BUY_US` ;
- les conditions méthodologiques nécessaires à une future calibration.

Aucune statistique de performance ou de réaction n’est utilisée dans le verdict : aucun taux de réussite, TP/SL, PF, expectancy, R, MFE/MAE, W5/W15/W60, SC, résultat H1/H2, résultat par E1/E2/E3 ou par tranche de score. Certains fichiers de code contiennent à la fois la construction des variables et des branches de calcul d’outcomes ; seules les parties définissant la géométrie, l’identité, le timing des variables, la transformation du modèle et l’interface Pine ont été retenues. Les champs de résultats ont été exclus du raisonnement.

Sources méthodologiques principales inspectées :

- `xau-wick-zone-pro/entry-research/xau_ebuy_coverage_v0_1.py`
- `xau-wick-zone-pro/entry-research/xau_ebuy_coverage_v0_2.py`
- `xau-wick-zone-pro/entry-research/xau_ebuy_coverage_v0_4_sticky.py`
- `xau-wick-zone-pro/entry-research/XAUUSD_Z4_EBUY_COVERAGE_PREREG_v0_4_STICKY_2026-08-25.md`
- `xau-wick-zone-pro/entry-research/xau_ebuy_reaction_dev_v1_0.py`, uniquement pour l’identité des épisodes et la définition temporelle des features
- `xau-wick-zone-pro/entry-research/xau_ebuy_score_dev_v1_0.py`, uniquement pour le schéma de variables et le pipeline
- `xau-wick-zone-pro/entry-research/xau_ebuy_score_freeze_v1_1.py`, uniquement pour la reconstruction du modèle gelé
- `xau-wick-zone-pro/entry-research/xau_ebuy_export_pine_model_v1_0.py`
- `xau-wick-zone-pro/entry-research/ebuy-pine-engineering-v1-0/E_BUY_US_PINE_MODEL_EXPORT_v1_0.json`
- Pine QA v2.4.x pour le timing réel, la mémoire de slot et l’étiquette affichée.

---

# 1. Current score reconstruction

## 1.1 Trois objets différents sont actuellement confondus par l’interface

Il faut distinguer strictement :

1. **la zone E**, c’est-à-dire un intervalle causal `[zlo, zhi]` issu de l’architecture locale ;
2. **le slot E1/E2/E3**, c’est-à-dire la place d’affichage de cette zone dans le top-3 sticky ;
3. **`E_BUY_US`**, c’est-à-dire un rang de percentile calculé pour un événement d’entrée BUY contextualisé après armement, contact, confirmation `BULL_REJECTION` et prochain open M1.

Le troisième objet n’est pas un score intrinsèque de la première entité. Le fait qu’il soit affiché sur l’étiquette de la zone crée une ambiguïté sémantique majeure.

## 1.2 Architecture de localisation E actuellement gelée

L’architecture locale est :

`Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`

avec un maximum de trois zones affichées.

Les familles n’utilisent pas une même unité de preuve :

- `EPM_M1_R2_A8H` agrège des pivots M1 confirmés avec rayon 2 et âge maximal de 8 heures ;
- `EWM_G60M` agrège des événements de mèche basse sur une fenêtre de 60 minutes ;
- `ESM_BOTH_G120M` agrège des micro-événements sur 120 minutes ;
- `ES_M1_8H_R2_T0.50` agrège des bas de session sur 8 heures ;
- `Z4` injecte les zones principales pertinentes avec priorité de déduplication.

Les champs de type `count` ont donc des significations et des opportunités d’observation différentes selon la famille. Leur somme ou leur comparaison brute ne constitue pas une échelle de force commune.

## 1.3 Construction du top-3 et signification de E1/E2/E3

Le moteur sticky :

- conserve d’abord une zone précédemment affichée si son identité reste appariée et valide ;
- libère le slot si la zone est franchie, n’est plus locale ou n’a plus de candidate sous-jacente correspondante ;
- remplit ensuite les slots disponibles avec les candidates restantes les plus proches sous le prix ;
- ordonne finalement l’affichage par centre décroissant, donc en pratique de la zone la plus proche sous le prix vers la plus éloignée.

Par conséquent :

> **E1/E2/E3 est un rang de localisation/affichage avec continuité sticky, pas un rang de qualité.**

`E1` ne signifie pas « meilleure zone ». Il signifie principalement « première zone affichée dans la pile locale », généralement la plus proche sous le prix, sous réserve de continuité et de déduplication.

## 1.4 Formule exacte de `E_BUY_US`

Le modèle gelé est un pipeline logistique supervisé :

1. 25 variables numériques ;
2. 3 variables catégorielles ;
3. imputation des numériques par la médiane de DEV ;
4. standardisation des numériques avec moyenne et écart-type de DEV ;
5. imputation des catégories par la modalité dominante et encodage one-hot ;
6. score brut :

`p = sigmoid(intercept + Σ beta_j * x_j_transformé)`

7. conversion de `p` en **rang percentile empirique** par rapport à la distribution des scores du jeu DEV gelé ;
8. conversion en entier E de 1 à 100 via les seuils de la CDF empirique gelée.

`E_BUY_US` n’est donc ni une probabilité calibrée, ni une note absolue, ni une mesure physique de force. C’est un rang relatif à une population historique de développement.

L’export canonique du pipeline contient :

- l’intercept scikit transformé ;
- les 38 coefficients après développement des catégories ;
- les médianes d’imputation ;
- les moyennes et échelles de standardisation ;
- les catégories one-hot ;
- les 100 seuils de percentile.

Le modèle Pine est une réécriture algébrique de ce pipeline et non un nouveau score.

## 1.5 Instant exact où le nombre affiché devient disponible

Le nombre visible après `E1`, `E2` ou `E3` n’est pas disponible à la naissance de la zone.

Il est finalisé seulement après :

1. existence causale de la zone ;
2. armement de l’épisode ;
3. premier contact éligible ;
4. confirmation d’une bougie M1 `BULL_REJECTION` ;
5. arrivée du prochain open M1, nécessaire pour calculer notamment `tp_distance_v` et `exec_gap_v`.

À cet open, le rang final est écrit dans `eDispLastE[slot - 1]`, puis l’étiquette de la zone affiche le **dernier rang d’entrée finalisé associé à ce slot**.

Conclusion de reconstruction :

> **Le système actuel ne calcule pas un score intrinsèque de chaque zone E. Il calcule un rang d’entrée BUY US contextualisé et mémorise sa dernière valeur sur un slot d’affichage.**

---

# 2. Causality audit

## 2.1 Causalité de la localisation

La localisation sticky v0.4 est causalement défendable sous ses règles gelées :

- snapshots confirmés ;
- generators utilisant uniquement les données connues à l’instant du snapshot ;
- pivots rendus disponibles après le délai de confirmation requis ;
- appariement d’identité fondé sur chevauchement ou proximité normalisée ;
- aucun maintien artificiel d’une zone sans candidate sous-jacente ;
- aucune réaction future utilisée pour conserver ou supprimer une zone.

Cette conclusion ne valide pas la qualité prédictive des zones. Elle valide seulement leur construction observable et reproductible.

## 2.2 Causalité de `E_BUY_US`

À son instant réel de finalisation — prochain open M1 après une confirmation — le calcul peut être causal : toutes ses variables sont alors connues.

Mais il n’est pas causalement disponible comme score de zone :

- à la naissance de la zone, les variables de contact n’existent pas ;
- avant la bougie de rejet, les variables de trigger n’existent pas ;
- avant le prochain open, les variables d’exécution n’existent pas.

Le problème n’est donc pas un lookahead automatique dans le calcul live ; c’est une **erreur de sémantique temporelle** si l’on interprète le nombre comme une qualité préexistante de la zone.

## 2.3 Supervision par un outcome

Les coefficients actuels ont été estimés à partir d’un label futur d’événement d’entrée. Ils sont donc, par construction, outcome-trained. Cela est acceptable pour un modèle prédictif correctement développé et validé, mais incompatible avec l’affirmation suivante :

> « ce score mesure de manière intrinsèque la force de la zone, indépendamment de ce qui se passe après ».

Aucune causalité runtime ne transforme un modèle supervisé d’entrée en mesure intrinsèque de géométrie.

## 2.4 Fuites et risques de double comptage

Aucun champ du schéma courant n’exige nécessairement une bougie postérieure au prochain open utilisé pour finaliser le rang. En revanche, plusieurs risques méthodologiques subsistent :

- confusion entre identité de zone et slot d’affichage ;
- redondance forte entre variables de prix, de pénétration et de forme de bougie ;
- intégration silencieuse de la géométrie Z4 dans un nombre présenté comme score E ;
- intégration du temps de session et du contexte de tendance dans un nombre présenté comme propriété de la zone ;
- comparabilité imparfaite des preuves issues de familles différentes ;
- rang percentile dépendant de la distribution DEV et non d’une unité stable.

---

# 3. Feature-by-feature review

Tous les numériques sont médiane-imputés puis standardisés avant application du coefficient logistique. Les catégories sont imputées puis one-hot. Les coefficients sont empiriques ; leur existence ne constitue pas une justification microstructurelle intrinsèque.

| Feature actuelle | Instant de disponibilité | Intrinsèque à E ? | Audit méthodologique |
|---|---|---:|---|
| `slot_rank` | snapshot/affichage | Non | Rang de proximité/slot sticky ; ne mesure pas la force. Peut changer sans modification fondamentale de l’épisode. |
| `episode_age_c5` | snapshot | Partiellement | Mesure la persistance de l’identité affichée, mais dépend aussi des règles de matching et du top-3. Défendable comme feature séparée, pas comme preuve suffisante. |
| `zone_width_v` | snapshot | Oui, descriptif | Largeur normalisée de l’intervalle. La direction « plus large = meilleur » ou l’inverse n’est pas justifiée a priori. |
| `arm_center_distance_v` | armement | Non | Contexte entre prix d’armement et centre E. Dépend du trajet du prix après apparition. |
| `tp_distance_v` | prochain open | Non | Distance jusqu’à la Z4 cible ; c’est explicitement de la géométrie Z4 et du prix d’exécution. |
| `minutes_to_us_end` | contact/trigger | Non | Contrainte d’horizon temporel, pas qualité de zone. |
| `v_contact` | contact | Non intrinsèque | Régime de volatilité au contact. Peut servir de normalisateur ou de contexte, pas de force E. |
| `trend5_v` | contact | Non | Tendance d’approche à très court terme. |
| `trend15_v` | contact | Non | Contexte de trajectoire, corrélé à `trend5_v`. |
| `trend60_v` | contact | Non | Contexte de régime, corrélé aux autres horizons. |
| `trend240_v` | contact | Non | Contexte plus large, pas propriété de la zone. |
| `contact_penetration_width` | contact | Non | Résultat du premier contact et profondeur de pénétration ; inexistant avant contact. |
| `contact_bull` | contact | Non | Direction de la bougie de contact. |
| `contact_close_position` | contact | Non | Position de clôture dans la bougie de contact ; redondance partielle avec corps/mèches. |
| `upper_z4_count` | snapshot/contact | Non | Descripteur de structure Z4 ; doit rester dans un bloc séparé. |
| `minutes_contact_to_trigger` | trigger | Non | Délai de confirmation ; caractérise l’événement d’entrée. |
| `trigger_body_v` | trigger confirmé | Non | Forme du signal de rejet. |
| `trigger_range_v` | trigger confirmé | Non | Taille du signal ; corrélée aux mèches et au corps. |
| `trigger_lower_wick_v` | trigger confirmé | Non | Feature du signal, pas de la zone. |
| `trigger_upper_wick_v` | trigger confirmé | Non | Feature du signal, pas de la zone. |
| `trigger_close_position` | trigger confirmé | Non | Feature du signal ; redondante avec corps et mèches. |
| `trigger_close_minus_zhi_v` | trigger confirmé | Non | Position du trigger par rapport à la borne E. Interaction zone × signal, pas intrinsèque E. |
| `trigger_close_minus_center_v` | trigger confirmé | Non | Interaction zone × signal ; fortement liée à la précédente et à la largeur. |
| `exec_gap_v` | prochain open | Non | Coût/gap d’exécution après le signal. |
| `max_penetration_to_trigger_width` | trigger confirmé | Non | Trajet entre contact et trigger ; corrélé à la pénétration du contact et aux positions de clôture. |
| `family` | snapshot/contact | Oui, descriptif | Identifie la famille candidate courante, mais n’est pas une échelle commune de force. |
| `episode_origin_family` | naissance de l’épisode | Oui, descriptif | Trace l’origine de l’identité sticky ; corrélée à `family`. |
| `us_subperiod` | contact/trigger | Non | Contexte horaire US, fortement lié à `minutes_to_us_end`. |

## 3.1 Variables effectivement compatibles avec un futur bloc intrinsèque

Parmi le schéma actuel, seules les variables suivantes peuvent entrer immédiatement comme descripteurs pré-contact de la zone :

- `episode_age_c5` ;
- `zone_width_v` ;
- famille(s) contributrice(s) de l’état courant ;
- famille d’origine de l’épisode.

Même ces variables ne justifient pas encore un score scalaire. Elles forment un petit vecteur descriptif.

## 3.2 Informations potentiellement pertinentes mais non encore spécifiées

Les générateurs actuels possèdent ou permettent de reconstruire des éléments tels que : nombre de preuves, récence, dispersion, concentration autour d’un pic, stabilité du centre et des bornes, ou diversité de familles. Ces éléments ne sont pas autorisés automatiquement.

Ils ne pourront entrer dans une future architecture que si :

1. leur définition exacte est écrite avant outcomes ;
2. leur unité est rendue comparable ou conservée famille par famille ;
3. les interactions sont déclusterisées pour éviter de compter plusieurs fois le même événement ;
4. leur snapshot est strictement antérieur au contact ;
5. leur code d’extraction et leurs tests de causalité sont gelés.

---

# 4. Weighting audit

## 4.1 Ce que représentent réellement les poids actuels

Les poids actuels sont les coefficients d’une régression logistique L2 entraînée sur une population d’événements d’entrée. Ils pondèrent simultanément :

- quelques descripteurs de zone ;
- la position de la zone et la géométrie Z4 ;
- le régime de volatilité et de tendance ;
- l’heure dans la session ;
- la qualité du contact ;
- la forme de la bougie de rejet ;
- le prochain open d’exécution.

Ils ne peuvent donc pas être réinterprétés comme des pondérations de « qualité intrinsèque E ».

## 4.2 Justification et arbitraire

Les poids sont reproductibles mais non justifiés a priori par une théorie de force de zone. Leur justification éventuelle est uniquement prédictive par rapport au label supervisé pour lequel ils ont été estimés.

Pour une note intrinsèque E :

- les signes ne sont pas pré-spécifiés ;
- aucune contrainte monotone n’est imposée ;
- la collinéarité peut répartir arbitrairement le poids entre variables proches ;
- le coefficient d’une catégorie dépend de la modalité de référence et de l’échantillon DEV ;
- l’imputation médiane peut créer un profil synthétique sans signification microstructurelle ;
- la transformation percentile rend la note relative à DEV et sensible au changement de régime.

## 4.3 Verdict de pondération

Il n’existe aujourd’hui aucune pondération défendable pour un score intrinsèque de zone. Les poids actuels doivent rester attachés à leur objet exact :

`ENTRY_CONTEXT_RANK_US_BUY`

et ne doivent pas être recyclés dans un futur `E_INTRINSIC_SCORE`.

---

# 5. E location vs E intrinsic quality

## Verdict explicite

> **Oui : tout futur score E prétendant mesurer la qualité intrinsèque doit être strictement séparé de la géométrie Z4 et du contexte d’entrée.**

Trois espaces de variables doivent être distincts :

### A. `E_INTRINSIC_SNAPSHOT`

Données décrivant l’évidence interne, la largeur, la stabilité et la persistance de l’épisode E, figées avant contact.

### B. `Z4_CONTEXT`

Position de E dans ou par rapport aux Z4, nombre de Z4, distance à une cible ou à une invalidation, potentiel structurel.

### C. `ENTRY_CONTEXT_US_BUY`

Trajectoire d’approche, contact, bougie de rejet, heure, volatilité, prochain open et conditions d’exécution.

La géométrie Z4 peut être utile dans une stratégie, mais elle ne doit pas être silencieusement absorbée dans une note de « force E ». Une architecture finale pourra utiliser les trois blocs, avec effets incrémentaux testés séparément.

---

# 6. Meaning of E1/E2/E3 rank

Le rang E1/E2/E3 est :

- **un rang de localisation/affichage** ;
- stabilisé par une mémoire sticky ;
- influencé par la proximité sous le prix et par la continuité de slot ;
- limité à trois zones pour des raisons de carte locale et d’interface.

Il n’est pas :

- un classement de probabilité de réaction ;
- un classement de densité homogène entre familles ;
- un classement de force intrinsèque ;
- une preuve que E1 est supérieure à E2 ou E3.

Usage autorisé : identifier sans ambiguïté le slot affiché à un instant donné.  
Usage interdit : employer E1 comme proxy de meilleure qualité sans validation indépendante.

---

# 7. Stability / repaint audit

## 7.1 Zone et identité

La zone sticky peut légitimement évoluer lorsque la candidate sous-jacente évolue. Cette évolution est causale si elle se produit seulement sur snapshot confirmé et si l’identité respecte la règle gelée :

- snapshots contigus de 5 minutes ;
- chevauchement ou distance de centres `<= 0.25 * max(v_old, v_new)` ;
- nouvelle identité en l’absence de match valide ;
- abandon lors d’une invalidation, d’une sortie de bande locale ou d’une disparition non appariée.

## 7.2 Score au fil du temps

Un futur score intrinsèque peut évoluer à mesure que de nouvelles preuves causales apparaissent, mais chaque version historique doit être immuable.

Règle nécessaire :

`score_snapshot = f(données disponibles jusqu’au snapshot confirmé t)`

Un backtest doit utiliser le dernier snapshot strictement antérieur au premier contact, jamais une valeur recalculée ultérieurement avec l’historique complet.

## 7.3 Mémoire actuelle de `E_BUY_US`

Le Pine mémorise le dernier rang d’entrée dans un tableau indexé par slot d’affichage. Cela suffit pour une UX de « dernière entrée associée au slot » si toutes les transitions de slot sont correctement réinitialisées et appariées.

Mais ce n’est pas une clé scientifique d’identité. Le code disponible ne permet pas de considérer l’étiquette comme un score immuable attaché à un `episode_id` universel. Une zone nouvellement remplie dans un slot ne doit jamais hériter silencieusement d’un rang produit par un épisode antérieur.

Avant toute future utilisation analytique de cette mémoire, un QA spécifique devra démontrer :

- reset lors du remplacement d’identité ;
- conservation seulement lors d’un match d’identité ;
- absence de transfert lors du réordonnancement E1/E2/E3 ;
- parité Python/Pine sur la clé d’épisode et le timestamp du score.

## 7.4 Repaint

- La localisation sur snapshots confirmés peut être non-repaint si les règles gelées sont respectées.
- La validation `BULL_REJECTION` scientifique doit rester confirmée à la clôture M1 ; l’état intrabar est seulement visuel.
- Le rang final d’entrée doit être commis au prochain open M1 et ne plus être modifié rétroactivement.
- Une note de zone affichée avant contact ne peut pas utiliser les features de contact, de trigger ou d’exécution.

---

# 8. Methodological verdict A/B/C/D

## Verdict : D — PAS DE SCORE JUSTIFIÉ À CE STADE

Ce verdict porte sur la demande précise d’un **score de qualité/force intrinsèque attribué à chaque zone E**.

Motifs :

1. le nombre actuellement affiché n’est pas calculé à la naissance de la zone ;
2. il dépend majoritairement du contexte de contact, de confirmation, de Z4 et d’exécution ;
3. E1/E2/E3 n’est pas un rang de qualité ;
4. les preuves brutes des différentes familles ne partagent pas une unité commune ;
5. les poids actuels ont été estimés pour un autre objet prédictif ;
6. les seules features intrinsèques déjà disponibles sont trop limitées pour justifier honnêtement une note globale.

Le modèle `E_BUY_US` peut être conservé techniquement sous son nom exact de **rang d’entrée BUY US**, avec ses non-claims existants. Il ne doit plus être décrit comme « score de la zone E ».

---

# 9. Frozen proposed score architecture

Aucun score scalaire n’est gelé par cet audit. L’architecture gelée proposée est d’abord un **ledger de features séparées**.

## 9.1 Bloc V1 immédiatement autorisé : `E_INTRINSIC_SNAPSHOT_V1`

À chaque snapshot C5 confirmé et pour chaque `episode_id` :

- `episode_id`
- `snapshot_time`
- `session_date_ny`
- `zlo`, `center`, `zhi`
- `v_snapshot`
- `zone_width_v`
- `episode_age_c5`
- `current_family_membership` sous forme multi-hot, pas seulement une chaîne fusionnée
- `episode_origin_family`
- hashes du code, des paramètres et de la source de données.

Ces champs restent des features, pas une note.

## 9.2 Bloc V2 conditionnel, à spécifier avant extraction

Les éléments suivants sont scientifiquement plausibles car ils dérivent de l’évidence déjà utilisée par les générateurs, mais ils ne sont pas encore autorisés :

- nombre d’interactions indépendantes après déclusterisation temporelle ;
- fraîcheur de la preuve la plus récente ;
- dispersion des prix contributifs autour du centre ;
- concentration normalisée autour du pic ;
- stabilité du centre et des bornes sur les derniers snapshots ;
- nombre de familles contributrices ;
- force interne propre à chaque famille, normalisée dans l’univers de cette famille et jamais additionnée à un count brut d’une autre famille.

Un document de spécification et un extracteur outcome-free devront préciser chaque formule, fenêtre, unité, règle de manque et règle d’identité.

## 9.3 Features explicitement exclues du futur score intrinsèque

- `slot_rank`
- toutes les distances à Z4 ou à la cible
- `upper_z4_count`
- heure/sous-période US et minutes restantes
- volatilité de contact utilisée comme signal de régime, hors normalisation mécanique
- tendances d’approche
- toutes les features de contact
- toutes les features de `BULL_REJECTION`
- toutes les features du prochain open
- tout résultat futur de réaction ou de trade.

Ces variables pourront exister dans des blocs contextuels séparés, jamais dans `E_INTRINSIC_SCORE`.

---

# 10. Preregistered future calibration protocol

Ce protocole est une proposition méthodologique. Il doit faire l’objet d’un fichier de pré-enregistrement distinct, hashé et commité avant ouverture des outcomes.

## 10.1 Population

- XAUUSD M1 ;
- BUY uniquement ;
- US 08:00–17:00 `America/New_York` ;
- architecture E sticky v0.4 gelée ;
- épisodes armés selon la règle causale existante ;
- premier contact éligible uniquement pour l’analyse primaire.

## 10.2 Unité statistique

Unité primaire :

> **un épisode structurel E par session NY, observé au premier contact armé, avec les features du dernier snapshot confirmé strictement antérieur au contact.**

Règles :

- une même identité dynamique ne crée pas plusieurs observations primaires ;
- les retests sont conservés dans un ledger secondaire de données répétées ;
- les incertitudes doivent être clusterisées au minimum par session NY et par épisode ;
- un épisode remplacé selon la règle d’identité reçoit un nouvel identifiant.

## 10.3 Ledger outcome-free avant calibration

Le ledger de features doit être produit sans aucune colonne future. Les contrôles obligatoires sont :

- causalité timestamp par timestamp ;
- parité d’identité Python/Pine sur un échantillon gelé ;
- invariance des snapshots historiques après ajout de données futures ;
- taux de valeurs manquantes ;
- distributions par famille et par sous-période, sans outcome ;
- matrice de corrélation entre features, sans sélection fondée sur un outcome ;
- vérification de l’unité et de l’échelle des preuves de chaque famille.

## 10.4 Construction du score

Ordre imposé :

1. geler le vecteur de features intrinsèques ;
2. geler les transformations et règles de manque ;
3. geler la population et l’unité statistique ;
4. geler l’outcome primaire et les outcomes secondaires ;
5. déclarer DEV et les validations scellées ;
6. seulement alors ouvrir DEV.

Modèle primaire proposé si un scalaire est toujours souhaité :

- une seule régression logistique L2 pré-spécifiée ;
- numériques standardisés exclusivement sur DEV ;
- catégories encodées exclusivement à partir du schéma gelé ;
- aucune compétition post hoc entre modèles ;
- aucune sélection automatique d’interactions ;
- aucun seuil de trading optimisé ;
- sortie conservée d’abord en score continu ;
- conversion éventuelle en percentile uniquement avec la CDF DEV gelée.

Si les features intrinsèques restent trop pauvres ou instables, le résultat correct est de conserver le vecteur sans fabriquer de score.

## 10.5 Périodes

Les périodes déjà utilisées dans les développements précédents ne doivent pas être présentées comme une validation indépendante neuve.

Ordre recommandé :

- **DEV :** une période historique explicitement déclarée comme déjà exploratoire ;
- **VAL-A :** un bloc historique jamais consulté pour E, si un audit de provenance confirme réellement son caractère scellé ;
- **VAL-B :** confirmation prospective sur des sessions postérieures au gel du 2026-08-28.

Aucune période ne devient OOS simplement parce qu’elle est renommée après consultation.

---

# 11. Preregistered validation protocol

## 11.1 Outcome primaire proposé pour la qualité intrinsèque

L’étude primaire ne doit pas tester une stratégie TP/SL ni intégrer les coûts. Elle doit tester la capacité d’une zone à produire une réaction après premier contact.

Définition proposée :

- `v0` = volatilité normalisatrice figée au dernier snapshot avant contact ;
- niveau favorable = `zhi_snapshot + 0.50 * v0` ;
- invalidation structurelle = première clôture M1 confirmée strictement sous `zlo_snapshot` ;
- fenêtre = 30 minutes après le premier contact ;
- succès = niveau favorable atteint avant invalidation ;
- échec = invalidation atteinte avant le niveau favorable ou absence de succès avant la fin de fenêtre ;
- si niveau favorable et invalidation coexistent sur la même M1, cas `AMBIGUOUS`, traité conservativement comme échec dans la métrique primaire et publié séparément.

Cette définition doit encore être pré-enregistrée séparément avant tout calcul. Les nombres `0.50v` et `30 minutes` ne pourront pas être modifiés après ouverture de DEV pour améliorer le résultat.

## 11.2 Outcomes secondaires pré-spécifiables

- MFE normalisée à W5/W15/W30/W60 ;
- MAE ou profondeur de pénétration normalisée à W5/W15/W30/W60 ;
- temps jusqu’au niveau favorable ;
- survie sans clôture sous `zlo` à W5/W15/W30/W60 ;
- profondeur maximale de pénétration dans la zone ;
- analyse séparée des retests, avec modèle de données répétées.

Ces outcomes secondaires ne peuvent pas remplacer l’outcome primaire si celui-ci échoue.

## 11.3 Critères d’un score validé

Les gates devront être gelées avant outcomes. Proposition :

1. association continue positive entre score et outcome primaire sur validation, avec intervalle bootstrap 95 % clusterisé par session dont la borne basse est > 0 ;
2. taux de succès ordonné de Q1 à Q4 selon les quartiles DEV gelés ;
3. différence Q4 − Q1 positive avec borne basse bootstrap 95 % > 0 ;
4. direction Q4 − Q1 positive dans au moins trois sous-blocs temporels pré-définis de validation ;
5. stabilité de la distribution du score et absence de concentration du résultat sur quelques extrêmes ;
6. aucun recalibrage, remapping ou nouveau seuil après ouverture de validation.

Les quartiles et tous les seuils doivent être dérivés de DEV puis figés avant validation.

## 11.4 Test incrémental ultérieur

Après validation intrinsèque seulement, une étude distincte pourra comparer :

- bloc intrinsèque E seul ;
- contexte Z4 seul ;
- contexte d’entrée seul ;
- combinaisons pré-spécifiées.

Le but sera de mesurer l’information incrémentale propre de E, pas simplement la performance brute d’une combinaison.

---

# 12. Remaining scientific risks

1. **Hétérogénéité des familles :** counts et preuves non directement commensurables.
2. **Biais de top-3 :** seules les zones locales affichées sont observées ; l’univers est conditionné par la sélection de carte.
3. **Dépendance à l’identité sticky :** l’âge et la stabilité dépendent du matcher.
4. **Dépendance de source :** Dukascopy et le flux opérationnel TradingView/FOREXCOM peuvent différer.
5. **Non-stationnarité :** un percentile DEV peut changer de signification avec le régime de volatilité.
6. **Données répétées :** épisodes proches dans une même session ne sont pas indépendants.
7. **Choix de réaction :** toute définition W30/0.50v reste une convention qui doit être gelée avant résultats.
8. **Contamination historique :** des périodes déjà utilisées ailleurs ne sont pas des validations neuves.
9. **Sémantique UX :** afficher un rang d’entrée sur une zone favorise une interprétation incorrecte de force intrinsèque.
10. **Mémoire par slot :** besoin d’un QA d’identité avant toute exploitation analytique du dernier score affiché.

---

# 13. Explicit forbidden uses before validation

Avant réussite d’une validation indépendante, il est interdit de :

- appeler `E_BUY_US` « score de force de la zone » ;
- considérer E1 supérieure à E2 ou E3 ;
- filtrer des zones sur leur dernier `E_BUY_US` comme si la valeur existait avant contact ;
- intégrer la géométrie Z4 dans un score présenté comme intrinsèque ;
- utiliser les coefficients actuels pour noter une zone vierge ;
- choisir les meilleures familles, heures, quartiles ou seuils après lecture de DEV ;
- recalculer un score historique avec des données apparues après le contact ;
- traiter un percentile comme une probabilité ;
- modifier le Pine de production pour afficher un nouveau score intrinsèque ;
- ouvrir la validation avant gel du ledger, de l’outcome, des splits, du modèle et des gates.

---

# 14. Point exact d’autorisation pour passer à la calibration empirique

L’ouverture de DEV devient scientifiquement permise uniquement après les cinq commits suivants, dans cet ordre :

1. présent audit méthodologique ;
2. spécification complète `E_INTRINSIC_SNAPSHOT_V1` ;
3. extracteur outcome-free + tests de causalité/identité/parité ;
4. pré-enregistrement de l’outcome primaire, des secondaires et des ambiguïtés ;
5. pré-enregistrement des périodes DEV/VAL, du modèle, des transformations et des gates.

Après ces gels, **DEV seulement** peut être ouvert pour estimer les poids. La validation reste scellée.

L’ouverture de VAL devient permise uniquement après :

- gel des coefficients ;
- gel du mapping du score ;
- gel des quartiles/cutpoints DEV ;
- gel du code de scoring ;
- preuve que plus aucun changement ne dépendra du résultat VAL.

---

# Décision finale

- La localisation E sticky reste un générateur causal de zones et n’est pas remise en cause par cet audit.
- E1/E2/E3 est un ordre d’affichage/localisation, pas une hiérarchie de force.
- `E_BUY_US` est un rang d’événement d’entrée US BUY finalisé au prochain open, pas un score intrinsèque de zone.
- Les poids actuels ne doivent pas être recyclés dans une note de zone.
- Le bon état scientifique actuel est un ledger de features intrinsèques séparées.
- Verdict officiel : **D — PAS DE SCORE INTRINSÈQUE JUSTIFIÉ À CE STADE**.
- Prochaine étape autorisée : spécifier et coder `E_INTRINSIC_SNAPSHOT_V1` sans outcome, puis pré-enregistrer l’étude de calibration.
