# MNQ/NQ 12-Model — Official Databento CME Validation V1.1

Status: `PRE_ECONOMIC_ROLL_QA_REPAIR_FROZEN`

This amendment is written **before the pinned external engine has been run on the official CME data and before any official-CME trade P&L has been opened**.

It changes one data-QA rule only. All signal logic, execution logic, friction assumptions, August confirmatory dates and economic gates from `PROTOCOL_CME_VALIDATION_V1.md` remain unchanged.

## Why V1 data QA stopped

The paid Databento request returned 80,594 official `NQ.v.0` OHLCV-1m rows with:
- zero duplicate timestamps;
- zero OHLC consistency violations;
- all 13 expected Aug3-Aug19 RTH sessions;
- exactly 390 RTH bars on the minimum and median complete August day;
- plausible NQ price scale.

The sole V1 QA failure was one >250-point adjacent-minute jump at 2026-06-16 20:00 America/New_York (2026-06-17 00:00 UTC).

## Vendor-defined continuous-contract behavior

Databento continuous futures are original, **unadjusted** prices. `NQ.v.0` is volume-ranked and maps to the contract with the highest previous-day volume. Databento explicitly does not back-adjust rollover jumps.

Therefore, a price discontinuity exactly at a verified continuous-contract mapping change is not a corrupt tick or impossible market move; it is the basis difference between two different tradable contracts.

## Outcome-blind free symbology diagnostic

No additional time-series data was purchased. Databento's free symbology endpoint resolved:
- `NQ.v.0` -> instrument `42004058` / raw symbol `NQM6` from 2026-06-12 through the start of 2026-06-17;
- `NQ.v.0` -> instrument `42004177` / raw symbol `NQU6` from 2026-06-17 onward in the diagnostic interval.

The archived official CME series contains exactly one adjacent-minute close jump >250 points:
- previous bar: 2026-06-16 19:59 ET, close 30012.75;
- next bar: 2026-06-16 20:00 ET = 2026-06-17 00:00 UTC, open 30330.50, close 30343.25;
- previous-close to new open: +317.75 points;
- the timestamp coincides exactly with the Databento `NQM6 -> NQU6` continuous mapping boundary.

There are zero >250-point adjacent-minute jumps during the confirmatory Aug3-Aug19 window.

## Repaired data-QA rule

Replace V1 rule 6 with:

> **6. Continuous-roll integrity:** Any adjacent-minute absolute close jump >250 NQ points fails QA **unless** its UTC date/time is exactly attributable to a Databento-resolved `NQ.v.0` underlying instrument mapping change. Every exempted jump must be enumerated. Any non-roll >250-point jump fails. The confirmatory Aug3-Aug19 window must contain zero such roll discontinuities.

This rule is deterministic and based on Databento's published data semantics plus the free symbology mapping, not on strategy outcomes.

## Other data gates — unchanged

1. `NQ.v.0` resolves successfully.
2. Timestamp uniqueness after normalization.
3. Zero OHLC consistency violations.
4. All expected Aug3-Aug19 RTH dates present.
5. Median complete-session RTH minute count >=380.
6. Repaired continuous-roll integrity rule above.
7. Plausible NQ price scale.

If these pass, official CME economic evaluation may open exactly once from the already-downloaded archived CME file. No second paid market-data request is permitted for V1.1.

## Economic protocol — unchanged

Pinned external repository/commit:
- `s-k-28/nq-es-trader-5k-payout`
- `d472d6b442764c2adafbba4bbeb96881c100e3e0`

Confirmatory window: 2026-08-03 through 2026-08-19 ET.

Additional friction after frozen trade-path generation:
- PRIMARY: -1.0 NQ point / round trip;
- STRESS: -2.0 NQ points / round trip.

All August gates from V1 remain unchanged:
- data QA pass;
- N >=25;
- >=1.5 trades / observed RTH day;
- PRIMARY mean >= +0.10R;
- PRIMARY PF >=1.25;
- Aug3-11 total R >0;
- Aug12-19 total R >0;
- PRIMARY closed-trade max DD <=7R;
- after removing best 10% of trades, remaining PRIMARY mean >=0;
- STRESS mean >0;
- STRESS PF >=1.10.

All must pass for `CME_AUGUST_CONFIRMATORY_PASS_FOR_PROPFIRM_SIMULATION`; otherwise `CME_AUGUST_CONFIRMATORY_NO_GO`.

No model removal, direction filter, date exclusion, parameter adjustment or economic rescue is allowed after official CME outcomes are opened.
