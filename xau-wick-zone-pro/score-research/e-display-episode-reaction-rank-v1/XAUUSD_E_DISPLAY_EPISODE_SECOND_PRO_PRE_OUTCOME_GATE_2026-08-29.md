# XAUUSD — E display episode V1 — second Pro pre-outcome scientific gate

**Gate date:** 2026-08-29  
**Repository:** `iagency971/twilio-voice-gateway`  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Scope:** XAUUSD M1, BUY only, US 08:00–17:00 `America/New_York`  
**Gate mode:** strict outcome-blind review  
**Production authorization:** NONE

## 1. Decision

# `GO_DEV_OUTCOME_OPENING`

The second Pro pre-outcome gate passes.

This decision authorizes **one DEV-only opening phase** under the exact frozen protocol. It does not validate the score, does not authorize historical replication, does not authorize prospective use or production, and does not authorize any Pine modification.

The only permitted real-outcome token at the next phase is:

`GO_DEV_OUTCOME_OPENING`

The token `GO_HISTORICAL_REPLICATION_DIAGNOSTIC` remains forbidden.

## 2. Materials reviewed without opening outcomes

The gate reviewed:

- the frozen pre-outcome repair specification;
- the timing addendum;
- the sequential outcome-opening addendum;
- the feature registry;
- the causal provenance instrumentation;
- the display-episode builder and independent QA;
- the reaction labeler and its synthetic tests;
- the model/evaluation pipeline and its synthetic tests;
- the canonical 24-month outcome-free evidence package;
- the exact v0.4 display-parity evidence;
- the locked scientific environment;
- an additional independent DEV-prefix invariance and M1-availability QA.

No real reaction label, success rate, MFE, MAE, W5/W15/W30/W60, TP/SL result, model coefficient, AUC, quartile performance or other post-contact outcome was generated or inspected during this gate.

## 3. Canonical frozen package

The canonical method is the commit:

`7ef065e209c94e21950c346eed9d4ae0a2d786da`

The canonical pre-outcome workflow run is:

`33259414496`

Its artifact is:

- artifact ID: `9716948881`;
- ZIP digest: `sha256:62932d000b46a6ad14bdfd8d1d3b47513be0094c72acbfe1028511684b0c707e`.

The evidence was materialized in the repository at commit:

`43136be3e2a7459c3b8e1c189aa7ab933b7084a4`

The package manifest reports:

- `E_DISPLAY_EPISODE_V1_PRE_OUTCOME_REPAIR_PASS`;
- `READY_FOR_NEW_PRO_PRE_OUTCOME_GATE`;
- real outcome generation forbidden;
- real outcome reading forbidden;
- model fitting on real labels forbidden;
- historical replication opening before DEV model freeze forbidden.

## 4. Closure of the first Pro gate blockers

### B1 — temporal coverage: CLOSED

The outcome-free ledger now covers both declared periods:

- DEV: 41,210 snapshots, 257 NY sessions;
- historical replication diagnostic: 42,776 snapshots, 258 NY sessions;
- total: 83,986 snapshots, 66,752 display episodes, 515 sessions.

Window splits are exact and non-empty. Contact-time membership is separately enforced by the labeler.

### B2 — episode identity and causal invariance: CLOSED

The repaired identity:

- forbids cross-family continuation;
- uses immutable causal source-state IDs for ESM/EWM;
- uses immutable confirmed-pivot event IDs for EPM;
- uses constituent confirmed-pivot IDs and deterministic one-to-one matching for ES;
- ignores E1/E2/E3 slot changes as identity evidence;
- resets across a C5 gap or NY-session boundary.

The canonical QA proves one family and one session per episode, contiguous C5 persistence, valid provenance continuity, unique episode/snapshot and unique slot/snapshot.

A separate outcome-blind prefix reconstruction then rebuilt the complete DEV history **without supplying any replication-era price file**. It compared:

- 43,511 provenance/display rows;
- 41,210 DEV feature rows;
- 41,210 row hashes.

All identities, slots, families, timestamps, provenance signatures, persistence values, geometries, normalized widths and row hashes matched the canonical full-period build. Therefore appending the replication period does not alter the DEV feature history.

### B3 — reaction labeler implementation: CLOSED

The labeler is implemented before outcome access and is fail-closed behind window-specific tokens.

For DEV it requires:

- declared window `DEV_HISTORY`;
- token `GO_DEV_OUTCOME_OPENING`;
- a ledger whose `feature_window` contains only `DEV_HISTORY`;
- all primary contact times inside `[2024-08-01T00:00:00Z, 2025-08-01T00:00:00Z)`.

Conflicting duplicate OHLC timestamps fail closed.

### B4 — contact-bar ordering: CLOSED

The primary rule is frozen:

- an arming bar cannot also be the contact bar;
- a contact bar may invalidate immediately by closing below frozen `zlo0`;
- its favorable high is ignored because M1 OHLC cannot prove whether it occurred after contact;
- favorable-event eligibility begins on the next available M1 bar;
- favorable plus invalidation on one later bar is `AMBIGUOUS_SAME_BAR`, binary 0;
- the horizon is 30 available completed M1 bars, truncated at 17:00 New York.

Synthetic tests cover each rule.

### B5 — unique model pipeline: CLOSED

Exactly one model is permitted:

- logistic regression;
- L2 penalty;
- `C=1.0`;
- `lbfgs`;
- `max_iter=5000`;
- no class weighting;
- no hyperparameter search;
- no alternative model comparison.

Exactly three pre-contact features are admitted:

