# XAUUSD Z4 breakout → retrace → E ABOVE_MAIN fresh August confirmation v1.0

Date: 2026-08-28
Branch: `agent/xau-wick-zone-pro-dev`

## Purpose
Confirm, on a fresh post-H2 period, the retrospective structural hypothesis observed independently in both H1 and H2: after a bullish close breakout of a frozen causal main Z4 and a subsequent wick-or-body retracement into that same main Z4, a bullish rejection on a currently displayed causal E zone that lies entirely ABOVE the frozen main Z4 may have a materially higher probability of reaching the next higher frozen causal Z4 before a close-based invalidation of the main Z4.

## Frozen setup
- Direction: BUY only.
- Session: 08:00–17:00 `America/New_York`.
- Main zone: causal Z4 frozen at bullish breakout.
- Breakout: M1 close crosses above the main Z4.
- Mandatory retracement: a later M1 range must intersect the frozen main Z4; wick contact is sufficient.
- Main invalidation: M1 CLOSE strictly below frozen `main_zlo`; a wick below `main_zlo` is explicitly allowed and is NOT an invalidation.
- Entry zones: exact frozen causal sticky E1/E2/E3 architecture from `xau_ebuy_coverage_v0_4_sticky.py`.
- E geometry eligibility for the primary hypothesis: `e_zlo > main_zhi` (`ABOVE_MAIN`). The E may otherwise be E1/E2/E3 and any frozen family; no rank/family cherry-pick is permitted.
- Trigger: bullish candle with `close > open` and close-position >= 0.70 on a touched E zone, only after the mandatory main-Z4 retracement.
- If one trigger candle touches multiple E zones, retain the engine's frozen lowest slot-rank selection.
- Execution: next M1 open.
- Stop/invalidation event: first later M1 close strictly below frozen `main_zlo`.
- TP: first touch of `target_zlo` of the next higher causal Z4 frozen at breakout.
- No score, no E80/E90, no refit, no parameter optimization.

## Fresh period
- Primary fresh domain: August 2026 data strictly after H2 (`2026-08-01T00:00:00Z` onward) and available before execution of this preregistered workflow.
- The workflow records the exact source SHA-256 and the last available raw timestamp. No rows after the downloaded file's last timestamp can be inferred or synthesized.
- July 2026 may be downloaded only as causal warmup for state/geometry construction; July outcomes are not part of the fresh endpoint.

## Primary endpoint
For executed `ABOVE_MAIN` trades in the fresh August domain:
- terminal TP rate = `TP_FIRST / (TP_FIRST + INVALIDATION_FIRST)`.
- `NEITHER` and ambiguous bars are reported separately.

## Confirmation labels
- `DIRECTIONAL_CONFIRMATION` if fresh `ABOVE_MAIN` terminal denominator >= 10 and terminal TP rate > 0.50.
- `STRONG_CONFIRMATION` only if, in addition, the two-sided 95% Wilson lower bound is > 0.50.
- Otherwise `NOT_CONFIRMED`.

These labels are confirmatory diagnostics only. Even a pass does not independently authorize production deployment because the fresh sample can be short.

## Mandatory secondary diagnostics
Report without filtering:
- all-trades fresh rate;
- E1/E2/E3 counts/rates;
- ABOVE / OVERLAP / INSIDE / BELOW geometry groups;
- wick-below-main vs no-wick-below-main;
- nominal RR and terminal R expectancy for TP/SL-only cases (`TP=nominal_rr`, invalidation=-1), before spread/commission;
- exact fresh session count and last source timestamp.

## Anti-leakage
This preregistration is committed before reading any fresh-August US outcome from this setup. Historical H1/H2 values motivated only the single frozen hypothesis `ABOVE_MAIN`; no fresh result may be used to alter the rule, threshold, family, rank, trigger, stop, target, or session inside this test.

## Authorization
`NONE_PREOUTCOME_FRESH_CONFIRMATION_ONLY`
