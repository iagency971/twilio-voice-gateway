# XAUUSD Z4 breakout → retrace → E1/E2/E3 bullish rejection — Asia / Europe no-score decision

Date: 2026-08-28  
Branch: `agent/xau-wick-zone-pro-dev`

## Final status

**NO SESSION-LEVEL TRANSFER OF THE US `ABOVE_MAIN` EDGE.**

No score was used. The exact frozen structural mechanics from the US study were transferred to:

- `ASIA_BROAD`: 18:00–03:00 `America/New_York`;
- `ASIA_CORE_STANDALONE`: 21:00–03:00 `America/New_York`, with no state inherited from 18:00–21:00;
- `EUROPE`: 03:00–08:00 `America/New_York`.

The prespecified `ABOVE_MAIN` replication gate fails in all three session definitions.

Europe is nevertheless a **separate expectancy-positive research candidate** because the unfiltered setup has positive normalized structural expectancy in both H1 and H2, despite sub-50% terminal TP rates. This is not production authorization and requires a separate confirmation cycle.

---

## Frozen mechanics

Exactly as preregistered in:
`XAUUSD_Z4_BREAK_RETRACE_E123_ASIA_EUROPE_NO_SCORE_PREREG_v1_0_2026-08-28.md`

- BUY only;
- causal main Z4 broken upward by confirmed M1 close;
- next higher causal Z4 frozen as target at breakout;
- mandatory post-breakout wick-or-more retrace into main Z4;
- E1/E2/E3 may be inside, overlap, above or below main Z4;
- wick below `main_zlo` allowed;
- only confirmed M1 close below `main_zlo` invalidates;
- legacy BR70 retained only for exact comparability (`close > open` and close-position >=0.70);
- entry next M1 open in-session;
- TP first touch of frozen next-higher Z4 lower boundary;
- same-M1 TP/invalidation = ambiguous;
- no E score, no E threshold, no family/rank filter, no refit.

Frozen US structural engine blob:
`7862638917015838948001a374f9bea7dba83e07`

Frozen session wrapper blob:
`536ff1fccf766184d7a61f4a2813b15f2fa79e5c`

Historical windows:
- H1: 2024-08-01 → 2025-08-01;
- H2: 2025-08-01 → 2026-08-01.

---

## 1. Asia broad 18:00–03:00 NY

### Raw structural setup

| Window | Breakouts | Higher target | Main retrace | Executed | TP | Invalidation | Neither | Terminal TP rate | Expectancy_R* | PF_R* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H1 | 350 | 259 | 190 | 94 | 34 | 56 | 4 | **37.78%** | **+0.174R** | 1.28 |
| H2 | 383 | 283 | 205 | 112 | 31 | 75 | 6 | **29.25%** | **-0.109R** | 0.85 |

Interpretation: **not stable**. H1 is mildly positive before costs, H2 reverses negative.

### `ABOVE_MAIN`

| Window | Terminal N | TP | Invalidation | TP rate | Wilson 95% | Expectancy_R* | PF_R* |
|---|---:|---:|---:|---:|---|---:|---:|
| H1 | 18 | 10 | 8 | **55.56%** | 33.72–75.44% | +0.090R | 1.20 |
| H2 | 23 | 9 | 14 | **39.13%** | 22.16–59.21% | -0.069R | 0.89 |

The US `ABOVE_MAIN` effect **does not transfer** to broad Asia.

### Prespecified Asia split by trigger time

#### 18:00–21:00 (`ASIA_EXP_18_21`)

| Window | Terminal N | TP rate | Expectancy_R* | PF_R* |
|---|---:|---:|---:|---:|
| H1 | 30 | **43.33%** | **+0.112R** | 1.20 |
| H2 | 42 | **35.71%** | **+0.343R** | 1.53 |

`ABOVE_MAIN` within 18–21:
- H1: 6/11 = 54.55%, +0.101R;
- H2: 4/8 = 50.00%, +0.026R.

This 18–21 subperiod is notable because normalized structural expectancy is positive in both historical windows, despite low hit rate. It remains **exploratory only**: the broader location/stability work had not scientifically authorized 18–21 as a validated E-zone window, and this study does not repair that prior gate.

#### 21:00–03:00 part within broad Asia

- H1: 21/60 terminal TP = **35.00%**, +0.205R, PF_R 1.31.
- H2: 16/64 = **25.00%**, -0.405R, PF_R 0.46.

This portion is clearly unstable and weak in H2.

### E rank

No stable rank rule is supported:
- E1 H1: 34/79 = 43.04%, +0.337R;
- E1 H2: 25/89 = 28.09%, -0.133R;
- E2/E3 are much sparser and inconsistent.

Do not promote E1/E2/E3 rank from Asia broad.

---

## 2. Asia Core standalone 21:00–03:00 NY

This run starts fresh at 21:00 and intentionally does **not** inherit 18–21 episodes/state.

### Raw structural setup

| Window | Breakouts | Higher target | Main retrace | Executed | TP | Invalidation | Neither | Terminal TP rate | Expectancy_R* | PF_R* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H1 | 249 | 182 | 139 | 63 | 21 | 38 | 4 | **35.59%** | **+0.225R** | 1.35 |
| H2 | 208 | 164 | 123 | 66 | 15 | 46 | 5 | **24.59%** | **-0.396R** | 0.48 |

### `ABOVE_MAIN`

- H1: 4/7 = **57.14%**, +0.074R, PF_R 1.17;
- H2: 5/15 = **33.33%**, -0.120R, PF_R 0.82.

Prespecified replication gate: **FAIL**.

Conclusion: although Asia Core 21–03 remains independently authorized for **zone location/stability display**, this new breakout→retrace→E-rejection trade logic is **not validated there**. This is consistent with the earlier Asia Core reaction work that did not authorize an Asia BUY/BR signal.

