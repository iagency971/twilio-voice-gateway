# BTC Prop-Firm Session Momentum Protocol V1

Status: PRE-OUTCOME / 2026 SEALED

## Hypothesis
Peer-reviewed Bitcoin research reports that the first half-hour return of a trading session positively predicts the last half-hour return, with stronger predictability in high-volume / high-volatility sessions. V1 translates that into a causal, prop-firm-compatible 30-minute trade.

## Data
- BTCUSDT spot, Binance public monthly 5-minute klines.
- DEV: 2019-01-01 through 2023-12-31.
- Temporal validation: 2024-01-01 through 2025-12-31.
- 2026 MUST NOT be downloaded or inspected by this protocol.

## Fixed session blocks (UTC)
- B00: 00:00-08:00; signal 00:00-00:30; trade 07:30-08:00.
- B08: 08:00-16:00; signal 08:00-08:30; trade 15:30-16:00.
- B16: 16:00-24:00; signal 16:00-16:30; trade 23:30-24:00.

## Direction and execution
- Signal = sign(first-half-hour close - first-half-hour open).
- LONG if positive, SHORT if negative; zero signal skipped.
- Entry = opening price of the first 5-minute bar of the final half-hour.
- Stop distance = high-low range of the first half-hour.
- Stop = entry minus one signal range for LONG; entry plus one signal range for SHORT.
- No take-profit.
- Exit = first causal stop hit during the last half-hour, otherwise final 5-minute close.
- Gap through stop exits at the observed bar open (adverse execution).

## Candidate set
Exactly six candidates:
- B00_ALL, B08_ALL, B16_ALL.
- B00_HIGHVOL, B08_HIGHVOL, B16_HIGHVOL.
HIGHVOL means the current first-half-hour range is strictly above the median of the previous 20 completed first-half-hour ranges for that same UTC block. The rolling statistic is shifted one session; no current/future information enters the threshold.

## Costs
- PRIMARY: 5 basis points per side.
- STRESS: 10 basis points per side.
Costs are converted to R using the frozen stop distance.

## Selection governance
1. Compute candidate metrics on DEV 2019-2023 only.
2. DEV eligibility: N >= 400, mean >= +0.05R, PF >= 1.10, at least 3/5 positive years, max DD <= 25R.
3. Among eligible candidates select exactly one by deterministic score = mean_R * sqrt(N), ties by candidate name.
4. Only after selection compute 2024-2025 validation for that selected candidate. Do not compute validation metrics for unselected candidates.
5. Validation PASS requires: N >= 150, mean >= +0.05R, PF >= 1.10, both 2024 and 2025 positive, max DD <= 15R, STRESS mean > 0 and STRESS PF > 1.00.
6. If PASS: status READY_FOR_2026_OOS_FREEZE. If FAIL: NO_GO. No parameter rescue is allowed before a separately preregistered V2.

## Prop mapping gate
No challenge-speed simulation is permitted until validation PASS. If PASS, freeze code + candidate first, then open 2026 once and simulate fixed-risk challenge outcomes separately.
