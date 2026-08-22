# FTMO Zero-Data XAUUSD RSI Mean-Reversion V5

Status: `PRE_2024_VALIDATION_FROZEN`

V3/V4 are closed DEV NO_GO. V5 is an independent audit of the open-source hypothesis published in `olivertwigg/XAU-RSI-Reversal-50-EMA-Bot` at pinned commit `f74adfada07a1538f2bf9f87eb9158dcd7d86a47`. It is not a post-hoc rescue of V3/V4.

## Hard operational constraint

Live deployment must require only native FTMO/MT5 `XAUUSD` Bid/Ask and free/local calculations. No paid CME/COMEX, Databento, order flow, footprint, options, paid news, or external paid market-data subscription.

The generic historical red-folder-news filter from the external project is deliberately NOT required because its historical implementation can depend on a third-party API key. V5 uses no paid calendar data. A future live implementation may optionally suppress current-week high-impact events from a free public calendar, but the strategy cannot depend on that filter to qualify.

## External hypothesis being audited

Pinned external source, current core parameters:
- timeframe: M5;
- RSI: Wilder RSI(14);
- source thresholds: SHORT on cross above 63, LONG on cross below 37;
- source stop: fixed `$10` Gold price distance;
- source exit: SHORT when RSI reaches 37, LONG when RSI reaches 63;
- cooldown after losing trade: 40 minutes;
- max 2 losses/day;
- daily EMA50 higher-timeframe trend filter available/enabled in current source;
- blocked UTC entry hours `{1,2,3,4,5,21,22,23}`;
- broad Wednesday FOMC blackout logic from source;
- current source README reports 1,504 trades / PF 1.35 / +212.8R over Oct-2023–Jul-2026 but explicitly states its backtest does NOT account for spread. These published outcomes are not accepted as validation.

## Public independent data

Same public HistData-format XAUUSD M1 Bid data used by V3/V4: `tiumbj/M1_XAUUSD`.

- warmup/context only: 2020;
- DEV economics: 2021–2023;
- VALIDATION: 2024, gated;
- FINAL OOS: 2025 sealed and forbidden to V5 code.

HistData timestamps are fixed EST (UTC-5) without DST. Convert to `America/New_York` before session construction and to UTC for the source UTC-hour filters.

## Causal FTMO execution adaptation

V5 deliberately removes optimistic implementation details from the external backtest:
- RSI signal is evaluated only after a completed M5 bar;
- market entry occurs at the NEXT M5 bar open, never the signal-bar close;
- RSI exit is identified on a completed M5 bar and executed at the NEXT M5 bar open;
- intrabar stop is checked before any close-based RSI exit;
- one position maximum;
- fixed stop is `$10` from the actual next-bar executable quote, not from the prior signal close;
- positions are force-closed by `16:55 America/New_York`, before the 17:00 rollover, so no swap assumption is needed;
- Friday no-new-entry cutoff after 19:00 UTC is retained from the current live source;
- max two losing trades per UTC calendar date and 40-minute cooldown after a losing exit are retained.

## FTMO-like transaction-cost screen

PRIMARY:
- fixed XAUUSD spread `$0.30`;
- metals commission `0.0007% of notional per side`;
- no extra slippage.

STRESS:
- spread `$0.50`;
- same commission;
- `$0.05` adverse slippage per side.

Commission price-equivalent per side for standard 100-ounce XAUUSD = `price × 0.000007`.

Final FTMO Free Trial/demo must replace the proxy assumptions with directly observed native Bid/Ask, commission and execution.

## Trend-bias construction

To create a broker-independent causal daily bias from native prices:
- Gold daily session = 17:00 New York through 16:59 the following date;
- each session's close is its last available Bid close;
- EMA50 uses only fully completed prior sessions;
- current session bias = LONG if prior completed session close > prior-session EMA50, otherwise SHORT;
- at least 50 completed sessions required.

## Deterministic source filters retained

- Wilder RSI(14) on completed M5 closes.
- UTC blocked entry hours `{1,2,3,4,5,21,22,23}`.
- source-style FOMC blackout is reproduced deterministically: every Wednesday, no entry from 17:00 through 20:30 UTC (union of the source's two possible 19:00/20:00 decision-hour windows).
- Friday: no new entry at or after 19:00 UTC.
- no generic historical economic-calendar filter.

## Predeclared candidate set

Exactly four candidates, no further V5 parameter search:

1. `RSI63_37_TREND` — thresholds 63/37, EMA50 trend filter ON.
2. `RSI63_37_BI` — thresholds 63/37, trend filter OFF.
3. `RSI70_30_TREND` — conventional 70/30 sensitivity, trend filter ON.
4. `RSI70_30_BI` — 70/30, trend filter OFF.

All use RSI14, fixed $10 stop, opposite-threshold RSI exit, cooldown and daily loss cap above.

## Speed metric

`R/session = total PRIMARY R / available 17:00-to-16:59 Gold sessions in DEV`.

A strategy can be statistically positive but still fail if too slow for a prop challenge.

## DEV gate — 2021–2023

All required:
- N >= 500 trades;
- >= 0.65 trades per available Gold session;
- PRIMARY mean >= `+0.12R/trade`;
- PRIMARY PF >= `1.25`;
- PRIMARY `R/session >= +0.30R`;
- PRIMARY max closed-trade DD <= `12R`;
- at least 2/3 calendar years positive;
- worst calendar-year mean >= `0R/trade`;
- >=58% active months positive;
- STRESS mean >= `+0.03R/trade`;
- STRESS PF >= `1.10`;
- STRESS `R/session >= +0.12R`;
- deterministic 5,000-rep contiguous 20-trade block-bootstrap p05 mean >= 0.

Bootstrap seed `260822`.

If multiple candidates pass, select exactly one using DEV only by frozen robustness score emphasizing worst-year mean, stress R/session, PRIMARY R/session, and lower DD.

If none passes, V5 is `DEV_NO_GO`; 2024 economic outcomes stay unopened.

## 2024 validation gate

For the single DEV-selected candidate, all required:
- N >= 150;
- >=0.65 trades/session;
- PRIMARY mean >= `+0.12R/trade`;
- PRIMARY PF >= `1.25`;
- PRIMARY `R/session >= +0.35R`;
- PRIMARY max DD <= `10R`;
- STRESS mean >= `+0.03R/trade`;
- STRESS PF >= `1.10`;
- STRESS `R/session >= +0.15R`;
- H1 total R > 0 and H2 total R > 0;
- >=58% active months positive;
- bootstrap p05 mean >= 0.

Pass: `VALIDATION_PASS_READY_TO_FREEZE_FOR_2025_OOS`.
Fail: `VALIDATION_NO_GO`; no post-validation rescue.

## 2025 / FTMO rule

V5 code must refuse any year >=2025. 2025 can only be opened after a separately frozen 2024 PASS manifest.

Even a 2025 pass is only proxy evidence. Final deployment requires an unchanged prospective FTMO Free Trial/demo on native `XAUUSD` and must require `0 EUR/month` external market-data spend.
