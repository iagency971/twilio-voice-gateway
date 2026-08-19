# PRO DECISION MEMO — XAUUSD architecture after the two COMEX NO-GO results

Date: 2026-08-19  
Repository: `iagency971/twilio-voice-gateway`  
Branch: `agent/xau-comex-acquisition-plan`  
Review status: **ACTUAL PRO REVIEW AFTER USER SWITCHED TO PRO**  
New market-data acquisition: **NO**  
New strategy outcomes computed in this review: **NO**

## 0. Traceability correction

The previously created files:

- `xau-multiyear/docs/PRO_DECISION_MEMO_XAU_RESEARCH_ARCHITECTURE_POST_COMEX_2026-08-19.md`;
- `xau-recovery/XAU_POST_COMEX_RESEARCH_ARCHITECTURE_DECISION_v1.json`;

were produced in **Très élevé**, not in Pro. Their attribution to Pro was incorrect. They are not scientific authority and their M5 authorization is withdrawn.

They are superseded by this memo and by:

`xau-recovery/XAU_POST_COMEX_PRO_DECISION_v2.json`

## 1. Overall verdict

`CONDITIONAL_CONTINUE_CORE_VALIDATION_FIRST`

The global XAUUSD research program is not stopped, but the evidence does **not** currently support calling any configuration a validated live strategy.

The correct order is:

1. preserve the 2011–2025 `DOZ_OBJECTIVE_ONLY + CLEAN_REJECTION + STRUCTURAL` result as the strongest historical candidate;
2. audit that candidate at trade-ledger and portfolio level with zero new market-data spend;
3. only if that audit passes, perform independent feed / broker replication;
4. do not open an M5 extension before the core itself survives those checks;
5. keep the post-hoc COMEX continuation interpretation parked for a future independent experiment.

The immediate decision is therefore **not**:

- `M5_AUTHORIZED`;
- `COMEX_CONTINUATION_AUTHORIZED`;
- `LIVE_READY`;
- `STOP_ALL_RESEARCH`.

It is:

`RUN_XAU_CORE_EVIDENCE_AUDIT_V1`

## 2. What the current evidence genuinely establishes

### 2.1 Price-defined zones contain reaction information

The strongest Phase-A evidence remains:

- `OBJECTIVE_LIQUIDITY`: positive reaction lift in all 15 annual windows;
- `DISPLACEMENT_ORIGIN`: positive reaction lift in all 15 annual windows;
- `MEMORY`: smaller and less stable lift;
- standalone `FVG_3BAR`: approximately flat/slightly adverse and not supported as a universal qualifier.

This establishes that some objective price-defined zones carry conditional reaction information. It does not by itself establish a profitable entry/SL/TP strategy.

Canonical source:

- `xau-multiyear/docs/CHECKPOINT_READY_FOR_COMEX_2026-08-18.md` on `agent/xau-multiyear-research`.

### 2.2 The 304-trade core is the strongest historical economic candidate

Candidate family:

`DISPLACEMENT_ORIGIN + OBJECTIVE_LIQUIDITY + CLEAN_REJECTION + STRUCTURAL`

On the corrected 2011–2025 Vantage-like execution overlay, all six neighboring RR cells from 0.5R to 3.0R survived the frozen historical gate.

At the already-used RR1.5 reference:

- trades: 304;
- average frequency: 20.27 trades/year;
- primary weighted net expectancy: +0.279918R/trade;
- primary positive years: 13/15;
- primary median annual PF: 1.6629;
- stress weighted net expectancy: +0.189605R/trade;
- stress positive years: 12/15;
- stress median annual PF: 1.4634.

The neighboring RR plateau is materially better evidence than an isolated optimized RR peak.

Canonical sources:

- `xau-multiyear/docs/PHASE_C_VANTAGE_RAW_MULTIYEAR_GATE.md`;
- `xau-multiyear/docs/CHECKPOINT_PHASE_C_VANTAGE_CORRECTED_2026-08-18.md`;
- `xau-final-results/phase_c_vantage_raw_2011_2025/survivors.csv`;
- all on `agent/xau-multiyear-research`.

### 2.3 Execution semantics are causal but execution evidence remains synthetic

The current core requires a causal `CLEAN_REJECTION` label, confirms first, and enters at the next active bar open. Same-M1 TP/SL ambiguity is resolved adversely: SL wins.

However, the economic replay uses a fixed symmetric Vantage-like spread overlay around the historical Dukascopy mid path. It is not historical Vantage BID/ASK or tick replay.

