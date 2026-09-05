# FTMO Zero-Paid-Data US100 — Adapted 12-Model Execution Filter V6

Status: `V6_PROTOCOL_FROZEN_BEFORE_MODEL_DIRECTION_SELECTION`

## Purpose

Adapt the already-profitable V5 native 12-model signal stream to improve edge-to-drawdown and FTMO challenge speed **without adding any paid external data or inventing new indicators/parameters**.

V5 direct native port produced a frozen final signal/trade stream from the original 12-model engine. V6 acts only as an execution acceptance layer: after the frozen engine has resolved model conflicts and emitted a final signal, V6 either accepts or declines that signal based on its frozen `model × direction` eligibility list.

This definition means V6 can be evaluated exactly by filtering the frozen V5 final trade ledger. Declining a signal does not resurrect any other signal suppressed earlier by the frozen engine.

## Immutable inputs

Frozen raw model engine:
- repo `s-k-28/nq-es-trader-5k-payout`
- commit `d472d6b442764c2adafbba4bbeb96881c100e3e0`

Free CFD data:
- repo `CodyOutcast/Academic-Paper-Data-Source`
- commit `50052606c16d71850755e6dbdda02d43b4399c2b`

Frozen V5 raw ledger SHA-256:
- `c2c705318ff19aee4fb1137b7ec2102e98a848b297701b334e1b777a0d5b7d31`

V6 uses the corrected V5.3 PRIMARY/STRESS rescoring and does not rerun the external 12-model engine.

No paid market-data feed is required in the proposed live architecture. The live input remains FTMO/MT5 `US100.cash` only.

## Partition

Selection/development: trades entered in **2021–2023 only**.

Validation: trades entered in **2024 plus Jan–Apr 2025**. No 2024/2025 model×direction statistic may be used in the selection rule.

Caveat: aggregate full-ensemble 2024/2025 performance was already observed in V5, so this is a model-selection quasi-holdout, not pristine OOS. A clean final proof must still be prospective FTMO Free Trial forward.

## Deterministic model × direction inclusion rule

For each finalized `model × direction` combo independently on 2021–2023 PRIMARY/STRESS, include the combo if **all** are true:
- `N >= 60`;
- PRIMARY expectancy `>= +0.10R/trade`;
- PRIMARY PF `>= 1.25`;
- PRIMARY max closed-trade DD `<= 12R`;
- PRIMARY total R positive in at least 2 of the 3 calendar years;
- worst calendar-year PRIMARY expectancy `>= -0.05R/trade`;
- STRESS expectancy `>= +0.07R/trade`;
- STRESS PF `>= 1.15`.

No ranking, manual exception, rescue inclusion or exclusion is permitted.

If no combos pass, V6 is `DEV_NO_GO` and stops.

## Development ensemble sanity gate

Filter the V5.3 2021–2023 ledger to the automatically included combos. Before opening validation combo outcomes, the selected DEV ensemble must satisfy:
- `N >= 1000`;
- `>= 2.0 trades per complete RTH day`;
- PRIMARY expectancy `>= +0.15R/trade`;
- PRIMARY PF `>= 1.35`;
- PRIMARY max DD `<= 12R`;
- all three DEV years total R positive;
- STRESS expectancy `>= +0.12R/trade` and PF `>= 1.25`.

If DEV sanity fails, V6 stops and validation model×direction outcomes remain uninterpreted.

## Validation gate — 2024 + Jan–Apr 2025

Apply the exact frozen allow-list to 2024 + Jan–Apr 2025 final signals. PASS requires all:
- `N >= 450`;
- `>= 2.0 trades per complete RTH day`;
- PRIMARY expectancy `>= +0.15R/trade`;
- PRIMARY PF `>= 1.35`;
- PRIMARY max DD `<= 10.5R`;
- 2024 total R > 0;
- Jan–Apr 2025 total R > 0;
- at least 70% of active validation calendar months have positive total R;
- STRESS expectancy `>= +0.12R/trade` and PF `>= 1.25`;
- worst validation calendar month loss no worse than `-8R`;
- no single positive validation month contributes more than 35% of total validation R.

## Challenge-speed rule

For the validation ensemble derive:

`SAFE_RISK = min(0.50%, 8% / (2.0 × validation_max_DD_R))`

`AGGRESSIVE_RISK = min(0.50%, 8% / (1.5 × validation_max_DD_R))`

A risk level is admissible only if the observed worst validation daily R × risk is <4% account loss.

Expected daily return = validation expectancy × validation trades/day × risk.

At least one admissible level must imply:
- theoretical Step 1 (+10%) `<= 45 trading days`;
- theoretical Step 2 (+5%) `<= 23 trading days`;
- combined `<= 68 trading days`.

These are expectation-based planning estimates, not guarantees.

## Result classification

If all validation and speed gates pass: `V6_NATIVE_ADAPTED_PROMISING_REQUIRES_FTMO_FORWARD`.

Otherwise: `V6_NATIVE_ADAPTED_NO_GO`.

Even a PASS is not LIVE_READY because the validation is not pristine; next evidence must be an unchanged prospective FTMO Free Trial forward using the native `US100.cash` feed.

## Prohibited after selection

No change to inclusion thresholds, no manual model/direction override, no RR/stop/time-window change, no new indicator, no model weighting, no day filter, no news filter, no spread filter, and no parameter search based on validation outcomes.