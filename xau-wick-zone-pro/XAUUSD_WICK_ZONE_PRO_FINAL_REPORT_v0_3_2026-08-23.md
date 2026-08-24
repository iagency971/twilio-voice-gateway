# XAUUSD Wick Zones — Rapport final Pro v0.3

**Date locale de gel : 2026-08-23**  
**Statut scientifique : M1 `P_REVISIT_240` PASS DEV → PASS VALIDATION → PASS OOS**  
**Réaction après contact : NO-GO**  
**Statut engineering Pine : combined proxy PASS; compilation/QA TradingView restant à effectuer sur le fichier Pine**

## 1. Résultat principal

L'hypothèse naïve « beaucoup de mèches historiques = zone qui rejettera le prix » n'est pas validée.

Une hypothèse plus précise, causale et testable est en revanche validée : sur XAUUSD M1 Dukascopy, l'architecture Z4 combinant géométrie de la montagne de mèches + composition/exposition + lignée/stabilité améliore de façon reproductible la prédiction de **revisite d'une zone dans les 240 prochaines M1 actives**, au-delà d'une baseline causale connaissant déjà distance, volatilité, tendances, heure/session et exposition historique.

Aucun résultat ne permet de transformer ce signal en probabilité de rejet, reversal ou support/résistance réussi après contact.

## 2. Z4 gelé

- 1 440 M1 actives (`high > low`).
- Prix sur grille absolue 0.01 USD dans la référence scientifique.
- `v60` : TR médian 60 M1 actives.
- `vseg` : TR médian 1 440 M1 actives.
- Gaussian exact Python `.25/.50/1.00 × vseg`.
- Coarse = famille ; meilleur pic medium ; confirmation fine.
- Bornes P50 de proéminence medium.
- Aucun Top N.
- Snapshots toutes les 15 minutes UTC.
- Lignées causales one-to-one.
- Endpoint : overlap `[zlo,zhi]` dans les 240 M1 actives futures.

## 3. DEV janvier–juillet 2024

BID folds APR/MAY/JUN/JUL, ΔBrier M0−M0GL :

- APR `+0.0012969675`
- MAY `+0.0015756988`
- JUN `+0.0018491785`
- JUL `+0.0012061727`

Pooled BID : ΔBrier **+0.0014727645**, ΔLogLoss **+0.0040951363**, bootstrap hebdomadaire95 **[+0.0006910282 ; +0.0023455891]**.

ASK réplique : ΔBrier **+0.0017428441**, bootstrap95 **[+0.0005757788 ; +0.0034426893]**.

## 4. Validation indépendante août 2024–juillet 2025

BID primaire :

- 134 272 rows / 23 518 landmarks ;
- Brier M0 `0.1394336344` ; M0GL `0.1372729365` ;
- ΔBrier **+0.0021606979** ;
- ΔLogLoss **+0.0064640617** ;
- 41/53 semaines positives ;
- bootstrap95 **[+0.0013474159 ; +0.0030235919]** ;
- H1 **+0.0019276763** ; H2 **+0.0023973542**.

Diagnostics tous positifs : BUY, SELL, US, non-US ; ASK global `+0.0019110452`.

**Gate Validation : PASS.**

## 5. OOS indépendant août 2025–juillet 2026

Modèle, coefficients, calibration et règles gelés avant ouverture.

BID primaire :

- 132 858 rows / 23 506 landmarks ;
- taux brut de revisite `29.8748%` ;
- Brier M0 `0.1686448215` ; M0GL `0.1561993591` ;
- ΔBrier **+0.0124454624** ;
- ΔLogLoss **+0.0427746202** ;
- bootstrap hebdomadaire95 **[+0.0100846293 ; +0.0146934804]** ;
- H1 **+0.0091764172** ; H2 **+0.0157083941** ;
- ASK secondaire ΔBrier **+0.0120343044**.

**Gate OOS : PASS.**

Le run OOS original a subi uniquement un conflit Git non-fast-forward pendant la publication finale, après réussite du calcul. Un rerun déterministe BID a reproduit les métriques primaires à `1e-15` et a imprimé `BIT-FOR-BIT PRIMARY METRIC RECOVERY MATCH: PASS`.

