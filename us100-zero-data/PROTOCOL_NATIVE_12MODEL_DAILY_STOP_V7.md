# FTMO Zero-Paid-Data US100 — 12-Model Daily Loss Stop V7

Status: `V7_PROTOCOL_FROZEN_BEFORE_DAILY_CAP_OUTCOMES`

## Objective

Preserve the profitable/high-frequency V5 native 12-model signal stream while reducing the 22R historical drawdown enough to make FTMO challenge sizing materially faster.

V7 changes **no model, signal, stop, target, direction, priority, feature or data source**. It adds only a prop-firm-style closed-P&L daily kill switch: once the day's cumulative realised R reaches or falls below the configured loss cap, all later finalized signals that day are declined.

No paid external market data is required. Live input remains native FTMO/MT5 `US100.cash` only.

## Immutable ledger

Use corrected V5.3 final trade ledger derived from frozen external commit `d472d6b442764c2adafbba4bbeb96881c100e3e0`.

Frozen raw ledger SHA-256: `c2c705318ff19aee4fb1137b7ec2102e98a848b297701b334e1b777a0d5b7d31`.

## Partition

DEV/select daily cap: entry years **2021–2023**.
Validation: **2024 + Jan–Apr 2025**.

Aggregate full-ensemble validation-period performance is already known from V5, so validation is a quasi-holdout for this previously unseen risk overlay. A clean final proof remains prospective FTMO forward.

## Predeclared cap candidates

Exactly four closed-P&L daily stop candidates:
- `-1.5R`
- `-2.0R`
- `-2.5R`
- `-3.0R`

For each date, process finalized trades chronologically. A trade is accepted if the cumulative realised R before that trade is above the cap. After an accepted trade closes, update cumulative R. If cumulative R is now <= cap, decline every later signal that calendar date.

The cap is not an intratrade hard stop: the trade that crosses the cap is allowed to close normally, so realised daily loss may overshoot the nominal cap.

PRIMARY and STRESS are simulated independently using their own realised R stream, because under worse execution costs the live daily kill switch would itself trigger from the worse realised P&L.

## DEV candidate gate

For each cap on 2021–2023, require PRIMARY:
- N >= 1800;
- >= 2.4 trades per complete RTH day;
- expectancy >= +0.16R/trade;
- PF >= 1.40;
- max DD <= 13R;
- all three calendar years total R > 0;

and STRESS:
- expectancy >= +0.13R/trade;
- PF >= 1.30;
- max DD <= 15R.

If none pass, V7 stops `DEV_NO_GO` and validation cap outcomes are not interpreted.

If multiple pass, freeze exactly one by deterministic hierarchy:
1. highest DEV PRIMARY R per complete RTH day (`total_R / sessions`);
2. tie: lower PRIMARY max DD;
3. tie: looser cap (more negative) to minimize intervention.

No manual choice.

## Validation gate

Apply only the frozen selected cap to 2024 + Jan–Apr 2025. Require:
- N >= 650;
- >= 2.4 trades per complete RTH day;
- PRIMARY expectancy >= +0.16R/trade;
- PRIMARY PF >= 1.40;
- PRIMARY max DD <= 10.7R;
- 2024 total R > 0 and Jan–Apr 2025 total R > 0;
- >=70% of active validation months positive;
- worst validation month >= -8R;
- STRESS expectancy >= +0.13R/trade;
- STRESS PF >= 1.30;
- STRESS max DD <= 12.5R.

## Challenge-speed gate

From validation PRIMARY max DD derive:
- SAFE risk = min(0.50%, 8% / (2 × DD_R));
- AGGRESSIVE risk = min(0.50%, 8% / (1.5 × DD_R)).

A risk level is admissible only if observed worst validation daily R × risk <4% account loss.

Use actual validation `R per complete RTH day` after the daily cap, not simply raw trades/day × raw expectancy.

At least one admissible level must imply:
- Step 1 (+10%) <=45 trading days;
- Step 2 (+5%) <=23 trading days;
- combined <=68 trading days.

## Classification

PASS: `V7_DAILY_STOP_PROMISING_REQUIRES_FTMO_FORWARD`.
FAIL: `V7_DAILY_STOP_NO_GO`.

No post-result cap adjustment, model filtering, day filter or parameter rescue is allowed inside V7.