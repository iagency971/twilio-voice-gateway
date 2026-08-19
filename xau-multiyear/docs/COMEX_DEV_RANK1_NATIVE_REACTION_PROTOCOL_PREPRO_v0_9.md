# COMEX DEV_RANK1 — Native reaction protocol PRE-PRO v0.9

Date: 2026-08-19
Branch: `agent/xau-comex-acquisition-plan`
Status: PRE-PRO DRAFT — NOT EXECUTABLE / NO REACTION OUTCOMES MAY BE INSPECTED

## 1. Purpose and scientific boundary

This document prepares the reaction study that follows completion of the exact-contact phase for native COMEX VWAP / POC / VAH / VAL levels.

It is deliberately written **before any reaction outcome is computed or inspected**. It is a draft for Pro-level methodological audit. It must not be treated as a frozen executable preregistration until Pro has reviewed the unresolved design choices listed below and a final v1 is published.

This draft is bound to the completed exact-contact population:

- 368 native levels;
- 238 exact contacts during the frozen next eligible GC auction session J+1;
- 130 resolved no-contact levels;
- 0 unresolved;
- final 368 status SHA-256: `8a825b0bc1deba51959b78ab6e62206fe49232e76329558e83949bf6d3d4151a`.

Canonical checkpoint: `CHECKPOINT_COMEX_NATIVE_N2_EXACT_CONTACT_COMPLETE_2026-08-19.md`.

The 238/368 contact result is incidence only. No edge, profitability, win rate, rejection quality, or promotion conclusion follows from it.

## 2. Two research tracks must remain separate

### Track A — reaction after exact J+1 contact

Population: the 238 levels whose first exact raw-GC contact was confirmed during the frozen next eligible GC auction session.

Question:

> Conditional on the first exact contact of a native COMEX level in J+1, what is the subsequent GC price reaction, in which direction, with what magnitude, adverse penetration, timing and persistence, and does that reaction differ from a suitably matched non-level baseline?

### Track B — lifetime / persistence beyond J+1

Track B is **not part of the present reaction computation** and must not be mixed into Track A.

Questions to preserve for Pro:

- among the 130 levels not contacted in J+1, what fraction first contact in J+2, J+3, J+5, etc.;
- how long should a native level remain valid before expiration;
- after a first J+1 contact, do later retests retain information;
- how should later-session testing handle raw-contract roll / expiry without introducing continuous-contract or adjusted-price artifacts.

No J+2+ market-data acquisition or outcome inspection is authorized by this draft.

## 3. Allowed data for Track A before any new purchase

The first reaction pass should use only already-owned data unless Pro concludes that exact post-contact tape is scientifically necessary.

Allowed inputs:

1. final exact-contact table for the 368 native levels;
2. N2 raw `trades` already acquired for each contact candidate minute, used to recover the exact first contact timestamp and the trades remaining after that contact inside the already-downloaded interval;
3. N1 raw-contract `ohlcv-1m` already acquired for the **full eligible next auction session J+1**;
4. fixed source-session information that was already known before J+1 and was used to create VWAP / POC / VAH / VAL, but only if its provenance and availability are QA-confirmed before execution.

Not allowed in Track A source/reaction definition:

- XAUUSD / CFD price to redefine a COMEX contact or level;
- GC continuous price in place of the raw source instrument;
- J+2 or later data;
- data selected because the reaction later looks good;
- new paid tape without a separate quote and explicit user authorization.

Primary reaction should be measured on **the same raw GC instrument that created the level**. Translation to XAUUSD execution is a later economic layer, not the native-zone reaction test.

## 4. Event time

For each of the 238 events:

- level price `L` = frozen `contact_tick_price` on the 0.10 GC tick;
- event time `t0` = first chronological raw GC trade in J+1 whose executed price equals `L` exactly;
- only the **first exact contact** is the Track-A event;
- later retests of the same level are not additional primary observations.

The contact minute is the UTC minute containing `t0`.

## 5. Causal approach-side definition

Reaction direction must not be hard-coded by level type. POC, VAH, VAL and VWAP may be approached from either side.

