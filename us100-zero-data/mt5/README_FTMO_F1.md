# FTMO US100 ORB30 RR2 F1 — MT5 Test Guide

## Goal

Validate the frozen zero-paid-data candidate directly on FTMO `US100.cash` using only FTMO's own MT5 feed.

Do not run this EA on the manual Gold Challenge. Use a dedicated FTMO 10k Free Trial first.

## Source

EA: `US100_ORB30_RR2_FTMO_F1.mq5`
Protocol: `../FTMO_FORWARD_PROTOCOL_ORB30_RR2_F1.md`

Frozen defaults:
- risk: $30/trade;
- OR: 16:30–16:59 MetaTrader platform time;
- signal window: 17:00–18:59;
- RR: 2.0;
- flatten: 22:55;
- first breakout/day only.

## Install / compile

1. In FTMO MT5: `File -> Open Data Folder`.
2. Put the `.mq5` file in `MQL5/Experts/`.
3. Open MetaEditor (F4), open the EA, Compile (F7).
4. Compilation must finish with 0 errors before any test.
5. If there is a compile error, do not edit strategy values; record the exact compiler message and correct implementation only.

## Stage A — native FTMO Strategy Tester

1. Open Strategy Tester (`Ctrl+R`).
2. Expert: `US100_ORB30_RR2_FTMO_F1`.
3. Symbol: `US100.cash`.
4. Period: M1.
5. Model: `Every tick based on real ticks` when available.
6. Use the largest native FTMO history range available without downloading paid external data.
7. Initial deposit: $10,000 USD.
8. No optimization.
9. Inputs stay at frozen defaults.

Export/save the Strategy Tester report and the Experts/Journal log.

Required report fields:
- actual history start/end;
- number of trades;
- net profit;
- profit factor;
- maximal balance/equity drawdown;
- win rate;
- expected payoff;
- modeling/tick mode;
- symbol specification if available.

## Stage B — Free Trial forward

Attach the EA to a `US100.cash` M1 chart on the dedicated 10k Free Trial and enable Algo Trading.

Keep MT5 running before 16:30 platform time so the opening range is observed normally. The EA can rebuild the OR from broker history after a restart, but a continuously running terminal is preferred for the forward test.

The EA writes `US100_ORB30_RR2_FTMO_F1.csv` to the MT5 Common Files directory. It records OR, signal, bid/ask/spread, volume, order events, fills and realised deal P&L/commission/swap.

Do not change parameters during F1.

## Immediate QA before letting it trade unattended

On the first session, verify visually:
- 16:30 platform time is the New York 09:30 cash open;
- OR high/low exactly cover 16:30–16:59;
- no signal can occur before 17:00 or at/after 19:00;
- a breakout signal is based on the previous fully closed M1 candle;
- order is placed on the next M1 bar;
- SL is the opposite OR edge;
- TP is 2R from the actual fill;
- intended loss at SL is approximately $30 after lot-step rounding;
- only one signal is consumed per day.

Any discrepancy is an implementation bug and must be fixed without changing the frozen strategy.