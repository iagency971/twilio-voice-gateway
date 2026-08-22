# FTMO Zero-Paid-Data US100 — V10 2-Step Robustness Stress

Status: `V10_PROTOCOL_FROZEN_BEFORE_RESULTS`

## Purpose

Stress-test the V9-selected fixed risk of **0.40% per 1R ($40 on 10k)** without trying any new sizing level or strategy parameter.

V9 selected 0.40% as the lowest predeclared risk level meeting its practical speed/pass gates. V10 tests whether that conclusion depends materially on the 5-session bootstrap block or on ignoring intratrade floating equity.

No paid market data is required. No model, signal, stop, target, direction, filter or risk percentage is changed.

Frozen V5 raw ledger SHA-256: `c2c705318ff19aee4fb1137b7ec2102e98a848b297701b334e1b777a0d5b7d31`.

## Fixed risk

Exactly 0.40% of initial 10k per 1R = $40. No other risk is evaluated.

## Bootstrap sensitivity

Run moving-block bootstrap separately with block lengths:
- 5 consecutive complete RTH sessions;
- 10 consecutive complete RTH sessions;
- 20 consecutive complete RTH sessions.

Use the same complete-session universe 2021 through Apr-2025, including zero-trade sessions. Preserve chronological trade order within every sampled session.

Run 25,000 simulations for each block length and for PRIMARY/STRESS.

## FTMO rules

Same modelling as V9:
- Step 1 target +10%;
- Step 2 target +5%;
- max daily loss 5% initial capital;
- max total loss 10% initial capital;
- minimum 4 active trading days per step;
- independent fresh sampling for Step 2;
- research timeout 250 sessions per step.

## Conservative floating-equity probe

Before booking each historical trade's realised R, assume that the trade may temporarily show **-1.0R** open P&L from the current closed balance.

At that probe:
- check the 5% daily loss rule relative to the day's starting balance;
- check the 10% total-loss rule relative to initial capital.

If either would breach, terminate the simulated step as a failure before the trade's eventual historical close is credited.

This is intentionally conservative for profitable trades because their true MAE is unavailable; it is a rule-risk stress, not a claim that every winner actually reaches -1R.

## Report

For each block length × PRIMARY/STRESS report:
- Step 1 pass probability and median/P25/P75/P90 pass days;
- combined 2-Step pass probability;
- median/P25/P75/P90 total days among full passes;
- daily-loss, total-loss and timeout failure shares;
- median max closed-equity drawdown among full passes.

## Robustness criterion

0.40% remains `V10_ROBUST_FOR_FREE_TRIAL` only if the **20-session-block STRESS** scenario satisfies all:
- Step 1 pass probability >= 80%;
- combined 2-Step pass probability >= 70%;
- median Step 1 days <= 55;
- median combined days <= 90;
- daily-loss breach share <= 10%;
- total-loss breach share <= 15%.

If not: `V10_040_NOT_ROBUST_ENOUGH`.

This remains historical resampling and cannot replace prospective FTMO native-feed forward validation.