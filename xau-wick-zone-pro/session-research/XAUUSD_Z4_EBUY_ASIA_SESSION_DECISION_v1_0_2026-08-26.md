# XAUUSD Z4 / E-BUY — Asia session decision v1.0

**Date:** 2026-08-26  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Study:** C5 Asia / OVERNIGHT `18:00–03:00 America/New_York`  
**Status:** `STOP_RETAIN_US_ONLY`  
**Production authorization:** NONE

## 1. Outcome-blind gate result

The preregistered Asia location/stability gate was run on the exact frozen Dukascopy BID source and the exact source-faithful C5 geometry used by current E-BUY evidence.

Result artifact run: `33018338282`  
Result status: `ASIA_C5_OUTCOME_BLIND_LOCATION_GATE_FAIL`.

### H1 — 2024-08-01 to 2025-08-01 UTC

- eligible snapshots: **19,998**
- Asia sessions: **256**
- mean displayed zones: **2.060956**
- median displayed zones: **2**
- p90 displayed zones: **3**
- coverage <=0.5v: **51.2251%**
- coverage <=1.0v: **78.5529%** — FAIL vs 80.00%
- coverage <=1.5v: **89.7290%** — FAIL vs 90.00%
- coverage <=2.0v: **94.6895%** — FAIL vs 95.00%
- nearest-zone median: **0.455406v**
- nearest-zone p90: **1.240139v** — PASS vs <=1.5v
- survival-aware display persistence: **97.9634%** — PASS vs >=70%
- unexplained disappearance share of survival-eligible transitions: **2.0366%** — PASS vs <=5%

H1 fails only the three preregistered coverage thresholds. The shortfalls are:

- <=1.0v: **-1.4471 percentage points**
- <=1.5v: **-0.2710 pp**
- <=2.0v: **-0.3105 pp**

### H2 — 2025-08-01 to 2026-08-01 UTC

- eligible snapshots: **21,392**
- Asia sessions: **258**
- mean displayed zones: **2.112706**
- median displayed zones: **2**
- p90 displayed zones: **3**
- coverage <=0.5v: **54.1698%**
- coverage <=1.0v: **80.4834%** — PASS
- coverage <=1.5v: **90.8798%** — PASS
- coverage <=2.0v: **95.6573%** — PASS
- nearest-zone median: **0.426230v**
- nearest-zone p90: **1.214118v** — PASS
- survival-aware display persistence: **98.0415%** — PASS
- unexplained disappearance share of survival-eligible transitions: **1.9585%** — PASS

H2 passes all eight preregistered location/stability checks.

## 2. Family mix

### H1 displayed zones
- ESM_BOTH_G120M: 17,682
- EWM_G60M: 10,007
- EPM_M1_R2_A8H: 6,910
- ES_M1_8H_R2_T0.50: 5,352
- Z4: 1,264

### H2 displayed zones
- ESM_BOTH_G120M: 19,156
- EWM_G60M: 11,329
- EPM_M1_R2_A8H: 7,339
- ES_M1_8H_R2_T0.50: 5,819
- Z4: 1,552

The architecture remains dominated by ESM/EWM during Asia, as in the intended fixed architecture; there is no evidence of pathological display churn.

## 3. Decision

The preregistration requires **all eight outcome-blind checks to pass in both H1 and H2** before opening the Asia BULL_REJECTION reaction study.

H1 does not pass the three coverage checks, even though the misses are small. Therefore:

- reaction study: **NOT AUTHORIZED under v1.0**;
- no BULL_REJECTION/TP1/invalidations are opened for this Asia v1.0 question;
- no current-US E score is transferred to Asia;
- no Pine scientific Asia signal is authorized;
- current scientific authorization remains **US-only**.

## 4. Interpretation

This is not a strong rejection of Asia. It is a **near-pass** of the current US-derived architecture:

- H2 passes every check;
- H1 stability is strong;
- H1 misses coverage by only 0.27–1.45 pp depending on the band;
- zone-count and distance constraints pass in both windows.

But the rule was frozen before results, so the correct v1.0 decision is still STOP.

A next Asia study, if pursued, must be preregistered separately and may investigate outcome-blind session-specific architecture or subperiod diagnostics. It must not retroactively relax the v1.0 thresholds or alter the Asia `18:00–03:00 NY` window merely to force a pass.
