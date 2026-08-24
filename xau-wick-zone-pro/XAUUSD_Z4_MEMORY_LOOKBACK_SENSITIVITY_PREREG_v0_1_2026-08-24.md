# XAUUSD Z4 — Memory Lookback Sensitivity Prereg v0.1

**Freeze date:** 2026-08-24  
**Status:** FROZEN BEFORE MEMORY-SENSITIVITY DEV OUTCOMES  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Incumbent validated architecture:** Z4 with 1,440 active M1 memory  
**Scope of this gate:** DEV sensitivity only; no Validation/OOS read and no TradingView production change.

## 1. Question

Does the frozen Z4 revisit architecture materially depend on the historical memory length used to construct the wick-density field and `vseg`, and is the incumbent 1,440-active-M1 memory part of a broad robust plateau or an avoidable long-memory choice?

This is an architecture sensitivity study, not a new trading-strategy optimization.

## 2. External rationale, fixed before outcomes

Published support/resistance research on intraday data provides a legitimate reason to test memory length rather than assume one day is optimal. In particular, Chung & Bellotti (2021, arXiv:2101.07410) explicitly study sliding historical windows from 30 to 1,440 minutes and report decaying support/resistance interaction information as lookback grows in several settings. Garzarelli et al. (Scientific Reports 2014, doi:10.1038/srep04487) also report scale-dependent memory in support/resistance interactions.

These papers do **not** validate a specific XAUUSD revisit lookback and do not justify replacing Z4. They justify a preregistered sensitivity test.

## 3. Candidate memories — frozen

Primary candidate set, in active M1 bars:

- **L240** = 240
- **L360** = 360
- **L600** = 600
- **L900** = 900
- **L1440** = 1,440 — incumbent control

No other memory may be added after seeing DEV results in this gate.

### Why L60 is not included

The frozen Z4 engine uses a 240-observation minimum for the rolling segmentation-volatility estimator. Testing 60 would therefore require changing a second mechanic (`min_periods`) in addition to memory length. That would violate the one-factor sensitivity objective. L240 is the shortest clean candidate compatible with the frozen engine mechanics.

## 4. Exactly what changes

For candidate `L`, only the constant `LOOKBACK` changes from 1,440 to `L` in the frozen Z4 reference engine.

Consequently, by design:

- wick/body crossing field uses the last `L` active M1;
- rolling price range used for zone search uses the last `L` active M1;
- `vseg` is median True Range over the same `L` active M1, with the frozen minimum of 240 observations;
- bars enter/leave the density field according to `L`.

The candidate engine must be produced mechanically from the exact frozen Z4 engine blob `a8a147615c3fd366c49e93b340fd2018b5b66e9e` by a single literal replacement of `LOOKBACK=1440` with the candidate value. Any other code diff invalidates the run.

## 5. What remains frozen

Unchanged across every candidate:

- source: Dukascopy XAUUSD M1 mirror used by Z4;
- active-bar rule: `high > low`;
- price grid: 0.01 USD, absolute origin 0.00;
- exact Gaussian construction and scales: 0.25 / 0.50 / 1.00 × `vseg`;
- coarse family, best medium peak, nearby fine confirmation;
- medium prominence and P50 bounds;
- no Top N;
- 15-minute UTC landmark cadence;
- side eligibility rule: entire P50 zone must lie above or below current close by the frozen half-step margin;
- one-to-one lineage mechanics and gap termination;
- exact active-bar lineage age;
- endpoint: `REVISIT_240`;
- M0 and M0GL feature definitions;
- StandardScaler fit on training only;
- LogisticRegression C=0.10, lbfgs, max_iter=500, tol=1e-6;
- equal total weight per landmark;
- chronological folds APR / MAY / JUN / JUL 2024;
- no P&L, no stop, no target, no RR and no R threshold.

## 6. Data boundary — frozen

DEV only:

- January through July 2024;
- BID primary;
- ASK independent feed replication;
- exact source hashes must match `results/XAUUSD_Z4_DEV_SOURCE_MANIFEST_v0_1.json`.

No Aug-2024+ Validation/OOS result may be opened or used to choose a memory in this DEV gate.

## 7. Primary predictive metrics — frozen

For each memory and feed, report:

- fold-by-fold M0 vs M0GL ΔBrier for APR/MAY/JUN/JUL;
- fold-by-fold ΔLogLoss;
- pooled OOF M0 and M0GL Brier;
- pooled OOF ΔBrier;
- pooled OOF ΔLogLoss;
- weekly ΔBrier count and positive-week count;
- weekly block/bootstrap 95% interval for mean ΔBrier.

The central scientific quantity remains **incremental predictive information of Z4 geometry/lineage features over causal M0 within that same candidate architecture**, not raw Brier comparison between different zone populations.

Raw M0GL Brier across memories may be displayed but must not by itself determine a winner because the candidate memories produce different zone populations and base rates.

## 8. Outcome-blind geometry / stability diagnostics — frozen

For each candidate and feed, compute without using future outcomes:

- total zone snapshots;
- distinct landmarks represented;
- distinct lineages;
- zones per represented landmark: mean / median / p90 / p95 / max;
- lineage length in snapshots: mean / median / p90 / p95 / max;
- share of lineages lasting at least 2, 4 and 8 snapshots;
- one-step lineage continuation rate among snapshots with a later represented landmark;
- corresponding one-step drop/churn rate;
- median and p95 absolute center shift in `vseg` units where available;
- median and p95 absolute width log-change where available.

These diagnostics are secondary. Better visual stability cannot promote a candidate that loses the predictive signal.

## 9. DEV robustness flags — frozen

Each candidate receives two predeclared flags.

### `BID_ROBUST_PASS`
True only if:

1. all four BID fold ΔBrier values are > 0;
2. pooled BID ΔBrier > 0;
3. BID weekly bootstrap lower 95% bound > 0.

### `DUAL_FEED_STRONG_PASS`
True only if `BID_ROBUST_PASS` is true **and**:

1. all four ASK fold ΔBrier values are > 0;
2. pooled ASK ΔBrier > 0;
3. ASK weekly bootstrap lower 95% bound > 0.

These flags define robustness only. They do **not** select the final memory.

## 10. No winner selection in this run

This DEV run may produce a **shortlist for Pro review**, but must not declare a replacement for 1,440.

After results are available:

- report all five candidates, including failures;
- inspect whether performance forms a broad plateau or a sharp optimum;
- inspect stability/churn only after predictive robustness is known;
- then use a targeted Pro methodological gate to decide whether any memory deserves freezing for historical replication.

No candidate may be selected by silently dropping poor variants or by adding a new lookback after outcomes.

## 11. Production protection

Until a later decision gate explicitly authorizes otherwise:

- Z4/1,440 remains the validated scientific incumbent;
- current `R` semantics remain tied to the frozen 1,440 architecture;
- no Pine `VALIDATED_PROXY` may be relabeled to a different lookback;
- no user-facing production change is authorized by this DEV sensitivity run alone.