For every exact contact, define the approach side mechanically using information available at or before `t0`:

1. search already-owned raw trades in the contact interval strictly before `t0`;
2. use the last trade whose price is strictly different from `L`;
3. if that trade price is below `L`, label `APPROACH_FROM_BELOW`;
4. if above `L`, label `APPROACH_FROM_ABOVE`;
5. if no such raw trade exists inside the downloaded contact interval, fall back to the latest prior completed J+1 M1 close strictly different from `L`;
6. if no causal side can be established, label `APPROACH_UNDEFINED` — do not guess.

Define `away_sign`:

- approach from above: `away_sign = +1`;
- approach from below: `away_sign = -1`.

For any later price `P(t)`, define signed displacement in GC ticks:

`D_away(t) = away_sign * (P(t) - L) / 0.10`

Interpretation:

- `D_away > 0` = price has moved back away from the level toward the side it came from;
- `D_away < 0` = price has penetrated through the level to the opposite side.

This prevents any ex-post assignment of bullish/bearish behavior by level family.

## 6. Data-resolution rule and no-lookahead constraint

The exact N2 tape exists for the contact candidate minute(s), but the rest of J+1 is owned as M1 OHLCV.

Therefore Track A must distinguish two resolution regimes.

### R0 — exact residual contact-minute module

Use raw trades from `t0` through the end of the contact minute, but only where those trades are already present in the acquired N2 raw interval.

This permits exact intraminute excursion after first contact for the already-owned residual tape.

### R1+ — completed-M1 module

After the contact minute, use only **completed one-minute bars** from N1.

M1 high/low may be used to measure the magnitude of favorable/adverse excursion over completed bars because they are executed-price extrema.

M1 data may **not** be used to infer the order of two intrabar events. In particular, if an M1 bar reaches both an away threshold and a penetration threshold, Track A may not claim which occurred first.

Consequences:

- no stop/target win-rate simulation from ambiguous M1 bars;
- no `rejection-before-failure` label from M1 alone;
- no exact retest count from an M1 high/low crossing;
- no path-order metric unless exact tape is separately acquired and authorized.

## 7. Candidate measurement horizons — to be validated by Pro

To avoid partial-minute lookahead, horizons are bar-aligned rather than exact wall-clock cutoffs.

Candidate family:

- `R0`: residual contact minute on exact already-owned tape;
- `B1`: residual contact minute + next 1 completed M1 bar;
- `B5`: residual contact minute + next 5 completed M1 bars;
- `B15`: residual contact minute + next 15 completed M1 bars;
- `B30`: residual contact minute + next 30 completed M1 bars;
- `B60`: residual contact minute + next 60 completed M1 bars;
- `SC`: from exact contact to the end of the frozen J+1 auction session.

For each event/horizon store the actual elapsed seconds from `t0` to the measurement endpoint.

No horizon crosses into J+2. If the session ends before a candidate B-horizon completes, that horizon is censored/missing for that event; do not extend or impute it. `SC` remains the session-end endpoint.

**Candidate primary horizon for Pro review:** `B15`. This is not yet frozen. Pro must either approve it or replace it before any reaction outcomes are computed.

## 8. Continuous level-centric endpoints

For each valid directional event and each horizon H, compute from `D_away(t)`:

1. `AWAY_MFE_TICKS_H = max(D_away)`;
2. `THROUGH_PENETRATION_TICKS_H = max(-D_away)`;
3. `REACTION_BALANCE_TICKS_H = AWAY_MFE_TICKS_H - THROUGH_PENETRATION_TICKS_H`;
4. `END_SIGNED_TICKS_H = D_away` at the horizon endpoint.

Also retain the same values in GC price units.

For `APPROACH_UNDEFINED` events:

- retain unsigned absolute excursions and QA information;
- exclude them from direction-signed primary endpoints rather than assigning a side post hoc.

No binary `win`, `clean rejection`, `accepted`, `failed`, `held`, `support`, or `resistance` label is primary in v0.9. Thresholded labels, if desired, must be frozen by Pro before outcome computation.

## 9. Volatility normalization

Raw GC ticks remain mandatory outputs.