Canonical sources:

- `xau-multiyear/src/rzr/entries_v1.py`;
- `xau-multiyear/scripts/run_phase_c_vantage_raw.py`;
- `xau-multiyear/docs/CHECKPOINT_PHASE_C_VANTAGE_CORRECTED_2026-08-18.md`.

### 2.4 The only temporal holdout did not validate the core

The May–June 2026 window contained:

- 11,447 total research events;
- 6 `DOZ_OBJECTIVE_ONLY` events;
- 0 executable `CLEAN_REJECTION` core trades.

The result is `NO_OPPORTUNITY / INCONCLUSIVE`, not a positive validation and not a negative expectancy observation.

Canonical source:

- `xau-multiyear/docs/CHECKPOINT_VANTAGE_HOLDOUT_2026_MAY_JUN_2026-08-18.md`.

### 2.5 Both tested COMEX paths are closed as NO-GO

#### Existing XAU POI augmentation

The DEV_RANK1 B1/B2 COMEX groups failed reaction, behavior, fill and Net-R tests. All 18 frozen economic feature-group verdicts were `NO_GO_DEV_RANK1`.

Source:

- `xau-multiyear/docs/CHECKPOINT_COMEX_DEV_RANK1_EXISTING_POI_COMPLETE_2026-08-18.md`.

#### Native COMEX rejection

The independent native POC/VAH/VAL/VWAP rejection experiment produced:

- 227 K=5 matched events;
- 81 treated dates;
- W15 `theta_NRB15 = -0.0177850349`;
- bootstrap 95% CI `[-0.0389945778, +0.0012119707]`;
- raw date-weighted reaction balance `-3.6212 GC ticks`;
- only 2/8 positive source years;
- only 1/4 positive families;
- decision `NO_GO_DEV_RANK2_NATIVE_REACTION`.

Source:

- `xau-final-results/comex_dev_rank1_native_reaction_track_a_v1/track_a_decision.json`.

The secondary W5 negative effect may motivate a future absorption/continuation hypothesis, but it was interpreted after outcomes were opened. It cannot confirm or tune a continuation strategy on the same 227 events.

## 3. Why the previous M5 proposal is not approved

### 3.1 It expands before validating the core

The current 304-trade candidate was selected from an extensively explored 2011–2025 research history and has no successful independent P&L confirmation. Adding another timeframe on the same chronology would create another development result, not validation.

The next marginal unit of research should reduce uncertainty about whether the existing edge is real, not create more signals before that uncertainty is resolved.

### 3.2 Its utility threshold did not match the project objective

The pre-Pro proposal required at least 304 incremental M5 trades over 15 years. Even a perfect pass would approximately double frequency from 20.27 to 40.53 trades/year.

That remains far from the original practical objective of a near-daily XAUUSD opportunity stream. The threshold was relative to the historical core, not to the user's actual utility requirement.

### 3.3 Adding M5 is not guaranteed to leave the core unchanged

The canonical pipeline generates all zones, finds contacts, then calls `collapse_contact_events` before family masks and trade construction.

`collapse_contact_events`:

- groups overlapping contacts within a time tolerance;
- merges constituent families and variants;
- changes the representative when a narrower zone is present.

Therefore inserting M5 zones into the common generator can alter:

- stack membership;
- representative geometry;
- constituent-family labels;
- which event qualifies as `DOZ_OBJECTIVE_ONLY`;
- the identity of the supposedly frozen 15m/30m/H1 core.

The phrase “only add M5” is therefore not an executable guarantee of an incremental arm. A valid future M5 design would require separately generated arms, exact core-parity assertions and post-generation deduplication.

Canonical sources:

- `xau-multiyear/src/rzr/config.py`;
- `xau-multiyear/src/rzr/zones.py`;
- `xau-multiyear/src/rzr/stacking.py`;
- `xau-multiyear/scripts/run_phase_c_vantage_raw.py`.

### 3.4 It compounds the selection problem

If M5 failed, trying M3/M10/M20 would be obvious data mining. If M5 passed, the result would still be generated on the same heavily inspected panel and could not establish live profitability.

M5 remains a plausible future development hypothesis, but it is not the highest-information next experiment now.

Decision:

`M5_NOT_AUTHORIZED_AT_THIS_GATE`

## 4. Critical evidence gaps in the 304-trade result

The current Vantage runner builds an in-memory `trades` dataframe, then writes only grouped `summary.csv` and `manifest.json`.

