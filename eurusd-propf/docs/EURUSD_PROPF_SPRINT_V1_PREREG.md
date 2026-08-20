# EURUSD PROPF SPRINT V1 — PRE-OUTCOME PROTOCOL

Date frozen: 2026-08-20
Branch: `agent/eurusd-propf-sprint-v1`
Status: `FROZEN_BEFORE_OUTCOME`

## Objective
Build a causal intraday EURUSD strategy suitable for prop-firm evaluation: frequent enough to progress quickly, but evaluated under realistic bid/ask execution, commission, drawdown and first-passage-to-target metrics.

No outcome from this experiment may be used to alter the rules below.

## Data
Primary source: public FXCM M1 candle files from `https://candledata.fxcorporate.com/m1/EURUSD/{year}/{week}.csv.gz`.

Columns are expected to contain DateTime plus BidOpen/BidHigh/BidLow/BidClose and AskOpen/AskHigh/AskLow/AskClose. Timestamps are UTC.

Attempt coverage from 2012 through the latest available 2026 week. Missing files are skipped and recorded. No forward filling across missing minutes.

External recency check, if needed because FXCM coverage stops early: public GetData EURUSD 5m GitHub sample for 2026. This external check is diagnostic/replication only and may not be merged into primary OOS statistics.

## Development / OOS
- DEV: 2012-01-01 through 2018-12-31.
- OOS: 2019-01-01 onward.
- Candidate selection is performed using DEV only.
- OOS is computed only for the DEV-selected final portfolio.
- If OOS contains fewer than 3 calendar years with trades or fewer than 80 trades, status is `INSUFFICIENT_OOS` rather than PASS.

## Execution conventions
- Signal information must be fully known before entry.
- Entry uses next eligible M1 bar open: LONG at AskOpen; SHORT at BidOpen.
- LONG exits execute on Bid; SHORT exits execute on Ask.
- Same-minute SL and TP => SL (conservative ambiguity rule).
- Stop gaps execute at the worse available executable open; target gaps get no positive price improvement beyond the target.
- Base commission: USD 6 round turn per 100k EURUSD = 0.6 pip equivalent round turn.
- Stress: USD 10 round turn plus 0.2 pip slippage per side (= 1.4 pip extra round-turn equivalent beyond native bid/ask).
- One position per engine at a time. Portfolio may have at most one NY-AMOM and one London-Fix trade on the same day.

## Engine A — NY_ABNORMAL_MOMENTUM
Economic hypothesis: unusually large same-day FX moves tend to continue during the remainder of the day; major US macro releases cluster around 08:30 New York.

For every weekday at 08:35 America/New_York:
1. Define `pre_move` from the mid open at 02:00 ET through the mid close of 08:34 ET.
2. Define `impulse_30` from the mid open at 08:00 ET through the mid close of 08:34 ET.
3. Compute the rolling median of `abs(pre_move)` over the prior 60 valid trading days only.
4. Directional agreement is required: sign(pre_move) == sign(impulse_30).
5. Candidate threshold q in {1.0, 1.5, 2.0}: require abs(pre_move) >= q * prior-60-day median.
6. Entry at 08:35 ET bar open in the direction of pre_move.
7. Structural stop:
   - LONG: min BidLow from 08:25 through 08:34 ET minus 0.5 pip.
   - SHORT: max AskHigh from 08:25 through 08:34 ET plus 0.5 pip.
8. If initial executable risk < 3 pips, widen stop to exactly 3 pips. If risk > 20 pips, skip the trade.
9. RR candidate in {1.0, 1.5, 2.0}.
10. Time exit at 11:00 ET if neither SL nor TP was hit.

This creates 9 DEV candidates (3 q x 3 RR).

## Engine B — LONDON_FIX_REVERSAL
Economic hypothesis: USD demand into the London fix creates temporary EURUSD weakness that tends to reverse after the 16:00 London benchmark fixing.

For every weekday at 16:05 Europe/London:
1. Define `pre_fix_move` from the mid open at 13:00 London through the mid close of 15:59 London.
2. Only LONG is allowed and `pre_fix_move` must be negative.
3. Compute rolling median of abs(pre_fix_move) over the prior 60 valid trading days only.
4. Candidate threshold q in {0.5, 1.0, 1.5}: require abs(pre_fix_move) >= q * prior-60-day median.
5. Entry LONG at 16:05 London AskOpen.
6. Structural stop = min BidLow from 15:30 through 16:04 London minus 0.5 pip.
7. If risk < 3 pips, widen to 3 pips. If risk > 20 pips, skip.
8. RR candidate in {1.0, 1.5, 2.0}.
9. Time exit at 18:30 London.

This creates 9 DEV candidates.

## DEV selection — frozen
For each engine separately:
- require N >= 50;
- require mean net R > 0;
- require PF > 1.05;
- score = mean_net_R * sqrt(N);
- select the single highest-scoring eligible candidate; ties: lower threshold q, then lower RR.
- if no candidate is eligible, engine is DEV-rejected.

Final portfolio selection uses DEV only:
- candidate portfolios: selected Engine A only; selected Engine B only; A+B equal risk if both engines survive.
- require portfolio N >= 100, mean net R >= +0.08R, PF >= 1.20, >=5 of 7 DEV years with positive summed R, max drawdown <= 15R.
- score = mean_net_R * sqrt(N).
- select the highest-scoring eligible portfolio; tie order A+B, A, B.
- if none eligible: terminal `EURUSD_PROPF_SPRINT_V1_DEV_NO_GO`; OOS is not opened.

## OOS gates — frozen
The DEV-selected portfolio passes only if all are true under BASE costs:
1. OOS support: >=80 trades and >=3 calendar years with trades.
2. Mean net R >= +0.10R.
3. Profit factor >= 1.25.
4. At least 60% of OOS calendar years have positive summed R.
5. Max drawdown <= 12R.
6. Longest losing streak <= 10 trades.
7. After removing the best 5% of trades by net R, remaining mean net R > 0.
8. Under STRESS costs: mean net R > 0 and PF >= 1.10.

If any economic gate fails: `EURUSD_PROPF_SPRINT_V1_OOS_NO_GO`.
If support is insufficient: `EURUSD_PROPF_SPRINT_V1_INSUFFICIENT_OOS`.
If all pass: `EURUSD_PROPF_SPRINT_V1_PASS_CANDIDATE`.

## Prop-firm diagnostics — not selection gates
For the OOS-selected strategy only, simulate sequential equity with fixed risk 0.50%, 0.75%, and 1.00% of starting balance per trade.

For each possible historical OOS trade start, measure whether +10% is reached before -10%, and the number of calendar/trading days required. Because the strategy caps each engine at one trade/day, also report worst one-day loss and whether a 5% daily-loss limit would have been breached historically.

Additionally bootstrap 20,000 trade sequences (seed 20260820) to estimate probability of reaching +10% before -10% at the three risk levels. Bootstrap results are diagnostics, not evidence replacing chronological OOS.

## Governance
- No post-OOS selection by direction, weekday, month, news type, session subtype, threshold, RR, year exclusion or cost assumption.
- Any such exploration after OOS is hypothesis generation only.
- A PASS is not a promise of future profit and does not authorize oversized risk; it identifies a historical candidate suitable for broker/feed replication and paper/prospective validation.
