# FTMO Zero-Paid-Data US100 — 12-Model Drawdown Throttle V8

Status: `V8_PROTOCOL_FROZEN_BEFORE_THROTTLE_OUTCOMES`

## Objective

Preserve the full high-frequency V5 native 12-model signal stream while reducing dollar/effective-R drawdown through dynamic position-size throttling based only on the strategy's own realised equity drawdown.

No model, signal, indicator, stop, target, direction, time window or data source changes. No paid external market data is required; live input remains FTMO/MT5 `US100.cash` only.

Frozen raw ledger SHA-256: `c2c705318ff19aee4fb1137b7ec2102e98a848b297701b334e1b777a0d5b7d31`.

## Partition

DEV/select throttle policy: entry years **2021–2023**.
Validation: **2024 + Jan–Apr 2025**.

Aggregate validation-period full-ensemble performance is already known from V5. V8 validation is therefore a quasi-holdout for an unseen sizing overlay; final proof must remain prospective FTMO Free Trial.

## Mechanism

Process final V5.3 trades chronologically. Track cumulative realised weighted R and its running peak. Before each trade, calculate current weighted drawdown from the running peak. The trade's intended risk is multiplied by the policy's current scale, and realised trade R is multiplied by that same scale.

PRIMARY and STRESS are simulated independently because actual realised P&L controls live drawdown state.

The throttle never increases a trade above 1.0× base risk and never changes the trade's market levels.

## Predeclared policies

Exactly three policies:

### T3_6
- DD < 3R: scale 1.00
- 3R <= DD < 6R: scale 0.50
- DD >= 6R: scale 0.25

### T4_8
- DD < 4R: scale 1.00
- 4R <= DD < 8R: scale 0.50
- DD >= 8R: scale 0.25

### T5_10
- DD < 5R: scale 1.00
- 5R <= DD < 10R: scale 0.50
- DD >= 10R: scale 0.25

No other thresholds/scales may be tried inside V8.

## DEV gate

For each policy on 2021–2023 PRIMARY require:
- all raw signals retained (same trade count as V5 DEV);
- weighted R per complete RTH day >= +0.43R;
- weighted PF >= 1.38;
- weighted max DD <= 11.0R;
- all three DEV calendar years weighted total R > 0.

STRESS require:
- weighted R per complete RTH day >= +0.37R;
- PF >= 1.28;
- max DD <= 12.5R.

If none pass, V8 stops and validation throttle outcomes are not interpreted.

If multiple pass, select deterministically:
1. highest PRIMARY weighted R per complete RTH day;
2. tie: lower PRIMARY max DD;
3. tie: least intervention (`T5_10` preferred to `T4_8`, preferred to `T3_6`).

## Validation gate

Apply exactly the selected policy to 2024 + Jan–Apr 2025. Require:
- weighted PRIMARY R per complete RTH day >= +0.44R;
- PRIMARY PF >= 1.40;
- PRIMARY max DD <= 10.7R;
- 2024 weighted total R > 0;
- Jan–Apr 2025 weighted total R > 0;
- >=70% of active validation months weighted total R > 0;
- worst validation month >= -8 weighted R;
- STRESS weighted R per complete RTH day >= +0.38R;
- STRESS PF >= 1.30;
- STRESS max DD <= 12.0R.

## Challenge-speed gate

Base risk is the risk used when scale=1.0. Actual trade risk is `base risk × throttle scale`.

From validation PRIMARY weighted max DD:
- SAFE base risk = min(0.50%, 8% / (2 × weighted_DD_R));
- AGGRESSIVE base risk = min(0.50%, 8% / (1.5 × weighted_DD_R)).

A level is admissible only if observed worst weighted validation daily R × base risk <4% account loss.

Expected account return per day = validation weighted R/day × base risk.

At least one admissible level must imply:
- Step 1 (+10%) <=45 trading days;
- Step 2 (+5%) <=23 trading days;
- combined <=68 trading days.

## Classification

PASS: `V8_DD_THROTTLE_PROMISING_REQUIRES_FTMO_FORWARD`.
FAIL: `V8_DD_THROTTLE_NO_GO`.

No post-result threshold change, scale change, model filtering, or parameter rescue is allowed inside V8.