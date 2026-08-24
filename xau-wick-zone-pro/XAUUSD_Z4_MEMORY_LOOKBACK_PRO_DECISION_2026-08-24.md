# XAUUSD Z4 — Pro Decision Memo: Memory Lookback

**Date:** 2026-08-24  
**Decision status:** **KEEP L1440**  
**Scope:** targeted methodological review of the preregistered DEV memory-sensitivity gate.  
**No new Validation/OOS read was used to choose the memory.**

## 1. Question reviewed

Should the validated Z4 historical memory of **1,440 active M1** be replaced by a shorter memory after a one-factor sensitivity test of 240 / 360 / 600 / 900 / 1,440 active M1?

## 2. Gate integrity

### 2.1 Preregistration chronology

The candidate set, metrics and pass flags were frozen in:

`XAUUSD_Z4_MEMORY_LOOKBACK_SENSITIVITY_PREREG_v0_1_2026-08-24.md`

before the five-candidate DEV outcome run.

### 2.2 One-factor code mutation

Every candidate was generated mechanically from the exact frozen Z4 reference engine Git blob:

`a8a147615c3fd366c49e93b340fd2018b5b66e9e`

The workflow required a single literal mutation of `LOOKBACK=1440` to the candidate value and attested `other_source_mutations = 0`.

### 2.3 Data provenance

All 14 Jan-Jul 2024 BID/ASK files were hash-gated against the frozen DEV source manifest before computation.

### 2.4 L1440 reproduction

The L1440 control reproduces the original frozen Z4 DEV metrics exactly to stored precision:

BID:
- APR ΔBrier `+0.0012969674799012676`
- MAY `+0.001575698829924338`
- JUN `+0.0018491784726369642`
- JUL `+0.001206172711918252`
- pooled ΔBrier `+0.0014727645192173233`
- pooled ΔLogLoss `+0.004095136286836887`
- weekly bootstrap95 `[+0.0006910281808650239, +0.0023455891239954046]`

ASK:
- pooled ΔBrier `+0.0017428441286502505`
- pooled ΔLogLoss `+0.004777601966964029`
- weekly bootstrap95 `[+0.0005757787685779064, +0.003442689328920215]`

This is a strong internal control that the sensitivity pipeline did not silently change the incumbent architecture.

## 3. Predictive result

| Lookback | BID pooled ΔBrier | BID folds + | BID weekly CI lower | ASK pooled ΔBrier | ASK folds + | ASK weekly CI lower | Frozen verdict |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 240 | +0.00166826 | 3/4 | -0.00020671 | +0.00130471 | 3/4 | -0.00026523 | FAIL |
| 360 | +0.00089691 | 2/4 | -0.00120625 | +0.00121989 | 2/4 | -0.00070224 | FAIL |
| 600 | +0.00085351 | 3/4 | -0.00063131 | +0.00051670 | 3/4 | -0.00119153 | FAIL |
| 900 | +0.00156285 | 3/4 | -0.00039165 | +0.00060570 | 3/4 | -0.00137475 | FAIL |
| **1440** | **+0.00147276** | **4/4** | **+0.00069103** | **+0.00174284** | **4/4** | **+0.00057578** | **PASS** |

Only **L1440** satisfies the preregistered BID robustness gate and the stronger dual-feed gate.

The shorter candidates sometimes show a numerically attractive pooled ΔBrier, especially L240 and L900 on BID, but that pooled average masks sign reversals by month. Under the frozen methodology, those candidates are not robust enough to challenge the incumbent.

## 4. Geometry stability result

BID one-step drop/churn decreases monotonically as memory length increases:

- L240: `20.96%`
- L360: `16.38%`
- L600: `11.70%`
- L900: `8.77%`
- L1440: `6.05%`

Median zones per represented landmark rises from 2 at L240 to 6 at L1440, while lineage persistence also lengthens materially.

This stability pattern is **secondary** and partly mechanically expected: replacing one active M1 changes a much larger fraction of a 240-bar memory than of a 1,440-bar memory. It is therefore not used as independent proof that L1440 is predictive.

However, it gives an important engineering conclusion: **shortening the memory would worsen, not solve, the current zone disappearance/reappearance problem.**

## 5. Decision

### **KEEP L1440**

The validated Z4 architecture remains:

- memory: **1,440 active M1**;
- snapshot cadence: **15-minute UTC**;
- endpoint: **REVISIT_240**;
- current frozen R semantics unchanged.

No shorter candidate is promoted and no separate Validation/OOS run is justified for L240/L360/L600/L900 after their preregistered DEV failure.

## 6. What this decision does and does not prove

Authorized conclusion:

> Within the preregistered clean one-factor candidate set 240/360/600/900/1440 active M1, L1440 is the only memory that preserves the frozen Z4 revisit uplift robustly across all four DEV months on BID and ASK with a positive weekly bootstrap lower bound. Retaining 1,440 is therefore justified.

Not authorized:

- `1,440 is the globally optimal support/resistance memory`;
- `all longer memories would be worse`;
- `adaptive/decayed memory cannot improve Z4`;
- `1,440 validates reaction/reversal`;
- `shorter lookbacks never contain information`.

Those are different hypotheses and were not tested.

## 7. Consequence for the visual problem

The observed LIVE-zone disappearance/reappearance should **not** be repaired by shortening the 1,440-bar history. The DEV sensitivity evidence points in the opposite direction: shorter memories have materially higher zone churn.

The remaining architectural variable most directly relevant to what the user observes in M1 Replay is the **15-minute snapshot cadence**, which has not been demonstrated to be optimal. If investigated, cadence must be tested separately with L1440 frozen so that memory and cadence are not confounded.

## 8. Production status

- Z4 L1440: **KEEP / incumbent validated architecture**.
- R map: **unchanged**.
- Pine production lookback: **do not change**.
- L240/L360/L600/L900: **NO-GO as replacements after this DEV gate**.
- Next optional architecture study: cadence sensitivity with L1440 fixed.
