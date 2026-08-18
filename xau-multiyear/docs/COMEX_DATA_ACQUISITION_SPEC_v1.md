# XAUUSD Reaction Zone Research — COMEX Data Acquisition Spec v1

Date: 2026-08-18 UTC
Branch: `agent/xau-multiyear-research`
Status: specification only; no Databento market-data download authorized or performed.

## Decision

The previous universal tick window `contact -10 min / contact +15 min` is rejected.

It is too short before contact for the multiscale local-flow study, one minute too short for the maximum causal rejection/failed-auction confirmation encoded by the M1 engine, and it cannot by itself support COMEX-native session-profile zones such as session POC, VAH/VAL, HVN/LVN or exact session VWAP.

The acquisition must answer two different questions:

1. Does COMEX add incremental information to the already-defined XAUUSD POIs and entry models?
2. Do COMEX-native auction zones create useful POIs independently of the XAUUSD zones?

Sparse windows around existing XAUUSD contacts can answer question 1, but not question 2.

## Time convention

`t0` is the timestamp/start of the first XAUUSD M1 bar whose high/low intersects a known zone. It is not the exact intrabar contact timestamp.

Because the current XAUUSD contact engine is M1, no COMEX observation from inside the contact minute may be used to qualify a same-minute passive fill. A tick-precise passive-contact model requires XAUUSD tick/second data and a separate specification.

## Causal decision cutoffs in the current code

| Model | Existing rule | Latest decision/qualification time relative to `t0` | Latest possible fill/entry bar | COMEX predictor cutoff in v1 |
|---|---|---:|---:|---:|
| `PASSIVE_TOUCH` | centre limit may fill during contact bar through 15 following bars | before `t0` for a genuinely standing passive order | fill bar can close at `t0+16m` | strictly before `t0` |
| `TOUCH_NEXT_OPEN` | next active M1 open after the contact bar | contact-bar close, `t0+1m` | open can be delayed to about `t0+3m` | `t0+1m` |
| `CLEAN_REJECTION` | proximal reclaim before distal breach within the 15-minute classifier | close of actual reclaim bar; maximum `t0+16m` | next active open, maximum about `t0+18m` | actual reclaim-bar close |
| `FAILED_AUCTION` | distal breach then proximal reclaim within the 15-minute classifier | close of actual reclaim bar; maximum `t0+16m` | next active open, maximum about `t0+18m` | actual reclaim-bar close |
| `ACCEPTANCE_RETEST` | acceptance from five M1 bars, then a 30-bar limit-retest window | acceptance confirmation at `t0+5m` | final candidate fill bar can close at `t0+35m` | `t0+5m`; fill-time requalification is a different model |
| `RECLAIM_PULLBACK` | reclaim confirmation then a 15-bar pullback limit window | close of actual reclaim bar; maximum `t0+16m` | final candidate fill bar can close at `t0+31m` | actual reclaim-bar close; fill-time requalification is a different model |

The 120-minute Phase-C horizon is an outcome/TP-SL horizon after entry. It is not part of the initial COMEX predictor acquisition. Post-decision COMEX data may be acquired later only for a separately preregistered dynamic-exit study.

## Required data layers

### Layer A — complete low-cost GC context: indispensable

Request `GLBX.MDP3`, `GC.v.0`, `ohlcv-1m`, from the earliest available date through the final research date.

Use it for:

- GC price path and realized range/volatility;
- real total futures volume per minute;
- relative volume by minute of session using trailing historical baselines;
- session and multihorizon price/volume context;
- GC-XAUUSD basis and basis change at M1 resolution;
- roll detection through `instrument_id` changes.

Do not label M1-derived typical-price weighting as exact VWAP. OHLCV M1 cannot reconstruct exact volume-at-price, exact session VWAP, POC, VAH/VAL or HVN/LVN.

Known metadata quote at this checkpoint: approximately USD 20.34 for June 2010 through 17 August 2026. This is a quote, not authorization to download.

### Layer B — local COMEX time-and-sales around XAUUSD POIs: indispensable for the incremental-value question

Baseline local envelope for a selected event:

- start: `t0 - 30 minutes`;
- end: `t0 + 16 minutes` for the uniform auction-classification dataset.

The 30-minute pre-window supports nested 1/5/15/30-minute features. Longer context is supplied by Layer A. Session-long signed flow is not silently approximated from this local window.

For model-specific strategy qualification, a cheaper second request set may stop at each model's actual decision cutoff. It must not replace the uniform `-30/+16` dataset when comparing rejection, acceptance and unresolved events, because variable data availability tied to the observed behavior would create selection/missingness bias.

Features permitted from `trades`:

- total volume and trade count;
- buy/sell aggressor volume where `side` is populated;
- delta and normalized delta;
- local CVD from the beginning of the downloaded window;
- trade rate, average/quantile trade size and large-trade share;
- price movement per signed/total volume;
- a clearly named trade-only absorption proxy;
- local 30-minute volume-at-price, local POC/value area/HVN/LVN.

A local POC is not a session POC. A trade-only absorption proxy is not direct observation of resting-liquidity absorption.

### Layer C — complete-session trade panel: indispensable for the COMEX-native-zone question

Sparse POI windows cannot generate or evaluate independent COMEX-native zones. A preregistered, outcome-blind panel of complete GC sessions across all years/regimes is required to test:

