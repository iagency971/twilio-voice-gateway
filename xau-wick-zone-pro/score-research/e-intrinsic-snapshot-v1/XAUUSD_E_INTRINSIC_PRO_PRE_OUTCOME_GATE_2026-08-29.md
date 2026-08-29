# XAUUSD — E zones — Pro scientific pre-outcome gate

**Gate date:** 2026-08-29  
**Repository:** `iagency971/twilio-voice-gateway`  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Scope:** XAUUSD M1, BUY only, US 08:00–17:00 `America/New_York`  
**Audited snapshot artifact commit:** `278528c2591d25ca49ae6d127f5c6ded237e6b4c`  
**Branch head at gate start:** `c2cf09a77c92f1f9ab5038e7ab7f1aa427a16dd7`  
**Workflow run / artifact:** `33254513629` / `9715394086`  
**Outcome access during this gate:** NONE  
**Pine production modification:** NONE  

## 1. Final verdict

# `NO_GO_DEV_OUTCOME_OPENING`

The real snapshot ledger passes its declared **technical QA**, but the complete scientific chain is not yet sufficiently specified, implemented, frozen and temporally covered to authorize generation, inspection or use of DEV outcomes.

This is not a rejection of the causal snapshot ledger. It is a separation between two gates:

- **Technical snapshot gate:** PASS.
- **Scientific pre-outcome gate for opening DEV:** FAIL / NO-GO.

Until every hard blocker below is closed and a new Pro gate returns GO, the following remain forbidden:

- generate or read the primary reaction labels on real DEV/replication data;
- inspect W5/W15/W30/W60, MFE/MAE or any future-price reaction;
- fit the model;
- calculate `E_REACTION_RANK_V1`;
- modify the production Pine on the basis of this research.

## 2. What is accepted

The January–July 2024 outcome-free ledger is accepted as a deterministic technical artifact for its declared source and period.

Verified properties:

- `E_INTRINSIC_SNAPSHOT_V1_REAL_QA_PASS`;
- `READY_FOR_PRO_PRE_OUTCOME_GATE`;
- 27,636 rows;
- 15,835 display episodes;
- 12,561 snapshot timestamps;
- 150 New York sessions;
- exact independent identity parity;
- prefix invariance / no repaint;
- deterministic row hashes;
- exact source and ledger hashes;
- no forbidden outcome column;
- no future-price outcome used.

Frozen ledger SHA-256:

`3be6b594c515efc2ca2df6aaa1a8ff63525cbd91ef5b9cfae9956c515ac3d740`

The prior methodological conclusions also remain accepted:

- E1/E2/E3 is an order of display/localization, not a quality ranking;
- the old `E_BUY_US` is an entry-context rank, not an intrinsic E-zone strength score;
- Z4 context and entry/rejection context must remain separate from the E pre-contact block.

## 3. Why technical PASS is not enough

The snapshot QA demonstrates that one frozen input table can be transformed reproducibly into one causal ledger. It does **not** establish that:

- the declared DEV and replication populations exist as frozen feature ledgers;
- episode identity has adequate construct validity;
- the reaction label can be generated without implementation discretion;
- the model and all validation statistics are executable from one frozen specification;
- the future-period generator/data/environment chain is fully sealed;
- the name “intrinsic E strength” accurately describes the sampled universe.

These are pre-outcome requirements because changing them after labels are visible would create researcher degrees of freedom.

## 4. Hard blocker B1 — temporal coverage mismatch

The accepted real ledger covers:

- first snapshot: `2024-01-03T13:00:00+00:00`;
- last snapshot: `2024-07-31T20:55:00+00:00`.

The model preregistration defines:

- DEV: `2024-08-01 <= contact_time < 2025-08-01`;
- historical replication: `2025-08-01 <= contact_time < 2026-08-01`;
- prospective confirmation from New York sessions on or after 2026-08-31.

Therefore the current frozen ledger contains **zero rows in the declared DEV period and zero rows in the historical replication period**.

### Required repair

Before any real reaction label is generated or read:

