# XAUUSD Z4 / E-BUY — Dukascopy Native Recovery + FOREXCOM Entry Transfer v0.3

Date de gel : 2026-08-25
Branche : `agent/xau-wick-zone-pro-dev`

## 1. Contexte et motif

Les pilotes entry-transfer v0.1 et v0.2 restent formellement FAIL uniquement parce que `common eligible C5 >= 250` n'est pas atteint : N=232. Les autres gates de location, trigger et score passent.

La collecte prospective v0.2 a montré que `FOREXCOM:XAUUSD` exact TradingView s'étend jusqu'au 26 août 2026, mais le miroir mensuel Dukascopy `kevingtlin/dukascopy_XAUUSD_1m_Data` utilisé par `acquire_dukascopy_window.py` reste arrêté au 20 août 23:58 UTC.

Cette v0.3 ne modifie aucun seuil de la couche entrée. Elle autorise conditionnellement l'utilisation du **feed natif public Dukascopy BI5** afin de récupérer les jours absents du miroir, seulement après une gate de parité feed-vs-mirror outcome-blind.

## 2. Stage A — Dukascopy native BI5 recovery QA

### Source native

Instrument : `XAUUSD`.

Transport : fichiers publics historiques Dukascopy `.bi5` LZMA, priorité au format horaire historique `datafeed/XAUUSD/YYYY/MM0/DD/HHh_ticks.bi5` ; mois zero-indexed. Chaque tick standard fait 20 bytes big-endian : ms offset, ask raw, bid raw, ask volume, bid volume. Pour XAUUSD, prix = raw / 1000.

### Reconstruction M1

- timestamps UTC ;
- BID M1 = first/max/min/last des ticks BID de chaque minute ;
- ASK M1 = first/max/min/last des ticks ASK de chaque minute ;
- aucune forward-fill ;
- synthetic MID barwise = `(BID OHLC + ASK OHLC)/2`, identique à la convention du pipeline existant ;
- minutes sans tick absentes.

### QA window

Parité mesurée sur 2026-08-19 et 2026-08-20, où le miroir mensuel et le natif doivent se chevaucher. Aucun signal E-BUY, trigger, score E, MFE/MAE, TP ou P&L n'est calculé dans Stage A.

### Gates Stage A, BID et ASK séparément

- native common M1 with mirror >= 2000 ;
- mirror timestamp coverage by native >= 0.99 ;
- close-return Spearman >= 0.999 ;
- median absolute OHLC error <= 0.005 USD ;
- p95 absolute close error <= 0.01 USD ;
- p95 absolute high error <= 0.02 USD ;
- p95 absolute low error <= 0.02 USD.

Stage A PASS seulement si toutes les gates BID et ASK passent.

## 3. Stage B — conditional entry-layer transfer

Stage B est interdit si Stage A FAIL.

Si Stage A PASS, reconstruire le snapshot Dukascopy natif BID+ASK sur la fenêtre nécessaire depuis le 16 août 2026 jusqu'au dernier bar natif disponible, et acquérir prospectivement le flux exact TradingView `FOREXCOM:XAUUSD` M1 `bar_source=mid`.

L'évaluation porte sur leur intersection temporelle exacte après les mêmes maturités :

1. 1440 M1 actives ;
2. 96 landmarks C5 de warm-up ;
3. timestamps communs ;
4. session US 08:00–17:00 America/New_York.

## 4. Objets entry-layer strictement figés

E-BUY : `Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`.

Display : v0.4 sticky top-3.

Trigger : `BULL_REJECTION`.

Score : `M1_LOGISTIC`.

Model SHA-256 : `ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342`.

CDF H1 et mapping `E_BUY_US` inchangés.

Comparator entry-layer : `xau_ebuy_forexcom_entry_transfer_v0_1.py`, seuils inchangés.

## 5. Gates Stage B — identiques à v0.1/v0.2

### Raw, BID et MID
- target timestamp coverage >= 0.97 ;
- return Spearman >= 0.95.

### Location, BID→FOREXCOM et MID→FOREXCOM
- common eligible C5 >= 250 ;
- zone match référence >=0.75 ; cible >=0.75 ;
- median relative IoU >=0.60 ;
- median center error <=0.35 v60 ; p90 <=0.75 v60 ;
- exact candidate-count agreement >=0.65 ;
- count within ±1 >=0.90 ;
- nearest/top1 agreement >=0.70.

### Trigger
- reference triggers >=25 ; target >=25 ; matched >=20 ;
- match rate reference >=0.60 ; target >=0.60 ;
- median time delta <=1m ; p90 <=2m ;
- median entry-zone center error <=0.50 v60.

### E_BUY_US
- raw-score Spearman >=0.80 ;
- E Spearman >=0.80 ;
- median |delta E| <=10 ;
- share |delta E|<=15 >=0.80 ;
- E80 binary agreement >=0.75 si union E80 >=10 ;
- E90 descriptif seulement.

## 6. Interdictions

Aucun MFE/MAE, aucun TP/invalidation futur, aucun P&L, aucun coût, aucun refit, aucun nouveau feature, aucun changement de trigger, aucun changement de CDF, aucun E remap, aucun abaissement de seuil, aucun choix de sous-fenêtre selon les métriques observées.

## 7. Verdict

- `DUKASCOPY_NATIVE_RECOVERY_FAIL` si Stage A échoue ; Stage B non exécuté.
- `ENTRY_TRANSFER_V03_FAIL_NO_PINE_PROMOTION` si Stage A passe mais une gate Stage B échoue.
- `ENTRY_TRANSFER_V03_PASS_OPERATIONAL` seulement si Stage A et toutes les gates Stage B passent.

Un PASS autorise uniquement le port engineering Pine M1 de la couche entrée sur `FOREXCOM:XAUUSD`.

## 8. Non-claims

Même en PASS : aucune performance future FOREXCOM, aucun P&L/coût live, aucun R_US route, aucun E-BUY HTF, et `E_BUY_US` reste un rang et non une probabilité calibrée.
