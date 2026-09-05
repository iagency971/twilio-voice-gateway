# FTMO US100.cash Native Forward — ORB30 RR2 F1

Status: `CANDIDATE_FORWARD_FROZEN_NOT_LIVE_VALIDATED`

## Purpose

Test the strongest zero-paid-data candidate found in the historical research directly on FTMO's own `US100.cash` feed, without any external paid market data.

No CME, Databento, order book, footprint, paid news or external signal feed is used or required.

## Why this candidate, despite V1 formal NO_GO

Frozen historical candidate: New York 30-minute Opening Range breakout, RR 2.0.

2021–2024 IC Markets USTEC DEV:
- 980 trades / 1026 candidate sessions;
- expectancy +0.09398R/trade;
- PF 1.2275;
- max closed-trade DD 12.01R;
- all four calendar years positive;
- doubled-recorded-spread stress expectancy +0.09247R, PF 1.2237.

Sealed Jan–Apr 2025 family OOS:
- 83 trades / 83 sessions;
- expectancy +0.14359R/trade;
- PF 1.3810;
- max DD 4.08R;
- 3 of 4 months positive;
- doubled-spread stress expectancy +0.14239R, PF 1.3776.

The formal V1 result remains NO_GO because the predeclared remove-best-10% concentration test failed (remaining mean -0.07341R). This forward therefore does **not** relabel V1 as historically validated. It treats ORB30/RR2 as the only candidate strong enough to justify a free native-feed prospective test.

## Frozen trading rules

Instrument: FTMO MetaTrader `US100.cash`.
Timeframe: M1.
Maximum one trade per MetaTrader platform calendar day.

FTMO MetaTrader platform clock is configured so the New York cash open maps to 16:30 platform time in the current operating convention. The EA exposes these times as inputs for verification but the F1 frozen defaults are:
- OR start: 16:30 platform time;
- OR end: 17:00 (bars 16:30 through 16:59);
- signal window: 17:00 inclusive through 19:00 exclusive;
- hard flatten: 22:55.

Opening range = maximum high and minimum low of the complete 30 M1 bars 16:30–16:59.

After the OR is complete:
- LONG signal: a fully closed M1 bar closes strictly above OR high;
- SHORT signal: a fully closed M1 bar closes strictly below OR low.

First signal/day only.
Entry: market order on the first tick of the next M1 bar.
Stop:
- LONG: OR low;
- SHORT: OR high.
Target: 2.0 × actual entry-to-stop distance.

No EMA/VWAP/ATR/news/day-of-week/direction/spread filter. No averaging, martingale, grid, recovery sizing or second entry.
If still open at 22:55 platform time, flatten.

## Risk for 10k Free Trial

Fixed intended risk: **$30 per trade** (0.30% of initial 10k), calculated from actual entry/stop distance using the broker symbol's own tick value/tick size and volume step.

This is deliberately below the $35 upper working level derived from the historical 12.0R DD. At $30/R:
- historical 12R DD ≈ $360;
- 1.5× historical DD ≈ $540;
- 2× historical DD ≈ $720.

The EA must never increase size after a loss.

## Stage A — FTMO Strategy Tester, zero calendar waiting

Run the exact frozen EA on whatever native FTMO `US100.cash` history MetaTrader makes available. No optimization and no parameter search.

Use M1 / Every tick based on real ticks if FTMO history supports it. Record:
- available test interval;
- N trades;
- net profit;
- PF;
- max balance/equity DD;
- win rate;
- average trade;
- modeling quality / tick mode;
- symbol specification and average observed spread if the report exposes it.

This stage is a broker-feed parity/economics check, not a new parameter-development sample.

## Stage B — FTMO Free Trial forward

Run unchanged on a dedicated FTMO 10k Free Trial. Do not use the user's manual Gold Challenge for this EA.

The EA writes every signal/order/exit with:
- server timestamp;
- OR high/low;
- signal direction and signal close;
- bid/ask/spread at order time;
- requested risk dollars;
- calculated lot size;
- actual fill price if available;
- SL/TP;
- exit price;
- realised profit, commission and swap.

Checkpoint 1: first 10 completed trades — execution/spread/logic QA only. No tuning.
Checkpoint 2: >= 30 completed trades — descriptive economics. Continue unchanged unless there is an implementation defect.
Checkpoint 3: >= 50 completed trades — decision gate.

F1 forward decision gate at N>=50:
- total net P&L > 0;
- realised expectancy > 0R/trade using $30=1R intended risk;
- PF >= 1.10;
- max closed-equity DD <= 10R ($300);
- no FTMO rule breach;
- no implementation divergence from frozen ORB30/RR2 rules.

A PASS only means `FTMO_NATIVE_FORWARD_PROMISING`; it does not guarantee future profitability.

## Prohibited changes during F1

No RR adjustment, no time adjustment, no direction deletion, no additional entry, no break-even/trailing addition, no spread/news/weekday filter and no dynamic risk scaling. Only a demonstrable implementation bug may be corrected, with the affected pre-fix observations retained and separately labelled.