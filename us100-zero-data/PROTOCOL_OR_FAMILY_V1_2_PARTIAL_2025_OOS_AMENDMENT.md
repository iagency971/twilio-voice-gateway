# OR Family V1.2 — Partial 2025 OOS Coverage Amendment

Status: `PRE_2025_ECONOMICS_REPAIR_FROZEN`

This amendment is written after the sealed 2025 file was opened for **data QA only** and before any 2025 trade P&L/economic result was calculated.

The first OOS runner stopped at `OR_FAMILY_V1_OOS_DATA_QA_FAIL` because the public file named `OHLC-USTEC-M1-2025.csv` contains only 2025-01-02 through 2025-04-30, with 83 candidate New-York sessions. No OOS trades or P&L were produced.

No strategy parameter changes. The already frozen selection remains exactly:
- family: `ORB`
- opening range: `30` minutes
- RR: `2.0`
- source commit: `50052606c16d71850755e6dbdda02d43b4399c2b`
- DEV runner Git blob SHA: `d0b6fc1789d876a677eeeb0f3e0027ad1554179c`

## Repaired confirmatory window

The confirmatory OOS window is now the full coverage actually available in the sealed file:
- start: 2025-01-02
- end: 2025-04-30
- expected candidate-session floor: >= 80

This is a coverage repair only. No 2025 outcome was used to choose the window.

## Repaired OOS gates

Unchanged gates:
- frequency >= 0.40 trade / candidate session;
- PRIMARY expectancy >= +0.05R/trade;
- PRIMARY PF >= 1.15;
- PRIMARY max DD <= 12R;
- doubled-spread STRESS expectancy > 0;
- doubled-spread STRESS PF >= 1.05;
- after removing best 10% of PRIMARY trades, remaining expectancy >= 0.

Window-length gates are repaired proportionally/conservatively:
- `N >= 30` (the original full-year N>=80 scaled to four months is ~27; 30 is rounded upward);
- at least `3 of 4` calendar months have positive total R (stricter proportion than the original 7 of 12).

If all gates pass, status is `OR_FAMILY_V1_JAN_APR_2025_OOS_PASS_REQUIRES_FTMO_FEED_PARITY`. Otherwise `OR_FAMILY_V1_JAN_APR_2025_OOS_NO_GO`.

No additional 2025 variant, parameter, direction, time window, stop, target, or filter may be opened or changed.