1. `zone_width_v`;
2. `display_persistence_c5`;
3. `current_family`.

DEV-only preprocessing, category vocabulary, model coefficients, score distribution, empirical rank mapping and quartile cutpoints are frozen by the DEV phase. The replication phase is a separate code path that loads a frozen model and cannot refit it.

### B6 — statistics and gates: CLOSED

The primary continuous association is fixed as:

`ROC AUC(continuous_logit, primary_binary_label) - 0.5`

Uncertainty uses 5,000 bootstrap resamples of complete NY sessions with seed `20260829`, a minimum of 4,750 valid draws and percentile 95% intervals.

DEV quartiles use `numpy.quantile(method="linear")`; the rank uses the frozen DEV midrank empirical CDF. Missing features are excluded and counted. Later unseen families map to all-zero family indicators and are counted.

No metric may be replaced after seeing DEV.

### B7 — scope, provenance, environment and seal: CLOSED

The estimand is explicitly limited to:

> local top-3 displayed E episodes generated by the frozen v0.4 architecture in an upper-Z4-conditioned US BUY universe.

It is not universal E strength.

The environment is frozen to:

- Python 3.11.16;
- NumPy 2.3.2;
- pandas 2.3.1;
- SciPy 1.16.1;
- scikit-learn 1.7.1.

The original v0.4 display geometry and the provenance-instrumented output match exactly on 88,557 rows for time, slot, family, center, `zlo` and `zhi`, with zero mismatch.

## 5. Additional M1-availability finding

The independent timestamp audit checked the full 08:00–17:00 NY grid for every represented session.

DEV contains:

- 257 sessions;
- 138,780 expected M1 opens;
- **0 missing M1 opens**.

Historical replication contains 482 missing M1 opens across two sessions. This does not block DEV because replication remains unopened. The later replication gate must retain and report those partial sessions under the already frozen rule that missing minutes are skipped as unavailable bars rather than counted as elapsed outcome bars.

## 6. Exact DEV-only execution contract

The GO is valid only under all of the following conditions.

### Inputs

Use only:

- `E_DISPLAY_EPISODE_LEDGER_V1_DEV.csv.gz`;
- SHA-256 `2cf40bfca54494f1609035307390f3e615348492bf8c853f0c79c63555d060e6`;
- the 12 hash-verified Dukascopy BID M1 files from 2024-08 through 2025-07 declared in the frozen data-input manifest;
- no M1 file dated 2025-08 or later;
- no replication ledger.

### Labeling invocation

The DEV labeler must use:

- `--declared-window DEV_HISTORY`;
- `--authorization-token GO_DEV_OUTCOME_OPENING`.

Its frozen source SHA-256 is:

`08ed29422ede890c300073789daa4669a22fbe48b74171c68402310c00aebef8`

### Model invocation

The model pipeline must use:

- `--phase DEV_FIT`;
- `--authorization-token GO_DEV_OUTCOME_OPENING`.

Its frozen source SHA-256 is:

`f547853609f16b00080049629f708fc0d4170c54071fd22a99228c807cd6dd2e`

### Outputs to freeze

Before any replication access, commit and hash at minimum:

- the complete DEV labels;
- the DEV labeler manifest;
- the frozen model JSON;
- the DEV model/evaluation report;
- all preprocessing statistics;
- family vocabulary/reference category;
- coefficients and intercept;
- DEV continuous-score distribution;
- empirical-rank definition;
- quartile cutpoints;
- exact input hashes;
- environment and package versions;
- run ID and artifact digest.

## 7. Explicit non-authorizations

This gate does **not** authorize:

- historical replication outcome generation or reading;
- `GO_HISTORICAL_REPLICATION_DIAGNOSTIC`;
- changing the three model features;
- changing the contact, reaction, invalidation or 30-bar rules;
- changing the model, transforms, bootstrap or gates;
- selecting a different method after looking at DEV;
- interpreting the output as calibrated probability;
- calling the output a universal E-strength score;
- changing production Pine;
- using the result for production trading.

## 8. Remaining risks, accepted for DEV but not for production

1. **High singleton rate.** 80.3916% of display episodes contain one C5 snapshot. `display_persistence_c5` may therefore have limited variation or predictive value. That is an empirical question; it is not a reason to redesign the feature after outcomes.
2. **Conditional target population.** The study concerns selected displayed episodes, not every candidate E zone.
3. **Reaction, not profitability.** The primary target is a BID-price reaction criterion. It does not include spread, commission, slippage, executable ASK levels or trade management.
4. **Historical replication is diagnostic.** Even a later positive historical replication cannot authorize production.
5. **Prospective confirmation remains mandatory.** Production consideration requires a separately frozen prospective protocol and a future gate.

## 9. Mandatory checkpoint after DEV

After DEV is opened and the single model is fitted, the process must stop at an immutable model-freeze checkpoint.

Historical replication remains closed until:

1. all DEV outputs are committed and hashed;
2. the exact frozen model reloads and reproduces its DEV scores bit-for-bit or under a separately declared deterministic numeric tolerance;
3. a model-freeze manifest confirms that replication outcomes were not read or used;
4. a separate authorization explicitly grants `GO_HISTORICAL_REPLICATION_DIAGNOSTIC`.

## 10. Final gate statement

All first-gate methodological blockers are closed sufficiently to permit the preregistered DEV experiment without changing the study after outcome access.

**Final decision:** `GO_DEV_OUTCOME_OPENING`  
**Authorized scope:** DEV only  
**Historical replication:** CLOSED  
**Production:** NONE  
**Pine modification:** FORBIDDEN
