# XAUUSD Wick Zones — Rapport final de validation Pro

**Date de gel : 2026-08-23**  
**Statut scientifique : P_REVISIT_240 M1 = VALIDÉ / RÉPLIQUÉ ; P_REACTION = NO-GO**  
**Actif / feed : XAUUSD Dukascopy M1, BID primaire, ASK réplication secondaire**

## 1. Conclusion exécutive

Le programme de recherche ne valide pas l'idée simpliste « beaucoup de mèches = forte réaction future ».

En revanche, il valide une hypothèse plus étroite et mesurable : une architecture Z4 combinant la géométrie causale des montagnes de densité de mèches avec des variables de lignée/stabilité apporte une information prédictive reproductible sur la probabilité qu'une zone soit **revisitée dans les 240 prochaines M1 actives**, au-delà d'une baseline causale qui connaît déjà distance, volatilité, tendance, heure/session et exposition historique.

Cette conclusion a franchi successivement : DEV chronologique (janvier–juillet 2024), Validation gelée (août 2024–juillet 2025), puis OOS gelé (août 2025–juillet 2026), sans réentraînement ni modification du modèle.

Le modèle de réaction après contact n'a pas franchi les gates DEV. Il n'existe donc **aucun score validé de support/résistance, rejet, sweep/reclaim/retest ou direction après contact**.

## 2. Résultats antérieurs invalides

Les rapports `XAUUSD_DEV_PILOT_2024_07_M0_M2LITE_v0_1.md` et `XAUUSD_DEV_M2_SPATIAL24H_DIRECTION_SESSION_REPORT_v0_1.md` restent définitivement exclus. Ils avaient présenté des chiffres avant exécution complète d'un run prédictif et n'entrent dans aucune conclusion ci-dessous.

## 3. Architecture Z4 gelée

- M1 actives : `high > low` ; les barres plates/inactives n'ajoutent pas d'interactions.
- Mémoire : 1 440 M1 actives.
- Grille prix : 0,01 USD, origine absolue 0,00 USD.
- Champ de mèches : crossings des intervalles de mèches ; corps conservés séparément comme contre-information.
- Volatilité de segmentation `vseg` : médiane du True Range sur les mêmes 1 440 M1 actives.
- Lissages gaussiens Python exacts : 0,25× / 0,50× / 1,00× `vseg`.
- Coarse = familles/bassins ; un meilleur pic medium par famille ; confirmation fine.
- Bornes de zone : largeur du pic medium à 50 % de sa proéminence (P50).
- Aucun Top N, aucun seuil choisi à partir des résultats futurs.
- Snapshots éligibles toutes les 15 minutes.
- Lignées causales : matching déterministe one-to-one selon distance/vseg, IoU et variation de largeur ; une absence de zone éligible coupe la lignée.

Endpoint primaire : `REVISIT_240 = 1` si une des 240 M1 actives futures chevauche `[zlo, zhi]`.

## 4. Modèles gelés

M0 est la baseline causale : côté BUY/SELL, distance et distance absolue normalisées, largeur, TR, tendances 15/60/240, saisonnalité hebdomadaire, session US, exposition historique au centre.

M0GL = M0 + géométrie/exposition de montagne + lignée/stabilité : proéminence, background, strength descriptif, masse, hauteur de pic, composition mèche/corps, largeur/vseg, âge actif/civil, déplacement du centre, changements de largeur/proéminence/masse/strength, séquence de renforcement, dispersion récente du centre, CV de largeur, proéminence relative au maximum de la lignée.

Modèle : StandardScaler DEV uniquement + LogisticRegression `C=0.10`, `lbfgs`, `max_iter=500`, `tol=1e-6`, poids total égal par landmark.

## 5. DEV — janvier à juillet 2024

### BID, folds chronologiques APR / MAY / JUN / JUL

| Fold | Δ Brier M0−M0GL | Δ LogLoss |
|---|---:|---:|
| APR | +0.0012969675 | +0.0025115013 |
| MAY | +0.0015756988 | +0.0033401082 |
| JUN | +0.0018491785 | +0.0073547636 |
| JUL | +0.0012061727 | +0.0035159833 |

Pooled OOF BID : Δ Brier **+0.0014727645**, Δ LogLoss **+0.0040951363**, 14/18 semaines positives, bootstrap hebdomadaire 95 % **[+0.0006910282 ; +0.0023455891]**.

ASK a répliqué le signe sur les quatre folds : pooled Δ Brier **+0.0017428441**, Δ LogLoss **+0.0047776020**, bootstrap 95 % **[+0.0005757788 ; +0.0034426893]**.

Gate DEV revisit : PASS.

## 6. Validation indépendante — août 2024 à juillet 2025

Aucun réentraînement, recalibrage, sélection de feature ou changement de seuil.

### BID primaire

- 134 272 zone-rows ; 23 518 landmarks.
- Brier M0 **0.1394336344** ; M0GL **0.1372729365** ; Δ Brier **+0.0021606979**.
- LogLoss M0 **0.4313721757** ; M0GL **0.4249081141** ; Δ LogLoss **+0.0064640617**.
- 41/53 semaines positives.
- bootstrap hebdomadaire 95 % **[+0.0013474159 ; +0.0030235919]**.
- H1 Δ Brier **+0.0019276763** ; H2 **+0.0023973542**.

