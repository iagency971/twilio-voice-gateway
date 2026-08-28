# XAUUSD Z4 breakout → retrace → E1/E2/E3 bullish rejection — Structural decision

Date: 2026-08-28  
Branch: `agent/xau-wick-zone-pro-dev`

## Final status

**RESEARCH CANDIDATE ONLY — NO PRODUCTION PROMOTION.**

The preregistered structural setup was evaluated on two historical windows and the strongest descriptive subgroup (`ABOVE_MAIN`) was then tested on fresh August 2026 data under a separate preregistration. The fresh confirmation label is **`NOT_CONFIRMED`** because the fresh terminal sample for `ABOVE_MAIN` is only `n=2` and the rate is exactly 50%.

This is best interpreted as **inconclusive fresh evidence**, not as proof that the historical `ABOVE_MAIN` effect is false.

---

## Frozen structural rule tested

BUY only, US 08:00–17:00 `America/New_York`.

1. A causal frozen main Z4 is broken upward by confirmed M1 close.
2. The next higher causal Z4 is frozen at breakout as TP reference.
3. Price must later retrace at least by wick into the original main Z4.
4. E1/E2/E3 may be inside, overlap, above, or below the main Z4.
5. A wick below `main_zlo` is explicitly allowed.
6. Only an M1 **close strictly below `main_zlo`** invalidates the main setup.
7. After the mandatory main-Z4 retracement, a displayed causal E zone must be touched and the candle must reject bullishly (`close > open`, close-position >= 0.70).
8. Entry is next M1 open.
9. TP = first touch of the frozen next-higher Z4 `target_zlo`.
10. Invalidation = first later M1 close strictly below frozen `main_zlo`.

No E score, no E80/E90 filter, no family/rank optimization, no model refit.

---

## Historical preregistered study

Workflow run: `33139524456`  
Artifact: `z4-break-retrace-e123-rejection-v1-1`  
Engine blob: `7862638917015838948001a374f9bea7dba83e07`

### All E1/E2/E3

| Window | Executed | TP | Invalidation | Neither | Ambiguous | Terminal TP rate | Structural expectancy before costs* |
|---|---:|---:|---:|---:|---:|---:|---:|
| H1 2024-08-01→2025-08-01 | 153 | 66 | 82 | 4 | 1 | 44.59% | +0.073R |
| H2 2025-08-01→2026-08-01 | 138 | 54 | 78 | 6 | 0 | 40.91% | -0.063R |
| Pooled terminal | — | 120 | 160 | — | — | 42.86% | +0.009R |

The unfiltered setup is therefore not strong enough to promote as a standalone entry rule.

### E rank

Historical rank does **not** show a stable monotonic hierarchy:

- H1: E1 45.61%, E2 41.67%, E3 40.00% terminal TP.
- H2: E1 40.57%, E2 45.83%, E3 0/2 sparse.
- Pooled: E1 43.18%, E2 43.75%, E3 33.33% sparse.

Conclusion: **do not promote E1 vs E2 vs E3 rank as an edge by itself.**

### Relative E geometry vs main Z4

| Geometry | H1 terminal TP | H2 terminal TP | Pooled historical |
|---|---:|---:|---:|
| `ABOVE_MAIN` | 25/42 = **59.52%** | 22/32 = **68.75%** | 47/74 = **63.51%** |
| `INSIDE_MAIN` | 13/43 = 30.23% | 8/36 = 22.22% | — |
| `OVERLAP_MAIN` | 28/62 = 45.16% | 23/60 = 38.33% | — |
| `BELOW_MAIN` | sparse | sparse | sparse |

Historical `ABOVE_MAIN` structural expectancy before costs*:

- H1: **+0.195R**, theoretical PF_R 1.48.
- H2: **+0.335R**, theoretical PF_R 2.07.
- pooled terminal 74 cases: **+0.255R**, theoretical PF_R 1.70.

Wilson 95% for historical terminal TP rate:

- H1 `ABOVE_MAIN`: 59.52%, interval approximately [44.49%, 72.96%].
- H2 `ABOVE_MAIN`: 68.75%, interval approximately [51.43%, 82.05%].
- pooled `ABOVE_MAIN`: 63.51%, interval approximately [52.13%, 73.56%].

This is a strong retrospective pattern and is directionally replicated H1/H2, but it was identified as a subgroup after inspecting the preregistered historical output. It therefore required fresh confirmation before any promotion.

---

## User-specified wick-below-main rule

The rule to allow a lower wick below the main Z4 while rejecting only a **close** below `main_zlo` materially changes the eligible sample and was correctly implemented.

Historical diagnostic:

