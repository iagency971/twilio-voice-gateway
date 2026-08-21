# MNQ/NQ 12-Model — Official Databento CME Validation V1

Status before paid data request: `PREOUTCOME_FROZEN_AWAITING_COST_AUTHORIZATION`
Branch: `agent/mnq-databento-cme-validation-v1`

## Purpose
Replace the Yahoo/GetData proxy evidence with official Databento CME Globex `NQ.v.0` OHLCV-1m data while keeping the external 12-model ensemble completely unchanged.

The Databento API key exists as a GitHub Actions secret; its value is never printed or persisted.
A free metadata cost query estimated the requested Jun1-Aug20 historical range at **$0.294231325388**. No time-series data has been downloaded yet.

Because requesting time-series data can consume account credits or incur a charge, no data request may run until explicit user authorization is obtained after this protocol is committed.

## Frozen external model
Repository: `s-k-28/nq-es-trader-5k-payout`.
Pinned commit: `d472d6b442764c2adafbba4bbeb96881c100e3e0` (2026-05-31).
The public model architecture, parameters, conflict handling, entry logic, stops, targets, breakeven behavior, time stops and daily caps are unchanged.

No model removal, long/short filtering, threshold change, stop/target modification or date exclusion is allowed after CME outcomes are opened.

## Databento request
- dataset: `GLBX.MDP3`
- symbol: `NQ.v.0`
- input symbology: `continuous`
- schema: `ohlcv-1m`
- start: `2026-06-01T00:00:00Z`
- end: `2026-08-20T17:40:00Z` (exclusive/currently accessible window)

Convert Databento UTC event timestamps to America/New_York and then strip timezone for the pinned external engine.

## Data QA before economics
Required:
1. Request resolves `NQ.v.0` without partial-symbol error.
2. OHLCV rows are timestamp-unique after normalization.
3. No OHLC consistency violations (`low <= open/close <= high`).
4. All expected RTH trading dates Aug3-Aug19 have data.
5. Median number of RTH minute bars per complete trading day >= 380.
6. Price scale is plausible for NQ and no isolated roll jump is introduced within the continuous series.

If QA fails: `CME_DATA_QA_FAIL_NO_ECONOMIC_INTERPRETATION`.

## Daily context
Use the external repository's historical `NQ_daily.csv` through its available pre-period history; append RTH daily bars built directly from Databento Jun-Aug minute data and de-duplicate by date preferring Databento. Pass the combined daily file through the external system's public `--nq-daily` path.

## Execution and friction
Run the pinned external engine unchanged on the official Databento minute bars.
The external engine's `total_r` does not fully charge futures commissions and uses only a small adverse exit slip, so rescore every completed trade downward after the trade path is generated:
- PRIMARY: subtract additional **1.0 NQ point per round trip**.
- STRESS: subtract additional **2.0 NQ points per round trip**.
- Extra cost in R = `extra_points / (risk_ticks * 0.25)`.

No resimulation of fills is allowed during the rescore; only a deterministic cost subtraction.

## Confirmatory temporal holdout — PRIMARY EVIDENCE
Economic validation window: **2026-08-03 00:00 ET through 2026-08-19 23:59:59 ET**.
August 20 is excluded solely because the Databento historical availability cutoff at the time of the cost probe occurs before the full US session close.

This August window was selected for the Yahoo forward protocol before its economic outcomes were opened. The external strategy was frozen May31 and has not been modified based on August results. The Databento test is therefore a higher-quality cross-source remeasurement of the same temporally frozen forward window, not a newly selected profitable date range.

### August CME gates — all required
PRIMARY:
1. Data QA passes.
2. >= 25 completed trades.
3. >= 1.5 completed trades per observed Aug3-19 RTH trading day.
4. Mean net expectancy >= **+0.10R/trade**.
5. Profit factor >= **1.25**.
6. Aug3-11 aggregate net R > 0 AND Aug12-19 aggregate net R > 0.
7. Closed-trade max drawdown <= **7R**.
8. Remove best 10% of trades: remaining mean net expectancy >= 0.

STRESS:
9. Mean net expectancy > 0.
10. Profit factor >= **1.10**.

If all pass: `CME_AUGUST_CONFIRMATORY_PASS_FOR_PROPFIRM_SIMULATION`.
Otherwise: `CME_AUGUST_CONFIRMATORY_NO_GO`.

## Jun-Jul official CME — diagnostic only
Trades from Jun1-Jul31 may be reported to:
- compare official CME results with the already-seen GetData proxy screen;
- quantify source sensitivity;
- increase descriptive sample size for later risk simulation if the August gate passes.

Jun-Jul results may NOT rescue a failed August gate, may NOT be used to remove models, and may NOT alter the signal rules.

## Cross-source diagnostic
If the archived Yahoo August snapshot is available, compare Databento and Yahoo OHLC/trade outcomes as a diagnostic. Yahoo disagreement cannot change the official-CME verdict.

## Stage 2 after August CME PASS only
Simulate the fixed official-CME trade ledger against prop-firm rules using multiple sizing regimes (e.g. 0.25%, 0.50%, 0.75%, 1.00% equivalent risk budgets or MNQ/NQ contract counts), including:
- probability of reaching challenge target before max loss;
- daily loss-rule violations;
- max drawdown and losing streak distribution;
- days/trades to target;
- concentration and Monte Carlo/bootstrapped path analysis;
- separate evaluation vs funded sizing if rules differ.

No signal optimization is allowed in Stage 2; only risk/sizing policy is evaluated.