Les six critères prospectifs ont passé. Diagnostics : BUY **+0.0037526374**, SELL **+0.0034128781**, landmarks US **+0.0032465582**, non-US **+0.0014695585**, ASK global **+0.0019110452**.

Gate Validation : **PASS**.

## 7. OOS indépendant — août 2025 à juillet 2026

L'OOS a été gelé avant lecture : même moteur Z4, mêmes paramètres DEV, même endpoint, mêmes métriques, aucun fit sur Validation/OOS.

### BID primaire — run original gelé

- 132 858 zone-rows ; 23 506 landmarks.
- taux de revisite brut : **29,8748 %**.
- Brier M0 **0.1686448215** ; M0GL **0.1561993591** ; Δ Brier **+0.0124454624**.
- LogLoss M0 **0.5253853430** ; M0GL **0.4826107228** ; Δ LogLoss **+0.0427746202**.
- bootstrap hebdomadaire 95 % Δ Brier **[+0.0100846293 ; +0.0146934804]**.
- OOS-H1 Δ Brier **+0.0091764172** ; OOS-H2 **+0.0157083941**.
- QA causal/data : PASS.

Les six critères OOS gelés sont TRUE : **PASS**. ASK secondaire : Δ Brier **+0.0120343044**.

### Incident de publication GitHub

Le run scientifique original a terminé tous les calculs et le scoring avec succès. La dernière étape de publication a échoué uniquement parce qu'un commit concurrent avait avancé la branche, provoquant un rejet Git non-fast-forward. L'incident est postérieur au calcul et n'affecte pas le gate scientifique. `xau-wick-zone-pro/oos/XAUUSD_Z4_OOS_ACTIONS_ATTESTATION_v0_1.json` archive les IDs du run/job, les hashes gelés et les métriques stdout exactes.

## 8. Calibration : ne pas appeler le score « probabilité % »

Le classement/discrimination OOS est fort, mais la calibration absolue DEV-frozen dérive en OOS : Brier calibré **0.1559541252**, LogLoss calibré **0.4875910132**, ECE10 correctement pondéré **0.0757288001**.

Les bins restent monotones, mais sous-estiment généralement le taux de revisite observé. Par conséquent, on peut promouvoir un **Revisit Score 0–100**, mais pas dire `R72 = 72 % de probabilité` sans une nouvelle étape de recalibration prospectivement contrôlée.

## 9. Réaction après contact : NO-GO

Les endpoints DEV comprenaient direction 5/15/30/60 min, MFE/MAE/violation, sweep du bord opposé, reclaim du bord/pic/complet et retest. Ils n'ont pas produit un gain incrémental suffisamment stable selon chronologie, BUY/SELL et US.

Il est donc interdit scientifiquement de promouvoir `P_REACTION`, un score de « force support/résistance », un score de rejet, un score de direction après contact ou un score combiné revisit×reaction.

## 10. Ce qui est désormais démontré

> Pour XAUUSD M1, la construction Z4 gelée et ses variables causales de géométrie + lignée/stabilité ajoutent une information prédictive reproductible pour la revisite d'une zone dans les 240 prochaines M1 actives, au-delà de la baseline causale M0. L'effet a passé DEV, Validation indépendante et OOS indépendant.

Cela ne démontre pas que la zone va rejeter le prix, qu'elle est un support/résistance « fort », qu'elle est rentable à trader, qu'elle donne une direction, que le `Strength` actuel du Pine est prédictif ou que les résultats M1 s'appliquent automatiquement à M5/M15/H1.

## 11. Conséquence pour l'indicateur Pine

Le `Strength` actuel doit rester descriptif ou être retiré. Le futur score validé peut être nommé `R 0–100 = Revisit Score H240`, présenté comme un indice validé de likelihood/ranking de revisite, pas comme une probabilité calibrée en pourcentage.

Il ne doit pas encore être injecté dans Pine v1.3.4 : la géométrie Pine actuelle n'est pas identique au moteur Z4 validé. Notamment : TR médian 60 vs `vseg` 1 440 M1 actives, approximation gaussienne 3 box-blurs vs SciPy exact, bornes/proéminences différentes, absence des lignées/stabilité Z4 dans Pine, cadence Pine chaque barre vs snapshots Z4 de 15 minutes, et absence de validation >M1.

La prochaine gate est une **parité d'implémentation outcome-blind**, puis seulement le port du score.

## 12. Statut final du programme Pro

- **P_REVISIT_240 M1 : PASS DEV → PASS VALIDATION → PASS OOS.**
- **P_REACTION : NO-GO.**
- **Calibration en probabilité absolue : insuffisante pour afficher un `%` honnête.**
- **Pine score : pas encore autorisé avant parité Z4.**
- **M15/H1 : zones descriptives uniquement tant qu'un protocole spécifique n'a pas été validé.**
