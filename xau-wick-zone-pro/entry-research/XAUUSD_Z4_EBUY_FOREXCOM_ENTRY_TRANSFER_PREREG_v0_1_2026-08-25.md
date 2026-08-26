# XAUUSD Z4 / E-BUY — FOREXCOM Entry-Layer Transfer Pilot v0.1

Date de gel : 2026-08-25
Branche : `agent/xau-wick-zone-pro-dev`

## 1. Objet

Tester, sans outcome futur, si la couche d'entrée BUY historiquement validée sur Dukascopy est transférable opérationnellement au flux exact TradingView `FOREXCOM:XAUUSD` M1.

Le pilote porte uniquement sur la représentation et l'exécution causale :

- carte E-BUY v0.4 sticky top-3 ;
- armement causal des zones ;
- trigger figé `BULL_REJECTION` ;
- features causales du score ;
- modèle figé `E_BUY_US` M1 Logistic ;
- mapping percentile/CDF H1 figé.

Il ne teste PAS la performance future sur FOREXCOM.

## 2. Interdictions

Pendant ce pilote :

- aucun MFE/MAE ;
- aucun TP hit / invalidation outcome ;
- aucun P&L ;
- aucun spread/slippage/commission ;
- aucun refit ;
- aucun nouveau feature ;
- aucun changement du trigger ;
- aucun remapping/recalibrage de `E_BUY_US` ;
- aucun changement des seuils E80/E90 ;
- aucune optimisation sur FOREXCOM.

## 3. Objets figés

### E-BUY location

Architecture :

`Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`

Display : `v0.4 sticky top3`.

### Trigger

`BULL_REJECTION`, sélectionné sur H1 uniquement avant ouverture H2.

### Score

Modèle : `M1_LOGISTIC`.

SHA-256 modèle :

`ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342`

`E_BUY_US` reste un rang percentile relatif, pas une probabilité calibrée.

## 4. Feeds

### Référence scientifique primaire

Dukascopy XAUUSD M1 **BID**, car c'est le type de feed utilisé pour le développement/validation historique de la couche entrée.

### Contrôle de sensibilité quote-basis

Dukascopy synthetic MID, calcul barwise depuis le snapshot BID/ASK déjà figé dans le pilote Z4 FOREXCOM.

### Cible opérationnelle

Flux exact TradingView `FOREXCOM:XAUUSD`, intervalle 1 minute, `bar_source=mid`, snapshot existant issu de `request_more_data`.

Aucune nouvelle source de données ne doit remplacer ces snapshots pendant le pilote.

## 5. Fenêtre

Intersection temporelle exacte des snapshots déjà figés Dukascopy / FOREXCOM.

L'évaluation ne commence qu'après :

1. 1440 M1 actives causales disponibles sur chaque feed ;
2. 96 landmarks C5 de warm-up après maturité 1440 ;
3. timestamps communs.

La session testée reste US : `08:00 <= America/New_York < 17:00`.

## 6. Reconstruction causale

Chaque feed est traité indépendamment :

1. reconstruction Z4 C5 outcome-blind ;
2. reconstruction E-BUY v0.4 depuis ses propres OHLC ;
3. armement et consommation des épisodes E-BUY ;
4. détection `BULL_REJECTION` ;
5. calcul des features disponibles au trigger ;
6. score brut avec le modèle figé ;
7. conversion en `E_BUY_US` avec la CDF H1 figée.

Aucune donnée du feed de référence n'est injectée dans la génération des zones ou du score du feed cible.

## 7. Appariement des cartes E-BUY

Comparaison uniquement sur C5 matures communs où les deux feeds ont une Z4 supérieure et sont donc éligibles au moteur BUY.

Les zones sont comparées relativement au close de leur propre feed. Un appariement candidat est admissible si les zones se chevauchent relativement ou si l'écart de centre est <= 0.75 v60. L'appariement final est un-à-un, coût minimal.

Mesures obligatoires :

- nombre de snapshots communs ;
- taux de zones appariées référence et cible ;
- IoU relatif ;
- erreur de centre relative / v60 ;
- accord du nombre de zones exact et à ±1 ;
- accord du slot nearest/top-1.

### Gates location

Pour BID vs FOREXCOM ET MID vs FOREXCOM :

- common eligible C5 >= 250 ;
- zone match rate référence >= 0.75 ;
- zone match rate cible >= 0.75 ;
- median relative IoU >= 0.60 ;
- median relative center error <= 0.35 v60 ;
- p90 relative center error <= 0.75 v60 ;
- exact candidate-count agreement >= 0.65 ;
- candidate-count agreement within 1 >= 0.90 ;
- nearest/top-1 agreement >= 0.70.

## 8. Appariement des triggers

Un trigger `BULL_REJECTION` de référence et un trigger cible sont appariables si :

- |temps trigger| <= 2 M1 ;
- les zones d'entrée relatives au close sont compatibles : overlap ou centre <= 0.75 v60.

Appariement un-à-un minimal en temps puis distance.

### Gates trigger

Pour BID vs FOREXCOM ET MID vs FOREXCOM :

- triggers référence >= 25 ;
- triggers cible >= 25 ;
- matched triggers >= 20 ;
- match rate référence >= 0.60 ;
- match rate cible >= 0.60 ;
- median |time delta| <= 1.0 min ;
- p90 |time delta| <= 2.0 min ;
- median relative entry-zone center error <= 0.50 v60.

## 9. Parité du score E_BUY_US

Sur triggers appariés uniquement :

- Spearman score brut >= 0.80 ;
- Spearman `E_BUY_US` >= 0.80 ;
- median |E_ref - E_target| <= 10 points ;
- part avec |ΔE| <= 15 >= 0.80.

Classification E80 : si l'union des cas E80 sur les deux feeds contient au moins 10 triggers, accord binaire E>=80 >= 0.75 ; sinon métrique descriptive seulement.

E90 reste descriptif dans ce petit pilote et ne peut pas, seul, faire échouer la gate.

## 10. Raw-feed sanity gates

Sur l'intersection raw :

- timestamp coverage target >= 0.97 ;
- return Spearman >= 0.95.

Ces gates sont reprises du pilote Z4 et doivent rester vraies.

## 11. Verdict

`ENTRY_TRANSFER_PILOT_PASS_OPERATIONAL` seulement si :

- aucune interdiction méthodologique n'est violée ;
- sanity raw passe pour BID et MID ;
- location passe pour BID et MID ;
- trigger passe pour BID et MID ;
- score passe pour BID et MID.

Sinon : `ENTRY_TRANSFER_PILOT_FAIL_NO_PINE_PROMOTION`.

Un PASS autorise uniquement la promotion engineering vers Pine/TradingView de la couche entrée sur `FOREXCOM:XAUUSD` M1.

## 12. Non-claims explicites

Même en cas de PASS :

- aucune performance de trading FOREXCOM n'est validée par ce pilote ;
- aucun coût de transaction n'est validé ;
- aucune rentabilité live n'est revendiquée ;
- aucun `R_US`/route model n'est validé ;
- aucun E-BUY M5/M15/M30/H1 n'est validé ;
- `E_BUY_US` n'est pas une probabilité calibrée.
