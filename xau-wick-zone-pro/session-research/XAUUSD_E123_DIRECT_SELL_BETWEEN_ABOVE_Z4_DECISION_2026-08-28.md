# XAUUSD direct E1/E2/E3 SELL between / above Z4 — decision

Date: 2026-08-28  
Branch: `agent/xau-wick-zone-pro-dev`  
Status: **RETROSPECTIVE DIRECT SELL STUDY COMPLETE — NO PRODUCTION PROMOTION**

## Corrected research question

This is the corrected study requested by the user. There is **no prerequisite Z4 break**.

A direct SELL is studied when a current causal M1 E1/E2/E3 resistance zone is either:

- `BETWEEN_Z4_STRICT`: entirely inside the open gap between two adjacent causal Z4 intervals; or
- `ABOVE_HIGHEST_Z4_STRICT`: entirely above the upper boundary of the highest causal Z4.

E zones overlapping a Z4 are excluded.

The design was frozen before outcomes in:
`XAUUSD_E123_DIRECT_SELL_BETWEEN_ABOVE_Z4_PREREG_v1_0_2026-08-28.md`
(blob `3c39c1162c6b5f84c76d8253dc39ca9c718f1347`).

No E score, threshold, family filter or refit is used.

## Frozen mechanics

- exact sign-reflection (`p -> -p`) of the frozen causal sticky E-BUY architecture creates the upper-wick/resistance E1/E2/E3 architecture without new fitting;
- touch of eligible E;
- bearish BR70 trigger: `close < open` and `(high-close)/(high-low) >= 0.70`;
- entry next M1 open in same session;
- one fire per structural E identity per session;
- if multiple E are touched on one candle, priority E1 then E2 then E3;
- stop/invalidation = frozen E upper boundary, but only a confirmed M1 close strictly above it invalidates; wick above is allowed;
- `BETWEEN_Z4_STRICT` TP = upper boundary of adjacent lower Z4;
- `ABOVE_HIGHEST_Z4_STRICT` TP = upper boundary of highest Z4;
- target is frozen at trigger;
- same-M1 TP + close invalidation = ambiguous;
- outcomes only until end of same session.

Windows:
- H1: 2024-08-01 → 2025-08-01 UTC;
- H2: 2025-08-01 → 2026-08-01 UTC.

Sessions:
- US 08:00–17:00 NY;
- Asia broad 18:00–03:00 NY;
- Asia Core standalone 21:00–03:00 NY;
- Europe 03:00–08:00 NY.

All R/PF values are structural before spread, commission and slippage and use terminal TP/invalidation cases.

## 1. Primary results — all eligible direct E SELLs

| Session | H1 terminal | H1 TP rate | H1 Exp.R | H1 PF_R | H2 terminal | H2 TP rate | H2 Exp.R | H2 PF_R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| US 08–17 | 4514 | 31.17% | +0.519 | 1.75 | 4747 | 30.15% | +0.570 | 1.82 |
| Asia 18–03 | 5395 | 24.34% | +0.485 | 1.64 | 5142 | 27.71% | +0.616 | 1.85 |
| Asia Core 21–03 | 3790 | 25.88% | +0.626 | 1.84 | 3546 | 28.40% | +0.534 | 1.75 |
| Europe 03–08 | 3217 | 28.60% | +0.575 | 1.80 | 3042 | 27.25% | +0.534 | 1.73 |

The notable fact is not high hit rate. Hit rate is only roughly 24–31%, but raw target-based structural expectancy is positive in every session and both historical halves.

## 2. Geometry — between Z4 vs above highest Z4

### `BETWEEN_Z4_STRICT`

| Session | H1 TP rate | H1 Exp.R | H1 PF_R | H2 TP rate | H2 Exp.R | H2 PF_R |
|---|---:|---:|---:|---:|---:|---:|
| US | 31.79% | +0.589 | 1.86 | 29.70% | +0.477 | 1.68 |
| Asia 18–03 | 25.66% | +0.589 | 1.79 | 28.40% | +0.703 | 1.98 |
| Asia Core | 27.61% | +0.819 | 2.13 | 29.27% | +0.616 | 1.87 |
| Europe | 29.10% | +0.632 | 1.89 | 27.99% | +0.583 | 1.81 |

