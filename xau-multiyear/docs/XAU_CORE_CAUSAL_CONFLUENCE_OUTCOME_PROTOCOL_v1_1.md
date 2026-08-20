# XAU CORE CAUSAL CONFLUENCE OUTCOME PROTOCOL v1.1

Date gelée : 2026-08-20  
Autorité : revue Pro finale, outcome-blind  
Décision : **A — AUTHORIZE_PNL_OPEN**  
Statut : **`CAUSAL_CORE_OUTCOME_V1_1_AUTHORIZED`**

## 1. Décision et portée

Le freeze causal des **498 événements** est accepté pour une ouverture économique unique.

Cette autorisation ne vaut ni validation live, ni autorisation de challenge prop firm, ni autorisation M5, COMEX, optimisation de paramètres ou sauvetage par sous-groupes.

Aucun TP, SL, exit, P&L, PF, winrate, drawdown, MFE ou MAE n'a été consulté pendant cette revue.

## 2. Correction pré-outcome de la V1

La V1 déposée dans le dépôt est supersédée **avant toute ouverture d'outcome** :

- protocole humain V1 : `9c7691c0de10784e87c411b8a28e3b081e9920818ba1edd5428024cb905a67af`
- protocole machine V1 : `112f25ed646ea9695e48268a08e87f74bea3c841b5f788f32a98371b74a86786`
- autorisation V1 : `7286b2151d38a1dfe8f179e5835204578a68bdaa8f7706b50a35539512effdbe`

Statut de la V1 :

`CAUSAL_CORE_OUTCOME_V1_SUPERSEDED_BEFORE_OUTCOME`

Motif matériel et unique : la V1 utilisait `sigma60` à l'entrée pour le buffer du stop. Or la règle historique et le protocole causal imposent le `sigma60` porté par l'ancre au **contact qui achève la confluence**. La V1.1 restaure cette règle sans modifier les 498 événements.

## 3. Binding pré-outcome immuable

- dépôt : `iagency971/twilio-voice-gateway`
- branche : `agent/xau-core-evidence-audit-v1`
- workflow : `32360173450`
- source commit : `106a0252e8292dd2dd690a7e336d9f493420ccc1`
- commit des artefacts du freeze : `b1882c5873c638cd1f5fb92ffcf7d42fe87f5e86`
- freeze manifest SHA-256 : `7a46a6847e8b574afa3576714349dbeaa8ec4d7ae2b1a39f4356a03e68fa4197`
- event manifest SHA-256 : `39ed2f7eac7465d46344bef85d64d3b897f0b56af66448e537fba1bfff315aeb`
- événements : **498**
- années actives : **15/15**
- côtés : **496 SAME_SIDE / 2 OPPOSITE_SIDE**

Toute divergence rend :

`CAUSAL_CORE_OUTCOME_V1_1_INVALID_BINDING_ABORT`

avant lecture de la première bougie post-entry.

## 4. Données et scénarios de coûts

Même input Dukascopy XAUUSD M1 BID/ASK, mêmes hashes annuels, sémantique `BAR_START_UTC`.

Le chemin économique utilise un overlay BID/ASK synthétique symétrique autour du mid. Le spread source n'est pas ajouté une seconde fois.

| Scénario | Rôle | Spread USD/oz | Commission RT / 100 oz |
|---|---|---:|---:|
| S10_C6 | sensibilité | 0,10 | 6 USD |
| S11_C6_PRIMARY | primaire | 0,11 | 6 USD |
| S12_C6 | sensibilité | 0,12 | 6 USD |
| S18_C9_STRESS | stress | 0,18 | 9 USD |

Aucun slippage supplémentaire en V1.1.

## 5. Entrée

Le `entry_time` gelé est autoritaire et ne peut pas être recherché à nouveau.

- ancre SUPPORT → LONG → entrée à l'ASK d'ouverture du scénario ;
- ancre RESISTANCE → SHORT → entrée au BID d'ouverture du scénario.

L'entrée doit correspondre exactement à la ligne gelée et disposer d'un `open_bid/open_ask` source valide. Une absence ou divergence est un hard fail ; l'événement ne peut pas être retardé ou supprimé.

## 6. Stop structurel et 1R — règle corrigée

Recalculer `robust_sigma60` sur l'input annuel hashé et prendre la valeur à :

`confluence_time / confluence_idx`

Cette valeur est le sigma porté par l'ancre au contact d'achèvement causal. **Le sigma à l'entry_time est interdit.**

Pour chaque scénario :

`buffer = max(2 × scenario_spread, 0.10 × sigma60_at_confluence)`

Géométrie unique :

- LONG : `stop = anchor_lower − buffer`
- SHORT : `stop = anchor_upper + buffer`

La géométrie de la paire n'est pas utilisée pour le stop. Aucun autre stop ne peut être comparé.

- LONG : `1R = entry − stop`
- SHORT : `1R = stop − entry`

Le risque doit être fini et strictement positif pour les 498 événements dans les quatre scénarios, sinon hard fail.

## 7. Cibles

Surface complète et indivisible :

`0.5 / 1.0 / 1.5 / 2.0 / 2.5 / 3.0`

- LONG : `target = entry + RR × risk`
- SHORT : `target = entry − RR × risk`

Même population dans toutes les cellules. Aucun meilleur RR ne peut devenir le primary après ouverture.

