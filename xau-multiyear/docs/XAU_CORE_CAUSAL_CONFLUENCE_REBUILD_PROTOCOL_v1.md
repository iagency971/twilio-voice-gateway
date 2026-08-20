# XAU CORE CAUSAL CONFLUENCE REBUILD PROTOCOL v1

Date frozen: 2026-08-19
Branch: `agent/xau-core-evidence-audit-v1`
Status: `FROZEN_BEFORE_CAUSAL_EVENT_SUPPORT_AND_PNL`
Authority: Pro architecture decision after `TEMPORAL_STACK_INTEGRITY_FAIL_CORE_CLASSIFICATION_LOOKAHEAD`.

## 1. Purpose

Rebuild the historical `DOZ_OBJECTIVE_ONLY + CLEAN_REJECTION + STRUCTURAL` candidate from a fully causal confluence representation before any repaired P&L is opened.

The prior 304-event statistical audit remains evidence about the original historical event set, but its external-replication authorization is suspended because 18/304 classifications used a DOZ or Objective Liquidity contact that was not yet observable by confirmation.

This protocol does **not** delete the 18 violating trades and requote the remainder. It defines a new causal event population from raw first contacts.

## 2. Frozen market-information universe

Use exactly the already-used Dukascopy XAUUSD historical universe and annual construction:

- target years: 2011–2025;
- annual rehydration window: January of year-1 through January of year+1, identical to the existing annual workflows;
- same `ResearchConfig`;
- same baseline zone generators;
- same quote-activity and sigma calculations;
- same first-contact detector;
- no new provider, timeframe, market, calendar period or paid data;
- `new_market_data_spend = 0`;
- canonical-input rehydration is permitted only as deterministic replay of already-used public data.

DOZ source timeframes remain exactly:

- 15min;
- 30min;
- 1h.

## 3. Raw-contact authority

The causal rebuild starts from raw zone first contacts produced by `find_first_contacts`, **before** `collapse_contact_events`.

Each raw contact carries its own:

- zone ID;
- family and variant;
- zone known time;
- first contact time/index;
- geometry;
- side;
- approach state.

No final `constituent_families` list from a two-minute stack may establish confluence.

## 4. Direct DOZ–Objective pair

A causal confluence candidate is exactly one direct pair consisting of:

- one `DISPLACEMENT_ORIGIN` raw first contact;
- one `OBJECTIVE_LIQUIDITY` raw first contact.

The pair qualifies only if all are true:

1. both zones are already known at their own raw first-contact timestamps (guaranteed by the contact detector and asserted again);
2. absolute difference between the two raw first-contact timestamps is `<= 2 minutes`;
3. direct relative geometric overlap between the two original zone intervals is `>= 0.50`;
4. the pair is not contaminated by a causal `MEMORY` or `FVG` contact under section 7.

The two-minute and 0.50 thresholds are inherited from the historical stacking design and are frozen here. They may not be varied after outcomes.

Relative overlap is:

`overlap_length / min(zone_width_A, zone_width_B)`.

Transitive geometry is forbidden: A overlapping B and B overlapping C does not make A and C a pair unless A and C themselves satisfy the direct-overlap threshold.

## 5. Causal completion time and execution anchor

For a qualifying pair:

`confluence_time = max(DOZ_contact_time, Objective_contact_time)`.

The contact that occurs at `confluence_time` is the execution anchor.

If both contacts occur at exactly the same timestamp, choose the anchor outcome-blind by:

1. smaller zone width;
2. earlier `known_time`;
3. earlier `origin_time`;
4. lexical `zone_id`.

The other zone is the partner.

The anchor supplies:

- side;
- lower/upper bounds;
- centre;
- sigma and approach state at the completion contact.

No later contact may change the anchor, geometry, side, family membership or event identity.

## 6. CLEAN_REJECTION clock reset

The behavioral clock starts at `confluence_time`, never at the earlier member contact.

For each causal confluence event:

- set `contact_idx` to the anchor/confluence contact index;
- classify `CLEAN_REJECTION` using the existing `classify_behavior_v2` semantics from that index forward;
- a clean rejection requires proximal-edge reclaim before distal-edge breach;
- confirmation index is the confluence index plus the frozen reclaim delay;
- entry eligibility is the next active minute after confirmation using the existing maximum wait of two minutes;
- no pre-confluence price path may satisfy the clean-rejection confirmation.

The pre-P&L event manifest records only causal signal/entry timing and structural metadata. It does not simulate TP, SL, exit, gross R or net R.

## 7. Causal meaning of `ONLY`

A `MEMORY` or `FVG` raw contact excludes a DOZ–Objective pair only when all are true:

1. the excluding zone is already known;
2. its own raw first contact has already occurred at or before `confluence_time`;
3. its contact lies in the same causal two-minute event window: `confluence_time - 2 minutes <= excluding_contact_time <= confluence_time`;
4. it directly overlaps by at least 0.50 with either the DOZ interval or Objective interval.

A future contact cannot retrospectively add or remove a family.

Additional DOZ or Objective contacts do not invalidate the pair; they are handled only by deterministic event deduplication.

## 8. Deterministic first-completion deduplication

All qualifying direct pairs are sorted by:

1. `confluence_time`;
2. anchor width;
3. partner width;
4. anchor zone ID;
5. partner zone ID.

For each candidate define `pair_geometry` as the direct intersection interval of the DOZ and Objective zones.

Process candidates chronologically. A later candidate is the same causal event cluster, and is not emitted as a new event, if an already-emitted event completed no more than two minutes earlier and either:

- the candidate shares a DOZ or Objective zone ID with that emitted event; or
- the candidate pair geometry directly overlaps the emitted pair geometry by at least 0.50.