This is the cleanest and most stable descriptive result. `BETWEEN_Z4_STRICT` is positive in all 8 session x half cells and is generally stronger than the above-highest class.

### `ABOVE_HIGHEST_Z4_STRICT`

| Session | H1 TP rate | H1 Exp.R | H1 PF_R | H2 TP rate | H2 Exp.R | H2 PF_R |
|---|---:|---:|---:|---:|---:|---:|
| US | 30.01% | +0.390 | 1.56 | 31.08% | +0.766 | 2.11 |
| Asia 18–03 | 21.83% | +0.287 | 1.37 | 26.00% | +0.403 | 1.54 |
| Asia Core | 22.42% | +0.237 | 1.31 | 26.26% | +0.335 | 1.45 |
| Europe | 27.57% | +0.457 | 1.63 | 25.27% | +0.404 | 1.54 |

Above-highest is also positive in all session/half cells, but weaker and less homogeneous than between-Z4 except US H2.

## 3. E1 / E2 / E3 — all geometries

### US
- E1: H1 32.93%, +0.475R; H2 31.47%, +0.613R.
- E2: H1 29.50%, +0.631R; H2 28.08%, +0.333R.
- E3: H1 26.65%, +0.464R; H2 29.01%, +0.945R.

### Asia broad
- E1: H1 25.83%, +0.505R; H2 30.45%, +0.652R.
- E2: H1 22.46%, +0.424R; H2 24.66%, +0.416R.
- E3: H1 21.37%, +0.530R; H2 21.54%, +0.921R.

### Asia Core standalone
- E1: H1 27.29%, +0.618R; H2 31.35%, +0.573R.
- E2: H1 24.73%, +0.707R; H2 24.45%, +0.340R.
- E3: H1 21.75%, +0.458R; H2 23.92%, +0.812R.

### Europe
- E1: H1 31.13%, +0.588R; H2 28.85%, +0.520R.
- E2: H1 25.16%, +0.583R; H2 24.64%, +0.418R.
- E3: H1 24.55%, +0.491R; H2 26.80%, +0.914R.

E1 has the most stable/highest hit rate. E2 and E3 can have higher expectancy because their successful trades tend to carry larger R. Rank alone is not a clean monotonic quality score.

## 4. Most stable interaction: E rank within `BETWEEN_Z4_STRICT`

### E1 between two Z4
- US: H1 33.25%, +0.483R; H2 31.52%, +0.509R.
- Asia broad: H1 26.57%, +0.567R; H2 30.69%, +0.686R.
- Asia Core: H1 28.19%, +0.742R; H2 32.01%, +0.601R.
- Europe: H1 30.89%, +0.653R; H2 29.78%, +0.524R.

### E2 between two Z4
- US: H1 30.85%, +0.770R; H2 26.90%, +0.237R.
- Asia broad: H1 24.19%, +0.603R; H2 25.68%, +0.484R.
- Asia Core: H1 27.09%, +1.011R; H2 24.83%, +0.428R.
- Europe: H1 26.61%, +0.597R; H2 25.10%, +0.471R.

### E3 between two Z4
- US: H1 27.32%, +0.639R; H2 28.16%, +0.892R.
- Asia broad: H1 24.71%, +0.661R; H2 23.80%, +1.322R.
- Asia Core: H1 26.06%, +0.712R; H2 26.98%, +1.123R.
- Europe: H1 26.15%, +0.608R; H2 27.51%, +1.150R.

All 24 rank x session x half cells for E1/E2/E3 inside strict between-Z4 geometry are positive in structural expectancy. This is strong descriptive replication, but it remains retrospective on the same H1/H2 universe and does not authorize a production rule by itself.

## 5. Robustness / failure-mode QA

### Tiny-stop check

