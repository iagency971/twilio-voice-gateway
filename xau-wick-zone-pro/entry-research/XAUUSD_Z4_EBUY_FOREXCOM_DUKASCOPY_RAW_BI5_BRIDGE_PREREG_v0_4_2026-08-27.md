# XAUUSD Z4 / E-BUY — Dukascopy raw `.bi5` bridge + FOREXCOM entry transfer v0.4

Date de gel : 2026-08-27
Branche : `agent/xau-wick-zone-pro-dev`

## 1. Motif

Les pilotes entry-layer v0.1 / same-source restent formellement bloqués à 232 C5 communs car le miroir GitHub Dukascopy s'arrête au 2026-08-20 23:58 UTC. Toutes les autres gates de transfert passent.

Le transport `dukascopy-node@1.46.4` direct a été instable dans GitHub Actions, alors qu'un probe HTTP raw du 2026-08-27 a montré que les fichiers `.bi5` Dukascopy du 20 et du 21 août BID/ASK sont accessibles en HTTP 200 et identiques entre les routes `www.dukascopy.com/datafeed` et `datafeed.dukascopy.com/datafeed`.

Cette v0.4 ne modifie AUCUNE règle scientifique/entry-layer. Elle remplace uniquement le client réseau par un décodeur raw déterministe des mêmes fichiers Dukascopy.

## 2. Transport raw figé avant décodage

Source primaire :
`https://datafeed.dukascopy.com/datafeed/XAUUSD/YYYY/MM0/DD/{BID|ASK}_candles_min_1.bi5`

où `MM0 = mois calendrier - 1` (août = `07`).

Fallback transport autorisé uniquement en cas d'erreur réseau :
`https://www.dukascopy.com/datafeed/...`

Le probe préalable a montré des SHA-256 identiques entre ces routes pour les quatre objets de contrôle 2026-08-20/21 BID/ASK.

Fenêtre brute : `[2026-08-16T00:00:00Z, 2026-08-26T00:00:00Z)`.

## 3. Décodeur figé

- Décompression : `lzma.LZMADecompressor(FORMAT_AUTO)` / `lzma.decompress` compatible.
- Record candle : big endian `>IIIIIf`.
- Champs : `seconds_from_day_start, open_i, high_i, low_i, close_i, volume_f`.
- Timestamp UTC : `day_start_utc + seconds_from_day_start`.
- Échelle XAUUSD : `open/high/low/close = integer / 1000.0`.
- Une réponse vide / 404 de jour non coté est ignorée ; toute autre erreur persistante après retries fait échouer l'acquisition.
- Aucun remplissage artificiel de minute n'est autorisé.

## 4. Référence bridge immuable

`xau-wick-zone-pro/feed-parity/forexcom-transfer-pilot-v0-1/DUKASCOPY_XAUUSD_M1_overlap_snapshot.csv.gz`

Le bridge compare BID et ASK séparément sur l'intersection exacte avec cette archive.

## 5. Gate bridge — inchangée par rapport à v0.3

Pour BID ET ASK :

- timestamp coverage archive par direct >= 0.995 ;
- >= 5 000 timestamps communs ;
- Spearman des retours close >= 0.999 ;
- médiane erreur absolue open/high/low/close <= 0.001 USD pour chaque champ ;
- p99 erreur absolue open/high/low/close <= 0.01 USD pour chaque champ ;
- max erreur absolue open/high/low/close <= 0.05 USD pour chaque champ.

Une seule check false => `DUKASCOPY_RAW_BI5_BRIDGE_FAIL`, STOP avant tout comparator FOREXCOM.

## 6. Extension minimale

Après bridge PASS seulement :

- merger BID+ASK par inner join timestamp ;
- synthetic MID barwise = `(BID OHLC + ASK OHLC)/2` ;
- couper à l'intersection avec le snapshot FOREXCOM figé SHA-256 `d9505e23ac4c82e11a14f192629bbc24d6f38ddadbfc82f3ef2d60e67dc7d1f4` ;
- exiger >= 500 lignes M1 directes strictement après `2026-08-20 23:58:00Z` dans cette intersection.

Sinon STOP `DIRECT_EXTENSION_INSUFFICIENT`.

## 7. Entry-layer totalement figé

Aucun changement de :

- E-BUY : `Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50` ;
- v0.4 sticky top-3 ;
- trigger `BULL_REJECTION` ;
- modèle `M1_LOGISTIC` ;
- modèle SHA-256 `ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342` ;
- CDF H1 / mapping `E_BUY_US` ;
- comparator SHA-256 `f0ef3bed13d4dcd15ed56831c2befa413be5a63d9886c28073b652328548e483` ;
- règles d'appariement ;
- toutes les gates v0.1, notamment `common eligible C5 >= 250` pour BID et MID.

## 8. Interdictions

Toujours interdits pendant bridge/transfert : MFE, MAE, TP/invalidation future, P&L, coûts, refit, recalibration, remapping E, nouveau feature, changement trigger, changement de seuil ou choix de fenêtre basé sur les résultats.

## 9. Verdicts

- `DUKASCOPY_RAW_BI5_BRIDGE_FAIL_NO_ENTRY_TRANSFER`
- `ENTRY_TRANSFER_V0_4_FAIL_NO_PINE_PROMOTION`
- `ENTRY_TRANSFER_V0_4_PASS_OPERATIONAL`

Un PASS complet autorise uniquement la promotion engineering Pine M1 de E-BUY / BULL_REJECTION / E_BUY_US sur `FOREXCOM:XAUUSD`.

## 10. Non-claims

Même en cas de PASS : aucune validation de P&L FOREXCOM, aucun coût de transaction, aucun `R_US`, aucun E-BUY HTF ; `E_BUY_US` reste un rang percentile et non une probabilité calibrée.
