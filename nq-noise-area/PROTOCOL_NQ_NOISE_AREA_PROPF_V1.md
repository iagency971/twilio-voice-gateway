# NQ Noise Area Prop-Firm V1 — Frozen Protocol

Status before outcome: `PREOUTCOME_FROZEN`
Branch: `agent/nq-noise-area-propf-v1`

## Objective
Test the published Zarattini/Aziz/Barbon intraday Noise Area momentum rule on an independent NQ 1-minute 2026 dataset, without parameter optimisation, and decide whether it is worth a second-stage prop-firm sizing simulation.

## Data
Primary source: public GetData NQ 1-minute sample, 2026-02-02 through 2026-07-31, UTC timestamps, OHLCV.
Cross-source identity has already been established on overlapping 2026 data against the independent axb0306 CME futures source (median OHLC difference 0 on the prior NQ QA).
RTH only: 09:30 through 15:59 America/New_York.

## Frozen published signal
- Lookback: 14 prior trading sessions; current day excluded.
- For each minute-of-session t: sigma_t = mean over prior 14 sessions of abs(P[d,t]/Open[d]-1).
- Upper_t = max(today RTH open, prior RTH close) * (1 + sigma_t).
- Lower_t = min(today RTH open, prior RTH close) * (1 - sigma_t).
- Session VWAP from 09:30 using typical price (H+L+C)/3 and reported volume.
- Decision grid: 10:00, 10:30, ..., 15:30 ET only.
- Flat -> LONG if close > Upper; SHORT if close < Lower.
- LONG -> flip SHORT on short signal; otherwise exit if close < max(VWAP, Upper).
- SHORT -> flip LONG on long signal; otherwise exit if close > min(VWAP, Lower).
- Force flat on the last RTH bar; no overnight exposure.
- No indicator, day-of-week, month, news, trend, or discretionary filter.
- No parameter sweep.

## Execution / cost scenarios
One NQ contract; point value = $20; tick = 0.25 point.

PRIMARY:
- 1 tick adverse slippage per transaction side.
- $2.50 commission+fees per side ($5.00 round trip), deliberately above current Topstep/Apex round-turn commission figures before slippage.

STRESS:
- 2 ticks adverse slippage per transaction side.
- $2.50 commission+fees per side.

Signals are evaluated only at completed check bars. Execution is charged adverse slippage at that check price. This is intentionally conservative relative to an ideal close fill.

## Evaluation periods
- Full evaluable 2026 sample after indicator warmup through 2026-07-31.
- Recent: 2026-05-01 through 2026-07-31.
- July: 2026-07-01 through 2026-07-31.
No date is excluded based on outcome.

## Predeclared viability gates
PRIMARY must satisfy all:
1. >= 30 completed trades.
2. Mean net P&L per trade > 0.
3. Profit factor >= 1.20.
4. At least 3 positive calendar months with trades.
5. Max mark-to-market closed-trade drawdown for 1 NQ <= $5,000.
6. Recent May-Jul mean net P&L per trade >= 0.

STRESS must satisfy:
7. Mean net P&L per trade > 0.
8. Profit factor > 1.05.

If all gates pass: `PASS_FOR_PROPFIRM_SIMULATION`.
Otherwise: `NO_GO_OR_INCONCLUSIVE`; no rescue filters or parameter tuning on this 2026 sample.

## Stage 2, only after PASS
Simulate challenge paths and sizing (MNQ/NQ or CFD equivalent) under explicit prop-firm drawdown rules. Stage 2 may change sizing, not the signal definition.
