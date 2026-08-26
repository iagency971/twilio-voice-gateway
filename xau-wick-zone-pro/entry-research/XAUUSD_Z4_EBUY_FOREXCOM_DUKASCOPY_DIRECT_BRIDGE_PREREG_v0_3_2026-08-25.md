# XAUUSD Z4 / E-BUY — Dukascopy Direct Source Bridge + FOREXCOM Entry Transfer v0.3

Date de gel : 2026-08-25 / 2026-08-26 UTC
Branche : `agent/xau-wick-zone-pro-dev`

## 1. Motif

Le pilote entry-layer v0.1 et son extension same-source ont échoué uniquement sur `common eligible C5 >= 250` : 232 C5. Le miroir `kevingtlin/dukascopy_XAUUSD_1m_Data` est toujours arrêté au 2026-08-20 23:58 UTC et reproduit exactement l'archive précédente.

Aucun seuil n'est abaissé.

Cette v0.3 teste si les données **Dukascopy directes** peuvent servir de transport d'extension du même feed économique Dukascopy, après une gate de bridge stricte sur la période déjà archivée.

## 2. Transport direct figé

Bibliothèque : `dukascopy-node` version `1.46.4`.

Instrument : `xauusd`.

Timeframe : `m1`.

Price types : `bid` et `ask` séparément.

Fenêtre d'acquisition : `[2026-08-16T00:00:00Z, 2026-08-26T00:00:00Z)`.

Le transport direct n'est PAS autorisé à entrer dans le comparator avant d'avoir passé la gate de bridge ci-dessous.

## 3. Référence de bridge figée

Archive miroir déjà immuable :

`xau-wick-zone-pro/feed-parity/forexcom-transfer-pilot-v0-1/DUKASCOPY_XAUUSD_M1_overlap_snapshot.csv.gz`

Fenêtre de bridge : intersection exacte entre cette archive et le direct, donc au plus tard jusqu'au 2026-08-20 23:58 UTC.

Comparaisons BID et ASK séparées, sur OHLC M1.

## 4. Gate Dukascopy direct ↔ miroir

Pour BID **et** ASK, toutes les checks doivent passer :

- timestamp coverage de l'archive par le direct >= 0.995 ;
- au moins 5 000 timestamps communs ;
- return Spearman sur closes communs >= 0.999 ;
- médiane erreur absolue open/high/low/close <= 0.001 USD pour chaque champ ;
- p99 erreur absolue open/high/low/close <= 0.01 USD pour chaque champ ;
- max erreur absolue sur chacun des quatre champs <= 0.05 USD.

Si une seule check échoue : `DUKASCOPY_DIRECT_BRIDGE_FAIL`, STOP avant tout comparator entry-layer.

Ces seuils sont fixés avant acquisition directe.

## 5. Extension temporelle minimale

Si le bridge passe :

- fusionner BID et ASK direct par timestamp ;
- calculer synthetic MID barwise comme dans le pipeline historique ;
- couper à l'intersection avec le snapshot FOREXCOM **figé** SHA-256 `d9505e23ac4c82e11a14f192629bbc24d6f38ddadbfc82f3ef2d60e67dc7d1f4` ;
- exiger que le direct apporte au moins 500 lignes M1 supplémentaires strictement après `2026-08-20 23:58:00Z` dans cette intersection.

Sinon : STOP, échantillon insuffisant.

## 6. Objets scientifiques/engineering totalement figés

Aucun changement de :

- architecture E-BUY `Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50` ;
- v0.4 sticky top-3 ;
- trigger `BULL_REJECTION` ;
- modèle `M1_LOGISTIC` ;
- modèle SHA-256 `ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342` ;
- CDF H1 / features / E80 / E90 ;
- comparator SHA-256 `f0ef3bed13d4dcd15ed56831c2befa413be5a63d9886c28073b652328548e483` ;
- règles d'appariement ;
- toutes les gates v0.1, notamment `common eligible C5 >= 250`.

## 7. Comparator

Après PASS du bridge seulement, reconstruire indépendamment Z4 + E-BUY sur :

- Dukascopy direct BID ;
- Dukascopy direct synthetic MID ;
- snapshot FOREXCOM figé.

Puis rejouer **sans modification** :

`xau-wick-zone-pro/entry-research/xau_ebuy_forexcom_entry_transfer_v0_1.py`

## 8. Interdictions

Pendant bridge + transfert :

- aucun MFE/MAE ;
- aucun TP/invalidation futur ;
- aucun P&L ;
- aucun coût ;
- aucun refit ;
- aucun remapping E ;
- aucune recalibration ;
- aucun changement de fenêtre en fonction du résultat ;
- aucun assouplissement des seuils après acquisition.

## 9. Verdicts

- Bridge fail : `DUKASCOPY_DIRECT_BRIDGE_FAIL_NO_ENTRY_TRANSFER`.
- Bridge pass mais comparator fail : `ENTRY_TRANSFER_V0_3_FAIL_NO_PINE_PROMOTION`.
- Bridge pass + comparator complet pass avec >=250 C5 sur BID et MID : `ENTRY_TRANSFER_V0_3_PASS_OPERATIONAL`.

Un PASS autorise uniquement la promotion engineering Pine M1 de la couche E-BUY / BULL_REJECTION / E_BUY_US sur `FOREXCOM:XAUUSD`.

## 10. Non-claims

Même PASS : aucune validation de P&L FOREXCOM, aucun coût de transaction, aucun `R_US`, aucun E-BUY HTF, et `E_BUY_US` reste un rang et non une probabilité calibrée.
