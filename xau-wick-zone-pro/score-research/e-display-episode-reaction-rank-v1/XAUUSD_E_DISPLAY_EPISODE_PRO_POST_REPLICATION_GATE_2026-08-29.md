# XAUUSD — E display episode reaction rank V1 — Pro post-replication scientific gate

**Date de gate :** 2026-08-29  
**Dépôt :** `iagency971/twilio-voice-gateway`  
**Branche :** `agent/xau-wick-zone-pro-dev`  
**Périmètre :** XAUUSD M1, BUY, session US 08:00–17:00 `America/New_York`  
**Gate :** `PRO_POST_REPLICATION_SCIENTIFIC_GATE`  
**Autorisation production :** aucune

# Verdict

## `GO_PROSPECTIVE_CONFIRMATION_PLANNING`

La combinaison du DEV gelé et de la réplication historique strictement hors échantillon justifie la préparation d’une confirmation prospective réellement nouvelle.

Cette décision autorise uniquement la **conception, l’implémentation et le gel du protocole prospectif**. Elle n’autorise pas encore l’ouverture d’un outcome prospectif, l’utilisation en trading, la modification du Pine, le réentraînement du modèle ou une affirmation de « force intrinsèque universelle » des zones E.

Le seul nouveau token autorisé est :

`GO_PROSPECTIVE_CONFIRMATION_PLANNING`

# 1. Intégrité du package revue par Pro

La réplication canonique est :

- run `33266656414` ;
- artifact `9719184524` ;
- digest `sha256:734bd0e14f9017dc23822175aa21bc341cfa5b27b5058dc5e028eb5fb5997688` ;
- commit d’exécution `2aa4abf4839558b42f5c999bf9e16127ece5b655` ;
- commit de matérialisation `685efd0dc89e6e71ab542c268f75f76cf8699f76` ;
- copie immuable `replication-freeze-canonical-33266656414/` ;
- commit de copie immuable `78af3d80af1a536babef17e05049bc320234c88a`.

Le digest du ZIP téléchargé a été revérifié. Les dix fichiers de preuve référencés par le manifeste de freeze correspondent tous à leur SHA-256. Le rapport de réplication est reproductible, le modèle DEV a été chargé sans refit et son SHA est resté inchangé avant et après scoring.

Les deux sessions partielles pré-identifiées ont été conservées, avec les 482 ouvertures M1 manquantes traitées selon la règle gelée. Aucun nettoyage post-outcome n’a été utilisé.

# 2. Résultat de réplication

La population hors échantillon contient :

- 34 007 épisodes affichés ;
- 17 454 contacts primaires ;
- 257 sessions NY représentées ;
- 8 649 `FAVORABLE_FIRST` ;
- 8 805 échecs binaires conservateurs ;
- taux favorable global : 49,5531 %.

Le modèle DEV totalement figé donne en réplication :

- AUC : `0.5657692601` ;
- AUC−0,5 : `+0.0657692601` ;
- IC95 % cluster sessions : `[+0.0568889680 ; +0.0744911974]`.

Les quartiles définis sur DEV, sans recalibrage, restent monotones :

| Quartile DEV figé | N réplication | Taux favorable |
|---|---:|---:|
| Q1 | 4 506 | 44,4962 % |
| Q2 | 4 067 | 45,6602 % |
| Q3 | 4 495 | 48,6763 % |
| Q4 | 4 386 | 59,2567 % |

L’écart Q4−Q1 vaut :

- `+0.1476049869`, soit +14,7605 points ;
- IC95 % cluster sessions : `[+0.1257313913 ; +0.1692963777]`.

Les trois blocs chronologiques complets conservent un Q4−Q1 positif :

- bloc 1 : +17,4812 points ;
- bloc 2 : +14,1193 points ;
- bloc 3 : +13,1060 points.

Les onze contrôles gelés avant l’ouverture de la réplication sont tous PASS.

# 3. Comparaison DEV → réplication

La réplication montre une atténuation raisonnable, attendue hors échantillon, sans effondrement :

- 86,89 % de l’excès d’AUC DEV est conservé ;
- 89,75 % de la séparation Q4−Q1 DEV est conservée ;
- le taux de succès de Q4 est pratiquement identique : 59,2710 % en DEV contre 59,2567 % en réplication.

Le résultat ne dépend donc pas uniquement de l’échantillon d’apprentissage. La réplication confirme que le rang figé ordonne de manière stable la probabilité du **reaction outcome précisément défini**.

# 4. Limite scientifique majeure : le rang est dominé par la largeur

La gate Pro a ajouté un diagnostic interprétatif, non préenregistré et donc **non utilisé comme gate ni comme moyen de tuning**.

Le modèle figé possède les coefficients standardisés suivants :

- `zone_width_v` : `+0.3178802467` ;
- `display_persistence_c5` : `+0.0175908258` ;
- effets famille : faibles, de `−0.0553` à `+0.0133`.

Le score complet est corrélé à `0.99465` avec sa seule composante largeur en DEV, et à `0.99451` en réplication.

AUC d’un simple classement déterministe par `zone_width_v` :

- DEV : `0.5742615596`, contre `0.5756928361` pour le modèle complet ;
- réplication : `0.5650434390`, contre `0.5657692601` pour le modèle complet.

L’apport observé de la persistance et de la famille au-delà de la largeur est donc très faible dans ces deux périodes.

Ce point n’annule pas la réplication du rang de réaction. Il limite strictement sa signification :

> Le résultat historique valide surtout qu’une zone plus large a davantage de chances d’atteindre le seuil favorable fixé au-dessus de `zhi` avant une clôture sous `zlo`.

