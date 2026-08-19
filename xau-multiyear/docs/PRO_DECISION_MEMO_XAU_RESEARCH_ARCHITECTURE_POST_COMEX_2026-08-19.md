# PRO DECISION MEMO — XAUUSD research architecture after COMEX Track-A

Date: 2026-08-19  
Repository: `iagency971/twilio-voice-gateway`  
Decision branch: `agent/xau-comex-acquisition-plan`  
Review mode: **STRATEGIC / POST-OUTCOME ARCHITECTURE REVIEW**  
New market-data acquisition during this review: **NO**  
New strategy backtest during this review: **NO**

## 1. Decision

`PIVOT_TO_PRICE_ONLY_CORE_PLUS_NEW_SECOND_MOTOR`

Do **not** stop the global XAUUSD strategy program.

Do **not** continue trying to rescue the failed COMEX rejection hypothesis.

Do **not** discard the existing 2011–2025 price-only candidate.

The existing price-defined candidate becomes the **frozen benchmark/core**, while the next research experiment is a **new, narrow, price-only frequency-extension hypothesis** designed to produce a second motor without retuning the original core.

The COMEX absorption/continuation interpretation is retained only as a **parked hypothesis-generation result**. It is not the next experiment and may not be tested by re-optimizing the already-opened 227 Track-A events.

## 2. Evidence inventory

### 2.1 Price-only zone information remains the strongest positive evidence

Canonical multiyear evidence on `agent/xau-multiyear-research`:

- `OBJECTIVE_LIQUIDITY`: positive reaction lift in **15/15** annual windows at the primary reaction threshold;
- `DISPLACEMENT_ORIGIN`: positive reaction lift in **15/15** annual windows;
- `MEMORY`: smaller/less stable positive effect;
- standalone `FVG_3BAR`: approximately flat/slightly negative and not supported as a general zone qualifier.

This means the original scientific problem — whether objective price-defined zones carry reaction information — is **not unanswered**. Two families already show long-horizon reaction information. The unresolved problem is conversion into a sufficiently frequent, executable strategy.

Source: `xau-multiyear/docs/CHECKPOINT_READY_FOR_COMEX_2026-08-18.md` on `agent/xau-multiyear-research`.

### 2.2 Existing core candidate is a serious historical strategy candidate

Canonical corrected Vantage-like Phase-C evidence on `agent/xau-multiyear-research`:

Core family:

`DISPLACEMENT_ORIGIN + OBJECTIVE_LIQUIDITY + CLEAN_REJECTION + STRUCTURAL`

The corrected 2011–2025 gate reports a broad neighboring RR plateau. At the already-used RR1.5 reference point:

- trades: **304** over 2011–2025;
- average frequency: approximately **20.27 trades/year**;
- primary weighted net R/trade: **+0.27992R**;
- positive years primary: **13/15**;
- median annual PF primary: **1.6629**;
- stress weighted net R/trade: **+0.18961R**;
- positive years stress: **12/15**;
- median annual PF stress: **1.4634**.

The neighboring RR surface 0.5 / 1.0 / 1.5 / 2.0 / 2.5 / 3.0 remains positive under the materially harsher stress cost scenario. This is a plateau, not a single isolated optimized RR. No live RR should be selected from this historical table.

Source: `xau-multiyear/docs/CHECKPOINT_PHASE_C_VANTAGE_CORRECTED_2026-08-18.md`.

Execution semantics were re-inspected in this review:

- `CLEAN_REJECTION` requires the causal behavior label;
- reclaim/confirmation occurs first;
- entry is at the **next active bar open**, not inside the confirming bar;
- for a market-at-open trade, if stop and target are both touched in one M1 bar, `simulate_one` assigns the **SL**, i.e. the ambiguity convention is adverse/conservative rather than favorable;
- fixed Vantage-like spread/commission remains an execution overlay, not a historical Vantage tick feed.

Sources:

- `xau-multiyear/src/rzr/entries_v1.py`
- `xau-multiyear/scripts/run_phase_c_vantage_raw.py`

The May–June 2026 frozen holdout produced **0 qualifying core CLEAN_REJECTION trades**. It is therefore `NO_OPPORTUNITY`, not validation and not invalidation. A genuinely prospective final block remains mandatory before any live-ready claim.

### 2.3 COMEX already failed as an incremental layer on existing XAU zones

The preregistered DEV_RANK1 existing-POI study asked whether causal GC/COMEX groups improve the already-defined XAU reaction zones / behavior / fill / Net-R model.

Result:

- B1 vs B0 reaction: FAIL;
- B2 vs B1 reaction: FAIL;
- behavior: FAIL;
- PASSIVE_TOUCH fill: FAIL;
- RECLAIM_PULLBACK fill: FAIL;
- economic Net-R plateau: **18/18 B1/B2 feature-group verdicts = `NO_GO_DEV_RANK1`**;
- COMEX features usually worsened cross-fitted prediction relative to the simpler XAU baseline.

This result explicitly does **not** invalidate the price-only CLEAN_REJECTION candidate.

