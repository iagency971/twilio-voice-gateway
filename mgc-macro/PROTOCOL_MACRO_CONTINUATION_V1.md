# MGC Macro Reaction Continuation V1

Status: `PREOUTCOME_FROZEN_AWAITING_EVENT_MANIFEST_AND_COST_AUTHORIZATION`
Branch: `agent/mgc-macro-event-research-v1`

## Objective
Test an event-driven Gold engine that is independent of the failed XAU causal-core and independent of the NQ 12-model ensemble. This is intended as a possible prop-firm news accelerator, not as a rescue of any previous Gold strategy.

## Evidence basis and epistemic status
### FOMC engine
Awartani, Hussain & Virk (International Review of Financial Analysis, 2024) use 5-minute gold futures data and report that gold price/volatility adjustment to FOMC monetary-policy shocks continues beyond the first five minutes; their preview reports the 10-minute adjustment is materially larger than the 5-minute adjustment.

The V1 trading rule below is a NEW price-only continuation hypothesis motivated by that delayed adjustment. It is not claimed to be the paper's trading strategy and does not use monetary-policy surprise data.

### CPI/NFP 08:30 engine
Prior intraday metal-futures research documents strong and very rapid Gold reactions to US macroeconomic releases, particularly CPI and the Employment Report/nonfarm payrolls. V1 tests a NEW price-only question: after the first one-minute price discovery bar, is there enough same-direction continuation during the next five minutes to trade after costs?

No result from either engine may be used to modify the other.

## Instrument and data
Official research instrument: Databento CME `MGC.v.0`, dataset `GLBX.MDP3`, `ohlcv-1m`, continuous symbology.
Timezone: America/New_York.
Contract size: 10 troy ounces. Minimum fluctuation: $0.10/oz = $1 per MGC tick.

Requested historical window after authorization: 2021-09-01 through the latest complete accessible session no later than 2026-08-19.
The continuous series may contain non-adjusted rollover jumps. A QA amendment identical in principle to the prior NQ work is allowed ONLY before economic P&L and ONLY when Databento symbology proves a discontinuity occurs exactly at a continuous-contract mapping boundary.

## Frozen event manifest
Economic outcomes may not be opened until `EVENT_MANIFEST_V1.csv` is committed.
Sources:
- FOMC: Federal Reserve meeting calendars, regular policy-decision dates only; statement time 14:00 ET.
- CPI: BLS official release calendar, Consumer Price Index releases at 08:30 ET only.
- NFP: BLS official Employment Situation releases at 08:30 ET only.
Canceled releases are absent. Revised release dates caused by government funding lapses must use the actual BLS release date/time, not the originally scheduled date.

No other macro release (PPI, GDP, retail sales, JOLTS, claims, Powell speeches, etc.) is allowed in V1.

## Engine A — FOMC post-5-minute continuation
For every frozen regular FOMC decision date:
1. Event timestamp = 14:00 ET.
2. Signal = signed price change from the 14:00 minute OPEN through the 14:04 minute CLOSE, i.e. the first completed five minutes after the statement.
3. If signal > 0: LONG. If signal < 0: SHORT. Exact zero: no trade.
4. Entry = 14:05 minute OPEN, strictly after the signal is known.
5. Exit = 14:09 minute CLOSE, five minutes of post-signal exposure.
6. One trade per FOMC event. No stop, TP, threshold, surprise filter, SEP filter, press-conference filter, direction filter or volatility filter.

Sensitivity diagnostic, frozen now and NEVER eligible to rescue a failed primary rule:
- same entry 14:05, alternate exit 14:14 close (10-minute exposure). Report only.