## 6. Calibration et vrai score utilisateur

La discrimination/ranking est validée, mais la calibration absolue dérive en OOS : ECE10 corrigé environ **0.07573**. Il serait trompeur d'afficher `72%`.

Le score utilisateur gelé est donc :

**`R xx = Revisit Score H240`**

Il s'agit du percentile du raw M0GL dans la distribution DEV pondérée également par landmark.

Exemple : `R 80` signifie environ 80e percentile de likelihood de revisite relativement à la référence DEV ; **pas 80% de probabilité**.

## 7. Réaction après revisite

Les endpoints sweep, reclaim du bord, reclaim du pic, reclaim complet, retest, MFE/MAE et direction 5/15/30/60 n'ont pas produit un gain suffisamment stable en DEV.

**`P_REACTION` = NO-GO.**

Il n'existe donc pas de score scientifiquement autorisé de « force support/résistance », rejet, reversal ou direction post-contact.

## 8. Port Pine outcome-blind

Les adaptations nécessaires pour Pine ont été testées sans utiliser les futurs outcomes.

### Gaussian 3-box

PASS : exact-match 92.41%, proxy-match 99.25%, Spearman score 0.99895, top1 89.27%.

### Warm-up lignée

Cap candidat `{96,128,160,192}` gelé ; **96** est le plus petit PASS. Score Spearman >0.9999995, top1 100% dans l'audit cap.

### Greedy lineage vs Hungarian

PASS : previous-link 99.9776%, score Spearman 0.999959, top1 99.956%.

### Compression de grille

Candidates `.02/.05/.10` gelés ; règle = plus grand PASS.

- `.02` PASS ;
- `.05` PASS ;
- `.10` FAIL (p95 center 0.3214 vseg et top1 82.40%).

Choix gelé : **0.05 USD**.

### Peak / prominence / P50 explicites Pine

PASS : référence-match 99.498%, Pine-match 99.882%, IoU médiane/p10 1.0, score Spearman 0.999992, top1 99.832%.

### Combined final proxy

Candidate : `0.05 + box3 + explicit peak/P50 + greedy lineage + warmup96`.

- exact rows 89 093 ; proxy 83 181 ; matched 82 183 ;
- exact match **92.2441%** ; proxy match **98.8002%** ;
- median IoU **0.973891** ; p10 **0.906309** ;
- median center error **0.038095 vseg** ; p95 **0.178571 vseg** ;
- score Pearson **0.997434** ; Spearman **0.998415** ;
- median raw-score error **0.002313** ; p95 **0.031047** ;
- top1 **86.9937%**.

Tous les seuils preregistered ont passé.

**Combined Pine proxy : PASS.**

## 9. Ce que le futur Pine peut afficher honnêtement

Sur M1, après historique et warm-up suffisants : `R xx` avec statut `VALIDATED_PROXY`.

Le statut signifie : le calcul Pine-feasible respecte les tolérances outcome-blind par rapport au moteur Z4 dont le pouvoir prédictif de revisite a passé DEV/Validation/OOS.

Cela ne valide pas automatiquement le feed TradingView/Vantage/OANDA : la validation scientifique primaire est Dukascopy BID. L'utilisation sur un autre feed est une hypothèse de transfert jusqu'à une étude cross-feed.

## 10. Higher timeframes

M5/M15/H1 peuvent conserver des zones de densité **descriptives**. Aucun `R` ne doit leur être attribué à ce stade. Il faudrait un protocole scientifique spécifique au timeframe pour valider un score swing.

## 11. Statut final

- **M1 Revisit information : VALIDÉE**.
- **R 0–100 ranking : AUTORISÉ**, sans symbole `%`.
- **Reaction/Direction : NO-GO**.
- **Combined Pine mathematical proxy : PASS**.
- **TradingView compile/runtime/replay QA : à faire sur le fichier Pine final**.
- **Cross-feed TradingView vs Dukascopy : non validé**.
- **M15/H1 score : non validé**.
