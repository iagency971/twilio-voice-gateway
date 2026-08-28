# XAUUSD Z4 BREAK -> RETRACE -> E1/E2/E3 BULL REJECTION — PREREG v1.0

Date: 2026-08-27
Branch: `agent/xau-wick-zone-pro-dev`
Scope: retrospective research only; BUY only; no Pine/production authorization.

## 1. Research question

Test the following causal BUY setup without changing the frozen Z4 / E-BUY architecture after seeing its outcomes:

1. price breaks a **main Z4 zone upward**;
2. price later retraces and **at least wicks into that same main Z4**;
3. after that penetration, price interacts with one of the currently displayed E entry zones **E1/E2/E3** and prints the frozen bullish-rejection candle;
4. no M1 candle has closed below the lower boundary of the main Z4 before the entry;
5. BUY is executed on the next M1 open;
6. target is the next higher Z4 zone that was already causally known when the breakout was confirmed.

The E zone is an entry refiner, not the main structural invalidation zone.

## 2. User clarification frozen before outcome access

E1/E2/E3 **does not need to be contained inside the main Z4**.

It may:
- be fully inside the main Z4;
- overlap one of its boundaries;
- be partially outside;
- be fully outside, including below the main Z4 lower boundary.

A wick below the main Z4 lower boundary is allowed. The setup is invalidated **only by an M1 close strictly below the main Z4 lower boundary**.

Mandatory pullback gate: after the bullish breakout and before entry, at least one M1 candle range must intersect the main Z4 `[zlo, zhi]`. A contact/rejection of an E zone before any such main-Z4 penetration cannot trigger a trade.

If the first main-Z4 penetration and the valid E-zone bullish rejection occur on the same M1 candle, the setup may fire provided that candle closes at or above the main Z4 lower boundary.

## 3. Frozen market/domain

Primary scientific domain: current validated **US** E-BUY domain only.

- session: 08:00 <= America/New_York < 17:00;
- no overnight carry;
- breakout, main-Z4 retrace, E rejection, entry and outcome are evaluated within the same US session;
- BID M1 historical source already frozen for the project;
- H1: `2024-08-01T00:00:00Z <= event < 2025-08-01T00:00:00Z`;
- H2: `2025-08-01T00:00:00Z <= event < 2026-08-01T00:00:00Z`.

Asia and Europe are not part of this v1 study. No E-score/session transfer is authorized here.

## 4. Frozen zone architecture

Main zone and target zone:
- Z4, causal geometry only;
- C5 operational geometry/state;
- no future reaction/outcome columns permitted in geometry input.

E entry display is unchanged:
`Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`

Display rules unchanged:
- maximum 3 displayed BUY entry zones;
- local band `0 < distance <= 2.0v` at each C5 state;
- sticky carry;
- `0.20v` deduplication;
- slots labelled E1, E2, E3 by current display rank.

No E score is used.

## 5. Main-Z4 breakout event

A candidate breakout of a causally known Z4 is confirmed on M1 candle `b` when:
- that Z4 is below/straddling price in the causal C5 state available at `b`;
- `close[b] > main_zhi`;
- immediately before the crossing, the breakout is not already active for the same main-Z4 episode.

Implementation must suppress duplicate consecutive closes above the same main Z4. A single structural breakout episode may generate at most one executed trade.

At breakout confirmation, freeze:
- main Z4 geometry: `main_zlo`, `main_center`, `main_zhi`;
- the next higher causally known Z4 target: nearest Z4 with target lower boundary above `main_zhi` (and above entry when the trade eventually fires);
- session id.

If no valid higher Z4 target is causally available at breakout, the episode is recorded but is not trade-eligible.

## 6. Pullback and structural invalidation

After breakout:

### Main-zone penetration
`main_retrace_seen = true` as soon as a later M1 range intersects `[main_zlo, main_zhi]`.

For a pullback from above, a wick into the zone is sufficient. No body/close inside the zone is required.

### Invalidation before entry
If any M1 candle closes strictly below `main_zlo` before execution, the breakout episode is invalidated and cannot later reactivate without a new distinct bullish breakout.

Intrabar lows below `main_zlo` are explicitly allowed if the candle closes at or above `main_zlo`.

## 7. E1/E2/E3 eligibility

At every causal C5 display state after the breakout, the current displayed E1/E2/E3 zones may serve as entry zones regardless of their geometric relation to the main Z4.