## Engine B — CPI/NFP first-minute continuation
For every frozen CPI or Employment Situation release at 08:30 ET:
1. Signal = signed change from 08:30 minute OPEN through 08:30 minute CLOSE (first completed one-minute reaction bar).
2. If signal > 0: LONG. If signal < 0: SHORT. Exact zero: no trade.
3. Entry = 08:31 minute OPEN.
4. Exit = 08:35 minute CLOSE (five minutes of post-signal exposure).
5. One trade per release. If CPI and Employment Situation ever share the same timestamp/date, treat it as one event/trade rather than double-counting.
6. No threshold on first-minute move, no actual-vs-forecast data, no direction filter, stop, TP or volatility filter.

Sensitivity diagnostic, frozen now and NEVER eligible to rescue a failed primary rule:
- same entry 08:31, alternate exit 08:40 close. Report only.

## Friction
Edge test is done on 1 MGC contract before prop sizing.
PRIMARY: subtract 0.50 Gold points per round trip (= $5/MGC).
STRESS: subtract 1.00 Gold point per round trip (= $10/MGC).
These deliberately exceed a bare two-tick market-friction assumption and are meant to cover commission + adverse execution conservatively.

Net points = signed gross exit-entry Gold points - friction points.
Net USD/MGC = net points * 10.
Also report net return in basis points of entry price for cross-regime comparability.

## Temporal reporting — no parameter fitting
Rules are frozen once, so periods are reporting partitions rather than tuning stages.
- Historical support: 2021-09 through 2023-12.
- Recent confirmation: 2024-01 through 2025-12.
- Current holdout: 2026-01 through latest complete available event <=2026-08-19.
No period can be removed or used to retune the rule.

## Predeclared primary gates
### Engine A FOMC
All required across 2021-09 through 2026 holdout combined, plus persistence conditions:
1. >= 30 completed FOMC trades.
2. PRIMARY mean net points > 0.
3. PRIMARY PF >= 1.20.
4. Recent confirmation 2024-2025 aggregate net points > 0.
5. 2026 aggregate net points >= 0 if >=3 events are available.
6. STRESS mean net points > 0.
7. STRESS PF >= 1.05.
8. Remove best 10% of FOMC trades: remaining PRIMARY mean >= 0.

### Engine B CPI/NFP
All required:
1. >= 100 completed trades.
2. PRIMARY mean net points > 0.
3. PRIMARY PF >= 1.15.
4. At least 3 positive calendar years among 2022-2025 with sufficient events.
5. 2024-2025 aggregate PRIMARY mean > 0.
6. 2026 PRIMARY mean >= 0 with >=10 events.
7. STRESS mean net points > 0.
8. STRESS PF >= 1.05.
9. Remove best 10%: remaining PRIMARY mean >= 0.

## Terminal classifications
- both engines pass: `MGC_MACRO_V1_BOTH_PASS_FOR_PROP_RISK_OVERLAY_RESEARCH`
- FOMC only passes: `MGC_FOMC_ACCELERATOR_PASS_ONLY`
- CPI/NFP only passes: `MGC_0830_MACRO_ENGINE_PASS_ONLY`
- neither passes: `MGC_MACRO_V1_NO_GO`

A PASS is not live-ready because V1 has no protective stop. A separate pre-registered risk overlay and CFD execution replication are mandatory before any challenge/funded use.

## No-rescue rule
After MGC outcomes are opened, forbidden rescue operations include:
- FOMC SEP-only/non-SEP split;
- dovish/hawkish, rate-cut/rate-hike classification;
- CPI vs NFP selection;
- long-only/short-only;
- first-minute magnitude threshold;
- day/month/year exclusions;
- stop/TP optimization;
- changing signal/entry/exit horizons;
- selecting the alternate sensitivity horizon because it looks better.
Any such observation can only seed a future hypothesis requiring new untouched data.

## Cost authorization
The free Databento metadata probe estimated `MGC.v.0` OHLCV-1m 2021-09-01 through 2026-08-20 17:40Z at **$6.254315897822**. No MGC time-series request is authorized by this protocol. Explicit user authorization is required after the event manifest is frozen.