The positive expectancy is not primarily a zero-stop artifact:
- median stop distance is roughly 0.76–0.80 x local M1 volatility across sessions/halves;
- share with stop <0.10v is roughly 0.6–1.1%;
- share with stop <0.05v is roughly 0.04–0.38%.

### Winner-R distribution

Successful trades have roughly:
- median winner RR ~1.95–2.52R;
- mean winner RR ~3.87–5.28R depending on session/half;
- the top 10% of winners contribute ~43–48% of positive R.

Thus the setup genuinely depends on retaining larger winners to the lower Z4 target.

A diagnostic cap on winner payoff shows this clearly:
- cap every winner at 3R: expectancy becomes negative in every session/half;
- cap at 5R: expectancy becomes near-flat and some Asia H1 variants remain negative;
- cap at 10R: expectancy is positive in every complete session/half.

This is not a replacement strategy; it demonstrates that aggressively taking profit early would destroy much of the observed edge.

### Non-overlapping position sensitivity

The raw study allows signals while previous trades are still active. A diagnostic one-position-at-a-time filter (take the next signal only after the selected trade has resolved) does **not** remove the effect.

All-signal one-position-at-a-time expectancy:
- US: H1 +0.519R / H2 +0.587R;
- Asia broad: +0.495R / +0.614R;
- Asia Core: +0.558R / +0.532R;
- Europe: +0.547R / +0.564R.

Between-Z4 one-position-at-a-time expectancy:
- US: +0.605R / +0.536R;
- Asia broad: +0.565R / +0.698R;
- Asia Core: +0.702R / +0.642R;
- Europe: +0.655R / +0.582R.

So overlapping positions are not the source of the result.

### Signal frequency

Raw executed signals are numerous because E1/E2/E3 are dynamic:
- US median ~18–19 signals/session;
- Asia broad ~21–22;
- Asia Core ~15–16;
- Europe ~13.

This raw research ledger is therefore not yet a manual execution plan.

## 6. Scientific interpretation

What the study supports:

1. The corrected direct SELL concept is **materially more promising** than the previously misinterpreted break/retrace SELL study.
2. Direct E SELLs **between two Z4** have a remarkably stable positive target-based structural expectancy across H1/H2 and all tested sessions.
3. E1 is the most stable rank for hit rate, but E2/E3 can produce higher expectancy through larger winners; there is no simple `E1 > E2 > E3` quality ordering.
4. Direct E SELLs above the highest Z4 are also positive historically, but weaker and less homogeneous than between-Z4.

What the study does **not** yet support:

- it does not prove the E zone itself adds incremental predictive information versus an appropriately matched bearish-rejection control in the same Z4 geometry;
- it is BID-only structural research before spread, commission and slippage;
- it does not validate early partial exits or tight profit caps; the edge depends on larger winners;
- it does not justify selecting the best-looking session/rank interaction after reading H1/H2;
- it does not authorize a Pine/production rule yet.

The appropriate next scientific step is a frozen control/confirmation study: compare these E-triggered bearish rejections against matched non-E bearish rejections in the same between-Z4 / above-highest geometry, then validate the surviving direct-E rule on genuinely future data.

## Evidence

Primary workflow run: `33193034282`.

Final aggregate artifact:
- `direct-esell-between-above-z4-v1-final`;
- artifact ID `9694742024`;
- digest `sha256:d2abca7e41ab3a70c239bc5b1aadc0d13d6a913856f7ade55ebfce6777728fec`.

Session artifact digests:
- US: `sha256:6ba15b34022486615366d8c4dc5e07a481def39b537727c0ad673f7f5d9361d9`;
- Asia broad: `sha256:1ed5338e0bb3609a007f96734b054d874d2d40839cf217abfba39c9099c2faec`;
- Asia Core: `sha256:bb6bb981b32b69f3e2e45135e3cabeb152b2f9440d7dfed2a7f09a93431614f6`;
- Europe: `sha256:62033bb56beb93f88e7cff187200b83251e825cc9d3b1c4677dc2dfc43a418a5`.

Production authorization: **NONE_RETROSPECTIVE_DIRECT_ESELL_RESEARCH**.
