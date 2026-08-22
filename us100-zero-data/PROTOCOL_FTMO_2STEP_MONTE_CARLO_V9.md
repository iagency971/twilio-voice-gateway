# FTMO Zero-Paid-Data US100 — 2-Step Monte Carlo Sizing V9

Status: `V9_PROTOCOL_FROZEN_BEFORE_MONTE_CARLO_OUTCOMES`

## Purpose

Determine whether the unchanged V5.3 native US100 12-model strategy can pass an FTMO 10k 2-Step Challenge fast enough by using a more aggressive but explicit fixed risk per trade, instead of adding more strategy filters.

No strategy parameter, signal, model, stop or data source is changed. No paid external market data is required.

## FTMO 2-Step rules modelled

Initial simulated capital: 10,000 USD.
- Step 1 profit target: +10% = +1,000 USD.
- Step 2 profit target: +5% = +500 USD.
- Maximum Daily Loss: 5% of initial capital = 500 USD.
- Maximum Loss: 10% of initial capital = 1,000 USD.
- Minimum trading days: 4 active trading days per step.
- Trading period: unlimited; simulation timeout is only a research reporting bound.

Daily-loss rule is approximated from the closed-trade intraday path because historical M1 trade ledger does not contain full tick-level floating MAE. The simulation checks cumulative closed P&L after every historical trade. This limitation must be stated in interpretation.

## Frozen strategy ledger

Use V5.3 `TRADES_RESCORED.csv`, raw ledger SHA-256 `c2c705318ff19aee4fb1137b7ec2102e98a848b297701b334e1b777a0d5b7d31`.

PRIMARY and STRESS are simulated separately.

## Predeclared fixed risk levels

Risk is fixed dollars as a percentage of the initial 10k balance, not compounded:
- 0.25% = $25 per 1R;
- 0.30% = $30;
- 0.35% = $35;
- 0.40% = $40;
- 0.45% = $45;
- 0.50% = $50.

No other risk level may be tested inside V9.

## Bootstrap

Use complete RTH sessions from the free USTEC archive 2021 through Apr-2025, including zero-trade complete sessions.

Preserve intraday trade order and trade R outcomes within each sampled session.

Resample history using **5-consecutive-session moving blocks** with replacement to preserve short-term clustering. Blocks may overlap in the source history.

For each scenario × risk level run 25,000 deterministic-seed simulations.

For each simulation:
1. simulate Step 1 from a fresh 10k account;
2. if Step 1 passes, reset to a fresh 10k Verification account and independently resample for Step 2;
3. each step allows max 250 sampled sessions for research timeout;
4. enforce max daily loss after every closed trade relative to that day's start balance (5% initial-capital allowance);
5. enforce max total loss after every closed trade relative to initial balance (-10%);
6. profit target may be achieved after any closed trade but pass is credited only after >=4 active trading days.

## Report

For each risk and PRIMARY/STRESS report:
- Step 1 pass probability;
- Step 1 median/P25/P75/P90 days among passes;
- Step 2 conditional pass probability after Step 1;
- combined 2-Step pass probability;
- median/P25/P75/P90 total days among full passes;
- failure share from daily-loss breach, total-loss breach, timeout;
- median maximum drawdown before terminal outcome among simulations.

## Practical candidate gate

A risk level is `V9_PRACTICAL_CANDIDATE` only if all:
- PRIMARY combined 2-Step pass probability >=65%;
- STRESS combined pass probability >=55%;
- PRIMARY median total days <=70;
- STRESS median total days <=90;
- PRIMARY Step 1 pass probability >=75%;
- STRESS Step 1 pass probability >=65%.

If multiple pass, recommend the **lowest risk level** meeting all gates.

If none pass, status `V9_NO_PRACTICAL_FAST_2STEP_SIZING` and we do not claim the current native 12-model strategy meets the user's speed objective.

Monte Carlo estimates are historical-resampling estimates, not guarantees.