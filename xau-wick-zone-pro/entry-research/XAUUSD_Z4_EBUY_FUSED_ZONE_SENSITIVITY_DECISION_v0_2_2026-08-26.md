# XAUUSD Z4 — E-BUY fused-zone sensitivity v0.2 — Decision memo

**Date:** 2026-08-26  
**Status:** study complete; baseline parity PASS; no production fusion authorized.

## 1. Provenance closure

The v0.2 rerun fixed a provenance-guard bug only. The original OOS coverage workflow hashed the uncompressed candidate CSV and then gzip-compressed that CSV for repository publication. Therefore the frozen manifest candidate SHA-256 `157a5f180cc548f51ac9a0fd38ce9e031da48a0dad4fd4170f74b5836d4af90b` is the hash of the decompressed CSV bytes, while the committed `.csv.gz` container has SHA-256 `bc0e1761c4a68ae94c58ea6a1d2225668d56a02987218358c69011c12e82cdbd`.

The corrected guard verifies the decompressed candidate bytes against the frozen manifest. No candidate data, fusion threshold, model, trigger, target, invalidation rule, session rule, or score mapping was changed.

Run `32983675104` passed all guards and completed the full 7-variant x 2-window sensitivity.

## 2. Baseline parity

Source-faithful H1 baseline from the frozen OOS candidate table:

- contacts: `16,895`;
- fired `BULL_REJECTION`: `7,127`;
- TP1 resolved rate: `31.4390%`;
- E>=80: `1,422`, positive rate `68.0731%`;
- E>=90: `712`, positive rate `77.3876%`.

H2 baseline reproduced the frozen validation evidence exactly, including contacts, BR count, resolved scored N, baseline rate, AUC, AP, E>=80 count/rate and E>=90 count/rate:

- contacts: `17,578`;
- fired `BULL_REJECTION`: `7,643`;
- TP1 resolved rate: `30.1296%`;
- E>=80: `1,306`, positive rate `67.0750%`;
- E>=90: `565`, positive rate `72.9204%`.

Baseline parity is PASS for both H1 and H2.

## 3. What fusion does geometrically

The separated baseline displays about `2.19–2.21` zones per eligible C5 snapshot with median width about `0.261v`.

Representative variants:

| Variant | H1 mean zones | H2 mean zones | H1 median width | H2 median width | H1 contacts vs base | H2 contacts vs base |
|---|---:|---:|---:|---:|---:|---:|
| BASELINE | 2.189 | 2.210 | 0.261v | 0.261v | — | — |
| G010 | 1.840 | 1.863 | 0.313v | 0.310v | -18.2% | -18.3% |
| G020 | 1.615 | 1.629 | 0.437v | 0.441v | -30.3% | -30.4% |
| G025 | 1.521 | 1.536 | 0.512v | 0.515v | -35.1% | -35.0% |
| G030 | 1.445 | 1.459 | 0.554v | 0.561v | -39.2% | -38.9% |
| G040 | 1.317 | 1.325 | 0.651v | 0.663v | -46.0% | -46.0% |
| G050 | 1.220 | 1.225 | 0.794v | 0.799v | -51.1% | -51.7% |

Thus larger thresholds clearly solve the visual fragmentation, but they also materially widen the scientific zone and collapse many previously separate contact episodes.

## 4. Reaction-rate result: apparent improvement is mainly mechanical

Fusion raises the unfiltered TP1 resolved rate monotonically, but the gain closely tracks the fall in invalidation-first outcomes caused by the lower composite `zlo`.

Examples versus BASELINE:

- G020 H1: TP1 `+1.93 pp`; invalidation-first `-1.89 pp`.
- G020 H2: TP1 `+1.81 pp`; invalidation-first `-2.04 pp`.
- G050 H1: TP1 `+3.82 pp`; invalidation-first `-4.50 pp`.
- G050 H2: TP1 `+4.29 pp`; invalidation-first `-4.85 pp`.

This pattern is consistent with the preregistered warning: widening the composite mechanically lowers the invalidation boundary. The raw TP-rate increase is therefore not evidence by itself that the merged area is a better entry structure.

## 5. Frozen E score does not gain coherent discrimination

The strongest check is whether the existing frozen E model becomes more discriminative under fusion. It does not.

### E>=80 positive rate

| Variant | H1 | Delta H1 | H2 | Delta H2 |
|---|---:|---:|---:|---:|
| BASELINE | 68.073% | — | 67.075% | — |
| G010 | 67.255% | -0.819 pp | 66.667% | -0.408 pp |
| G020 | 67.851% | -0.222 pp | 66.810% | -0.265 pp |
| G025 | 67.819% | -0.254 pp | 66.696% | -0.379 pp |
| G030 | 67.224% | -0.849 pp | 66.517% | -0.558 pp |
| G040 | 67.891% | -0.182 pp | 66.968% | -0.107 pp |
| G050 | 68.107% | +0.034 pp | 67.760% | +0.685 pp |

### E>=90 positive rate

| Variant | H1 | Delta H1 | H2 | Delta H2 |
|---|---:|---:|---:|---:|
| BASELINE | 77.388% | — | 72.920% | — |
| G010 | 76.831% | -0.557 pp | 72.677% | -0.244 pp |
| G020 | 76.241% | -1.147 pp | 73.694% | +0.773 pp |
| G025 | 75.562% | -1.825 pp | 73.175% | +0.255 pp |
| G030 | 75.301% | -2.086 pp | 72.909% | -0.011 pp |
| G040 | 74.627% | -2.761 pp | 72.426% | -0.495 pp |
| G050 | 75.146% | -2.241 pp | 73.154% | +0.234 pp |

AUC is essentially flat/slightly worse under fusion. Raw AP rises with the higher base positive rate, but AP excess over the base rate does not improve coherently. In particular, the E-band uplift above the new base rate shrinks as fusion becomes wider.

## 6. Decision

**No actual fusion threshold is promoted or labelled `PROMISING_RETROSPECTIVE`.**

Reason:

1. the raw TP-rate gain is largely explained by the mechanically wider/lower invalidation boundary;
2. E>=80 does not improve coherently across H1/H2;
3. E>=90 degrades materially in H1 for wider fusions and is mixed in H2;
4. AUC does not improve;
5. actual fusion reduces contact frequency substantially, from about -18% at G010 to about -52% at G050;
6. both H1 and H2 are already outcome-exposed for this fusion question, so even a retrospective winner could not be promoted without fresh prospective validation.

Production authorization remains `NONE_RETROSPECTIVE_SENSITIVITY_ONLY`.

## 7. Practical UX recommendation

The original visual complaint remains valid: three very small E zones separated by tiny gaps often look like one practical reaction area.

The clean solution is therefore to separate **display** from **scientific state**:

- keep E1/E2/E3 separated internally for contact, BR, invalidation, features and score E;
- optionally draw a single visual envelope when adjacent displayed E zones have edge gaps <= `0.20v`;
- do not change the internal `zlo`, contact state, invalidation or E model because of this visual envelope.

`0.20v` is the preferred visual-only default because it removes/reduces the displayed-zone count in about `46.5–47.0%` of snapshots while remaining materially less aggressive than G025-G050. It is not claimed to be statistically superior; it is an ergonomics choice supported by the geometry sensitivity.

If actual fused-zone trading logic is still desired later, freeze one rule first and validate it prospectively on data strictly after this study date.