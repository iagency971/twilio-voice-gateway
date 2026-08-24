# XAUUSD Wick Zones — Rapport final Pro v0.4

**Date locale de gel : 2026-08-23**  
**Statut scientifique : M1 `P_REVISIT_240` PASS DEV → PASS VALIDATION → PASS OOS**  
**Réaction après contact : NO-GO**  
**Port mathématique Pine : PASS outcome-blind**  
**R-label 0–100 : PASS outcome-blind**  
**Reste hors laboratoire : compilation/runtime/replay TradingView + transfert de feed**

## 1. Conclusion scientifique

L'hypothèse simple « forte densité de mèches = forte probabilité de rejet/réaction » n'est pas validée.

Une hypothèse plus étroite est validée : sur XAUUSD M1 Dukascopy, l'architecture Z4 (géométrie de la montagne + exposition/composition + lignée/stabilité) apporte une information prédictive reproductible sur la **revisite de la zone dans les 240 prochaines M1 actives**, au-delà d'une baseline causale connaissant déjà distance, volatilité, tendances, session/heure et exposition historique.

Aucune conclusion de rejet, reversal, support/résistance réussi ou direction après contact n'est autorisée.

## 2. Architecture Z4 gelée

- M1 active : `high > low` ; barres plates exclues.
- Mémoire : 1 440 M1 actives.
- Grille scientifique : 0,01 USD, origine absolue 0,00 USD.
- `v60` : TR médian sur 60 M1 actives.
- `vseg` : TR médian sur 1 440 M1 actives.
- Gaussian exact Python `.25/.50/1.00 × vseg`.
- Coarse = famille ; meilleur medium peak ; confirmation fine.
- Bornes : P50 de proéminence du medium peak.
- Aucun Top N.
- Landmark toutes les 15 minutes UTC.
- Lignées causales one-to-one.
- Endpoint primaire : overlap `[zlo,zhi]` dans les 240 M1 actives futures.

Modèle gelé : StandardScaler DEV + LogisticRegression `C=0.10`, `lbfgs`, poids total égal par landmark. M0 = baseline causale ; M0GL = M0 + géométrie/composition/lignée/stabilité.

## 3. DEV janvier–juillet 2024

BID ΔBrier M0−M0GL :

- APR `+0.0012969675`
- MAY `+0.0015756988`
- JUN `+0.0018491785`
- JUL `+0.0012061727`

Pooled BID : ΔBrier **+0.0014727645**, ΔLogLoss **+0.0040951363**, bootstrap hebdomadaire95 **[+0.0006910282 ; +0.0023455891]**.

ASK réplique : pooled ΔBrier **+0.0017428441**, bootstrap95 **[+0.0005757788 ; +0.0034426893]**.

## 4. Validation indépendante août 2024–juillet 2025

BID : 134 272 rows / 23 518 landmarks.

- Brier M0 `0.1394336344`
- M0GL `0.1372729365`
- ΔBrier **+0.0021606979**
- ΔLogLoss **+0.0064640617**
- 41/53 semaines positives
- bootstrap95 **[+0.0013474159 ; +0.0030235919]**
- H1 **+0.0019276763**
- H2 **+0.0023973542**

BUY, SELL, US, non-US ont un ΔBrier positif ; ASK global **+0.0019110452**.

**VALIDATION : PASS.**

## 5. OOS gelé août 2025–juillet 2026

BID : 132 858 rows / 23 506 landmarks.

- taux brut de revisite : **29,8748 %**
- Brier M0 `0.1686448215`
- M0GL `0.1561993591`
- ΔBrier **+0.0124454624**
- ΔLogLoss **+0.0427746202**
- bootstrap hebdomadaire95 **[+0.0100846293 ; +0.0146934804]**
- H1 **+0.0091764172**
- H2 **+0.0157083941**
- ASK secondaire ΔBrier **+0.0120343044**

**OOS : PASS.**

L'incident Git du run original est strictement post-calcul : publication non-fast-forward après réussite du score. Un recovery BID déterministe a reproduit les métriques primaires à `1e-15` (`BIT-FOR-BIT PRIMARY METRIC RECOVERY MATCH: PASS`).

## 6. Calibration : pourquoi R n'est pas un pourcentage

La calibration absolue gelée dérive en OOS ; ECE10 corrigé ≈ **0,07573**. Il serait faux d'écrire `R80 = 80%`.

Le score utilisateur est donc :

**`R xx = Revisit Score H240`**