- H1 with a pre-entry wick below main: terminal TP 46.03%; without: 43.53%.
- H2 with a pre-entry wick below main: terminal TP 30.30%; without: 51.52%.

The direction is not stable. Therefore:

**Wick below main remains ALLOWED, but it is NOT promoted as a positive filter.**

---

## Fresh August 2026 confirmation

Fresh preregistration committed before reading fresh US outcomes:
`XAUUSD_Z4_BREAK_RETRACE_E_ABOVE_MAIN_FRESH_AUG_PREREG_v1_0_2026-08-28.md`

Successful workflow run: `33141326583`  
Artifact: `z4-e-above-main-fresh-aug-v1-1`

Source:

- July warmup SHA-256: `1861d23f4edbaa9cc5c5ca2bd419c9a7d54ef60299a75c5d4e8e8681bd308286`
- August SHA-256: `4f61d531018a8e8c37b1f410945e1d23d59fee96cde13bef223dcc9e63d0f852`
- Available August timestamps: 2026-08-02 00:00 UTC → 2026-08-20 23:58 UTC.

### Fresh all-setup diagnostic

- Main bullish Z4 breakouts: 33.
- Breakouts with a higher causal target: 17.
- Main-Z4 retraces by wick-or-more: 12.
- Executed trades: 7.
- TP: 3.
- Invalidation: 4.
- Terminal TP rate: **42.86%**.
- Structural expectancy before costs*: **-0.172R**.

### Fresh preregistered primary hypothesis: `ABOVE_MAIN`

- Executed/terminal cases: **2**.
- TP: **1**.
- Invalidation: **1**.
- Terminal TP rate: **50.00%**.
- Wilson 95%: approximately **[9.45%, 90.55%]**.
- Structural expectancy before costs*: **-0.043R**.
- Theoretical PF_R: **0.91**.

Preregistered directional-confirmation rule was `n >= 10` and terminal TP rate `> 50%`.

**Result: `NOT_CONFIRMED`.**

The fresh sample is far below the required denominator and does not exceed 50%. It cannot validate the historical effect. Because `n=2`, it also does not provide enough information to confidently reject it.

Fresh rank diagnostics are similarly too sparse:

- E1: 6 terminal trades, 2 TP / 4 invalidations = 33.33%.
- E2: 1 terminal trade, 1 TP = 100%, non-inferential.
- E3: 0 trades.

Fresh geometry diagnostics:

- `ABOVE_MAIN`: 1/2 TP = 50%.
- `OVERLAP_MAIN`: 2/4 TP = 50%.
- `INSIDE_MAIN`: 0/1 TP.
- `BELOW_MAIN`: 0 trades.

---

## Scientific decision

1. **Do not promote the raw breakout→retrace→any-E rejection setup.** Its H1/H2 aggregate is essentially flat before costs and fresh August is 3/7.
2. **Do not promote E1/E2/E3 rank as an edge.** No stable rank ordering exists.
3. **Retain `ABOVE_MAIN` as the only structural candidate deserving continued prospective observation.** Historical evidence is coherent and economically positive before costs, but the independent fresh sample is too small and fails the preregistered confirmation rule.
4. **Keep wick-below-main allowed exactly as specified**, with close-below-main as invalidation. Do not use wick-below itself as a score or positive filter.
5. **No Pine BUY marker, no production alert, no production score modification** is scientifically authorized from this study at this stage.
6. The next valid evidence should be additional genuinely new US sessions under the frozen `ABOVE_MAIN` rule, without changing geometry, trigger, stop, TP, rank, family, or session after observing outcomes.

### Current authorization

`NO_PRODUCTION_PROMOTION_ABOVE_MAIN_FRESH_INCONCLUSIVE`

---

\* Structural R is a normalized research diagnostic: TP wins use the frozen nominal target/stop distance ratio and invalidations are normalized to -1R. It is **before spread, commissions and execution/slippage**, and the invalidation event is close-based rather than a hard intrabar broker stop. It must not be interpreted as a live-account PnL backtest.

## Evidence hashes

Historical result SHA-256: `48a8477f5743c034c148eb8a918861560d57c5dea71e65db6d602fdb28cfdb9c`  
Historical trades SHA-256: `1aacd87f8b0787f330976c0e47dcdc91f3bcdecb74ac7de96a3acb0da6e59e0d`  
Fresh decision SHA-256: `de2d8c670b0f6874ce9acd4670f27c5410021d905dd68cf016309474e350596a`  
Fresh result SHA-256: `969cee68529274d3a52232637b0138dba08e2db567d4a588e69591bc51202b80`  
Fresh trades SHA-256: `140601fa947aa3b0a358dc09cc2cfcddfefc2f7c2f3413ef5654445e887586c9`