A normalized companion is desirable because 2011–2018 volatility regimes differ, but the normalizer must be known before contact and must not depend on future J+1 reaction.

Candidate normalizer for Pro review:

- completed source-session high-low range in GC ticks, known when the native level becomes known.

Candidate normalized metrics:

- `AWAY_MFE / source_session_range`;
- `THROUGH_PENETRATION / source_session_range`;
- `REACTION_BALANCE / source_session_range`.

Before execution, a zero-outcome QA must prove that the source-session range is available with stable provenance for all relevant source sessions. If not, Pro must choose a replacement causal normalizer before results are computed.

Do not choose a normalizer after comparing which one makes the result strongest.

## 10. Contact-time and context variables

Context is descriptive / stratification information, not an ex-ante filter.

Record at minimum:

- level type: POC / VAH / VAL / VWAP;
- source research date and eligible next-session date;
- year;
- exact UTC contact time;
- ET clock time with DST-aware conversion;
- minutes since canonical GC auction-session open;
- approach side;
- source raw instrument;
- contact acquisition stage 1 / 2 / 3 as QA metadata;
- source-session range if approved as normalizer.

Do **not** pre-filter to US, London, Asia, overlap, or any other session bucket.

If named session buckets are later shown, their boundaries must be frozen before outcome inspection and they are descriptive unless Pro explicitly preregisters a hypothesis involving them.

Continuous contact time / minute-of-session should be retained even if buckets are added.

## 11. Dependence and analysis unit

The 238 contacted levels are not 238 independent trading days.

VWAP / POC / VAH / VAL from the same source/retest date can share the same price path and are correlated.

Primary inference must therefore cluster at the **source/retest trading-date level**, consistent with the earlier native-retest freeze.

Rules:

- descriptive tables may show level-level N;
- confidence intervals / resampling must operate on date clusters, not independent level rows;
- overlapping event windows remain in descriptive level-type outputs but their dependence is absorbed by date-level clustering;
- no level family may be dropped because its DEV_RANK1 reaction looks weak.

Candidate inference engine for Pro review:

- 10,000 date-cluster bootstrap resamples;
- fixed RNG seed written into final protocol;
- medians and interquartile ranges as robust primary summaries;
- confidence intervals reported for aggregate and preregistered type-specific estimates.

Pro must validate or replace this inference plan before execution.

## 12. Matched-control requirement — unresolved PRE-PRO design gate

A raw post-contact excursion is not by itself sufficient to claim that a COMEX native level creates an edge. The earlier frozen acquisition protocol explicitly requires matched controls preserving at minimum year, contact time-of-day, approach/direction and volatility context.

The control construction is therefore a **blocking PRE-PRO decision**. No edge claim and no full reaction run should be released until Pro selects and freezes a control method.

### Candidate Control A — zero-new-cost M1 persistence control

Purpose: test whether post-contact directional persistence after the contact minute differs from ordinary matched market moments using already-owned M1.

Observed anchor:

- contact-minute close, after the exact level has been contacted.

Control anchors:

- minute closes from other eligible DEV_RANK1 J+1 sessions;
- no outcome-based selection;
- exclude minutes inside a fixed exclusion window around known native exact-contact minutes to avoid contaminating controls with another native event;
- match on year, fixed time-of-day bin, causal pre-anchor direction proxy and causal pre-anchor volatility;
- deterministic nearest-neighbor selection with timestamp tie-break, with K fixed before outcomes.

Outcomes use subsequent completed M1 bars only.

This is a **persistence** control, not an exact-tape replica of the immediate contact microstructure.

### Candidate Control B — exact-tape matched pseudo-events

If Pro considers exact intraminute control essential, construct a matched pseudo-event manifest first, quote it with Databento metadata only, stop for explicit user authorization, then acquire exact tape under a new financial cap.

No such acquisition is authorized by this draft.

### Pro must decide

Pro must explicitly answer:

1. Is Control A sufficient for DEV_RANK1 screening of a native reaction effect?
2. If not, what exact pseudo-event construction is scientifically defensible and outcome-free?
3. What time-of-day bin width, volatility metric, exclusion window and number of controls K should be frozen?
4. Should the primary edge estimand be paired contact-minus-control `REACTION_BALANCE`, `END_SIGNED`, or another continuous metric?

