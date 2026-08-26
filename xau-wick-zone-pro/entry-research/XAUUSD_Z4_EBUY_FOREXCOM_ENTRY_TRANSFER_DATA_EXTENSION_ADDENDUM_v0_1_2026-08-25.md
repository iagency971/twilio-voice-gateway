# XAUUSD Z4 / E-BUY — FOREXCOM Entry Transfer Data-Extension Addendum v0.1

Date de gel : 2026-08-25
Branche : `agent/xau-wick-zone-pro-dev`

## Objet

Le pilote entry-layer v0.1 s'est exécuté correctement mais a obtenu `232` snapshots C5 communs matures, sous la gate préenregistrée `>=250`. Toutes les autres gates location / trigger / score ont passé.

Cet addendum autorise UNE SEULE réparation : étendre l'intersection temporelle en réacquérant le mois courant Dukascopy avec exactement le même pipeline que le pilote Z4 FOREXCOM canonique.

## Acquisition Dukascopy figée

Commande identique au pilote Z4 FOREXCOM run `32845282794` :

`python xau-multiyear/scripts/acquire_dukascopy_window.py --from-month 2026-08 --to-month 2026-08 --out <snapshot>`

Source déclarée par le manifest canonique : `kevingtlin/dukascopy_XAUUSD_1m_Data`, BID+ASK, août 2026.

Le snapshot réacquis est archivé avec son SHA-256 avant interprétation du résultat.

## FOREXCOM

Réutiliser le snapshot exact déjà figé :

`xau-wick-zone-pro/feed-parity/forexcom-depth-test/FOREXCOM_XAUUSD_M1_depth_test.csv.gz`

Aucune nouvelle acquisition TradingView n'est autorisée dans cette extension.

## Invariants absolus

AUCUN changement de :

- architecture E-BUY ;
- top-3 sticky v0.4 ;
- définition `BULL_REJECTION` ;
- modèle `M1_LOGISTIC` ;
- SHA modèle `ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342` ;
- CDF H1 de `E_BUY_US` ;
- seuils E80/E90 ;
- règles d'appariement ;
- gates de parité ;
- gate `common eligible C5 >= 250`.

Interdiction de consulter MFE/MAE, TP, invalidation future, P&L ou tout outcome de trading pendant cette extension.

## Procédure

1. Réacquérir août 2026 avec la commande ci-dessus.
2. Enregistrer nombre de lignes, min/max timestamp et SHA-256.
3. Couper uniquement à l'intersection avec le snapshot FOREXCOM figé.
4. Si l'intersection ne permet toujours pas `>=250` C5 communs matures : STOP, le pilote reste FAIL pour taille insuffisante.
5. Si l'intersection est suffisante : reconstruire indépendamment Z4 + E-BUY pour BID, synthetic MID et FOREXCOM, puis rejouer exactement `xau_ebuy_forexcom_entry_transfer_v0_1.py` sans modification.

## Verdict

Le verdict du pilote initial n'est jamais réécrit. L'extension produit un verdict séparé :

- `ENTRY_TRANSFER_DATA_EXTENSION_PASS_OPERATIONAL`, si toutes les gates v0.1 inchangées passent ;
- `ENTRY_TRANSFER_DATA_EXTENSION_FAIL`, sinon.

Un PASS autorise la promotion engineering Pine M1 sur `FOREXCOM:XAUUSD`. Il ne constitue pas une nouvelle validation de performance future ni une validation P&L.
