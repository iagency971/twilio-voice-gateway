# US100 Zero-Paid-Data — OR Family V1 Conclusion

Final status: `OR_FAMILY_V1_JAN_APR_2025_OOS_NO_GO`

The family respected the hard operational constraint: no paid external data is required in live operation; all signals use native USTEC/US100 M1 OHLC/spread data.

## Frozen DEV selection

Selected deterministically before OOS: `ORB`, 30-minute New York opening range, RR 2.0.

DEV 2021–2024 PRIMARY:
- N 980 / 1026 candidate sessions
- frequency 0.955
- expectancy +0.09398R/trade
- total +92.10R
- PF 1.227
- win rate 49.08%
- max DD 12.01R
- all four years positive

DEV doubled-spread STRESS:
- expectancy +0.09247R/trade
- PF 1.224
- max DD 12.03R

## Sealed confirmatory OOS

The public 2025 file was discovered at QA to contain only 2025-01-02 through 2025-04-30. No economics were opened before the V1.2 coverage amendment froze this four-month confirmatory window.

Jan–Apr 2025 PRIMARY:
- N 83 / 83 candidate sessions
- expectancy +0.14359R/trade
- total +11.918R
- PF 1.381
- win rate 50.60%
- max DD 4.084R
- positive months: Feb, Mar, Apr (3/4)

STRESS:
- expectancy +0.14239R/trade
- total +11.818R
- PF 1.378
- max DD 4.089R

All OOS gates passed except the predeclared concentration gate: after removing the best 10% (9 trades), remaining expectancy = -0.07341R/trade.

Therefore the family is rejected without rescue tuning. No alternative 2025 OR variant was opened.