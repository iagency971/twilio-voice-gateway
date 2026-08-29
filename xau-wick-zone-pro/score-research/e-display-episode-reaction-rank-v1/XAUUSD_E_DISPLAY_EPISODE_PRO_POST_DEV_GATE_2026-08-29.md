# XAUUSD — E display episode reaction rank V1 — Pro post-DEV scientific gate

**Gate date:** 2026-08-29  
**Repository:** `iagency971/twilio-voice-gateway`  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Scope:** XAUUSD M1, BUY, US 08:00–17:00 `America/New_York`  
**Gate:** `PRO_POST_DEV_SCIENTIFIC_GATE`  
**Production authorization:** NONE

# Decision

## `GO_HISTORICAL_REPLICATION_DIAGNOSTIC`

The frozen DEV evidence is scientifically sufficient to justify opening the already-declared historical replication diagnostic with the model and protocol held completely fixed.

This is **not** a validation of the score. DEV is the model-development sample and its statistics are in-sample. The decision authorizes only a strict out-of-sample historical replication diagnostic. It does not authorize production, Pine modification, prospective use, calibrated-probability language or a universal E-strength claim.

The only newly authorized token is:

`GO_HISTORICAL_REPLICATION_DIAGNOSTIC`

## Materials reviewed

The gate reviewed the canonical DEV seal, immutable DEV evidence directory, artifact metadata, frozen model, label QA, model QA, input provenance, environment, post-DEV gate request and the original preregistration.

Canonical DEV authority:

- run: `33264659057`;
- artifact: `9718487805`;
- artifact digest: `sha256:481ad65013241f4dfcdb4f2378f4168476bb92695519de00166149c4a5ac6c0e`;
- execution commit: `637ece27b49cc71d0ab972a6d015029ed60a3ddb`;
- materialization commit: `8e9bd3166d1e3bab987fb50fa48052b5101a920e`;
- immutable copy commit: `d1e1a32a06a7ae3f6e039360122f042a0ced5f15`;
- immutable copy: `dev-freeze-canonical-33264659057/`.

The downloaded artifact digest was independently verified. All nine evidence-file SHA-256 values matched the DEV freeze manifest. The frozen model reproduced all 16,461 DEV logits exactly, and the primary point statistics were independently reproduced.

No historical-replication outcome was generated, loaded, scored or inspected during this gate.

## DEV evidence

The frozen DEV population contains:

- 32,745 displayed episodes;
- 16,461 primary contacts;
- 257 NY sessions;
- 8,044 favorable-first outcomes;
- 8,417 binary failures, including conservative ambiguous and neither cases.

The preregistered continuous association is:

- ROC AUC: `0.5756928361`;
- AUC minus 0.5: `+0.0756928361`;
- session-cluster 95% CI: `[+0.0661773290, +0.0851757254]`.

The fixed DEV quartiles are ordered monotonically:

| Fixed quartile | N | Success rate |
|---|---:|---:|
| Q1 | 4,292 | 42.8239% |
| Q2 | 3,939 | 44.5291% |
| Q3 | 4,115 | 48.9186% |
| Q4 | 4,115 | 59.2710% |

Q4 minus Q1 is:

- `+0.1644710156`, or +16.4471 percentage points;
- session-cluster 95% CI: `[+0.1415397113, +0.1874155024]`.

The model converged in 10 iterations. Feature exclusion was 0%, unseen-family rate was 0%, and model reload reproduced the complete DEV score vector exactly.

As a non-gating concentration check only, DEV was also divided into three contiguous session-count blocks. Frozen Q4 minus Q1 remained positive in all three: `+0.1560`, `+0.1620`, `+0.1747`. This check did not alter any feature, coefficient, threshold, quartile or decision metric.

## Scientific interpretation

The DEV evidence is too strong and coherent to justify abandoning the candidate before an out-of-sample test:

1. the continuous association is positive with a narrow session-cluster interval entirely above zero;
2. the four fixed quartiles are monotonically ordered;
3. the top-versus-bottom separation is substantial and its cluster interval remains entirely positive;
4. the result is not caused by feature exclusions, unknown categories or optimizer instability;
5. the model has only five fitted coefficients for 16,461 primary contacts and follows the single preregistered pipeline;
6. the replication firewall remained intact through the DEV freeze.

At the same time, these are development-sample results. They cannot validate generalization. The correct scientific action is therefore neither promotion nor rejection, but the already-planned frozen historical replication.

## Exact replication authorization

### Window

