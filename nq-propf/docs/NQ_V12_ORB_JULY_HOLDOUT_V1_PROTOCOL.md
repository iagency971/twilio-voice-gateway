# NQ v12 Morning ORB — July 2026 Temporal Holdout V1

Status before outcome calculation: `PROTOCOL_FROZEN_BEFORE_JULY_HOLDOUT`

## Purpose
Replicate only the final **Morning ORB** component of the external CruzCapital NQ v12 strategy on an independent NQ 1-minute source after the strategy repository's final development commit.

This is a temporal holdout check, not proof of long-term profitability.

## Freeze boundary
External strategy repository: `cruzepchbuilds-code/nq-bot`.
- v12 trading logic committed 2026-07-03.
- repository final commit: 2026-07-04.
- no later commits observed before this protocol freeze.

Therefore the holdout is fixed to **2026-07-06 through 2026-07-31 inclusive**. Earlier data may be used only as causal warm-up/context.

## Independent data
Primary holdout source: public `getdata-finance/nq-1m-ohlcv-stocks-historical-data/NQ_1m.csv`, timestamps UTC, sample 2026-02-02 through 2026-07-31.

Cross-source identity QA: compare overlapping February-April 2026 bars against `axb0306/cme-futures-ohlc/NQ/NQ_15min_20260120_20260415.csv`.
Required data QA before any economic interpretation:
- median absolute 15-minute close difference <= 0.25 NQ points;
- >=95% of compared 15-minute closes within 0.50 points;
- first overlapping RTH prices on same scale;
- if QA fails, status = `INVALID_DATA_ABORT`.

## Frozen Morning ORB rules
Only the Morning ORB is included. Rejection, PM ORB, Asia and VWAP components are excluded by design and may not be added after seeing July outcomes.

Instrument: NQ futures, 1-minute bars.
Session timezone: America/New_York.
RTH context: 09:30 <= time < 16:00 ET.

### Prior-day context
Using completed prior RTH sessions only:
- `prevClose` = prior RTH final close;
- prior day high/low;
- prior day close-based VWAP = sum(close*volume)/sum(volume);
- queue of up to 14 prior RTH daily ranges (high-low).

### Opening range
- OR = bars 09:30 through 09:44 inclusive.
- `orHi`, `orLo`, `orRange=orHi-orLo`.
- require 55 <= OR range <= 110 points.
- regime gate: once at least 3 prior daily ranges exist, require OR range >= 0.18 * mean(last up to 14 prior RTH ranges).
- Skip Mondays.
- Fridays are allowed, matching v12 default `SkipFridays=false`.

### Confidence score (0-4), frozen threshold >=3
Context price = 09:44 close.
For LONG / SHORT respectively, add 1 point for each:
1. Pivot alignment relative to prior-day P=(H+L+C)/3.
2. Prior RTH close-based VWAP alignment.
3. HOT pivot zone: R1<=price<=R2 for long; S2<=price<=S1 for short.
4. Current-day close-based VWAP slope 09:35 -> 09:44 aligned with direction.

### Entry signal
Signal bars: 09:46 through 10:29 ET inclusive. 09:45 is explicitly skipped.
- LONG if signal-bar close > OR high + 4 points.
- SHORT if signal-bar close < OR low - 4 points.
- pseudo-gap filter used by the frozen implementation: `(OR midpoint - prevClose) > +20` for long, `< -20` for short.
- signal-bar volume >=200.
- confidence score >=3.

Execution is made causal for this replication:
- signal is known at the 1-minute bar close;
- market entry at the **next 1-minute bar open**, not the already-known signal close.
- planned stop/target price levels remain those of v12: based on the signal close, 27-point stop distance and 2R target in Eval Mode.

### Exit / costs
Eval Mode = TRUE.
- quantity = 1 NQ contract.
- planned stop = signal close +/-27 points.
- planned target = signal close +/-54 points.
- stop evaluated before target if both are touched in one OHLC bar (conservative ambiguity rule).
- force flat at 15:55 ET if still open.

Primary friction:
- entry slippage = 0.50 point adverse (2 ticks);
- stop slippage = 0.50 point adverse;
- target limit filled at target (no favorable price improvement assumed);
- time exit slippage = 0.50 point adverse;
- commission = $2.50/side = 0.25 NQ point round trip at $20/point.

Stress friction:
- entry adverse slippage = 1.00 point;
- stop/time-exit adverse slippage = 1.00 point;
- same commission.

### One re-entry (ORB2)
Frozen v12 behavior is retained:
- ORB2 is eligible only after ORB1 exits at its target;
- no ORB2 before 10:00 ET;
- still requires the same signal/gap/volume/confidence rules;
- signal cutoff remains 10:29;
- at most one ORB2 per day.

## Holdout decision gates
Primary holdout is 2026-07-06..2026-07-31 only.

If fewer than 5 trades occur: `NQ_V12_ORB_JULY_HOLDOUT_V1_INCONCLUSIVE_LOW_N`.
Otherwise all of the following are required for `PASS_FOR_EXTENDED_VALIDATION`:
- total primary net P&L > 0;
- primary mean planned-R > +0.10R/trade, where 1R = 27 NQ points;
- primary PF >=1.25;
- max drawdown <=4.0 planned-R;
- stress total P&L >=0;
- stress PF >=1.05.

Failure of any gate => `NQ_V12_ORB_JULY_HOLDOUT_V1_NO_GO`.

A PASS does NOT authorize live trading by itself. It only authorizes extended/cross-market validation and prop-firm path simulations.

## No post-outcome rescue
After July outcomes are opened, do not rescue by changing:
- OR min/max;
- 4-point breakout buffer;
- 20-point gap threshold;
- volume threshold;
- confidence threshold/components;
- Monday/Friday rules;
- stop, target, RR;
- entry cutoff;
- long/short inclusion;
- re-entry rule;
- cost model.
