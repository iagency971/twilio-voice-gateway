# COMEX DEV_RANK1 — existing XAU POI checkpoint before net-R v1

Date: 2026-08-18 America/Guadeloupe
Status: FROZEN PRE-NET-R CHECKPOINT

No COMEX-conditioned net-R/P&L result has been computed under or after this checkpoint. DEV_RANK2, RETRO_CONFIRM, LOCKED_TEST, and native-zone retest tape remain unopened.

## Frozen feature stacks

- B0: XAU baseline.
- B1: B0 + continuous GC N0 M1 context.
- B2: B1 + causally available active DUAL V0/N0 raw tape/profile.

Primary comparisons always use the same B2-available observations, outer leave-one-year-out 2011–2018, C chosen by inner LOYO on remaining years, cluster bootstrap by trading date, and family-balanced event log-loss as the directional primary metric.

## Existing-XAU-POI target 1 — reaction

Status: **NO-GO for the frozen B1/B2 stacks.**

B1 does not provide robust incremental value over B0. B2 materially worsens B1. This target is frozen and may not be rescued by post-hoc feature/threshold changes.

## Existing-XAU-POI target 2 — multiclass auction behavior

Target: CLEAN_REJECTION / FAILED_AUCTION / ACCEPTED_BREAK / UNRESOLVED.

Status: **NO-GO.**

B1 vs B0:
- family-balanced log-loss improvement: -0.08895647681196683
- positive outer years: 1/8
- session-cluster bootstrap 95%: [-0.18509828602253298, -0.014713994851130466]

B2 vs B1:
- family-balanced log-loss improvement: -0.041492783889132356
- positive outer years: 2/8
- session-cluster bootstrap 95%: [-0.0702123867460549, -0.011280598334848674]

B2 vs B1 is negative in all five broad families. The multiclass target is frozen and cannot be retuned from observed outcomes.

## Existing-XAU-POI target 3 — entry/fill probability

Decision populations and model-specific causal decision times were frozen before modeling.

### PASSIVE_TOUCH

- decisions: 31,710
- raw fills: 18,714 (59.0161%)
- primary B2-available sample: 30,525 = 18,041 fills / 12,484 nonfills

Status: **NO-GO.**

B1 vs B0:
- family-balanced improvement: -0.013534166954381588
- positive years: 1/8
- bootstrap 95%: [-0.027149632241167912, -0.000886166760941684]

B2 vs B1:
- family-balanced improvement: -0.04633219244529274
- positive years: 1/8
- bootstrap 95%: [-0.0874405023328534, -0.01360636800751359]

B2 vs B1 is negative in all five broad families.

### RECLAIM_PULLBACK

- decisions: 31,163
- raw fills: 17,982 (57.7030%)
- primary B2-available sample: 30,127 = 17,415 fills / 12,712 nonfills

Status: **NO-GO.**

B1 vs B0:
- family-balanced improvement: -0.0172042 approximately
- positive years: 4/8
- bootstrap entirely below zero

B2 vs B1:
- family-balanced improvement: -0.0715669 approximately
- positive years: 0/8
- bootstrap entirely below zero

B2 vs B1 is negative in all five broad families.

### ACCEPTANCE_RETEST

- decisions: 380
- raw fills: 207 (54.4737%)
- primary B2 sample: 349 = 188 fills / 161 nonfills

Status: **NO EVIDENCE OF INCREMENTAL COMEX VALUE; SMALL/POWER-FRAGILE.**

Both B1 vs B0 and B2 vs B1 have negative family-balanced improvements and fail the directional gate. This target is not interpreted as a definitive negative by family because of its much smaller sample.

### TOUCH_NEXT_OPEN

- decisions: 31,710
- fills: 31,579 (99.5869%)

Status: **FILL TARGET QUASI-DETERMINISTIC / NON-PROMOTIONABLE.**

B1 does not improve robustly. B2 has a small positive family-balanced point estimate but its cluster bootstrap spans zero. The economically relevant question is net-R conditional on entry, not fill probability.

### CLEAN_REJECTION

- decisions: 16,643
- fills: 16,606 (99.7777%)

Status: **FILL TARGET QUASI-DETERMINISTIC / NON-PROMOTIONABLE.**

No robust incremental value. The economically relevant question is net-R conditional on entry.

### FAILED_AUCTION

- decisions: 14,520
- fills: 14,487 (99.7727%)
- primary B2 sample contains only 10 nonfills.

Status: **FILL TARGET QUASI-DETERMINISTIC / INCONCLUSIVE FOR DISCRIMINATION.**

A nominal B1 gate in the automatic runner is not promotionable because the minority class is only 10 observations in the primary sample and some outer-year folds contain zero nonfills. This is treated as a rare-class artifact, not evidence of COMEX value.

## Scientific interpretation at this checkpoint

For the currently frozen feature/model stacks applied to **existing XAU POIs**, COMEX has not demonstrated robust incremental predictive value for:

1. reaction probability;
2. multiclass reject/accept/break behavior;
3. the two large nontrivial fill targets PASSIVE_TOUCH and RECLAIM_PULLBACK.

This is not equivalent to “COMEX is useless.” Three separate questions remain open:

- economic value/net-R conditional on fills under a pre-frozen outcome protocol;
- COMEX-native zones and their exact future raw-contract retests;
- hypothesis generation for a later feature redesign, which cannot retroactively rescue these primary DEV_RANK1 tests.

## Next gate

No net-R/P&L analysis may start until `COMEX_DEV_RANK1_NET_R_PRO_GATE_PREP_v1.md` has been adjudicated in Pro and an exact economic outcome / RR / cost / multiplicity / promotion rule is frozen.

No new Databento purchase is authorized by this checkpoint.
