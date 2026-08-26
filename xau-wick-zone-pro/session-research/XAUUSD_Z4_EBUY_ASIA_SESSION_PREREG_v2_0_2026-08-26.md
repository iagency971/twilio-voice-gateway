# XAUUSD Z4 / E-BUY — Asia session architecture preregistration v2.0

**Frozen:** 2026-08-26, after Asia v1 location/stability near-fail and before any Asia v2 architecture result or any Asia reaction result is generated or inspected.  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Scope:** BUY-only, C5, Asia/OVERNIGHT `18:00–03:00 America/New_York`, retrospective outcome-blind architecture development.  
**Production authorization:** NONE.

## 1. Motivation

Asia v1 kept the current US-derived architecture unchanged and produced a near-pass: H2 passed all eight location/stability gates; H1 failed only the three coverage thresholds by 0.27–1.45 percentage points. No Asia reaction outcome was opened.

v2 does **not** relax any v1 threshold and does **not** move the Asia time window. It asks whether an already-defined pre-existing outcome-blind E-BUY architecture from the historical v0.3 grid transfers more robustly to Asia.

## 2. Frozen population and state

Unchanged from Asia v1:
- Asia session: `18:00–03:00 America/New_York`;
- cadence: C5;
- source: exact frozen Dukascopy BID manifest/hashes;
- source-faithful C5 Z4 geometry;
- H1: `2024-08-01 <= t < 2025-08-01 UTC`;
- H2: `2025-08-01 <= t < 2026-08-01 UTC`;
- mature warm-up: 96 C5 landmarks;
- top-3 displayed BUY zones;
- local band `0 < distance <= 2.0v`;
- sticky carry rules from E-BUY v0.4;
- cross-family de-duplication `0.20v`;
- Z4 priority on overlap;
- no future outcome information and no E score.

## 3. Candidate generator set — no new parameter values

Reuse only the outcome-blind family/configuration grid already frozen in E-BUY coverage v0.3 before this Asia study:

### ESM grid
Nine existing E-STRUCTURE-MEMORY configurations:
- observation mode in `{LOW, BODYLOW, BOTH}`;
- grace in `{30, 60, 120}` minutes;
- structural windows remain `{5,10,20,40}` active M1;
- all ESM geometry/matching/invalidation rules remain unchanged.

### Fixed prior families
- EPM = `EPM_M1_R2_A8H`;
- EWM = `EWM_G60M` using frozen `EW_M1_8H_S0.25` detector;
- ESWING = `ES_M1_8H_R2_T0.50`;
- Z4 below = unchanged.

No new family, timeframe, grace, smoothing, distance, de-duplication or memory parameter may be introduced.

## 4. Frozen architecture matrix

For each of the nine ESM configurations, evaluate exactly these five pre-existing architecture shapes using the v0.4 sticky display:

1. `Z4 + ESM`;
2. `Z4 + ESM + EPM`;
3. `Z4 + ESM + EWM`;
4. `Z4 + ESM + EPM + EWM`;
5. `Z4 + ESM + EPM + EWM + ESWING`.

Total candidate count = **45**. The current v1 architecture is one member of this matrix: `Z4 + ESM_BOTH_G120M + EPM + EWM + ESWING`.

## 5. Outcome-blind gate — unchanged thresholds

For every candidate, compute H1 and H2 separately. PASS requires all eight checks in **both** windows:

1. coverage <=1.0v >= 0.80;
2. coverage <=1.5v >= 0.90;
3. coverage <=2.0v >= 0.95;
4. displayed-zone count median between 1 and 3;
5. displayed-zone count p90 <=3;
6. nearest-zone distance p90 <=1.5v;
7. survival-aware display persistence >=0.70;
8. unexplained disappearance share of survival-eligible transitions <=0.05.

Raw persistence, family mix, mean zone count, crossed-below/no-longer-local/hidden-underlying shares and runtime are reported but are not new selection thresholds.

## 6. Deterministic selection among robust passers

A candidate is eligible for selection only if it passes all eight checks in both H1 and H2.

Among eligible candidates select deterministically by:

1. **fewest supplemental families beyond Z4** (`ESM`=1; `ESM+EPM` or `ESM+EWM`=2; `ESM+EPM+EWM`=3; full=4);
2. highest worst-window coverage <=1.0v;
3. highest worst-window coverage <=1.5v;
4. highest worst-window survival-aware persistence;
5. lowest worst-window nearest-zone p90;
6. deterministic architecture ID.

This ordering is frozen before v2 results.

## 7. Asia subperiod diagnostics

For the selected candidate only, report outcome-blind diagnostics for:
- `ASIA_EARLY`: 18:00–21:00 NY;
- `ASIA_LATE_PRE_MIDNIGHT`: 21:00–00:00 NY;
- `ASIA_POST_MIDNIGHT`: 00:00–03:00 NY.

Subperiods are diagnostic only and cannot rescue a whole-session candidate that fails the H1/H2 gate. The session window remains 18:00–03:00.

## 8. Reaction authorization

If and only if at least one candidate passes both H1 and H2 and a deterministic selected candidate exists, freeze its candidate table and authorize the already-preregistered Asia BULL_REJECTION reaction semantics as a separate step.

If no candidate passes both windows, stop and retain scientific US-only authorization. Do not open Asia BULL_REJECTION/TP1/invalidation outcomes.

## 9. Nonclaims

Even a v2 PASS is retrospective architecture development. It does not validate the US E score on Asia, profitability, spread/slippage robustness, production Pine activation, or prospective statistical validity.