Primary contact membership must satisfy:

`2025-08-01T00:00:00Z <= contact_bar_open_time_utc < 2026-08-01T00:00:00Z`

### Replication ledger

Use only:

`E_DISPLAY_EPISODE_LEDGER_V1_REPLICATION.csv.gz`

SHA-256:

`a3baa2f48b9d397ebcdd3e0be936e5947e49caa4ca77dec531f726c321f586a6`

### Frozen DEV model

Use only:

`dev-freeze-canonical-33264659057/DEV_FROZEN_MODEL.json`

SHA-256:

`72e7548de826e2ae2ba66ddcaaf6b2fa7cd35ada0f5f2cd9db585d9734fd48e1`

The model may be loaded and applied. It may not be refitted, altered or regenerated.

### Frozen code and environment

- reaction labeler SHA-256: `08ed29422ede890c300073789daa4669a22fbe48b74171c68402310c00aebef8`;
- model/evaluation SHA-256: `f547853609f16b00080049629f708fc0d4170c54071fd22a99228c807cd6dd2e`;
- requirements lock SHA-256: `4cb67a768b857847b7ecad790e77637174a79e7cb299176b5543edc12a1b82cf`;
- Python 3.11.16;
- NumPy 2.3.2;
- pandas 2.3.1;
- SciPy 1.16.1;
- scikit-learn 1.7.1.

The labeler invocation must use:

- `--declared-window HISTORICAL_REPLICATION_DIAGNOSTIC`;
- `--authorization-token GO_HISTORICAL_REPLICATION_DIAGNOSTIC`.

The model invocation must use:

- `--phase HISTORICAL_REPLICATION_DIAGNOSTIC`;
- `--authorization-token GO_HISTORICAL_REPLICATION_DIAGNOSTIC`;
- the immutable frozen DEV model JSON.

### Replication inputs

Only the 12 hash-verified Dukascopy BID M1 files covering August 2025 through July 2026 may be loaded.

The two known partial replication sessions and their 482 missing M1 opens must be retained and reported. Missing opens remain unavailable bars under the preregistered rule. They may not be converted into elapsed bars, imputed or used as a post-outcome reason to delete sessions.

## Replication support gate frozen before opening

To remove discretionary rescue after the replication is seen, the replication support rule is now fixed. Every check below is required:

1. at least 1,000 primary eligible episodes;
2. at least 90 completed NY sessions represented;
3. AUC minus 0.5 greater than zero;
4. session-cluster 95% CI lower bound for AUC minus 0.5 greater than zero;
5. fixed DEV quartile rates satisfy `Q1 <= Q2 <= Q3 <= Q4`;
6. fixed DEV Q4 minus Q1 greater than zero;
7. its session-cluster 95% CI lower bound greater than zero;
8. fixed DEV Q4 minus Q1 positive in all three contiguous complete-session blocks;
9. feature exclusion rate no greater than 2%;
10. unseen-family rate no greater than 5%;
11. no frozen method or data-definition component changed.

Passing this support gate can authorize only a later Pro decision about prospective confirmation. It cannot authorize production. Failure cannot be rescued by modifying the model, selecting a subgroup, changing quartiles or trying an alternate threshold. Any further candidate after failure requires a newly preregistered research cycle.

## Explicit prohibitions

During replication it is forbidden to:

- refit or alter the frozen DEV model;
- change any of the three features;
- change standardization, family vocabulary, coefficients or intercept;
- change the reaction target, contact rule, 30-bar horizon or ambiguity treatment;
- change the frozen DEV empirical-rank mapping or quartile cutpoints;
- load DEV labels for a new fit or alternative model selection;
- compare models, thresholds or subgroups to rescue the result;
- delete partial sessions after outcome access;
- modify Pine;
- present the rank as a calibrated probability, profit forecast or universal E strength.

## Required next checkpoint

After the replication execution, the complete labels, input manifest, label QA, frozen-model load/no-refit QA, replication report, environment, hashes, run ID and artifact digest must be frozen in an immutable package.

The process must then stop at:

`READY_FOR_PRO_POST_REPLICATION_GATE`

Only a later Pro gate may interpret the frozen replication result and decide whether a prospective-confirmation protocol is justified.

# Final statement

**Decision:** `GO_HISTORICAL_REPLICATION_DIAGNOSTIC`  
**Model:** immutable, no refit  
**Production:** NONE  
**Pine:** FORBIDDEN  
**Next execution mode:** Très élevé, through the complete replication freeze and no further.
