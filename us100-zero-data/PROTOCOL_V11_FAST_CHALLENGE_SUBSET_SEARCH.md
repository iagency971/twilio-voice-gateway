# V11 — US100 Native 12-Model Fast-Challenge Subset Search

Status: `FROZEN_BEFORE_V11_SUBSET_RESULTS`

## Goal

Optimize for **calendar speed to pass an FTMO 2-Step**, not for trade frequency.

A candidate with ~1 trade/day is acceptable if a lower drawdown permits materially higher fixed risk per trade and therefore a faster challenge than the full 12-model ensemble.

Hard constraint: **zero paid external market data required live**. Candidate must remain computable from native `US100.cash`/USTEC-style OHLCV/tick-volume data.

## Frozen input

Use only the already-frozen V5.3 CFD-native 12-model ledger:

- source ledger: `us100-zero-data/results/native_12model_port_v5/TRADES_RESCORED.csv`
- source raw-ledger SHA-256: `c2c705318ff19aee4fb1137b7ec2102e98a848b297701b334e1b777a0d5b7d31`
- model logic commit: `d472d6b442764c2adafbba4bbeb96881c100e3e0`
- CFD source commit: `50052606c16d71850755e6dbdda02d43b4399c2b`

No signal is regenerated and no trade outcome is modified.

## Development / validation partition

- DEV selection: calendar years **2021–2023 only**.
- Mechanical validation after selection: **2024** and **Jan–Apr 2025**.
- DEV complete-session denominator: 746 sessions.
- 2024 complete-session denominator: 246 sessions.
- Jan–Apr 2025 complete-session denominator: 83 sessions.

Important limitation: 2024/2025 aggregate outcomes have already been exposed elsewhere in the research. V11 is mechanically outcome-separated at the code level, but the validation is not fully human-blind. A prospective FTMO Free Trial remains the decisive OOS test.

## Search space

Search all non-empty subsets of the **12 model names**, not model×direction combinations.

With 12 models this is 2^12 − 1 = **4,095 subsets**.

LONG and SHORT behavior inside an included model remains unchanged. No per-direction cherry-picking in V11.

## DEV metrics for each subset

Compute on 2021–2023 only:

- N trades;
- trades/session;
- PRIMARY expectancy, total R, PF, max closed-trade DD;
- STRESS expectancy, total R, PF, max closed-trade DD;
- yearly PRIMARY expectancy/sum;
- worst daily PRIMARY/STRESS R;
- remove-best-10%-of-trades remaining PRIMARY expectancy;
- model count.

## DEV eligibility gate

A subset is eligible only if all are true:

- N >= 250;
- PRIMARY expectancy > 0;
- PRIMARY PF >= 1.20;
- STRESS expectancy >= +0.05R/trade;
- STRESS PF >= 1.12;
- at least 2 of 3 DEV calendar years have positive PRIMARY total R;
- worst DEV calendar-year PRIMARY expectancy >= −0.05R/trade;
- remove-best-10% remaining PRIMARY expectancy >= 0.00R/trade.

There is **no minimum trades/day gate**.

## Fixed-risk sizing from DEV only

For each eligible subset, determine the maximum admissible fixed initial-account risk fraction per trade as:

`risk = min(1.00%, 8% / (1.5 × STRESS maxDD_R), 4% / (1.25 × abs(STRESS worst_daily_R)))`

If the worst daily R is non-negative, the daily-loss term is ignored.

Rationale:

- 1.5× observed STRESS DD must fit inside an 8% working loss budget, leaving 2 percentage points below FTMO's 10% maximum loss;
- 1.25× observed worst STRESS day must fit inside a 4% working daily budget, leaving 1 percentage point below the 5% daily limit;
- absolute cap 1.00% per trade.

The risk value is frozen from DEV and is not changed in validation.

## Speed objective

For each eligible subset:

- `stress_R_per_day = STRESS total_R / 746`
- `expected_daily_return = stress_R_per_day × risk`
- `theoretical_step1_days = 10% / expected_daily_return`
- `theoretical_step2_days = 5% / expected_daily_return`

Select the eligible subset with the **lowest theoretical STRESS Step-1 days**.

Tie-breaks, in order:

1. lower STRESS maxDD;
2. lower fixed risk fraction;
3. fewer included models;
4. alphabetical model-list representation.

## Mechanical validation

After one subset and one fixed risk are selected from DEV, open 2024 and Jan–Apr 2025 for that exact candidate only.

For each validation block report:

- N and trades/session;
- PRIMARY/STRESS expectancy, PF, maxDD and total R;
- risk-scaled maxDD percentage;
- risk-scaled worst daily loss percentage;
- implied Step-1 and Step-2 calendar pace from observed STRESS R/session;
- chronological FTMO-style path test using fixed initial-account risk:
  - +10% Step-1 target;
  - −10% maximum total loss;
  - −5% maximum daily loss;
  - no parameter/sizing changes.

## V11 promising gate

V11 is `PROMISING_FOR_MONTE_CARLO` only if:

- selected DEV candidate exists;
- 2024 STRESS total R > 0 and PF >= 1.10;
- 2025 Jan–Apr STRESS total R > 0 and PF >= 1.10;
- validation risk-scaled STRESS maxDD < 8% in each block;
- validation risk-scaled worst STRESS day < 4% in each block;
- observed STRESS pace implies Step 1 <= 45 sessions in both validation blocks.

Otherwise V11 is NO_GO.

## Prohibited changes

After this protocol is committed:

- do not change DEV years;
- do not change subset granularity to model×direction;
- do not relax gates;
- do not change the risk formula;
- do not add indicators or filters;
- do not alter raw/rescored trades;
- do not choose a runner-up manually because validation looks better.