For each candidate E zone record the relationship at contact:
- `INSIDE_MAIN`;
- `OVERLAP_MAIN`;
- `ABOVE_MAIN`;
- `BELOW_MAIN`.

The relationship is diagnostic only and is not a filter.

The E zone must be displayed causally before/contact-time; future displays cannot be backfilled.

A valid E contact requires the M1 range to intersect that E-zone interval.

## 8. Frozen bullish-rejection trigger

No new trigger tuning is allowed. Reuse the previously frozen `BULL_REJECTION` definition:

- `close > open`, and
- candle close position `(close-low)/(high-low) >= 0.70`.

The trigger is only eligible after `main_retrace_seen == true`.

On a trigger candle:
- if `close < main_zlo`, invalidation wins and no trade fires;
- otherwise the trigger is valid even if `low < main_zlo`.

Execution: **next M1 open**.

If the next open is at/above the frozen target Z4 lower boundary, classify `TARGET_ALREADY_REACHED_BEFORE_ENTRY` and do not execute.

If several E zones qualify on the same trigger candle, deterministic priority is E1, then E2, then E3. First valid executed rejection consumes the structural breakout episode.

## 9. Trade outcome

Stop/invalidation reference: frozen `main_zlo`, not the E-zone lower boundary.

After execution, scan to US session end:
- `TP_FIRST`: M1 high reaches or exceeds frozen target `target_zlo` before a close below `main_zlo`;
- `INVALIDATION_FIRST`: M1 close falls strictly below `main_zlo` before TP;
- `AMBIGUOUS`: both conditions occur on the same M1 candle;
- `NEITHER`: neither occurs before 17:00 NY.

Same-bar TP/close-invalidation is never resolved by assumed intrabar ordering.

## 10. Measurements frozen before outcomes

Report H1 and H2 separately, plus pooled diagnostics:

### Funnel
- main Z4 bullish breakouts;
- breakouts with a causally frozen higher-Z4 target;
- breakouts that wick/retrace into main Z4;
- pre-entry close invalidations;
- E contacts after main retrace;
- bullish-rejection triggers;
- executed trades.

### Outcome
- TP_FIRST / INVALIDATION_FIRST / NEITHER / AMBIGUOUS;
- resolved TP rate = `TP_FIRST / (TP_FIRST + INVALIDATION_FIRST + NEITHER)` after removing ambiguous cases;
- strict directional rate among terminal TP/invalid only = `TP_FIRST / (TP_FIRST + INVALIDATION_FIRST)`;
- median and p90 time breakout->main retrace;
- median and p90 time main retrace->trigger;
- median and p90 time entry->TP / invalidation;
- MFE and MAE in `v`;
- stop distance `(entry-main_zlo)/v`;
- target distance `(target_zlo-entry)/v`;
- nominal reward/risk `(target_zlo-entry)/(entry-main_zlo)` for positive-risk trades.

### E-zone diagnostics
Report separately for E1, E2, E3:
- opportunities/contact count;
- fired count/share;
- TP/invalid/neither/ambiguous;
- terminal TP rate;
- median nominal R:R.

Also report by E family and by E-vs-main relation (`INSIDE_MAIN`, `OVERLAP_MAIN`, `ABOVE_MAIN`, `BELOW_MAIN`).

### Wick-below-main diagnostic
Because wick breaches are allowed, report:
- share of executed trades where the trigger/pullback low traded below `main_zlo` before entry but no candle closed below;
- outcome split for that subset versus no-wick-breach subset.

This diagnostic must not retroactively become an entry filter in v1.

## 11. Episode handling / anti-duplication

- One executed trade maximum per main-Z4 bullish-breakout episode.
- A breakout episode ends at the earliest of: executed trade consumed, close invalidation, target reached before entry, or US session end.
- No repeated trade from multiple E rejections in the same structural breakout episode.
- No tuning of timeouts, rejection threshold, E rank, family, Z4 geometry, or target definition after outcome access.

## 12. Interpretation

This is a retrospective hypothesis test, not production authorization.

Primary evidence requirement is H1/H2 directional coherence and adequate sample size. No single pooled rate may override a material H1/H2 contradiction.

E1/E2/E3, family, geometry-relation and wick-breach strata are diagnostics unless a future study preregisters one as a filter.

Any later change to the setup requires a new preregistration before re-reading outcomes.
