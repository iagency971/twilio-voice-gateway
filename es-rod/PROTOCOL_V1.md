# ES Rest-of-Day -> Last-Half-Hour Momentum V1

Status before outcomes: `PREOUTCOME_FROZEN`
Branch: `agent/es-rod-intraday-momentum-v1`

## External hypothesis
Baltussen, Da, Lammers & Martens (JFE 2021): rROD, the return from the previous market close until 30 minutes before the current close, positively predicts the final 30-minute return. eta(rROD) is LONG for the last half hour when rROD>0 and SHORT otherwise. The paper provides direct S&P 500 futures/gamma evidence.

This is the final test of this hypothesis family in the current research. No gamma/news/volatility threshold is added.

## Independent direct ES data
Source: public axb0306/cme-futures-ohlc `ES/ES_1min_20260120_20260415.csv`.
Timestamps: UTC -> America/New_York.
RTH: 09:30-15:59 ET.

## Frozen rule
- Prior close = previous complete RTH 15:59 close.
- Signal at 15:29 close, fully known before entry.
- LONG if 15:29 close > prior close; SHORT otherwise; equality=no trade.
- Entry = 15:30 bar open.
- Exit = 15:59 bar close.
- One ES contract, one trade/day, no stop, no filter.
- ES point value = $50.

## Costs
PRIMARY = $30 round-turn = conservative allowance for ~$5 fees/commission plus one ES tick adverse slippage per side.
STRESS = $55 round-turn = ~$5 fees plus two ES ticks adverse slippage per side.

## Predeclared gates
PRIMARY all required:
1. >=45 completed trades.
2. Mean net ES points/trade >0.
3. Profit factor >=1.15.
4. At least 2 positive calendar months among Feb/Mar/Apr 2026 with trades.
5. Closed-trade max drawdown <=100 ES points.
6. Win rate >=52%.

STRESS all required:
7. Mean net points >0.
8. PF >=1.05.

If all pass: `PASS_REQUIRES_SECOND_ES_REPLICATION_BEFORE_PROP_SIM`.
Otherwise: `NO_GO` and the rROD family is closed; no rescue filters on NQ/ES 2026.