1. generate the v0.4-equivalent outcome-free candidate sources for the full DEV and replication windows, including their causal warm-up;
2. generate the snapshot ledgers from those sources;
3. independently QA them;
4. freeze all source, ledger and manifest hashes;
5. confirm exact temporal completeness and missing-session handling.

## 5. Hard blocker B2 — episode identity construct

The current identity rule is reproducible, but reproducibility is not the same as a uniquely defensible economic/structural identity.

It continues an episode when zones overlap **or** their centers are within `0.25 × max(v_old,v_new)`, and it may continue through a family change. Because the source retains only top-3 displayed candidates and no stable generator identity, the match is reconstructed geometrically after the fact.

Outcome-blind diagnostics on the frozen ledger show:

- 9,529 of 15,835 episodes are single-snapshot episodes: **60.18%**;
- median episode length: **1** C5 snapshot;
- 11,801 continued transitions;
- 5,473 continued transitions change family: **46.38%**;
- 4,326 continued transitions change display slot: **36.66%**;
- among 25,996 current rows in contiguous snapshot pairs, 1,406 have more than one possible prior match: **5.41%**;
- among 26,002 prior rows, 1,847 have more than one possible current match: **7.10%**;
- **14.09%** of chosen transitions move the center by more than `0.25 × max(v_old,v_new)`;
- **5.48%** move it by more than `0.50 × max(v_old,v_new)`;
- **26.74%** change zone width by more than a factor of two;
- **8.53%** change zone width by more than a factor of five.

These diagnostics use no outcome. They matter directly because two of the four proposed model features—`episode_age_c5` and `origin_family`—depend on the episode chain, and first-contact selection also depends on it.

### Required repair

Preferred route:

- instrument stable, causal source/provenance identities in the frozen E generators;
- prove that adding identities does not change candidate geometry or top-3 display;
- construct display-episode identity from those source IDs with deterministic merge/split rules.

Minimum alternative:

- freeze a new family/geometry-preserving display-episode rule;
- explicitly rename `episode_age_c5` as display persistence rather than intrinsic zone age;
- preregister one primary rule and any sensitivity rule before outcomes;
- obtain a new Pro approval.

No identity rule may be selected because it later produces a better reaction result.

## 6. Hard blockers B3 and B4 — reaction labeler and intrabar ordering

The reaction outcome is currently specified in prose, but no canonical `xau_e_intrinsic_reaction_v1.py` and no edge-case test suite are frozen.

Unresolved implementation choices include:

- which zone bounds govern arming while geometry evolves;
- whether arming persists after bounds or family change;
- whether an episode must remain displayed at contact;
- how to handle disappearance between C5 snapshots;
- exact bar timestamp versus information-availability timestamp;
- missing and inactive M1 minutes;
- whether the 30-bar horizon counts wall-clock or available completed bars;
- exact 17:00 truncation;
- duplicate/overlapping episode contacts;
- exclusion-reason precedence.

There is also a material M1 ordering problem. The preregistration allows the contact bar itself to satisfy:

`high >= zhi0 + 0.50 × v0`.

On OHLC M1 data, the high may have occurred **before** the low/price path contacted the zone. Counting that bar as a favorable reaction can therefore create a false favorable event.

### Required repair

Implement and freeze a deterministic event automaton before running it on any real outcome period. It must include:

- explicit `bar_open_time`, `bar_close_time` and `feature_available_time`;
- exact arming, contact, disappearance and geometry-update rules;
- synthetic tests for every ordering case;
- a conservative contact-bar rule, for example:
  - classify any contact-bar favorable touch as `AMBIGUOUS_CONTACT_BAR_ORDER`, or
  - make favorable-event eligibility begin only after the contact bar.

The selected rule, including its primary binary treatment, must be frozen before outcomes.

## 7. Hard blocker B5 — model and evaluation pipeline absent

The preregistration names a logistic model, transformations and broad validation gates, but no canonical executable pipeline is present for:

- episode/contact reduction;
- feature exclusion and missingness;
- DEV preprocessing;
- one-hot vocabulary;
- model fit;
- convergence failure;
- continuous logit generation;
- empirical CDF/rank;
- frozen quartiles;
- replication report;
- session-cluster bootstrap;
- prospective checkpoint and gate decision.