The persisted trade records do not include or expose a canonical ledger containing:

- stable event ID;
- contact, confirmation, entry and exit timestamps;
- entry and exit indices;
- direction;
- source DOZ timeframe and exact objective-level constituents;
- simultaneous or overlapping positions;
- chronological portfolio equity;
- drawdown and losing streak;
- per-date clustering;
- best-trade concentration;
- confidence intervals for expectancy;
- single-position execution behavior.

The published annual aggregate is therefore sufficient to identify a promising historical family, but insufficient to certify an implementable strategy.

This gap must be closed before either paying for broker replication or expanding frequency.

## 5. One next experiment — `XAU_CORE_EVIDENCE_AUDIT_V1`

### 5.1 Purpose

Determine whether the frozen 304-trade core remains credible after a trade-level, dependence-aware and portfolio-realistic audit, without changing any signal, entry, stop, target surface, cost scenario or zone definition.

This is a falsification and evidence-quality audit on already-viewed history. It is not a new OOS validation.

### 5.2 Frozen population

The only eligible strategy family is:

`DOZ_OBJECTIVE_ONLY + CLEAN_REJECTION + STRUCTURAL`

Frozen DOZ timeframes:

- 15min;
- 30min;
- 1h.

Frozen target surface:

- 0.5R;
- 1.0R;
- 1.5R;
- 2.0R;
- 2.5R;
- 3.0R.

Frozen horizon:

- 120 minutes.

Frozen execution scenarios:

- `S10_C6`;
- `S11_C6_PRIMARY`;
- `S12_C6`;
- `S18_C9_STRESS`.

No M5, COMEX, FVG, session, direction, score, volatility, trend, breakeven, trailing, partial-exit or stop modification is allowed.

### 5.3 Mandatory canonical trade ledger

Persist one row per strategy event × scenario × RR with at least:

- stable `event_id` and `stack_id`;
- source year/date;
- contact/confirmation/entry/exit timestamps and indices;
- direction;
- zone lower/upper/centre;
- constituent families and variants;
- exact DOZ source timeframe(s);
- objective-level subtype(s);
- entry, stop, target and exit price;
- structural risk in USD;
- spread and commission;
- gross R and net R;
- result (`TP`, `SL`, `TIME`);
- ambiguity flag;
- concurrent-open-position count;
- source-data and code commit hashes.

The ledger must be hashed and immutable before inferential summaries are produced.

### 5.4 Hard parity gate

Before interpretation:

1. reproduce exactly 304 core events for every RR cell in the primary arm;
2. reproduce the published aggregate results within floating-point tolerance;
3. prove that all six RR cells use the same underlying 304 entry events;
4. prove that the four cost scenarios do not silently change the event population;
5. fail closed on any untraceable event or duplicate event ID.

A parity failure gives:

`CORE_RESULT_INVALID_REPAIR_REQUIRED`

No strategy interpretation is allowed after a parity failure.

### 5.5 Dependence-aware inference

Primary statistical unit:

- trading date.

Required inference:

- 20,000 date-cluster bootstrap replicates;
- seed `20260821`;
- percentile 95% CI for mean net R and PF-compatible profit/loss aggregates;
- leave-one-year-out recomputation;
- annual contribution shares;
- three-month moving-block bootstrap of monthly aggregate R;
- 20,000 replicates;
- seed `20260822`.

The six R targets are one response surface, not six independent discoveries. No best-R selection is permitted.

RR1.5 remains a pre-existing descriptive reference only; it is not promoted because it is the best point.

### 5.6 Concentration and fragility audit

For every RR and cost scenario, report:

- contribution of best 1%, 5% and 10% of trades;
- expectancy after removing the best 5% of trades;
- contribution by year;
- contribution by direction, session, DOZ timeframe and objective subtype as diagnostics only;
- maximum drawdown in R;
- longest losing streak;
- monthly and annual trade-count distribution;
- risk-price distribution and smallest risks;
- ambiguous same-bar rate.

No diagnostic subgroup can rescue a failing aggregate or become a new filter in V1.

### 5.7 Portfolio-concurrency audit

The historical summaries treat each qualifying entry independently. A deployable strategy must define what happens when signals overlap.

Run both:

1. `INDEPENDENT_SIGNAL_LEDGER`: preserves the historical event accounting;
2. `SINGLE_POSITION_REPLAY`: at most one open XAUUSD position.

For `SINGLE_POSITION_REPLAY`:

