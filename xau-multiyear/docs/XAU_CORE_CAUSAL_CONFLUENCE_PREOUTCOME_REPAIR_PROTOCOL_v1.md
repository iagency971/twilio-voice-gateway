# XAU CORE CAUSAL CONFLUENCE PREOUTCOME REPAIR PROTOCOL v1

Date frozen: 2026-08-20
Branch: `agent/xau-core-evidence-audit-v1`
Status: `FROZEN_BEFORE_REPAIRED_SUPPORT_AND_PNL`
Authority: Pro decision `B — REPAIR_PREOUTCOME` after review of freeze `106fa7d8efc1006f53c9dd4b130e3031549fcadfa6e425fbe5068b0299c6606b`.

## 1. Purpose

Repair one remaining pre-outcome causal defect in `XAU_CORE_CAUSAL_CONFLUENCE_REBUILD_PROTOCOL_v1` without inspecting or using any strategy P&L.

The direct DOZ + Objective Liquidity pair construction, direct-overlap threshold, two-minute contact tolerance, contamination logic, first-completion deduplication, anchor selection, timeframes and all later economic gates remain unchanged.

The invalidated pre-outcome freeze contained 590 candidates but selected them using final `behavior_v2 == CLEAN_REJECTION`. Because the final behavior classifier can later relabel an initially clean reclaim as `FAILED_AUCTION` after a subsequent breach/reclaim, that population could be revoked by information arriving after the historical entry time.

This protocol replaces only that behavior-selection step.

## 2. Binding inherited causal-pair rules

The following remain exactly as frozen in `XAU_CORE_CAUSAL_CONFLUENCE_REBUILD_PROTOCOL_v1`:

- source: the same already-used Dukascopy XAUUSD M1 bid/ask history;
- target years: 2011–2025;
- annual rehydration: January of year-1 through January of year+1;
- DOZ timeframes: 15min / 30min / 1h;
- one direct `DISPLACEMENT_ORIGIN` + one direct `OBJECTIVE_LIQUIDITY` raw first-contact pair;
- absolute contact-time gap <= 2 minutes;
- direct relative overlap >= 0.50;
- causal MEMORY/FVG exclusion only from already-known, already-contacted overlapping contacts inside `[confluence_time-2m, confluence_time]`;
- `confluence_time = max(DOZ_contact_time, Objective_contact_time)`;
- later member contacts may never modify an already-emitted event;
- deterministic first-completion deduplication and stable event IDs;
- no session, direction, age, timeframe, variant, subtype or side-relation filter.

No tolerance or geometry parameter may be changed after this freeze.

## 3. Irreversible causal CLEAN_REJECTION trigger

For each emitted causal confluence, start the behavioral clock at `confluence_idx`.

Resolve the anchor effective side exactly as the existing engine:

- SUPPORT => prospective LONG rejection;
- RESISTANCE => prospective SHORT rejection;
- NEUTRAL => resolve mechanically from the already-frozen approach direction.

Scan at most the existing 15-minute behavioral window, beginning with the confluence minute.

For SUPPORT:

- distal breach on minute j if `low[j] < anchor_lower`;
- proximal reclaim on minute j if `close[j] > anchor_upper`.

For RESISTANCE:

- distal breach on minute j if `high[j] > anchor_upper`;
- proximal reclaim on minute j if `close[j] < anchor_lower`.

The causal trigger is the first minute offset `j` for which a proximal reclaim is observed and **no distal breach has been observed on any minute from confluence through j inclusive**.

If breach and reclaim are both present in the same M1 bar, the event does **not** trigger CLEAN_REJECTION because intraminute ordering is unknown and the adverse interpretation is required.

Once a causal CLEAN_REJECTION trigger occurs it is irreversible. Any later breach, later reclaim, failed-auction pattern or accepted-break label may be recorded only as a descriptive diagnostic; it may not revoke, delay, advance or otherwise change the already-observable trigger.

The repaired pre-outcome builder must not select candidates on final `behavior_v2`.

## 4. Confirmation and entry timing

For a finite causal trigger offset `m`:

- `confirm_idx = confluence_idx + m`;
- `entry_idx = first quote-active minute after confirm_idx`, using the unchanged maximum wait of two minutes;
- if no such active entry minute exists, no trade candidate is emitted.

No entry price, stop, target, exit, gross-R, net-R, PF, win rate or drawdown may be computed in this stage.

## 5. PREFIX_INVARIANCE hard gate