Source: `xau-multiyear/docs/CHECKPOINT_COMEX_DEV_RANK1_EXISTING_POI_COMPLETE_2026-08-18.md` on `agent/xau-comex-acquisition-plan`.

### 2.4 COMEX-native rejection also failed independently

The subsequent independent native-zone Track-A hypothesis tested exact next-session contacts with POC / VAH / VAL / VWAP under a frozen matched-reference design.

Final primary result:

- 227 K=5 matched events;
- 81 matched treated dates;
- W15 `theta_NRB15 = -0.0177850349`;
- 95% bootstrap CI `[-0.0389945778, +0.0012119707]`;
- date-weighted raw reaction-balance difference `-3.6212 GC ticks`;
- sign-flip p `0.08236`;
- positive source years: 2/8;
- positive families: 1/4;
- final decision: `NO_GO_DEV_RANK2_NATIVE_REACTION`.

Source: `xau-final-results/comex_dev_rank1_native_reaction_track_a_v1/track_a_decision.json`.

### 2.5 The COMEX continuation/absorption clue is real but is hypothesis generation only

Secondary W5 result from the failed native-rejection experiment:

- W5 theta `-0.01488317`;
- raw sign-flip p `0.01484`;
- Holm p `0.04452`.

This is compatible with the idea that some native COMEX contacts may behave more like short-horizon absorption/continuation than rejection. However:

1. the confirmatory W15 rejection result failed;
2. the continuation interpretation was formulated **after** seeing the negative outcomes;
3. the existing 227 outcomes are now contaminated for confirmatory design selection;
4. therefore they may generate a hypothesis, but may not confirm or tune it.

A future COMEX continuation study requires a new preregistration and independent/unopened outcome data. It is **not** allowed to use DEV_RANK2 or another old reserve as a rescue of the failed Track-A specification unless explicitly reclassified as a new experiment with independent-design safeguards.

## 3. Comparative decision across the three requested paths

### Path 1 — preserve / exploit the existing 15-year strategy

Decision: **KEEP AS FROZEN CORE / BENCHMARK**.

Why:

- it is currently the only price-to-entry-to-SL/TP architecture with positive evidence spanning 2011–2025;
- its core zone ingredients independently showed 15/15 annual reaction lift;
- its execution is causal at the signal/entry boundary and resolves M1 TP/SL ambiguity adversely;
- its broad RR plateau is materially stronger evidence than an isolated optimized target.

Why it cannot be the final answer alone:

- 304 trades / 15 years is only ~20.27/year;
- at the RR1.5 reference, mean annual net return is only about the already-reported ~5.67R/year under the primary overlay and ~3.84R/year under stress;
- May–June 2026 provided no qualifying core trade, so prospective evidence is still absent;
- execution costs are simulated by fixed spread/commission rather than replayed from the eventual prop/broker feed.

Conclusion: preserve it; do not retune it; do not pretend it solves the required opportunity frequency by itself.

### Path 2 — objectively find / extend tradable XAUUSD zones

Decision: **OPEN AND MAKE THIS THE NEXT RESEARCH PRIORITY**.

But do not restart as unconstrained “find any zone that works”. That would be data mining on an already heavily explored 2011–2025 XAUUSD history.

The next price-only test must therefore be a **single structural extension** of the mechanism already supported, with all parameters frozen before its outcomes are opened.

### Path 3 — COMEX absorption / continuation

Decision: **PARK, DO NOT KILL, DO NOT PRIORITIZE NOW**.

The W5 sign is sufficiently interesting to preserve a future hypothesis, but two separate COMEX programs have now failed to improve the main path:

1. COMEX B1/B2 did not improve existing XAU POIs/entries;
2. native POC/VAH/VAL/VWAP did not produce the expected rejection edge.

A third immediate COMEX experiment would have a materially worse prior justification than a narrow extension of the already-positive price-only mechanism and would require new independent data to be scientifically convincing.

## 4. One next experiment — `XAU_PRICE_ONLY_M5_FREQUENCY_EXTENSION_V1`

### 4.1 Scientific question

Does the already-supported mechanism

`DISPLACEMENT_ORIGIN ∩ OBJECTIVE_LIQUIDITY -> CLEAN_REJECTION -> STRUCTURAL entry/SL`

retain positive economic value when the displacement-origin generator is extended to a **new M5 scale**, and does the M5-only incremental motor materially increase opportunity count without retuning the frozen 15m/30m/1h core?

This is a scale-extension hypothesis, not a new SMC label and not a search over many timeframes.

### 4.2 Why M5 is the single extension

The current canonical displacement-origin generator uses exactly:

`15min / 30min / 1h`

with:

- displacement quantile `0.90`;
- efficiency minimum `0.60`;
- base search maximum `5` bars;
- variants `DOZ_LAST / DOZ_BODY / DOZ_BASE`;
- unchanged objective-liquidity generator;
- stack overlap threshold `0.50`.

M5 is not part of the current generator. Adding **only M5** is the lowest-dimensional way to test whether the same supported structural mechanism exists at a finer scale and can increase frequency. No M3/M10/M20 grid and no after-result timeframe selection are authorized.

