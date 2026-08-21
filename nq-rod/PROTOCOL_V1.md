# NQ Rest-of-Day -> Last-Half-Hour Momentum V1

Status before outcomes: `PREOUTCOME_FROZEN`
Branch: `agent/nq-rod-intraday-momentum-v1`

## External hypothesis
Baltussen, Da, Lammers & Martens, "Hedging demand and market intraday momentum", Journal of Financial Economics 2021.
Published rule: the return during the rest of the day (rROD), from the previous market close until 30 minutes before the current close, positively predicts the final 30-minute return (rLH). Timing strategy eta(rROD): LONG during the last half hour if rROD > 0; SHORT otherwise.

No threshold, gamma filter, news filter, volatility filter, DOW filter, or parameter fit is allowed in V1.

## QQQ post-publication persistence test
Source: lvrusu/QQQ_price_data public 5-minute files merged with later file priority.
- RTH 09:30-15:55 ET bars.
- Prior close = prior session 15:55 bar close (price at 16:00).
- rROD signal price = current 15:25 bar close (price immediately before 15:30).
- Direction: LONG if signal price > prior close; SHORT otherwise; exact equality = no trade.
- Entry = current 15:30 bar open.
- Exit = current 15:55 bar close.
- One trade/day, no stop.
- Evaluate 2022-01-01 through 2025-12-31 as post-publication persistence; 2026 partial reported separately.
- PRIMARY = 2 bps round-turn cost.
- STRESS = 5 bps round-turn cost.

## Direct NQ futures 2026 test
Source: axb0306/cme-futures-ohlc public NQ 1-minute file `NQ/NQ_1min_20260120_20260415.csv`.
- Timestamps interpreted as UTC and converted to America/New_York.
- RTH 09:30-15:59 ET.
- Prior close = prior complete RTH 15:59 close.
- rROD signal = current 15:29 close / prior close - 1. This is fully known before 15:30.
- Direction: LONG if rROD > 0; SHORT otherwise; equality = no trade.
- Entry = 15:30 bar open.
- Exit = 15:59 bar close.
- One NQ contract only for edge measurement; point value $20.
- PRIMARY friction = $15 round turn (fees plus 1 tick adverse slippage per side equivalent).
- STRESS friction = $25 round turn (fees plus 2 ticks adverse slippage per side equivalent).
- No stop, no sizing optimisation.

## Predeclared gates
### QQQ supporting persistence
1. >= 900 trades during 2022-2025.
2. PRIMARY mean net return > 0.
3. PRIMARY PF >= 1.05.
4. At least 3 positive calendar years among 2022-2025.

### Direct NQ current viability — mandatory core gates
5. >= 45 completed trades.
6. PRIMARY mean net points/trade > 0.
7. PRIMARY PF >= 1.15.
8. At least 2 positive calendar months among Feb, Mar, Apr 2026 with trades.
9. Closed-trade max drawdown <= 400 NQ points for one NQ.
10. STRESS mean net points/trade > 0.
11. STRESS PF >= 1.05.

Terminal classification:
- If all QQQ and NQ gates pass: `PASS_FOR_PROPFIRM_RISK_RESEARCH`.
- If direct NQ gates pass but QQQ supporting persistence fails: `NQ_PASS_QQQ_NONCONFIRMING_REQUIRES_SECOND_FUTURES_REPLICATION`; do not call validated.
- Otherwise: `NO_GO_OR_INCONCLUSIVE`.

No rescue filters or sign/threshold changes after outcomes are opened.