- sort by entry timestamp, then contact timestamp, then stable event ID;
- the earliest eligible trade opens;
- later entries are ignored until that trade exits;
- no choice is made based on future P&L;
- the same rule applies to every RR and scenario.

This replay is a deployability audit, not a retroactive replacement of the historical result.

### 5.8 Frozen pass/fail logic

#### A. Integrity

All parity requirements pass.

#### B. Broad-RR statistical support

At least 4 of 6 RR cells must satisfy in `S11_C6_PRIMARY`:

- mean net R >= +0.10R;
- PF net >= 1.25;
- date-cluster bootstrap 95% lower bound for mean net R > 0.

All six RR cells must remain positive in mean net R under `S18_C9_STRESS`, and at least 4 of 6 must have stress PF net >= 1.20.

#### C. Temporal robustness

For RR1.5 and at least 4 of 6 RR cells:

- every leave-one-year-out aggregate mean net R > 0;
- at least 10/15 individual years positive in primary;
- at least 8/15 individual years positive in stress;
- no single year contributes more than 35% of total absolute annual R contribution.

#### D. Concentration robustness

For RR1.5 in primary and stress:

- mean net R remains > 0 after removing the best 5% of trades;
- the best 5% do not contribute more than 50% of total positive R.

#### E. Portfolio realism

For RR1.5 `SINGLE_POSITION_REPLAY`:

- primary mean net R > 0;
- primary PF net > 1.10;
- stress mean net R >= 0;
- no unresolved sequencing ambiguity.

### 5.9 Decision mapping

All A–E pass:

`CORE_INTERNAL_AUDIT_PASS_FOR_EXTERNAL_REPLICATION`

Integrity failure:

`CORE_RESULT_INVALID_REPAIR_REQUIRED`

Any B–E failure:

`CORE_HISTORICAL_CANDIDATE_NO_GO_FOR_EXTERNAL_REPLICATION`

A pass does **not** authorize live trading, M5, or a prop-firm challenge. It authorizes only a separately preregistered independent-feed / broker-realistic replication and its source/cost feasibility gate.

## 6. Decision on the three strategic paths

### Path 1 — exploit the existing 15-year candidate

`PRIORITY_1_BUT_AUDIT_FIRST`

It is the strongest existing evidence, but it is not yet a validated strategy. Preserve it exactly and try to falsify it at ledger/portfolio level.

### Path 2 — objectively search for more tradable XAUUSD zones

`OPEN_STRATEGICALLY_BUT_NOT_THE_NEXT_EXPERIMENT`

If the core audit fails, return to architecture review. Do not immediately scan more timeframes or stack more mandatory confluences. A future discovery program must reserve genuinely independent chronology before opening outcomes.

If the core audit passes and later replicates, a second motor can be developed, including a properly isolated M5 arm, but only with core-parity safeguards and a utility target aligned with the actual cadence requirement.

### Path 3 — COMEX absorption / continuation

`PARKED_HYPOTHESIS_GENERATION_ONLY`

It remains scientifically interesting but lower priority after two COMEX NO-GO programs. It requires:

- a new preregistration;
- independent/unopened outcomes;
- no tuning on the 227 Track-A events;
- a realistic live-data path;
- explicit cost authorization.

No new COMEX spend is authorized now.

## 7. Other historical Order-Block candidates

The prior Pine L1/L2/S1 Order-Block candidates remain separate screening hypotheses. They do not rescue or invalidate the 304-trade core and are not promoted by this decision.

No paid long-history OOS acquisition for those candidates is authorized before the core evidence audit establishes whether the strongest already-owned candidate is internally credible.

## 8. Capital and mode decision

Current spend authorization:

`ZERO_NEW_MARKET_DATA_SPEND`

Current research authorization:

`XAU_CORE_EVIDENCE_AUDIT_V1_ONLY`

Execution of this mechanical audit should be done in **Très élevé**, using this memo as the fixed Pro gate. Return to Pro only after the audit artifacts and verdict are frozen, or earlier if a parity defect requires a methodological decision.

## 9. Bottom line

The honest conclusion is not “we found the strategy” and not “nothing works”.

It is:

> The 304-trade core is the only long-history economic candidate worth preserving, but its current evidence is aggregate, development-exposed and not portfolio-complete. Before searching for more trades, prove that this candidate survives an auditable ledger, dependence-aware inference, concentration stress and realistic position sequencing.

Final decision:

`CONDITIONAL_CONTINUE_CORE_VALIDATION_FIRST`
