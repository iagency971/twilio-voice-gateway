# XAUUSD Z4 — C5 Promotion Decision

**Date:** 2026-08-25  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Status:** C5 SCIENTIFIC + PYTHON ENGINEERING PASS / TRADINGVIEW RUNTIME QA STILL REQUIRED

## Decision

The preregistered cadence study and subsequent targeted Pro gate authorize **C5 (5-minute scientific snapshots)** as the replacement candidate for the validated C15 incumbent.

This is not a post-hoc choice. C5 was frozen as the primary candidate before cadence-specific Aug-2024→Jul-2026 historical replication outcomes were opened. C1 remains a sensitivity result and is not a rescue branch.

The memory choice remains **LOOKBACK = 1440 active M1**. The prediction endpoint remains **REVISIT_240 active M1**. No reaction, reversal, SL/TP, RR or profitability claim is added.

## Historical replication — PASS

Frozen full-DEV C5 M0/M0GL parameters were fit on Jan-Jul 2024 before H1/H2 scoring.

### BID primary

- H1 2024-08-01→2025-08-01: ΔBrier +0.0023430074; ΔLogLoss +0.0073704307; weekly bootstrap 95% CI [+0.0015754862, +0.0031830433].
- H2 2025-08-01→2026-08-01: ΔBrier +0.0124078110; ΔLogLoss +0.0426264414; weekly bootstrap 95% CI [+0.0102328671, +0.0144924768].

### ASK support

- H1: ΔBrier +0.0020965279; ΔLogLoss +0.0068000311.
- H2: ΔBrier +0.0123195408; ΔLogLoss +0.0427214018.

`C5_HISTORICAL_REPLICATION_PASS = true`.

These are historical temporal replications of a cadence hypothesis formulated after the original C15 history was already known; they are not relabeled as pristine new holdouts.

## Geometry provenance

C1/C15 same-run geometry QA passed exactly at common 15-minute timestamps on BID and ASK. This closed the earlier byte-hash ambiguity and confirmed that changing snapshot cadence does not alter frozen detector geometry at identical timestamps.

C5 common-anchor geometry parity against C15 had already passed before C5 historical replication.

## C5 engineering gate — PASS

C5 DEV BID reconstruction is exact against the frozen provenance:

- rows: 267,059;
- landmarks: 41,110;
- cadence: 5 minutes;
- lookback: 1440 active M1;
- grid proxy: 0.05 USD;
- model: C5-specific frozen BID M0GL;
- score map: C5-specific DEV equal-landmark-weighted percentile map.

### Warm-up / cold-start

Preregistered candidates: 96, 192, 288, 384, 480, 576 C5 landmarks.

The frozen rule selects the smallest candidate passing every criterion. **96 C5 landmarks passes and is selected.**

At cap 96:

- Pearson 0.9996221;
- Spearman 0.9996974;
- median raw-score error 0;
- p95 raw-score error 0.0162869;
- share |error| > 0.05 = 0.478%;
- within-landmark median Spearman 1.0;
- top-1 agreement 99.518%;
- top-3 Jaccard 99.483%.

The vectorized implementation was checked against the original cold-start algorithm on 750 landmarks with tolerance 1e-12 and passed.

### Greedy lineage

C5 deterministic greedy lineage parity passes the pre-existing strict lineage criteria. No Hungarian solver is required in Pine.

### Combined Pine-math proxy

The C5 combined proxy (0.05 grid + 3-box smoothing + explicit Pine peaks/P50 + greedy lineage + selected cold-start handling) passes.

Published C5 metrics:

- exact zone match 92.312%;
- proxy zone match 98.807%;
- median IoU 0.973891;
- p10 IoU 0.906393;
- median center error 0.038095 vseg;
- p95 center error 0.178571 vseg;
- score Pearson 0.997385;
- score Spearman 0.998329;
- median raw-score error 0.003383;
- p95 raw-score error 0.038428;
- top-1 zone agreement 87.349%.

A separate attestation applies the **original stricter C15 authorization thresholds** unchanged. Every strict criterion passes. The earlier GitHub Actions run named `XAU Z4 C5 Strict Combined Attestation v0.1` failed only in its waiting/orchestration step before the C5 artifact existed; the scientific strict gate was never executed in that failed run. The direct immutable attestation supersedes interpreting that workflow failure as scientific evidence.

### R display parity

C5 uses a new DEV-only percentile map; the C15 R thresholds are not reused.

R display parity passes:

- median |ΔR_float| 0.431;
- p95 |ΔR_float| 3.714;
- median displayed integer difference 1 point;
- p95 displayed difference 4 points;
- 90.54% within ±2 displayed points;
- 97.70% within ±5 displayed points;
- R Spearman 0.998329;
- matched top-1 agreement 97.014%.

`R` remains a percentile/rank of revisit likelihood. It is **not a probability**, reaction strength or support/resistance strength.

## Production decision

### Authorized now

C5 is authorized as the **scientifically selected production-replacement candidate** and as a Python/Pine-math validated proxy architecture.

### Not yet authorized automatically

Do **not** relabel an uncompiled Pine file `VALIDATED_PROXY` merely from Python evidence.

The last known repaired TradingView source is:

- `XAUUSD_Z4_Revisit_Score_QA_v2_1_0_M1_QA_PROXY.pine`
- SHA-256 `6d5480368a0c3b5ab0480e73afd6a34199806ca05a62b37683847ffc00406144`

A C5 Pine candidate must be derived from that repaired v2.1.0, changing only the cadence/model/map elements required by this decision while retaining the repaired confirmed-bar, side, overlap exclusion, GRID_LIMIT recovery and Class-A UI behavior.

Until TradingView compile/replay/live-close QA of that C5 source passes, **C15 remains the operational incumbent** and the C5 Pine stays `QA_PROXY`.

## Mandatory TradingView runtime gate for C5 Pine

1. compile in Pine v6 with no errors;
2. M1-only behavior;
3. confirmed-bar update only (`barstate.isconfirmed`);
4. snapshots only at confirmed 5-minute boundaries;
5. Replay across consecutive 5-minute snapshots: no intra-landmark repaint of the frozen snapshot;
6. verify zone DROP/appearance behavior across snapshots;
7. trigger/check GRID_LIMIT fail-closed reset and 96-landmark re-arm where practicable;
8. confirm R remains unavailable during data/lineage warm-up;
9. confirm Class-A drawing changes do not alter snapshot geometry or score;
10. record Pine source SHA and static manifest before any `VALIDATED_PROXY` label.

## Cross-feed limitation

Primary science remains Dukascopy XAUUSD BID. TradingView `FOREXCOM:XAUUSD` remains a **transfer assumption, not validated feed parity**. Passing Pine runtime QA does not validate FOREXCOM transfer.

## Final scope

- Z4 C5 `P_REVISIT_240`: GO within the documented Dukascopy M1 scope.
- LOOKBACK 1440: retained.
- C5 cadence: selected replacement candidate.
- C1: sensitivity only; no post-hoc rescue use.
- R C5: GO as rank only, using C5-specific map.
- P_REACTION / reversal: NO-GO.
- higher TF R: not validated.
- BODY variants: not validated.
- MEMORY after DROP: experimental/preregistration required.
- FOREXCOM: transfer assumption only.