Without one frozen implementation, post-outcome discretion remains possible even if the prose is broadly sensible.

### Required repair

Before opening real DEV outcomes:

- implement the one allowed model/evaluation pipeline;
- add deterministic synthetic tests;
- lock Python, NumPy, pandas and scikit-learn versions;
- freeze tolerance, iteration, precision, category, missing-value and convergence rules;
- hash the code and environment lock.

## 8. Hard blocker B6 — primary statistic underspecified

The phrase “continuous score association” is not mathematically defined. The following are also incomplete:

- confidence-interval type;
- bootstrap multiplicity and invalid-resample handling;
- standard-deviation convention;
- empirical-percentile tie method;
- DEV quantile method;
- quartile boundary convention;
- treatment of tied cutpoints;
- chronological three-sub-block construction;
- whether a New York session may be split between sub-blocks.

### Required repair

Freeze exact formulas and code. Recommended primary definitions:

- continuous association: `AUC(frozen continuous score, binary label) - 0.5`;
- 5,000 resamples of complete New York session dates with replacement;
- include every episode from a sampled session with the session’s multiplicity;
- percentile 95% interval at 2.5% and 97.5%;
- fixed rule for single-class/invalid bootstrap samples;
- fixed DEV quantile algorithm and exact interval boundaries;
- prospective sub-blocks formed from complete chronologically ordered NY sessions, never by splitting episodes from one session.

This recommendation is still outcome-blind; it must be accepted and frozen before labels are opened.

## 9. Hard blocker B7 — estimand, provenance and canonical seal

The sampled population is not all E zones. A candidate exists in this research universe only when the coverage engine has an eligible BUY-context snapshot, including at least one upper Z4; displayed candidates are local below price, constrained to `0 < distance <= 2v`, deduplicated and capped at three sticky zones.

Consequently, a future result would estimate:

> reaction ranking among local top-3 displayed E episodes in an upper-Z4-conditioned US BUY universe.

It would not establish universal “intrinsic strength” of any E zone.

Furthermore:

- the freeze JSON records triggering commit `111045c…`;
- generated ledger/QA artifacts were committed in `278528c…`;
- later-period raw M1, Z4 inputs and complete v0.1/v0.2/v0.3/v0.4 dependency hashes are not yet sealed;
- the workflow environment installs moving package versions rather than a frozen lock.

### Required repair

1. Use a non-overclaiming name, recommended:
   - `E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1`, or
   - `E_PRECONTACT_STATE_REACTION_RANK_US_BUY_V1`.
2. State the conditional target population in every manifest/report.
3. Hash the full generator dependency graph, all raw/Z4 inputs and the environment.
4. Create a canonical two-stage seal recording:
   - method commit;
   - data/artifact commit;
   - workflow run;
   - artifact ID and archive digest;
   - exact output hashes.

## 10. Required repair order

All work below remains outcome-blind:

1. Freeze the conditional estimand and final non-overclaiming name.
2. Repair/instrument episode identity and rerun identity QA.
3. Produce complete outcome-free DEV and replication candidate/snapshot ledgers.
4. Implement and test the reaction labeler, without running it on real periods.
5. Implement and test the model/evaluation pipeline.
6. Complete every missing mathematical convention.
7. Lock dependencies and create the canonical provenance seal.
8. Run a new Pro pre-outcome gate.

Only a subsequent explicit `GO_DEV_OUTCOME_OPENING` may authorize the first generation/opening of DEV labels.

## 11. Mode decision

The next authorized work is mechanical/method implementation and QA, so it belongs in **Très élevé**.

Pro is required again only after all repairs are present and frozen, immediately before opening DEV.

## 12. Final scientific interpretation

The current package has achieved something useful and real:

- a causal, deterministic, no-repaint pilot snapshot ledger;
- a strict separation from prior entry-context scores;
- a defined direction for a prospective reaction study.

It has **not yet** achieved:

- a validated episode construct;
- a complete DEV/replication feature population;
- a frozen real-outcome labeler;
- a frozen executable model/evaluation chain;
- authorization to inspect outcomes.

**Final Pro decision: `NO_GO_DEV_OUTCOME_OPENING`.**