Cette relation peut être en partie géométrique, car une zone plus large place l’invalidation plus loin alors que la cible favorable reste fixée à `zhi + 0,50v0`.

Il est donc interdit de conclure aujourd’hui que :

- la persistance ou la famille ajoutent une information matérielle validée ;
- le score mesure une force intrinsèque indépendante de la largeur ;
- le score prédit une expectancy de trading ;
- le nombre est une probabilité calibrée.

Le nom scientifique reste :

`E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1`

# 5. Pourquoi le verdict reste GO pour la planification prospective

Malgré cette limite sémantique, une confirmation prospective est scientifiquement justifiée pour quatre raisons :

1. le protocole historique a produit une association hors échantillon claire et stable ;
2. les quartiles DEV se transportent sans recalibrage ;
3. l’architecture a été sélectionnée au terme d’un long programme de recherche antérieur, ce qui laisse un risque résiduel de sélection que seule une période future totalement nouvelle peut réduire ;
4. la confirmation prospective permettra de tester la causalité opérationnelle, la stabilité de la collecte et l’absence de révision rétrospective.

Le GO porte donc sur la préparation d’un test futur rigoureux du **rang de réaction**, pas sur la promotion immédiate d’un score de qualité ou d’un signal de trading.

# 6. Exigences obligatoires du plan prospectif

La phase Très élevé suivante doit produire un package complet, outcome-blind et gelé avant la première session éligible.

## 6.1 Début prospectif

La période commence à l’ouverture de 08:00 New York de la première session complète située strictement après le scellement final du package prospectif.

Aucune donnée d’août 2026 déjà observable avant ce scellement ne pourra être réintroduite comme prospective.

## 6.2 Population, modèle et outcome

Tout reste inchangé :

- mêmes zones top-3 affichées ;
- même univers BUY US conditionné par Z4 ;
- même modèle DEV et mêmes coefficients ;
- mêmes transformations ;
- même distribution DEV pour le rang ;
- mêmes quartiles DEV ;
- même armement, premier contact, cible `zhi0 + 0,50v0`, invalidation, ambiguïtés et horizon de 30 M1 disponibles.

Aucun refit ni recalibrage n’est autorisé.

## 6.3 Checkpoint unique

Le résultat ne sera ouvert qu’une seule fois, immédiatement après la première session complète pour laquelle les deux conditions cumulatives sont satisfaites :

- au moins 90 sessions NY éligibles représentées ;
- au moins 1 000 contacts primaires.

Il sera interdit de retarder ou prolonger le checkpoint en fonction d’un aperçu de performance.

## 6.4 Firewall anti-peeking

Pendant la collecte, seuls pourront être suivis :

- la disponibilité des fichiers ;
- leurs hashes ;
- les erreurs de données ;
- les comptes de sessions et de contacts ;
- les exclusions de features et familles inconnues sans outcome.

Devront rester inaccessibles jusqu’au checkpoint :

- labels favorables/échecs ;
- taux de succès ;
- AUC ;
- résultats par quartile ;
- toute métrique ou proxy de performance.

## 6.5 Provenance prospective

Le plan doit définir avant démarrage :

- source M1 exacte ;
- cadence et horodatage d’acquisition ;
- stockage append-only ;
- SHA-256 de chaque fichier ;
- gestion des révisions de source ;
- génération causale des snapshots E ;
- règles pour données manquantes et doublons ;
- seuil fail-closed de qualité des données ;
- environnement logiciel exact ;
- artefacts quotidiens ou périodiques permettant de prouver que les features ont été figées avant ouverture des outcomes.

## 6.6 Contrôle interprétatif largeur

Le plan devra préenregistrer, séparément du test principal :

- un comparateur déterministe `zone_width_v` sans ajustement ;
- l’AUC du modèle complet et celle de ce comparateur ;
- une comparaison appariée clusterisée par session ;
- une règle de langage.

Ce contrôle ne pourra jamais sauver un échec du test principal ni servir à sélectionner un nouveau modèle.

Si le modèle complet ne montre pas de valeur incrémentale au-delà de la largeur, un éventuel succès prospectif devra être décrit comme **rang de réaction dominé par la largeur**, et non comme score multifactoriel de force E.

# 7. Ce qui reste interdit

La présente gate n’autorise pas :

- la génération ou lecture d’outcomes prospectifs ;
- un réentraînement ;
- une modification des features ou seuils ;
- une nouvelle sélection de familles ;
- une analyse de sous-groupes destinée à améliorer le résultat ;
- l’utilisation du score comme probabilité ;
- une étude de profitabilité implicite ;
- une modification du Pine ;
- une utilisation en production.

# 8. Prochain checkpoint

La phase Très élevé doit s’arrêter uniquement après avoir produit et vérifié :

- le préenregistrement prospectif complet ;
- le pipeline de collecte append-only ;
- le mécanisme de blindage ;
- les tests synthétiques et dry-runs ;
- les règles exactes de checkpoint et de qualité des données ;
- les hashes et l’environnement ;
- un package immuable.

Le statut attendu sera :

`READY_FOR_PRO_PRE_PROSPECTIVE_EXECUTION_GATE`

Il faudra alors revenir en Pro pour décider uniquement :

- `GO_PROSPECTIVE_CONFIRMATION_EXECUTION`, ou
- `NO_GO_PROSPECTIVE_CONFIRMATION_EXECUTION`.

# Conclusion

**Verdict :** `GO_PROSPECTIVE_CONFIRMATION_PLANNING`  
**Prospective execution :** non autorisée  
**Production :** aucune  
**Pine :** interdit  
**Prochaine phase :** Très élevé, planification et gel uniquement.
