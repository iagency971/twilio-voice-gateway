# XAUUSD Z4 — E-BUY reaction development preregistration v1.0 CONDITIONAL

**Frozen:** 2026-08-25 while the frozen E-BUY coverage OOS replication v1.0 is still running, before its result and before any E-BUY reaction outcome is opened.  
**Activation condition:** this protocol may execute only if `EBUY_COVERAGE_OOS_REPLICATION_PASS` is obtained with both OOS_H1 and OOS_H2 passing all frozen coverage/stability gates.  
**Scope:** BUY only.

## 1. Frozen location engine

If activated, use E-BUY v0.4 unchanged:

`Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`

with the frozen sticky top-3 display rule. No location generator, local-band threshold, de-duplication tolerance, family parameter or display parameter may be retuned using reaction outcomes.

## 2. Data separation

Primary BID source remains the frozen Dukascopy monthly files.

- **REACTION_DEV:** 2024-08-01 00:00 UTC <= t < 2025-08-01 00:00 UTC (`OOS_H1`). Outcomes may be opened here after activation.
- **REACTION_HOLDOUT:** 2025-08-01 00:00 UTC <= t < 2026-08-01 00:00 UTC (`OOS_H2`). No reaction/TP/MFE/MAE/trigger result from H2 may be computed or inspected during reaction development.

The E-BUY location engine runs causally/continuously. H2 is reserved for a later preregistered frozen reaction validation.

## 3. BUY context and target

Study only New York session times before 17:00 America/New_York.

An E-BUY zone is actionable only while:
- it is one of the frozen displayed top-3 zones;
- its center is below current price;
- at least one causal Z4 exists strictly above current close.

For every C5 snapshot, define `TP1_Z4` as the **nearest causal Z4 above current close by lower boundary**. Its geometry is known at that snapshot.

For a contact occurring between C5 snapshots, freeze the target to `TP1_Z4` from the most recent confirmed C5 snapshot at or before the contact. No later target substitution is allowed for that contact episode.

This study does not use the old `REVISIT_240` endpoint to define success. All outcomes stop at 17:00 New York on the same session day.

## 4. Stateful zone identity and duplicate prevention

Reconstruct displayed zones with the frozen sticky engine and assign deterministic `display_episode_id` through the same one-step matching rule used by the sticky pool.

A display episode begins when a zone enters a displayed slot without matching a displayed zone from the immediately preceding eligible C5 snapshot. It continues across matched sticky snapshots and terminates when the zone is crossed below, leaves the local band, loses underlying identity, or the session ends.

Each display episode can generate **at most one fresh contact opportunity per US session**. After its first contact, it is consumed for that session even if price leaves and retouches it. This prevents repeated counting of the same support idea.

## 5. Arming and first contact

A displayed zone is not eligible for a fresh contact merely because its center is below price.

It becomes **ARMED** only when, while displayed, a confirmed M1 close is strictly above its current `zhi`. If the zone first appears while price is already inside/under it, wait until a confirmed close above `zhi` before arming.

After arming, first contact is the first subsequent M1 bar before 17:00 NY whose range overlaps the frozen current zone: `high >= zlo` and `low <= zhi`.

The zone/target/features used at contact are those known from the most recent confirmed C5 state before or at that M1 bar. If the zone ceases to be displayed/eligible before contact, the arm is cancelled.

## 6. Zone invalidation

For post-contact outcomes, zone invalidation is the first confirmed M1 **close strictly below the contact-state `zlo`**. The contact-state zone bounds are frozen for that episode's reaction outcome; later geometry updates do not move the invalidation threshold.

The evaluation horizon ends at the earliest of:
- 17:00 America/New_York same day;
- data end.

## 7. Contact outcomes — fixed before DEV outcomes

Reference volatility `v_contact` = causal TR60 active-M1 median known at contact.

Reference direct-touch entry price for path diagnostics = contact-state `zhi` (the first boundary approached from above). This is an analytical reference, not yet a live fill/slippage claim.

Report without selection:

### A. First-passage reaction tests
- `FP_0.50v_vs_0.25v`: price reaches `entry_ref + 0.50*v_contact` before `entry_ref - 0.25*v_contact`, before 17:00.
- `FP_1.00v_vs_0.50v`.
- `FP_1.50v_vs_0.75v`.

If both barriers are contained inside the same M1 bar and intrabar order is unknowable, mark that barrier contest `AMBIGUOUS` and exclude it from the resolved-rate denominator; report ambiguity rate separately.

