# FTMO Zero-Data XAUUSD ML Walk-Forward V6

Status: `PRE_2024_VALIDATION_FROZEN`

V3/V4/V5 are closed DEV NO_GO. V6 is a distinct supervised-learning hypothesis using only causal price/time features that an FTMO/MT5 EA can compute locally from native XAUUSD bars. It is not a post-hoc parameter rescue of prior rule families.

## Hard operational constraint

Live deployment must require `0 EUR/month` external market-data spend. Allowed inputs: native FTMO/MT5 XAUUSD OHLC, spread, bar time and locally calculated indicators. Forbidden dependencies: CME/COMEX, Databento, order-flow/footprint, options, paid news/calendar, paid alternative data, proprietary external market feeds.

## Public research data

Public HistData-format XAUUSD M1 Bid files from `tiumbj/M1_XAUUSD`, converted from fixed EST (UTC-5, no DST adjustment) to `America/New_York` before feature construction.

Partitions:
- 2020: initial training/context only;
- DEV walk-forward OOS folds:
  - test 2021, train 2020;
  - test 2022, train 2020–2021;
  - test 2023, train 2020–2022;
- VALIDATION 2024: sealed from model/candidate selection; may be downloaded/evaluated only after a DEV candidate passes;
- FINAL OOS 2025: forbidden to V6 code and stays sealed.

The 2021–2023 DEV result is therefore itself stitched from genuinely out-of-training yearly predictions.

## M5 bars and allowed causal features

M1 Bid bars resampled to completed M5 OHLC. No future information may enter any feature.

Features, frozen before execution:
- returns normalized by ATR over 1, 3, 6 and 12 M5 bars;
- Wilder RSI14 scaled to 0–1;
- `(close-EMA20)/ATR14`;
- `(close-EMA50)/ATR14`;
- `(EMA20-EMA50)/ATR14`;
- 3-bar EMA20 slope / ATR14;
- M5 body / ATR14;
- M5 range / ATR14;
- 20-bar close z-score;
- location of close within trailing 20-bar high/low range;
- ATR14 / close;
- rolling 12-bar return standard deviation;
- New-York time-of-day sine/cosine;
- weekday sine/cosine.

No volume feature is used, so live behavior does not depend on broker-specific volume semantics.

## Training labels

For every eligible completed M5 signal bar, reference entry is the next M5 Bid open. ATR is frozen from the signal bar.

Two independent binary labels are built over the next 12 M5 bars (60 minutes):
- LONG success = a raw upside barrier `+2.25 × ATR14` is reached before a raw downside barrier `-1.50 × ATR14`;
- SHORT success = a raw downside barrier `-2.25 × ATR14` is reached before a raw upside barrier `+1.50 × ATR14`.

Same-bar target/stop ambiguity is labeled as failure (stop first). No label crosses the 16:55 New-York rollover cutoff. Eligible signal time window: 07:00–15:45 America/New_York.

These labels correspond to a nominal 1.5R target using a 1.5×ATR stop. Actual economic evaluation separately includes FTMO-like spread/commission/slippage.

## Model — fixed, no hyperparameter search

Two `sklearn.ensemble.HistGradientBoostingClassifier` models, one LONG and one SHORT, each with:
- `max_iter=150`;
- `learning_rate=0.05`;
- `max_leaf_nodes=15`;
- `min_samples_leaf=100`;
- `l2_regularization=1.0`;
- `random_state=260822`.

No calibration, feature selection or hyperparameter tuning after outcomes are opened.

## Predeclared candidate set

Four execution candidates applied to the same yearly walk-forward predictions:
1. `ML55_BI`: bidirectional, trade if max LONG/SHORT probability >=0.55;
2. `ML60_BI`: bidirectional, threshold 0.60;
3. `ML55_LONG`: LONG only, threshold 0.55;
4. `ML60_LONG`: LONG only, threshold 0.60.

If bidirectional LONG and SHORT both exceed threshold, take the larger predicted probability. No other probability threshold may be tested in V6.

## Execution and FTMO-like costs

- signal on completed M5 bar; entry next M5 open;
- signal window 07:00–15:45 NY;
- maximum 3 entries per 17:00–16:59 Gold session;
- minimum 30 minutes between entries;
- no overlapping trades;
- stop = 1.5×ATR14 from next-bar Bid reference;
- economic target = 1.5R after transaction costs;
- stop/target same-bar ambiguity: stop first;
- maximum hold = 60 minutes;
- force flat by 16:55 NY;
- no overnight rollover, therefore no swap assumption.

PRIMARY costs:
- fixed XAUUSD spread `$0.30`;
- metals commission `0.0007% of notional per side`;
- no extra slippage.

STRESS costs:
- spread `$0.50`;
- same commission;
- `$0.05` adverse slippage per side.

Final FTMO Free Trial/demo must replace these proxy costs with observed native Bid/Ask and actual executions.

## DEV gate — stitched walk-forward 2021–2023

A candidate passes only if ALL hold:
- N >= 500 trades;
- >=0.65 trades per available Gold session;
- PRIMARY mean >= `+0.15R/trade`;
- PRIMARY PF >= `1.30`;
- PRIMARY `R/session >= +0.35R`;
- PRIMARY max closed-trade DD <= `12R`;
- each of 2021, 2022 and 2023 has positive total R;
- worst yearly mean >= `+0.05R/trade`;
- >=60% active months positive;
- after removing best 10% of PRIMARY trades, remaining mean >= 0;
- STRESS mean >= `+0.05R/trade`;
- STRESS PF >= `1.15`;
- STRESS `R/session >= +0.15R`;
- deterministic 5,000-rep contiguous 20-trade block-bootstrap p05 mean >= 0.

Bootstrap seed `260822`.

If multiple candidates pass, select exactly one using DEV only with a frozen robustness score weighted toward worst-year mean, STRESS R/session, PRIMARY R/session, remove-best-10% mean and lower DD.

No DEV pass => `DEV_NO_GO`; 2024 data/economics stay unopened.

## 2024 validation

Only after a DEV PASS:
- retrain the two fixed models on 2020–2023;
- generate 2024 predictions once;
- apply only the single DEV-selected execution candidate.

All validation gates required:
- N >= 150;
- >=0.65 trades/session;
- PRIMARY mean >= `+0.15R/trade`;
- PRIMARY PF >= `1.30`;
- PRIMARY `R/session >= +0.40R`;
- PRIMARY max DD <= `10R`;
- remove-best-10% mean >= 0;
- STRESS mean >= `+0.05R/trade`;
- STRESS PF >= `1.15`;
- STRESS `R/session >= +0.18R`;
- H1 total R >0 and H2 total R >0;
- >=60% active months positive;
- bootstrap p05 mean >=0.

Pass: `VALIDATION_PASS_READY_TO_FREEZE_FOR_2025_OOS`.
Fail: `VALIDATION_NO_GO`; no parameter/model rescue.

## 2025 / FTMO rule

V6 code must refuse any request for year >=2025. Only a separately frozen 2024 PASS manifest can authorize a one-time 2025 OOS run.

Even a future 2025 pass is only proxy evidence. Paid FTMO use requires an unchanged prospective FTMO Free Trial/demo using native `XAUUSD` only and no paid external data.
