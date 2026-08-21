# NQ Last-Half-Hour Intraday Momentum V1

Status before outcomes: `PREOUTCOME_FROZEN`
Branch: `agent/nq-last-halfhour-momentum-v1`

## External hypothesis
Gao, Han, Li & Zhou, "Market Intraday Momentum" (first public draft 2014; Journal of Financial Economics 2018).
Core published relation: the first half-hour return, measured from the previous trading day's close through the end of the current day's first 30 minutes, predicts the final half-hour return. Market-timing rule: long the final half hour when the signal is positive; short when negative.

No parameter fitting or sign threshold is allowed here.

## Rule — QQQ replication
- RTH timestamps in America/New_York.
- Prior close = prior complete session 15:55 5-minute bar close (price at 16:00).
- Signal price = current 09:55 5-minute bar close (price at 10:00).
- Signal = signal_price / prior_close - 1.
- At 15:30: LONG if signal > 0, SHORT if signal < 0. Zero signal = no trade.
- Entry = 15:30 5-minute bar open.
- Exit = 15:55 5-minute bar close (16:00).
- One trade/day, no stop, no filter.
- Source: public lvrusu/QQQ_price_data merged 2000-2026 files.
- Evaluation: post-publication 2014-01-01 through 2025-12-31; 2026 partial reported separately.
- PRIMARY cost: 2 basis points round-turn of entry notional.
- STRESS cost: 5 basis points round-turn.

## Rule — NQ recent replication
- Same economic rule using NQ 1-minute RTH data.
- Prior close = prior trading day's 15:59 close.
- Signal price = current 09:59 close (10:00).
- Enter at 15:30 open; exit at 15:59 close.
- LONG if signal >0, SHORT if signal <0.
- One NQ contract only for stage-1 edge measurement; point value $20.
- Source: GetData public NQ sample, 2026-02-02 through 2026-07-31. This source is an independent price proxy whose overlapping NQ bars were previously cross-checked against a CME/TopstepX source; it is not treated as exchange tape.
- PRIMARY friction: $15 round-turn per trade = $5 fees/commission assumption + one NQ tick adverse slippage on each side.
- STRESS friction: $25 round-turn = $5 fees + two ticks adverse slippage on each side.

## Predeclared gates
### QQQ post-publication persistence
All required:
1. >= 2,500 trades during 2014-2025.
2. Net mean trade return > 0 after PRIMARY costs.
3. Profit factor >= 1.05 after PRIMARY costs.
4. At least 8 positive calendar years among 2014-2025.
5. 2020-2025 aggregate mean net trade return >= 0.

### NQ 2026 current usefulness
All required:
6. >= 100 completed trades.
7. Mean net NQ points/trade > 0 under PRIMARY.
8. Profit factor >= 1.10 under PRIMARY.
9. At least 4 positive calendar months among Feb-Jul 2026 with trades.
10. Closed-trade max drawdown <= 500 NQ points for 1 NQ.
11. STRESS mean net points > 0.
12. STRESS profit factor > 1.02.

If all QQQ and NQ gates pass: `PASS_FOR_PROPFIRM_SIZING_RESEARCH`.
Otherwise: `NO_GO_OR_INCONCLUSIVE`; do not tune the signal on these opened periods.

## Stage 2 after PASS only
Because the published market-timing rule has no stop, prop sizing must be studied separately using MNQ/NQ contract count, daily loss caps, empirical adverse last-half-hour tails, and account rules. Stage 2 may change size/risk caps but not signal direction or timing.