Canonical source: `xau-multiyear/src/rzr/config.py` and `xau-multiyear/src/rzr/zones.py` on `agent/xau-multiyear-research`.

### 4.3 Frozen core arm

The historical core remains unchanged:

- DOZ timeframes: `15min / 30min / 1h`;
- `DOZ_OBJECTIVE_ONLY` confluence;
- `CLEAN_REJECTION` behavior;
- `STRUCTURAL` risk;
- same Vantage-like primary/sensitivity/stress execution overlays;
- same 120-minute horizon;
- preserve the full RR surface `0.5 / 1.0 / 1.5 / 2.0 / 2.5 / 3.0`.

No historical core parameter may be changed because of the M5 result.

### 4.4 M5 incremental arm

Only new displacement-origin zones whose source timeframe is exactly M5 are eligible for the incremental arm.

All other mechanics remain exactly those of the existing generator and execution engine.

The primary incremental population must exclude an M5 event when it collapses into / duplicates an already-existing core event under the frozen stack/contact rules. This prevents counting the same opportunity as both “core” and “new motor”.

No new session filter, bias filter, FVG filter, score, volatility threshold, time-of-day selection, direction split, RR choice, stop variant or COMEX filter is permitted in V1.

### 4.5 Historical status

Because 2011–2025 has already been heavily used during XAU research, an M5 run on that history is **development/falsification evidence only**, even though M5 was not part of the prior DOZ generator.

It may answer:

- whether M5 is obviously dead;
- whether its effect is broad or fragile;
- whether it can plausibly solve the frequency problem.

It may **not** by itself make the combined strategy live-ready.

### 4.6 Frozen success logic before outcomes

Use the existing Phase-C cost scenarios, structural execution, temporal/year robustness logic, bootstrap/multi-seed logic and broad-RR plateau principle rather than inventing a favorable new economic gate.

Report two separate conclusions:

1. `M5_EDGE_STATUS`: whether the incremental M5-only set is positive and robust under the inherited Phase-C criteria across a broad RR neighborhood, including the stress execution scenario;
2. `M5_UTILITY_STATUS`: whether the M5-only set adds at least **304 distinct incremental trades over the 15-year historical development panel**, i.e. at least one additional core-sized opportunity set rather than a cosmetically small frequency increase.

Overall historical development status:

- edge pass + utility pass => `M5_SECOND_MOTOR_DEVELOPMENT_PASS`;
- edge pass + utility fail => `M5_EDGE_POSITIVE_BUT_FREQUENCY_INSUFFICIENT`;
- edge fail => `M5_SECOND_MOTOR_NO_GO`.

The numeric utility threshold is relative to the frozen 304-trade core and is therefore defined before M5 outcomes rather than selected from them.

### 4.7 Confirmation rule

Even if historical M5 development passes, do not merge it into a deployable strategy immediately.

Freeze the M5 specification, then test **core and M5 incremental arm prospectively/virgin** on data whose strategy outcomes were not used to formulate or tune this M5 hypothesis.

Broker/prop execution replication remains required before a live-ready claim.

## 5. COMEX continuation re-opening rule

Do not spend on a COMEX continuation experiment now.

A future `COMEX_NATIVE_CONTINUATION_V1` may be designed only after the M5 price-only decision, or if the price-only second-motor path is stopped.

If opened later:

- direction/anchor/horizon/entry/stop/target must be frozen before new outcomes;
- the 227 Track-A outcomes may be used only to motivate the broad continuation hypothesis, not to choose thresholds/families/horizons;
- independent/unopened data are mandatory;
- W5 from the old run is not a confirmation sample;
- no “best family” rescue from POC/VAH/VAL/VWAP is allowed.

## 6. Capital / data decision now

`NO_NEW_MARKET_DATA_SPEND_NOW`

The next decision-quality experiment is price-only and can be specified and run with already-owned research data first.

Do not authorize:

- GC/MGC subscription solely to rescue rejection;
- richer COMEX order book;
- DEV_RANK2 native reaction;
- broker tick purchase before the price-only second-motor development question is resolved.

## 7. Final strategic order

1. **Freeze and preserve** the 2011–2025 price-only CLEAN_REJECTION core as benchmark.
2. **Run one new price-only M5 displacement-origin frequency-extension experiment** with no other degrees of freedom.
3. If M5 development passes, freeze it and seek genuinely prospective/broker-realistic confirmation of core + M5.
4. If M5 fails, do not try M3/M10/M20 rescues on the same panel. Return to architecture review before another zone family is opened.
5. Keep COMEX continuation parked as an independent future hypothesis; do not spend on it now.

## 8. Bottom line

The research program is not at `STOP`.

It is at:

`PIVOT — PRESERVE THE ONLY LONG-HORIZON PRICE-ONLY EDGE CANDIDATE, STOP COMEX REJECTION/INCREMENTAL RESCUE, AND TEST ONE LOW-DIMENSION PRICE-ONLY FREQUENCY EXTENSION.`

The purpose of the next experiment is not to manufacture a profitable result. It is to answer, with one frozen change, whether the strongest mechanism already found can become frequent enough to be useful.