# XAUUSD Z4 / E-BUY — Dukascopy native M1 recovery + FOREXCOM entry transfer v0.4

Date de gel : 2026-08-26
Branche : `agent/xau-wick-zone-pro-dev`

## 1. Motif

Les pilotes FOREXCOM E-BUY v0.1/v0.2 restent bloqués uniquement par `common eligible C5 = 232 < 250` parce que le miroir mensuel Dukascopy utilisé jusque-là s'arrête au 2026-08-20 23:58 UTC.

Le Stage A v0.3 a établi, sans outcome futur, que les minutes Dukascopy natives BI5 effectivement récupérées sont identiques au miroir sur BID et ASK (erreurs OHLC nulles sur la partie commune), mais la récupération par ticks horaires était incomplète et n'a couvert que 58.3 % de la fenêtre QA.

La v0.4 change uniquement le transport Dukascopy : elle utilise les chandelles M1 natives quotidiennes Dukascopy comme source prioritaire, avec ticks natifs uniquement comme fallback des minutes absentes. Aucun remplissage, aucune interpolation, aucun changement de modèle ou de seuil n'est autorisé.

## 2. Interdictions

Pendant v0.4 :

- aucun MFE/MAE ;
- aucun outcome TP / invalidation / P&L ;
- aucun spread/slippage/commission ;
- aucun refit ;
- aucun nouveau feature ;
- aucun changement du trigger `BULL_REJECTION` ;
- aucun remapping/recalibrage de `E_BUY_US` ;
- aucun changement des seuils E80/E90 ;
- aucun changement du comparator entry-transfer v0.1 ;
- aucun abaissement des gates de parité ou du minimum `common eligible C5 >= 250` ;
- aucune interpolation ou forward-fill des minutes Dukascopy manquantes.

## 3. Transport Dukascopy figé

Instrument : `XAUUSD`.

Prix : diviseur `1000`, déjà vérifié par la parité exacte du Stage A v0.3.

Source prioritaire par jour et par quote side :

- `BID_candles_min_1.bi5`
- `ASK_candles_min_1.bi5`

Format M1 : records BI5 24 octets big-endian, `seconds, open, close, low, high, volume`.

Fallback autorisé : ticks horaires natifs Dukascopy BI5 uniquement pour compléter des minutes absentes de la M1 directe. Les valeurs M1 directes ne sont jamais remplacées par le fallback quand elles existent. Aucun autre feed n'est autorisé à compléter Dukascopy.

Hosts autorisés : les deux endpoints publics Dukascopy déjà testés (`www.dukascopy.com/datafeed` et `datafeed.dukascopy.com/datafeed`). Le choix de host est un détail de transport et ne modifie pas l'identité du feed.

## 4. Stage A — QA native M1 vs miroir

Fenêtre figée avant exécution :

`2026-08-19 00:00:00 UTC <= t < 2026-08-21 00:00:00 UTC`.

Référence : miroir mensuel Dukascopy BID+ASK déjà utilisé dans le projet.

Candidat : reconstruction native M1 directe + fallback ticks ci-dessus.

Les checks restent EXACTEMENT ceux de `xau_dukascopy_native_mirror_qa_v0_1.py`, séparément pour BID et ASK :

- common M1 >= 2000 ;
- mirror coverage >= 0.99 ;
- return Spearman >= 0.999 ;
- median absolute pooled OHLC error <= 0.005 ;
- p95 close error <= 0.01 ;
- p95 high error <= 0.02 ;
- p95 low error <= 0.02.

Stage B est interdit si l'un des deux côtés BID/ASK échoue.

## 5. Stage B — extension et transfert FOREXCOM

Uniquement si Stage A passe :

1. acquérir Dukascopy natif M1 avec exactement le même moteur v0.4 sur `2026-08-16` → `2026-08-26` ;
2. acquérir un nouveau snapshot exact TradingView `FOREXCOM:XAUUSD` M1 ;
3. figer leur intersection temporelle exacte ;
4. reconstruire Z4 C5 indépendamment sur Dukascopy BID, Dukascopy MID et FOREXCOM MID ;
5. reconstruire E-BUY v0.4 sticky, armement, `BULL_REJECTION`, features et score avec les objets déjà figés ;
6. exécuter byte-for-byte le comparator `xau_ebuy_forexcom_entry_transfer_v0_1.py`.

## 6. Objects figés entry layer

E-BUY location : `Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`, display `v0.4 sticky top3`.

Trigger : `BULL_REJECTION`.

Score : modèle `M1_LOGISTIC` figé, SHA-256 :

`ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342`

Comparator entry transfer : aucune modification autorisée ; en particulier `common eligible C5 >= 250` reste obligatoire pour BID vs FOREXCOM ET MID vs FOREXCOM, avec toutes les autres gates location/trigger/score déjà prérégistrées en v0.1.

## 7. Décision

`ENTRY_TRANSFER_V04_PASS_OPERATIONAL` seulement si :

- Stage A = `DUKASCOPY_NATIVE_RECOVERY_PASS` sur BID ET ASK ;
- le comparator entry-transfer inchangé retourne `ENTRY_TRANSFER_PILOT_PASS_OPERATIONAL` ;
- aucune interdiction ci-dessus n'est violée.

Un PASS autorise uniquement la promotion engineering de la couche E-BUY / `BULL_REJECTION` / `E_BUY_US` vers Pine sur `FOREXCOM:XAUUSD` M1.

Sinon : `ENTRY_TRANSFER_V04_FAIL_NO_PINE_PROMOTION`.

## 8. Non-claims

Même en cas de PASS :

- aucune performance future FOREXCOM n'est validée par ce transfert outcome-blind ;
- aucune rentabilité live n'est revendiquée ;
- aucun coût de transaction n'est validé ;
- aucun higher-TF E-BUY n'est validé ;
- `E_BUY_US` reste un rang percentile relatif, pas une probabilité calibrée.
