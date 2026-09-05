# V12 — Fastest FTMO Subset × Risk Search

Status: `FROZEN_BEFORE_V12_RESULTS`

## Objective

Find the fastest FTMO 2-Step candidate from the frozen native-US100 12-model ledger, even if it averages substantially fewer than 3 trades/day.

A low-frequency subset is acceptable if its better edge / lower DD permits a higher fixed risk per trade and therefore a shorter calendar challenge.

Hard constraint: zero paid external data required live.

## Frozen source

- V5.3 `TRADES_RESCORED.csv`
- raw signal ledger SHA-256 `c2c705318ff19aee4fb1137b7ec2102e98a848b297701b334e1b777a0d5b7d31`
- 12-model logic commit `d472d6b442764c2adafbba4bbeb96881c100e3e0`

No signals or outcomes are regenerated.

## Partition

- DEV selection: 2021–2023, 746 complete sessions.
- Validation: 2024 (246 sessions) and Jan–Apr 2025 (83 sessions).

The validation is mechanically held out from V12 selection but is not fully human-blind because aggregate 2024/2025 information has already appeared elsewhere. Prospective FTMO Free Trial remains the decisive OOS test.

## Search space

- all 4,095 non-empty **model-level** subsets of the 12 models;
- LONG/SHORT remain combined inside each model;
- fixed risk grid per trade: 0.25%, 0.30%, 0.35%, 0.40%, 0.45%, 0.50%, 0.55%, 0.60%, 0.65%, 0.70%, 0.75%, 0.80%, 0.85%, 0.90%, 0.95%, 1.00% of initial account.

No minimum trades/day.

## Basic DEV quality gate for a subset

Before testing risk levels, require:

- N >= 200 trades on 2021–2023;
- PRIMARY expectancy > 0;
- PRIMARY PF >= 1.15;
- STRESS expectancy >= +0.05R/trade;
- STRESS PF >= 1.10;
- at least 2 of 3 DEV years have positive PRIMARY total R;
- worst DEV year PRIMARY expectancy >= −0.10R/trade.

`remove_best_10%` is calculated and reported but is **not** a V12 selection gate.

## Risk-level admissibility on DEV

For each quality-eligible subset and each risk-grid value, require:

- STRESS closed-trade max DD × risk < 9.0% of initial account;
- worst STRESS intraday cumulative loss from that day's start × risk < 4.5%;
- chronological DEV path does not breach −10% total or −5% daily before the end of the DEV sample.

## Speed ranking

For each admissible subset × risk pair:

- `stress_R_per_session = STRESS total R / 746`;
- `stress_daily_return = stress_R_per_session × risk`;
- `implied_step1_days = 10% / stress_daily_return`;
- `implied_step2_days = 5% / stress_daily_return`.

Select the pair with the **lowest implied STRESS Step-1 days**.

Tie-breaks:
1. higher STRESS PF;
2. lower risk;
3. lower STRESS DD;
4. fewer models;
5. alphabetical model list.

## Validation

Freeze the selected model subset and risk. Then evaluate exact 2024 and exact Jan–Apr 2025 separately.

Report for each:
- N / trades per session;
- PRIMARY/STRESS expectancy, PF, DD, total R;
- risk-scaled STRESS DD;
- risk-scaled worst intraday day loss;
- implied Step-1/Step-2 days from STRESS R/session;
- chronological +10% and +5% FTMO-style path status.

## V12 promising gate

`V12_PROMISING_FOR_MONTE_CARLO` only if all are true:

- 2024 STRESS total R > 0;
- 2024 STRESS PF >= 1.10;
- 2025 STRESS total R > 0;
- 2025 STRESS PF >= 1.10;
- each validation block has risk-scaled STRESS DD < 9%;
- each validation block has worst intraday day loss < 4.5%;
- implied STRESS Step-1 pace <= 45 sessions in 2024;
- implied STRESS Step-1 pace <= 45 sessions in Jan–Apr 2025.

If it passes, only then run a separate long-block Monte Carlo/floating-loss stress. If it fails, do not promote a runner-up manually.