## 13. Multiple-horizon / multiple-type protection

The candidate horizon family and four level types create multiple comparisons.

Before execution, Pro must designate:

- one primary horizon;
- one primary continuous edge endpoint;
- aggregate native-level test as primary or not;
- status of POC / VAH / VAL / VWAP analyses as secondary / confirmatory / descriptive;
- multiplicity handling for secondary inferential claims.

After results are visible, the study may not redefine the winner as whichever type/horizon looks best.

All preregistered horizons/types must remain in the output, including weak or adverse ones.

## 14. What may be computed before Pro

Allowed before Pro, provided no price-outcome summaries are produced:

- file/integrity inventory;
- artifact availability and checksums;
- cardinality checks: 368 final levels / 238 contacts;
- confirmation that N1 contains the required J+1 M1 windows;
- confirmation that N2 raw contact files are present for the 238 events;
- missingness counts caused purely by file availability;
- verification that causal context fields can be generated without reading post-contact outcome values.

Not allowed before Pro:

- MFE / MAE / penetration distributions;
- level-type reaction rankings;
- session/time reaction rankings;
- threshold search;
- best horizon selection;
- profitability or entry-model simulation.

## 15. Track B — lifetime / later contact questions preserved for Pro

Track B must be separately preregistered because extending a native level beyond J+1 changes the scientific question and raises contract-roll problems.

Pro should specifically review:

1. maximum lifetime to test: J+2 / J+3 / J+5 / J+10 / until invalidation / other;
2. whether an untouched absolute price level can legitimately persist when the source raw GC contract is no longer active;
3. whether later contact must remain on the original raw instrument, and how to classify a level when that instrument stops trading;
4. whether a level may transfer to a new GC expiry without an adjusted/spread-transposed mapping — default v0.9 position: **no transfer unless a causal mapping is preregistered**;
5. whether first retest and later retests are separate hypotheses;
6. whether a first exact contact consumes/invalidates a level for the primary lifetime study.

No later-session result may be used to repair the J+1 Track-A result.

## 16. Economic XAUUSD layer remains downstream

Even a robust GC reaction is not yet an executable XAUUSD strategy.

Required sequence:

1. establish or reject a native GC reaction effect;
2. if justified, replicate under DEV_RANK2 according to a Pro-approved promotion gate;
3. only then map a causal entry rule to XAUUSD using the frozen execution/cost framework;
4. do not use CFD/XAU price to retroactively define native COMEX levels.

No XAUUSD win-rate target is tested in this reaction draft.

## 17. Locked-state preservation

Until Pro review and publication of a final reaction v1:

- reaction outcome run: NOT AUTHORIZED;
- new Databento spend: NOT AUTHORIZED;
- Track-B J+2+ acquisition: NOT AUTHORIZED;
- DEV_RANK2: CLOSED;
- RETRO_CONFIRM: CLOSED;
- LOCKED_COMEX_TEST: CLOSED;
- existing-POI B1/B2 path: remains closed NO_GO.

## 18. PRE-PRO decisions required before final freeze

Pro must return an explicit verdict on each item:

- APPROVE / MODIFY approach-side rule;
- APPROVE / MODIFY bar-aligned horizons and choose primary horizon;
- APPROVE / MODIFY continuous endpoints and choose primary endpoint;
- APPROVE / MODIFY source-session-range normalization;
- APPROVE / MODIFY date-cluster inference;
- SELECT matched-control design and all its parameters;
- DEFINE multiplicity handling;
- DEFINE the DEV_RANK1 -> DEV_RANK2 promotion gate without seeing reaction outcomes;
- ADVISE whether Track B should be designed before or after Track-A reaction execution;
- flag any hidden lookahead, survivorship, roll, intrabar, dependence, or selection-bias issue.

Only after these decisions are incorporated may `COMEX_DEV_RANK1_NATIVE_REACTION_PROTOCOL_v1.md` be published as FROZEN and the reaction extraction run begin.