R est le percentile du raw M0GL dans la distribution DEV pondérée également par landmark. `R80` signifie environ 80e percentile de likelihood de revisite dans la référence DEV, sans interprétation probabiliste absolue.

## 7. Reaction branch

Sweep, reclaim du bord/pic/complet, retest, MFE/MAE et direction 5/15/30/60 ont été étudiés en DEV mais n'ont pas fourni un gain incrémental suffisamment stable.

**P_REACTION : NO-GO.**

Aucun score de « force support/résistance », rejet ou direction ne peut être dérivé de R.

## 8. Engineering Pine outcome-blind

### 8.1 3-box Gaussian
PASS : exact-zone 92,41 %, proxy 99,25 %, raw-score Spearman 0,99895, top1 89,27 %.

### 8.2 Warm-up / dépendance à l'historique de lignée
Candidates `{96,128,160,192}` gelés ; 96 = plus petit PASS. Avec cap96, raw-score Spearman >0,9999995 et top1 100 %. Cela autorise un cold-start live de **96 landmarks éligibles** avant d'afficher `VALIDATED_PROXY`.

### 8.3 Greedy one-to-one lineage vs Hungarian
PASS : previous-link agreement 99,9776 %, raw-score Spearman 0,999959, top1 99,956 %.

### 8.4 Grid compression
Candidates `.02/.05/.10` gelés ; règle = plus grand PASS.

- `.02` PASS ;
- `.05` PASS ;
- `.10` FAIL (p95 center 0,3214 vseg >0,25 et top1 82,40 % <85 %).

Grid Pine gelée : **0,05 USD**.

### 8.5 Peak / prominence / P50 explicites
PASS : reference-match 99,498 %, Pine-match 99,882 %, IoU médiane/p10 1,0, raw-score Spearman 0,999992, top1 99,832 %.

### 8.6 Combined proxy conservatif cap96
`0.05 + box3 + explicit peaks/P50 + greedy + cap96` : PASS.

- exact match 92,2441 % ; proxy 98,8002 %
- median IoU 0,973891 ; p10 0,906309
- median center error 0,038095 vseg ; p95 0,178571
- raw-score Pearson 0,997434 ; Spearman 0,998415
- median raw-score error 0,002313 ; p95 0,031047
- top1 86,9937 %

### 8.7 Actual carried-state Pine
Le comportement réellement prévu dans le Pine (état de lignée porté au-delà du warm-up, sans reset artificiel toutes les 96 observations) a été testé directement : **PASS**.

- raw-score Pearson **0,997432**
- Spearman **0,998415**
- median error **0,002311**
- p95 **0,031067**
- top1 **86,9937 %**

### 8.8 Affichage R 0–100
La transformation percentile et l'arrondi de label ont été testés outcome-blind sur 82 183 paires : **PASS**.

- median |ΔR_float| **0,283 point**
- p95 **2,974 points**
- displayed R médian : **0 point d'écart**
- 93,45 % des labels dans ±2 points
- 98,10 % dans ±5 points
- R Spearman **0,998415**
- matched top1 **96,99 %**

## 9. Autorisation Pine

Un fichier Pine M1 peut maintenant afficher `R xx` avec statut `VALIDATED_PROXY` après 1 440 M1 actives + warm-up 96 landmarks, à condition de respecter les paramètres gelés et de fail-closed en cas de limite de grille/historique.

Le statut `VALIDATED_PROXY` signifie « proxy mathématique Pine ayant passé les gates de parité vers le modèle Z4 scientifiquement validé ».

Il ne signifie pas « feed TradingView validé ». La science primaire est Dukascopy BID. Vantage/OANDA/autre feed = **hypothèse de transfert** jusqu'à un cross-feed test.

## 10. Higher timeframes

M5/M15/H1+ peuvent garder les zones natives descriptives de la branche précédente. **Aucun R n'est scientifiquement autorisé hors M1** aujourd'hui. Un score swing demanderait un protocole et une validation propres à chaque timeframe.

## 11. Statut Pro final

- M1 `P_REVISIT_240` : **VALIDÉ DEV + Validation + OOS**.
- R 0–100 ranking : **AUTORISÉ** sans `%`.
- P_REACTION / direction : **NO-GO**.
- Pine math proxy : **PASS**.
- Pine actual carried-state : **PASS**.
- R display parity : **PASS**.
- TradingView compiler/runtime/replay : **reste un QA d'implémentation à faire dans l'éditeur Pine**.
- Cross-feed : **non validé**.
- M15/H1 score : **non validé**.
