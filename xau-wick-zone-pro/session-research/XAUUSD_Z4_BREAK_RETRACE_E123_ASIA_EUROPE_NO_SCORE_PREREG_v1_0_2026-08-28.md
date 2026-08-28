# XAUUSD Z4 breakout → retrace → E1/E2/E3 bullish rejection — Asia / Europe no-score preregistration v1.0

Frozen: 2026-08-28 before opening any Asia/Europe outcomes for this structural setup.

## Purpose

Evaluate the already defined BUY structural setup outside the US session, **without E_BUY_US or any other score**, while preserving the exact structural mechanics used in the US retrospective study.

## Frozen structural mechanics

For every tested session:

1. A causal main Z4 is broken upward by a confirmed M1 close.
2. The next higher causal Z4 known at breakout is frozen as the TP reference.
3. After breakout, price must retrace at least by wick into the original main Z4.
4. E1/E2/E3 may be fully inside, overlap, lie above, or lie below the main Z4.
5. A wick below `main_zlo` is allowed.
6. Only an M1 close strictly below frozen `main_zlo` invalidates the setup before or after entry.
7. After the mandatory main-Z4 retrace, a current causal sticky E1/E2/E3 must be touched.
8. Legacy bullish-rejection trigger remains unchanged for comparability: `close > open` and close-position `(close-low)/(high-low) >= 0.70`.
9. If several E zones are touched on the same rejection candle, the lowest rank number (E1 before E2 before E3) is selected, identical to the US runner.
10. Entry = next M1 open inside the same tested session.
11. TP = first touch of frozen next-higher Z4 lower bound `target_zlo`.
12. Invalidation = first confirmed M1 close strictly below frozen `main_zlo`.
13. Same-M1 TP + invalidation = `AMBIGUOUS`.
14. Outcome horizon stops at the end of the tested session.
15. One rejection candle may execute at most one active structural episode, with the same deterministic arbitration as the frozen US runner.

No score, no E>= threshold, no family filter, no rank filter, no post-hoc time filter, no model fit.

## Frozen E-zone architecture

Use the same architecture and cadence as the current structural study:

`Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`, sticky max-3, C5.

The session predicate is changed only to make the already frozen candidate-generation functions evaluate the requested session. Candidate geometry/families/dedup/sticky logic are otherwise unchanged.

## Sessions

All times are `America/New_York`.

### A. ASIA_BROAD
- 18:00 inclusive → 03:00 exclusive, crossing midnight.
- Session identity is the NY calendar date on which the 18:00 session begins.
- Episodes may persist across midnight within the same 18–03 session.

Prespecified descriptive subperiods by **trigger time**:
- `ASIA_EXP_18_21`: 18:00–21:00.
- `ASIA_CORE_PART_21_03`: 21:00–03:00.

These subperiods are descriptive; do not choose one after results and call it primary.

### B. ASIA_CORE_STANDALONE
- 21:00 inclusive → 03:00 exclusive, crossing midnight.
- Session identity is the NY calendar date on which the 21:00 session begins.
- **No episode/state from 18:00–21:00 is inherited.** The structural session starts at 21:00.

This standalone run is prespecified because 21–03 is the independently location/stability-authorized Asia Core window.

### C. EUROPE
- 03:00 inclusive → 08:00 exclusive.
- Session identity = same NY calendar date.
- Session ends before the US 08:00 window; no US episode/outcome continuation.

## Historical windows

Use the same two 12-month windows as the US structural study:

- H1: `2024-08-01 00:00 UTC <= breakout < 2025-08-01 00:00 UTC`.
- H2: `2025-08-01 00:00 UTC <= breakout < 2026-08-01 00:00 UTC`.

Window assignment is by breakout timestamp.

## Primary reporting for each session/window

Report without optimization:

- main Z4 bullish breakouts;
- breakouts with higher causal Z4 target;
- main-Z4 retraces by wick-or-more;
- executed trades;
- TP_FIRST / INVALIDATION_FIRST / NEITHER / AMBIGUOUS;
- terminal TP rate = TP / (TP + invalidation);
- resolved TP rate including NEITHER;
- stop distance v, target distance v, nominal RR, MFE v, MAE v;
- by E1/E2/E3;
- by E family;
- by E-vs-main relation: `INSIDE_MAIN`, `OVERLAP_MAIN`, `ABOVE_MAIN`, `BELOW_MAIN`;
- wick-below-main diagnostic;
- structural expectancy before costs for terminal trades: TP = `nominal_rr`, invalidation = -1R;
- theoretical PF_R from the same normalized terminal values.

## Prespecified structural subgroup reporting

`ABOVE_MAIN` must be reported because it was the strongest US post-hoc candidate, but **it is not assumed to be superior in Asia or Europe**.

For each session and H1/H2 report `ABOVE_MAIN` N, TP, invalidations, terminal TP rate, Wilson 95%, normalized structural expectancy/PF_R.

No subgroup may be promoted solely because it is numerically best in this study.

## Replication interpretation

A session-level structural candidate is considered directionally replicated only if:

- the same prespecified subgroup has terminal N >= 20 in H1 and >= 20 in H2;
- terminal TP rate > 50% in both H1 and H2;
- normalized expectancy > 0R in both H1 and H2.

This is a research classification only, not production authorization. No failed result may be rescued by moving session boundaries, changing BR70, choosing a family/rank, or adding a score after outcomes are opened.

## Fresh data

Historical H1/H2 is the requested study. Any August-2026 fresh diagnostic may be run only after historical outputs exist and must be labeled descriptive unless separately preregistered before its outcomes are opened.

## Production claims

No Pine BUY marker, alert, score, live profitability or CFD execution claim is authorized by this preregistration alone.