- exact session VWAP;
- previous/current-session POC and VAH/VAL;
- session HVN/LVN and volume voids;
- session CVD;
- migration of value;
- subsequent retests of COMEX-derived zones, including cases where no existing XAUUSD POI was present.

The first panel must be selected across the full historical span by a fixed seed and temporal strata, not by choosing historically profitable years. Development, validation and locked test sessions must be assigned before COMEX outcomes are inspected.

The panel size is to be determined by power analysis and exact `metadata.get_cost()` results. A null result from Layer B must not be used to declare session-profile information useless if Layer C has not been tested.

### Layer D — top-of-book: optional second stage

Before requesting `mbp-1`, obtain free cost quotes for `tbbo`, `bbo-1s` and `mbp-1` on the same local windows.

`tbbo` is a candidate first upgrade because it contains every trade with the BBO immediately before the trade, including bid/ask sizes and order counts. If its premium over `trades` is modest, it may dominate trades for local spread and trade-time queue-imbalance research.

`mbp-1` is required for true top-of-book update-space features such as OFI, replenishment, withdrawal and quote-update dynamics. It is not required for the first volume/delta experiment.

### Layer E — full depth/MBO: not authorized in v1

MBO is excluded from the first acquisition. Adds, cancels, full-depth liquidity and queue-position work may be considered only if trades/TBBO/MBP-1 show stable incremental out-of-sample value.

## Family coverage

- Include all DOZ, objective-liquidity, MEMORY and their confluences in the event universe.
- Do not restrict the COMEX study to `DOZ_OBJECTIVE + CLEAN_REJECTION` or to previously surviving Phase-C cells.
- FVG-only events are too numerous for an all-event tick download. They must remain in the research through an outcome-blind stratified sample across year, session, side, volatility and FVG geometry. Sampling weights must be retained for population estimates.
- The complete M1 layer remains available for all FVG events.

## Feature availability and live reproducibility

| Feature | Minimum historical schema | Required history | Live-reproducible | v1 status |
|---|---|---|---|---|
| GC price/volume context, relative volume, basis | `ohlcv-1m` | full continuous history plus warm-up | yes | indispensable |
| local total volume/trade rate/size distribution | `trades` | `t0-30m` to decision | yes | indispensable |
| local aggressor delta/local CVD | `trades` | `t0-30m` to decision | yes, subject to side QA | indispensable experiment |
| exact local volume-at-price/local POC/VA | `trades` | local tick window | yes | indispensable experiment |
| exact session VWAP/session POC/VA/HVN/LVN | `trades` | session open to decision, plus complete prior sessions where used | yes | complete-session panel required |
| spread and BBO immediately before each trade | `tbbo` | local windows | yes | optional cost-compared upgrade |
| quote imbalance and OFI in update space | `mbp-1` | local windows | yes | optional stage 2 |
| full-depth adds/cancels/queue position | `mbo` | local windows or full sessions | yes but costly/complex | deferred |
| dynamic COMEX exit management | trades/TBBO/MBP as specified | decision through exit/horizon | yes | separate future phase |

## Continuous-contract and roll rules

Use `GC.v.0` only with its returned `instrument_id` and symbology mapping. Prices are unadjusted and the mapped contract changes with the volume-based rule. All basis, CVD, profile and session state must reset or split when the underlying instrument changes. Events crossing a roll mapping boundary must be flagged and excluded from pooled profile calculations unless the mapping logic explicitly handles them.

## Side and data-quality QA

Before modelling delta:

- measure the fraction of trade records with unspecified side by year and contract;
- verify the side convention in code and tests;
- inspect sequence gaps, duplicate records, trade corrections and mapping changes;
- compare OHLCV/volume reconstructed from downloaded trades against Databento OHLCV for the same windows;
- hash every raw DBN file and keep request/cost manifests.

If missing side is material, compare `tbbo` and/or derive a transparent classification from pre-trade BBO. Do not silently replace missing sides with tick-rule guesses.

## Statistical tasks

Keep two analyses separate:

1. Existing-POI incremental model: price-only baseline versus baseline plus COMEX feature groups, across every family and entry model.
2. COMEX-native-zone event study: zones constructed from complete-session trades and tested against matched controls.

Add feature groups sequentially: M1 context, local trades, complete-session profile, TBBO, MBP-1. A feature group is retained only for stable walk-forward/OOS incremental value after costs and calibration. A null result for one group does not eliminate untested groups or POI families.

## Acquisition/cost procedure — no download

1. Regenerate the full event table and export, for every event/model, `contact_time`, `decision_time`, `order_time`, `entry_time`, eligibility and family stack.
2. Freeze temporal splits and the FVG/session sampling seeds.
3. Build and merge the uniform local windows, model-specific cutoff windows and complete-session panel.
4. Produce a request-count/cost frontier using overlap-only and small-gap merge thresholds.
5. Call `metadata.get_cost()`, record count and billable size for `ohlcv-1m`, `trades`, `tbbo`, `bbo-1s`, `mbp-1`, definitions/status as applicable.
6. Publish exact cost manifests with `download_performed=false`.
7. Stop and request explicit user authorization before any market-data request.

## Current authorization state

No Databento market-data download is authorized by this specification. Metadata cost queries are permitted. The existing full-history quotes are informational only.
