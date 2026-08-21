# NQ Breakout SHORT-only — OOS2 V1

Status before OOS2 outcomes: `PREOUTCOME_FROZEN`
Branch: `agent/nq-breakout-short-oos2-v1`

## Hypothesis origin and contamination boundary
The full published 2022 NQ breakout was independently tested on 2026-01-20 through entries 2026-04-08. The full strategy failed, but the predeclared direction diagnostic showed that the SHORT trades actually executed by the full engine were positive while LONG trades were strongly negative.

Therefore Jan-08-Apr 2026 is DEVELOPMENT evidence for a NEW architecture. It is not validation for the new strategy and cannot be counted as OOS performance.

This document freezes the new SHORT-only architecture before calculating its outcomes on the later period.

## OOS2 data
Independent public GetData NQ 1-minute sample.
OOS2 entry period: 2026-04-16 through 2026-07-31, America/New_York RTH data.
No trade outcome from this SHORT-only architecture has been calculated on this OOS2 interval before this freeze.

## Frozen SHORT-only architecture
This is a new architecture derived from the published 2022 breakout rules; it is NOT claimed to be the original full long+short strategy.

- NQ 1-minute bars -> 5-minute bars, left-labelled.
- Opening range: 09:30 <= ET < 11:00.
- Entry window: 11:00 through 15:30 ET.
- SHORT-only: no LONG signals or positions exist in this architecture.
- Enter SHORT when a 5-minute bar trades below the frozen opening-range low.
- Conservative stop-fill entry: entry = min(opening-range low, breakout bar open).
- Stop = entry + 100 NQ points.
- Target = entry - 200 NQ points.
- Maximum 2 short entries per trading day.
- No stop/target evaluation on the entry bar.
- Subsequent-bar gap-aware exits: if bar opens above stop, stop fill is bar open; if bar opens below target, target fill is bar open.
- If still open, force flat on the 15:30 ET bar (matching the corrected source engine's short close convention).
- If a short exits before 15:30, a second short may occur on a later bar while the 2-trade/day cap is not exhausted.
- No DOW, month, trend, volatility, news, session-quality, or discretionary filters.
- No parameter sweep.

## Costs / R
NQ point value = $20.
Published stop risk = 100 points = $2,000 = 1R per contract.
PRIMARY cost = $20 round turn per completed trade.
STRESS cost = $45 round turn per completed trade.

## Predeclared prop-viability gates
PRIMARY must satisfy all:
1. >= 25 completed trades.
2. >= 1.5 completed trades per 5 cash trading days.
3. Mean expectancy >= +0.10R/trade.
4. Profit factor >= 1.30.
5. At least 2 positive months among May, June, July 2026 with trades.
6. Closed-trade max drawdown <= 8R.

STRESS must satisfy:
7. Mean expectancy > 0.
8. Profit factor >= 1.15.

If all pass: `PASS_FOR_PROPFIRM_SIZING_AND_CHALLENGE_SIM`.
Otherwise: `NO_GO_OR_INCONCLUSIVE`; OOS2 is spent and may not be used for rescue tuning.

## Diagnostics only
Monthly performance, losing streak, average win/loss, exit reason, and remove-best-5%-trade concentration are reported but cannot change the frozen verdict.