## 8. Horizon et ambiguïtés M1

Horizon exact : **120 minutes de temps écoulé**.

Bougies suivies :

`entry_time <= bar_start < entry_time + 120 minutes`

À l'échéance, sortie à la première quote exécutable à ou après `entry_time + 120 minutes`.

Règles :

1. gap adverse à l'open ;
2. touches SL/TP de la bougie ;
3. si SL et TP sont touchés dans la même M1, **SL gagne** ;
4. gap favorable au-delà du TP : exécution au TP, sans amélioration favorable.

La bougie d'entrée peut être utilisée intégralement puisque l'entrée est market-at-open.

## 9. Commission, gross R, net R et PF

Le spread est déjà inclus une seule fois dans les quotes du scénario.

`commission_R = commission_RT_USD / (100 × risk_price_USD_per_oz)`

- LONG : `gross_R = (exit − entry) / risk`
- SHORT : `gross_R = (entry − exit) / risk`
- `net_R = gross_R − commission_R`

PF :

`sum(net_R positifs) / abs(sum(net_R négatifs))`

## 10. Endpoint primaire

**`CAUSAL_CORE_RR_SURFACE_MEAN_NET_R`**

Scénario primaire : `S11_C6_PRIMARY`.

Pour chaque événement, moyenne arithmétique des six net-R ; puis moyenne arithmétique des **498 scores événementiels**.

La date de trading, définie par la coupure New York 17:00, est l'unité de dépendance du bootstrap. Le point estimate reste pondéré également par événement afin de conserver l'interprétation R/trade.

Bootstrap :

- 20 000 réplications ;
- seed `20260821` ;
- `NumPy default_rng / PCG64` ;
- grappes = dates de trading ;
- IC percentile 2,5 % / 97,5 %.

Bootstrap secondaire diagnostique : blocs circulaires de trois mois, 20 000 réplications, seed `20260822`.

## 11. Gates économiques irrévocables

### Gate A — Integrity

Tout doit être vrai : hashes exacts, N=498, IDs/lignes exacts, 15 hashes annuels exacts, même population toutes cellules, tous les compteurs causaux à zéro, shuffle PASS, hashes V1.1 exacts, aucune mutation.

### Gate B — Primary / broad RR

Sous `S11_C6_PRIMARY` :

- surface mean net R ≥ +0,10R ;
- borne basse bootstrap 95 % > 0 ;
- au moins 4 RR/6 avec mean net R ≥ +0,10R, PF ≥ 1,25 et borne basse > 0.

### Gate C — Stress

Sous `S18_C9_STRESS` :

- 6 RR/6 avec mean net R > 0 ;
- au moins 4 RR/6 avec PF ≥ 1,20 ;
- surface stress > 0.

### Gate D — Robustesse temporelle

RR1.5 et au moins 4 RR/6 doivent chacun satisfaire :

- 15/15 leave-one-year-out primary > 0 ;
- au moins 10/15 années positives primary ;
- au moins 8/15 années positives stress ;
- aucune année > 35 % de la contribution annuelle absolue, primary et stress.

### Gate E — Concentration

À RR1.5, primary et stress :

- retirer `ceil(N × 5 %)` meilleurs trades ;
- mean net R restant > 0 ;
- top 5 % ≤ 50 % du total de R positif.

### Gate F — Portefeuille une position

À RR1.5, ordre `entry_time → confluence_time → event_id` :

- conserver le premier trade ;
- ignorer toute entrée avec `entry_time <= active_exit_time` ;
- mean primary > 0 ;
- PF primary > 1,10 ;
- mean stress ≥ 0 ;
- aucune ambiguïté de séquencement.

## 12. Diagnostics obligatoires

Pour chaque scénario × RR : N, mean/sum net R, PF, TP/SL/TIME %, ambiguïté same-bar %, IC date-cluster.

À RR1.5 primary/stress : max drawdown R, longest losing streak, contribution top 1/5/10 %, résultat sans top 5 %, nombre sélectionné/écarté au replay une position.

Aucun seuil de drawdown ou série de pertes ne pourra être inventé après résultat.

## 13. Interdictions post-outcome

Un FAIL ne peut pas être sauvé par LONG/SHORT, SAME_SIDE, session, transition de session, M15/M30/H1, âge, variante DOZ, subtype Objective, RR, année, combinaison, autre stop, autre coût, autre horizon, autre entrée ou autre règle d'ambiguïté.

Les sous-groupes resteront exclusivement `HYPOTHESIS_GENERATION`.

## 14. Statuts terminaux

- autorisation : `CAUSAL_CORE_OUTCOME_V1_1_AUTHORIZED`
- échec binding : `CAUSAL_CORE_OUTCOME_V1_1_INVALID_BINDING_ABORT`
- toutes gates PASS : `CAUSAL_CORE_OUTCOME_V1_1_PASS_FOR_EXTERNAL_REPLICATION`
- au moins une gate économique FAIL : `CAUSAL_CORE_OUTCOME_V1_1_NO_GO`

Un PASS n'est pas live-ready. Un FAIL ferme ce core économique sur 2011–2025.

## 15. Ouverture unique

Une seule ouverture canonique est autorisée.

Un retry infrastructure n'est permis que si aucune bougie outcome n'a été lue et si tous les hashes/code sont identiques. Après lecture d'un outcome, seule une reproduction déterministe exacte est permise.