For every emitted repaired trade candidate, recompute the causal trigger on a data prefix ending exactly at its confirmation minute.

The following must equal the result obtained when the full historical path is present:

- eligibility as a causal CLEAN_REJECTION;
- trigger offset;
- confirmation index;
- entry index;
- direction;
- anchor zone ID and anchor geometry;
- stable event ID.

The aggregate hard gate is:

`prefix_invariance_violations = 0`.

No candidate failing prefix invariance may be silently dropped. Any violation fails the pre-outcome freeze.

## 6. Required side provenance

The repaired manifest must record, for every emitted candidate:

- `doz_side`;
- `objective_side`;
- `side_relation`.

`side_relation` is outcome-blind:

- `NEUTRAL_RESOLVED` if either raw member side is NEUTRAL;
- otherwise `SAME_SIDE` if the two raw sides are equal;
- otherwise `OPPOSITE_SIDE`.

These fields are descriptive only. No side relation may filter the primary population before or after P&L.

## 7. Mandatory unit tests before annual rebuild

The precheck must pass all of the following before annual data are processed:

1. reclaim first, later breach, later reclaim => trigger remains at the first reclaim and entry remains the next active minute;
2. breach before reclaim => no CLEAN_REJECTION trigger;
3. same-bar breach + reclaim => no trigger under adverse ambiguity;
4. a triggering prefix extended with multiple different future paths => unchanged event eligibility, trigger, confirmation and entry;
5. no reclaim in the allowed window => no trigger;
6. existing direct-pair row-order shuffle identity test => PASS.

## 8. Repaired support gate

A repaired freeze may be published only if all are true:

- at least 200 causal CLEAN_REJECTION entry candidates over 2011–2025;
- candidates present in at least 12 of 15 years;
- `timing_integrity_violations = 0`;
- `prefix_invariance_violations = 0`;
- duplicate event IDs = 0;
- fixed row-order shuffle identity = PASS for every annual rebuild.

PASS status:

`CAUSAL_CORE_PREOUTCOME_REPAIRED_READY_FOR_PNL`

FAIL status:

`CAUSAL_CORE_PREOUTCOME_REPAIR_SUPPORT_FAIL`

Both statuses require `pnl_inspected_or_used = false` and `tp_sl_exit_simulated = false`.

## 9. Invalidation of the prior freeze

The prior freeze is invalid for outcome execution:

- prior preoutcome freeze SHA-256: `106fa7d8efc1006f53c9dd4b130e3031549fcadfa6e425fbe5068b0299c6606b`;
- prior event manifest SHA-256: `7595d18257af70341ad0c1288d40d1fea65cc84b56d48bc29c5b420f034aaaf5`;
- prior artifact freeze commit: `97cb99bf340affbc6003fa731232f215c86a7656`.

Invalidation status:

`INVALIDATED_PREOUTCOME_FUTURE_BEHAVIOR_RECLASSIFICATION`.

No P&L executor may use the prior 590-event manifest.

## 10. Economic protocol remains frozen and unopened

If and only if the repaired support gate passes, a later separately authorized P&L executor may use the economic surface and Gates A–F already frozen in section 12 of `XAU_CORE_CAUSAL_CONFLUENCE_REBUILD_PROTOCOL_v1`:

- structural risk;
- 120-minute horizon;
- RR surface 0.5 / 1.0 / 1.5 / 2.0 / 2.5 / 3.0;
- cost scenarios `S10_C6`, `S11_C6_PRIMARY`, `S12_C6`, `S18_C9_STRESS`;
- primary metric `CAUSAL_CORE_RR_SURFACE_MEAN_NET_R`;
- date-cluster bootstrap 20,000;
- Gates A–F unchanged;
- RR1.5 descriptive only for drawdown/concentration/portfolio checks.

This repair does not authorize P&L opening.

## 11. No-rescue rule

During this repair and after the repaired freeze, it is forbidden to change the population or rescue a failure using:

- LONG/SHORT;
- session or session transition;
- M30 or another timeframe;
- zone age;
- DOZ variant;
- Objective subtype;
- side relation;
- overlap threshold;
- time tolerance;
- RR;
- cost scenario;
- COMEX information.

No new paid market data are authorized.

## 12. Mandatory stop

After publishing and hashing the repaired support population, stop with:

`STOP_BEFORE_PNL`

and return the repaired freeze to review before any TP/SL/exit/net-R computation.