# XAUUSD Z4 / E-BUY — Dukascopy Jetta M1 + FOREXCOM entry transfer v0.5

Date de gel : 2026-08-26
Branche : `agent/xau-wick-zone-pro-dev`

## Objet

Contourner uniquement l'indisponibilité HTTP partielle de l'ancien endpoint BI5 Dukascopy, sans changer l'identité du feed scientifique ni aucune règle de la couche d'entrée.

Dukascopy-node v1.50.0 utilise l'API Dukascopy actuelle `https://jetta.dukascopy.com/v1`. La v0.5 utilise cette API officielle, via la version npm figée `dukascopy-node@1.50.0`, pour récupérer XAUUSD M1 BID et ASK.

Aucun outcome futur de trading n'est consulté ou utilisé dans cette étape.

## Transport figé

- package : `dukascopy-node@1.50.0` ;
- instrument : `xauusd` ;
- timeframe : `m1` ;
- quote sides : BID et ASK séparément ;
- UTC offset : 0 ;
- `ignoreFlats: true` pour rester cohérent avec le dataset historique du projet ;
- aucun remplissage ajouté par notre code ;
- intersection BID/ASK exacte par timestamp ;
- MID = moyenne barwise BID/ASK, identique à la convention historique du projet.

## Stage A — QA Jetta vs miroir historique

Fenêtre figée : `2026-08-19T00:00:00Z <= t < 2026-08-21T00:00:00Z`.

Le script QA reste `xau_dukascopy_native_mirror_qa_v0_1.py` sans changement. Pour BID et ASK :

- common M1 >= 2000 ;
- mirror coverage >= 0.99 ;
- return Spearman >= 0.999 ;
- median absolute pooled OHLC error <= 0.005 ;
- p95 close error <= 0.01 ;
- p95 high error <= 0.02 ;
- p95 low error <= 0.02.

Stage B est interdit si Stage A échoue.

## Stage B — extension et transfert FOREXCOM

Uniquement si Stage A passe :

- récupérer Dukascopy Jetta sur la fenêtre complète de jours terminés `2026-08-16T00:00:00Z <= t < 2026-08-26T00:00:00Z` ;
- acquérir un snapshot exact TradingView `FOREXCOM:XAUUSD` M1 ;
- figer l'intersection exacte ;
- reconstruire Z4 C5 outcome-blind indépendamment sur Dukascopy BID, Dukascopy MID et FOREXCOM MID ;
- reconstruire E-BUY v0.4 sticky / armement / `BULL_REJECTION` / features ;
- appliquer le modèle figé `M1_LOGISTIC`, SHA-256 `ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342` ;
- exécuter byte-for-byte `xau_ebuy_forexcom_entry_transfer_v0_1.py`.

Toutes les gates v0.1 restent inchangées, notamment `common eligible C5 >= 250` pour BID vs FOREXCOM et MID vs FOREXCOM.

## Interdictions

Aucun MFE/MAE, TP outcome, P&L, coût, refit, nouveau feature, changement de trigger, remapping E, changement E80/E90, changement de comparator, baisse de seuil, sélection de fenêtre d'après un résultat futur.

## Décision

`ENTRY_TRANSFER_V05_PASS_OPERATIONAL` uniquement si Stage A passe et si le comparator entry-transfer inchangé retourne `ENTRY_TRANSFER_PILOT_PASS_OPERATIONAL`.

Un PASS autorise la promotion engineering vers Pine de la couche E-BUY / `BULL_REJECTION` / `E_BUY_US` sur `FOREXCOM:XAUUSD` M1. Il ne constitue pas une validation de performance future FOREXCOM ni une revendication de rentabilité live.