The emitted event is **never updated** by later candidates. Thus the first causal completion fixes the event permanently.

Events more than two minutes apart are distinct even if their geometries later overlap.

## 9. Stable event identity

Each emitted event receives an outcome-independent ID from SHA-256 of:

- DOZ zone ID;
- Objective zone ID;
- DOZ raw contact timestamp;
- Objective raw contact timestamp;
- confluence timestamp;
- anchor zone ID.

No P&L field participates in identity or deduplication.

## 10. Pre-P&L support population

From emitted causal confluences, the pre-P&L trade-candidate manifest includes only events that:

1. classify as `CLEAN_REJECTION` after causal confluence completion;
2. have a finite reclaim confirmation index;
3. have a next active entry minute under the unchanged `CLEAN_REJECTION` timing rule.

No entry price, stop result, target, exit or P&L is computed in this stage.

Required support gate before any P&L may be opened:

- at least 200 causal clean-rejection entry candidates over 2011–2025;
- candidates present in at least 12 of the 15 target years;
- zero temporal-integrity violations;
- zero duplicate event IDs;
- deterministic rebuild identity under a fixed row-order shuffle self-test.

If support gate fails, terminal pre-P&L status is:

`CAUSAL_CORE_PREOUTCOME_SUPPORT_FAIL`

and the economic experiment is not executed.

If it passes:

`CAUSAL_CORE_PREOUTCOME_FROZEN_READY_FOR_PNL`

This status authorizes only a later, separately triggered outcome execution under the frozen gates in section 12.

## 11. Mandatory pre-P&L artifacts

Before any repaired P&L is opened, persist and hash:

- one annual causal clean-rejection event manifest for each 2011–2025 year;
- annual support summaries;
- aggregate 2011–2025 event manifest;
- exclusion/contamination counts;
- deterministic shuffle-identity checks;
- protocol SHA-256;
- builder-script SHA-256;
- source code SHAs for zones, contacts, behavior and entry-timing dependencies;
- aggregate manifest SHA-256;
- a machine-readable preoutcome freeze publication.

Every artifact must explicitly state:

- `pnl_inspected_or_used = false`;
- `tp_sl_exit_simulated = false`;
- `new_market_data_spend = 0`.

## 12. Frozen economic gates for a later outcome run

Only after a successful pre-P&L freeze may a separate outcome executor compute P&L.

Frozen strategy surface:

- family: causal direct `DISPLACEMENT_ORIGIN + OBJECTIVE_LIQUIDITY`;
- entry: `CLEAN_REJECTION`;
- risk: structural;
- horizon: 120 minutes;
- target R surface: 0.5 / 1.0 / 1.5 / 2.0 / 2.5 / 3.0;
- cost scenarios: `S10_C6`, `S11_C6_PRIMARY`, `S12_C6`, `S18_C9_STRESS`;
- no session, direction, age, timeframe or variant filter.

Primary metric:

`CAUSAL_CORE_RR_SURFACE_MEAN_NET_R`

For each trading date, equal-weight the six RR net-R outcomes, then aggregate by trading date. Date-cluster bootstrap: 20,000 replicates. RR1.5 remains descriptive for drawdown/concentration/portfolio checks; no best-R selection is allowed.

### Gate A — integrity/support

- exact preoutcome event-manifest hash verified;
- zero causal violations;
- same event IDs across all RR/cost scenarios;
- N >= 200 and >= 12 active years.

### Gate B — primary and broad-RR support

Under `S11_C6_PRIMARY`:

- RR-surface mean net R >= +0.10R;
- bootstrap 95% lower bound > 0;
- at least 4/6 RR cells each have mean net R >= +0.10R, PF >= 1.25 and bootstrap lower bound > 0.

### Gate C — stress

Under `S18_C9_STRESS`:

- all 6 RR mean net R > 0;
- at least 4/6 RR PF >= 1.20;
- RR-surface mean net R > 0.

### Gate D — temporal robustness

For RR1.5 and at least 4/6 RR cells:

- every leave-one-year-out aggregate mean > 0;
- >= 10/15 positive years primary;
- >= 8/15 positive years stress;
- no year > 35% of total absolute annual R contribution.

### Gate E — concentration

At RR1.5, primary and stress:

- expectancy > 0 after removing best 5% of trades;
- best 5% contribute <= 50% of total positive R.

### Gate F — one-position portfolio

At RR1.5:

- primary mean net R > 0;
- primary PF > 1.10;
- stress mean net R >= 0;
- no unresolved sequencing ambiguity.

Any Gate A–F failure yields:

`CAUSAL_CORE_HISTORICAL_NO_GO`

All gates passing yields:

`CAUSAL_CORE_PASS_FOR_EXTERNAL_REPLICATION`

A PASS still does not authorize live trading, prop-firm use, M5, subgroup filters or COMEX continuation.

## 13. No-rescue / no-selection rule

After repaired P&L is opened, no failure may be rescued by selecting:

- LONG or SHORT;
- NY/Asia/London sessions;
- M30 only;
- an age bucket;
- DOZ_BODY/DOZ_LAST/DOZ_BASE;
- London -> NY_AM or another session transition;
- a preferred Objective subtype;
- a different overlap threshold;
- a different time tolerance;
- a preferred RR.

These dimensions remain diagnostic/hypothesis-generation only.

## 14. Research ordering

Until this causal core experiment resolves:

- external broker/feed replication: blocked;
- M5 extension: blocked;
- rejected-strategy subgroup promotion: blocked;
- COMEX absorption/continuation: parked;
- new paid market-data purchase: blocked.