### B. Upper-Z4 destination outcome
`TP1_BEFORE_INVALIDATION_US_END` = the frozen TP1 Z4 lower boundary is reached after contact before the first confirmed M1 close below the contact-state zlo and before 17:00 NY.

Also report:
- neither TP1 nor invalidation by 17:00;
- invalidation before TP1;
- same-M1 ambiguity where ordering cannot be resolved from OHLC.

### C. Continuous diagnostics
Report MFE and MAE from `entry_ref` in `v_contact` units until 17:00, plus time-to-TP1 / time-to-invalidation when present. These diagnostics may not redefine the fixed first-passage thresholds after results are viewed.

## 8. Trigger candidates — fixed set

Evaluate exactly four causal triggers after first contact:

1. `TOUCH_REF`: analytical entry at contact-state zhi on first contact. This is the baseline and has no confirmation delay.
2. `RECLAIM_CENTER`: first confirmed M1 close at/above contact-state center after first contact; hypothetical execution reference = next available M1 open.
3. `RECLAIM_FULL`: first confirmed M1 close at/above contact-state zhi after first contact; execution reference = next available M1 open.
4. `BULL_REJECTION`: first post-contact confirmed M1 bar with close > open and close-position `(close-low)/(high-low) >= 0.70`; execution reference = next available M1 open.

A confirmation trigger must occur before invalidation and before 16:55 NY so a next-M1 execution exists before session end. If it never occurs, that trigger has no trade for the episode.

No MSS/FVG parameter search is included in v1.0. Those require a new preregistration if the simple trigger set proves insufficient.

## 9. Fixed known-at-trigger descriptors

For descriptive stratification and a later frozen score design, record only information known by the trigger time:
- origin family (`Z4`, `ESM`, `EPM`, `EWM`, `ESWING`);
- displayed slot rank 1/2/3;
- zone width / v;
- zone-center distance from close at the arming C5 snapshot / v;
- TP1 lower-bound distance from trigger execution reference / v;
- minutes remaining to 17:00 NY;
- TR60 v;
- causal normalized price trends over 5, 15, 60 and 240 active M1;
- approach move over last 5 and 15 active M1 / v;
- contact penetration depth into zone / zone width, clipped only for reporting, not selection;
- contact M1 body direction and close-position in bar;
- trigger type;
- zone display-episode age in completed C5 snapshots.

No future variable may enter descriptors.

## 10. Reaction DEV analysis and trigger selection rule

The first development run is **descriptive/selection only**, not an ML model fit.

For each trigger report:
- eligible contact episodes;
- trigger-fired count and share;
- resolved `FP_0.50v_vs_0.25v`, `FP_1.00v_vs_0.50v`, `FP_1.50v_vs_0.75v` rates;
- `TP1_BEFORE_INVALIDATION_US_END` resolved rate;
- invalidation-first rate;
- neither rate;
- ambiguity rates;
- medians/p90 of MFE, MAE, time remaining, and TP1 distance;
- results by origin family and by US subperiod (08:00–09:30, 09:30–12:00, 12:00–17:00 NY), provided denominator >=100; otherwise label sparse and do not select from that stratum.

A trigger is `DEV_ELIGIBLE` only if:
- >=1000 fired episodes over REACTION_DEV;
- fired share >=20% of fresh contacts;
- resolved TP1/invalidation ordering >=90% of fired episodes.

Primary trigger selection among DEV_ELIGIBLE triggers:
1. highest `TP1_BEFORE_INVALIDATION_US_END` resolved rate;
2. highest `FP_1.00v_vs_0.50v` resolved rate;
3. lowest invalidation-first resolved rate;
4. highest fired count;
5. deterministic order: `TOUCH_REF`, `RECLAIM_CENTER`, `RECLAIM_FULL`, `BULL_REJECTION`.

The selected trigger and any later E-score specification must be frozen in a **new preregistration before H2 reaction outcomes are opened**.

If no trigger is DEV_ELIGIBLE, H2 remains closed and a new DEV preregistration is required.

## 11. Explicit nonclaims

This reaction-development study does not by itself validate:
- profitable trading after spread/commission/slippage;
- a specific hard SL;
- a production E score;
- `R_US`, `UP_FIRST`, `DOWN_FIRST` or route probability;
- the old Z4 R as reaction strength.
