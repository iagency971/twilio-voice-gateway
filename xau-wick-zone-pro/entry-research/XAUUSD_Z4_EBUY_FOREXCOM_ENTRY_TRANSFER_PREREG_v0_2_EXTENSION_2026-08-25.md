# XAUUSD Z4 / E-BUY — FOREXCOM Entry-Layer Transfer Sample Extension v0.2

Date de gel : 2026-08-25 (avant lecture de tout résultat du run d'extension)
Branche : `agent/xau-wick-zone-pro-dev`

## 1. Motif prédéfini de l'extension

Le pilote v0.1 est formellement `ENTRY_TRANSFER_PILOT_FAIL_NO_PINE_PROMOTION` parce que la gate de taille `common eligible C5 >= 250` n'est pas satisfaite : 232 C5 communs. Toutes les autres gates v0.1 passent sur BID→FOREXCOM et synthetic MID→FOREXCOM.

Aucun seuil v0.1 n'est abaissé. Le résultat v0.1 reste FAIL dans l'historique.

Cette v0.2 autorise uniquement une **extension prospective de l'échantillon temporel** avec de nouveaux bars des mêmes feeds et la réexécution inchangée du comparator v0.1 afin de déterminer si la gate préexistante passe lorsque N>=250.

## 2. Feeds inchangés en identité

- Référence primaire : Dukascopy XAUUSD M1 BID.
- Contrôle quote-basis : Dukascopy synthetic MID issu du même snapshot BID+ASK.
- Cible opérationnelle : TradingView `FOREXCOM:XAUUSD` M1, `bar_source=mid`, acquisition websocket `request_more_data`.

Aucun autre broker/symbole/feed n'est autorisé.

## 3. Acquisition prospective autorisée

Une nouvelle acquisition des deux feeds est autorisée après le gel de ce document afin d'étendre leur intersection temporelle. Les bytes de l'acquisition étendue doivent être archivés immuablement avec le résultat.

La fenêtre évaluée est l'intersection exacte du nouveau snapshot Dukascopy août 2026 et du nouveau snapshot FOREXCOM. Les mêmes maturités causales restent obligatoires :

1. 1440 M1 actives disponibles sur chaque feed ;
2. 96 landmarks C5 après maturité ;
3. timestamps communs ;
4. session US `08:00 <= America/New_York < 17:00`.

## 4. Objets figés — aucun changement

Architecture E-BUY : `Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`.

Display : v0.4 sticky top-3.

Trigger : `BULL_REJECTION`.

Score : `M1_LOGISTIC`.

SHA-256 modèle : `ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342`.

CDF H1, features et mapping `E_BUY_US` inchangés.

Comparator : `xau-wick-zone-pro/entry-research/xau_ebuy_forexcom_entry_transfer_v0_1.py`, sans modification scientifique.

## 5. Gates

**Toutes les gates v0.1 sont reprises sans modification**, notamment :

### Raw
- timestamp coverage >= 0.97 ;
- return Spearman >= 0.95.

### Location, BID et MID séparément
- common eligible C5 >= 250 ;
- zone match référence >= 0.75 ;
- zone match cible >= 0.75 ;
- median relative IoU >= 0.60 ;
- median relative center error <= 0.35 v60 ;
- p90 center error <= 0.75 v60 ;
- exact candidate-count agreement >= 0.65 ;
- candidate-count agreement within 1 >= 0.90 ;
- nearest/top-1 agreement >= 0.70.

### Trigger, BID et MID séparément
- triggers référence >=25 ; cible >=25 ; matched >=20 ;
- match rate référence >=0.60 ; cible >=0.60 ;
- median |delta temps| <=1 minute ; p90 <=2 minutes ;
- median entry-zone center error <=0.50 v60.

### Score
- Spearman score brut >=0.80 ;
- Spearman E_BUY_US >=0.80 ;
- median |delta E| <=10 ;
- share |delta E|<=15 >=0.80 ;
- accord E80 >=0.75 si union E80 >=10 ;
- E90 descriptif seulement.

## 6. Interdictions

Toujours interdits : MFE/MAE, TP/invalidation futur, P&L, coûts, refit, recalibration, nouveau feature, changement trigger, changement CDF, remapping E, ajustement de seuil après résultat, sélection de fenêtre basée sur les métriques de parité.

L'extension n'est pas une optimisation ; elle corrige uniquement l'insuffisance N=232 par collecte prospective de bars additionnels.

## 7. Verdict

`ENTRY_TRANSFER_EXTENSION_PASS_OPERATIONAL` uniquement si le comparator inchangé produit un PASS complet sur **toutes** les gates v0.1 avec `common eligible C5 >= 250` pour BID et MID.

Sinon : `ENTRY_TRANSFER_EXTENSION_FAIL_NO_PINE_PROMOTION`.

Un PASS autorise uniquement la promotion engineering Pine/TradingView M1 de la couche entrée sur `FOREXCOM:XAUUSD`.

## 8. Non-claims

Même en cas de PASS : aucune performance future FOREXCOM, aucun P&L, aucun coût de transaction, aucun `R_US`, aucun E-BUY HTF, et `E_BUY_US` reste un rang percentile et non une probabilité calibrée.
