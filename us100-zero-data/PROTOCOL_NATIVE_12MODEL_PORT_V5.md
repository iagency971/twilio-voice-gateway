# FTMO Zero-Paid-Data US100 — Native 12-Model Port V5

Status: `V5_PROTOCOL_FROZEN_NO_PARAMETER_SEARCH`

## Objective

Test whether the already-frozen 12-model Nasdaq engine can be operated directly from a CFD/MT5 Nasdaq-100 feed, with zero paid external market-data requirement and enough trade frequency to make an FTMO 10k 2-Step challenge economically relevant.

Hard constraint: live operation must require **0 EUR/USD per month of external market data**. Only the broker/FTMO `US100.cash` feed may be required in live use.

## Frozen external model

Repository: `s-k-28/nq-es-trader-5k-payout`
Commit: `d472d6b442764c2adafbba4bbeb96881c100e3e0`

No model parameter, threshold, direction, priority, stop, target, time window, conflict rule, daily win cap or quality filter may be tuned from USTEC outcomes in V5.

The 12 source models are used as-is. This V5 is a portability test, not a new optimization search.

## Free historical CFD source

Repository: `CodyOutcast/Academic-Paper-Data-Source`
Commit: `50052606c16d71850755e6dbdda02d43b4399c2b`
Files: `OHLC-USTEC-M1-2021.csv` through `OHLC-USTEC-M1-2025.csv`.

The repository states IC Markets as source. The data contain M1 OHLC, tick volume and recorded spread.

2021-2024 are complete calendar-year research/history. The public 2025 file contains Jan-Apr only.

Because prior zero-data families have already exposed aggregate outcomes on these years, V5 does **not** claim pristine OOS status for any historical year. The purpose is translation/robustness screening. The first clean validation, if V5 is promising, must be a prospective FTMO Free Trial forward.

## Time translation

IC MetaTrader server time follows US DST with a persistent 7-hour difference to New York wall-clock time. Every source timestamp is translated by subtracting exactly 7 hours before being passed to the frozen model engine.

Thus broker 16:30 maps to 09:30 New York, preserving the engine's original session windows without changing model code.

## Price/tick convention

USTEC and NQ track the same Nasdaq-100 index scale. V5 passes USTEC prices to the frozen engine without price rescaling and retains the engine's original 0.25 model tick. This intentionally preserves all original thresholds in index-point terms. It does not imply the CFD itself has a 0.25 broker tick.

## Spread/friction

The source engine already applies its frozen 0.25-tick adverse slippage model on non-target exits.

In addition, V5 rescoring charges recorded CFD spread once per round trip:
- PRIMARY: recorded spread at the relevant execution side;
- STRESS: 2x recorded spread.

Recorded MT5 `spread` is converted using 0.1 index point per spread unit for this archive, as already QA-verified in V1-V4. If exact entry/exit timestamp spread is unavailable, the nearest same-session M1 spread is used; no future bar may be used for an entry-side cost.

This friction is screening-level. A promising candidate still requires direct FTMO bid/ask forward logging.

## Outputs

Run the single unchanged 12-model engine over the translated 2021-Jan2025 archive and report:
- total trades and trades per candidate RTH day;
- PRIMARY/STRESS expectancy, PF, win rate, max closed-trade DD, longest losing streak;
- total R;
- stats by calendar year and month;
- model-by-model contribution;
- worst daily R and best daily R;
- concentration: top 10% contribution and expectancy after removing top 10%;
- first-half / second-half performance.

No model is deleted or reweighted based on these diagnostics.

## Challenge-speed assessment

For a 10k FTMO 2-Step feasibility estimate, derive two risk levels from the observed PRIMARY max DD:

`SAFE_RISK_PCT = min(0.50%, 8% / (2.0 * max_DD_R))`

`AGGRESSIVE_RISK_PCT = min(0.50%, 8% / (1.5 * max_DD_R))`

The 8% budget deliberately leaves 2% headroom below a 10% total-loss limit. Also reject any proposed risk level for which the observed worst daily R would imply >=4% daily loss, leaving headroom below a 5% daily limit.

For each admissible risk level estimate:
- expected account return per trading day = expectancy_R/trade × trades/day × risk_pct;
- theoretical Step-1 days = 10% / expected daily return;
- theoretical Step-2 days = 5% / expected daily return;
- total theoretical trading days.

These are expectation-based planning numbers, not guarantees.

## V5 operational gate

`V5_PROMISING_FOR_FTMO_NATIVE_FORWARD` requires all:
- N >= 1000 historical trades;
- trades/day >= 2.0;
- PRIMARY expectancy >= +0.08R/trade;
- PRIMARY PF >= 1.20;
- PRIMARY max DD <= 18R;
- at least 3 of 4 full calendar years 2021-2024 positive;
- STRESS expectancy > 0 and PF >= 1.10;
- expectancy after removing best 10% of trades >= 0;
- an admissible SAFE or AGGRESSIVE risk level producing theoretical Step-1 <= 45 trading days and total 2-Step <= 70 trading days.

If the gate fails, the exact port is rejected. We may later define a **new adapted native ensemble**, but only under a new pre-registered protocol; we do not tune V5 after opening its outcomes.

If the gate passes, next status is `V5_PROMISING_REQUIRES_FTMO_FREE_TRIAL_FORWARD`, never LIVE_READY.