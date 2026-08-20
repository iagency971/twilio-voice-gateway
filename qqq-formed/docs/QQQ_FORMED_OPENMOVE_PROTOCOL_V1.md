# QQQ Formed Opening-Move Replication Protocol V1

Status: FROZEN BEFORE OUTCOME

## External rule being replicated
External source: EdgeLab, published 2026-07-24, NQ 1-minute 2010-2026.

Rule is fixed externally and is not optimized in this replication:
1. Regular trading hours only.
2. If the 09:30-09:35 five-minute bar closes higher than it opens, consider a LONG. Exact equality is skipped. The external article says near-flat dojis are skipped but gives no numeric threshold, so this replication does not invent one.
3. Trade only if the prior completed daily close is above its prior completed 200-day simple moving average.
4. Enter at the 09:35 five-minute bar open.
5. Stop = entry - 0.05 × prior completed 14-day ATR.
6. No profit target.
7. If the stop is not hit, exit at the 15:55 five-minute bar close.
8. One trade per day; no shorts.

## Causality
- SMA200 uses only completed daily RTH closes through D-1.
- ATR14 uses completed daily RTH OHLC through D-1 and Wilder smoothing (alpha=1/14).
- Signal uses only the completed 09:30 five-minute bar.
- Entry is next-bar open at 09:35.
- A gap below stop after entry exits at observed bar open; otherwise a bar low touching stop exits at stop.

## Independent proxy data
QQQ 5-minute public files from `lvrusu/QQQ_price_data`:
- `QQQ5m_regular_raw_01_01_2000_to_04_10_2024.csv`
- `QQQ5m_Ext_J_23_to_Mar_20a_2026.csv`
Files are combined, sorted and deduplicated. The second file takes precedence on overlap. QQQ is a Nasdaq-100 ETF proxy, not NQ futures; therefore a successful result requires later NQ/US100 replication before prop-firm promotion.

## Cost scenarios
The external NQ study uses 0.01% round-trip.
- SOURCE_COST: 0.5 basis point per side = 1.0 bp round-trip.
- DOUBLE_COST: 1.0 bp per side = 2.0 bp round-trip.
- HARD_STRESS: 2.0 bp per side = 4.0 bp round-trip.
Costs are subtracted from P&L and converted to R using the frozen stop distance.

## Reporting windows
No parameter selection is performed. Report all windows regardless of sign:
- BACKGROUND: 2000-2009.
- SOURCE_IS_PROXY: 2010-2017.
- SOURCE_OOS_PROXY_FULL_YEARS: 2018-2025.
- RECENT_FULL_YEARS: 2023-2025.
- PARTIAL_2026: 2026-01-01 through data end.
- SOURCE_OOS_PROXY_ALL: 2018 through data end 2026.

## Gate for moving to higher-resolution / tradable replication
This is only a gate for further replication, not proof of live profitability.
- SOURCE_IS_PROXY mean_R > 0 and PF >= 1.15.
- SOURCE_OOS_PROXY_FULL_YEARS N >= 500, mean_R > 0, PF >= 1.15.
- At least 6 of 8 full OOS years 2018-2025 have positive total R.
- OOS max drawdown <= 20R.
- DOUBLE_COST OOS mean_R > 0 and PF > 1.05.
- RECENT_FULL_YEARS mean_R >= 0 and PF >= 1.00.
If all pass: `QQQ_FORMED_OPENMOVE_V1_PASS_FOR_1M_NQ_REPLICATION`.
Otherwise: `QQQ_FORMED_OPENMOVE_V1_NO_GO`.

No change to first-bar rule, SMA length, ATR length, stop multiplier, direction, exit, or costs is allowed after seeing this result within V1.