### E rank

- E1 H1: 21/51 = 41.18%, +0.417R;
- E1 H2: 11/52 = 21.15%, -0.452R.

Again no stable rank edge.

---

## 3. Europe 03:00–08:00 NY

### Raw structural setup

| Window | Breakouts | Higher target | Main retrace | Executed | TP | Invalidation | Neither | Terminal TP rate | Expectancy_R* | PF_R* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H1 | 228 | 165 | 130 | 75 | 34 | 35 | 6 | **49.28%** | **+0.455R** | **1.90** |
| H2 | 163 | 131 | 97 | 55 | 20 | 26 | 9 | **43.48%** | **+0.270R** | **1.48** |

This is the most interesting non-US result.

The hit rate is below 50% in H2, but **normalized structural expectancy is positive in both H1 and H2**, and theoretical PF_R remains >1 in both. The effect therefore appears to come from favorable target/stop geometry rather than a high win rate.

This warrants a **new Europe-specific confirmation study**, but cannot be promoted from these same H1/H2 outcomes.

### `ABOVE_MAIN`

- H1: 14/22 = **63.64%**, +0.491R, PF_R 2.35;
- H2: 4/11 = **36.36%**, -0.013R, PF_R 0.98.

Prespecified replication gate: **FAIL**.

Therefore `ABOVE_MAIN` is **not** the stable Europe driver and the US structural edge does not transfer.

### E rank

E1 is descriptively notable but is not authorized as a post-hoc filter:
- H1: 31/59 = **52.54%**, +0.616R, PF_R 2.30;
- H2: 18/40 = **45.00%**, +0.247R, PF_R 1.45.

E2/E3 are sparse. Because this rank observation is opened on the same historical data, it may only motivate a future preregistered test.

### Relation geometry

Europe's positive global expectancy is not driven by `ABOVE_MAIN` in H2. Descriptively:
- `INSIDE_MAIN`: H1 +0.692R; H2 +0.359R;
- `OVERLAP_MAIN`: H1 +0.319R; H2 +0.358R;
- `ABOVE_MAIN`: H1 +0.491R; H2 -0.013R.

These are post-outcome diagnostics, not filters authorized for trading.

---

## Comparison with the prior US study

| Session | H1 terminal TP | H1 Exp_R* | H2 terminal TP | H2 Exp_R* | `ABOVE_MAIN` replicated? |
|---|---:|---:|---:|---:|---|
| US 08–17 | 44.59% | +0.073R | 40.91% | -0.063R | Historical yes, fresh still inconclusive |
| Asia 18–03 | 37.78% | +0.174R | 29.25% | -0.109R | **No** |
| Asia Core 21–03 | 35.59% | +0.225R | 24.59% | -0.396R | **No** |
| Europe 03–08 | 49.28% | +0.455R | 43.48% | +0.270R | **No** |

Key distinction: **Europe is the only non-US full-session setup with positive normalized expectancy in both H1 and H2.**

---

## Scientific decision

1. **Asia Broad 18–03: do not promote.** Raw setup and `ABOVE_MAIN` fail H1→H2 stability.
2. **Asia Core 21–03: do not promote a BUY/rejection rule.** H2 is clearly negative for this setup despite previously validated zone location/stability.
3. **Europe 03–08: retain as a new research candidate**, because unfiltered normalized structural expectancy/PF_R are positive in both H1 and H2. This is not yet a live or Pine signal.
4. **Do not transfer the US `ABOVE_MAIN` filter to Asia or Europe.** It fails replication in both.
5. **Do not promote E1/E2/E3 or family filters** from these outcomes. Any Europe E1/INSIDE/OVERLAP follow-up must be preregistered separately and tested on genuinely new evidence.
6. **18–21 Asia is interesting descriptively** because expectancy is positive in both H1/H2, but it remains an exploratory zone window and requires its own location + structural confirmation cycle before any signal claim.
7. No score was used anywhere in this study.
8. No Pine BUY marker, alert, production score, hard-SL profitability or CFD execution claim is authorized.

Current classifications:

- `ASIA_BROAD_NO_SCORE_NOT_VALIDATED`
- `ASIA_CORE_NO_SCORE_NOT_VALIDATED`
- `EUROPE_NO_SCORE_EXPECTANCY_CANDIDATE_REQUIRES_CONFIRMATION`
- `ABOVE_MAIN_SESSION_TRANSFER_FAIL`

---

## Evidence

Successful parallel workflow run: `33168286052`.

Aggregate artifact digest:
`sha256:995a41cc8343840c2649e8ba89f3ed3b1776d0c35049b649d617b92bb019fa52`

Result SHA-256:
- Asia broad: `a3dac3de9f339b53110327b54244065e70637f7473f42c01fff1a7ff9491614c`
- Asia Core standalone: `7b2df31f9221892fc59a45e6180e584f949cd007cef1bad9dfe0eea9ec16a34b`
- Europe: `83bc9d2e3b935e51df922ecd434a9198033faf2d4f840be3161216938dd3cf26`

Trade-table SHA-256:
- Asia broad: `3425d581dde9efb4704a5fea2af12c453e8582185d47049e856f684ce874df14`
- Asia Core standalone: `a167ff8022b7f8d6bb3a7a9e182ec0e88572572a2e97988dff5601983931c983`
- Europe: `585475560b26a3b93224e4d342b144b9396dbdd58f47d17befabc95bbde779cc`

\* `Expectancy_R` and `PF_R` are normalized structural diagnostics before spread, commissions and slippage. Wins use the frozen target/entry versus main-Z4-close-invalidation geometry; invalidations are -1R. They are not a broker/live-account P&L backtest and invalidation is close-based, not a hard intrabar stop.
