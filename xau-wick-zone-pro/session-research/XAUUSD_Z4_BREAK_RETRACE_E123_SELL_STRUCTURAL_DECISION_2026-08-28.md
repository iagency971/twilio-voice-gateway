# XAUUSD Z4 → retrace → E1/E2/E3 SELL structural study — decision

Date: 2026-08-28  
Branch: `agent/xau-wick-zone-pro-dev`  
Status: **RETROSPECTIVE SELL STUDY COMPLETE — NO PRODUCTION PROMOTION**

## Frozen design

This study is the exact directional mirror of the frozen BUY structural study and was preregistered before SELL outcomes in:

`XAUUSD_Z4_BREAK_RETRACE_E123_SELL_NO_SCORE_PREREG_v1_0_2026-08-28.md`

Prereg blob: `d03d059c2d4dd29990924cf8884e3d918a50dbc2`.

No E score and no E threshold were used.

The frozen BUY machinery was reflected mathematically (`p -> -p`) so that the already frozen lower-wick/support E architecture becomes an exact upper-wick/resistance E architecture without new parameter fitting.

Original-space SELL mechanics:
- confirmed bearish close through a causal lower main Z4;
- later wick-or-more retracement into the broken main Z4 is mandatory;
- current causal sticky E1/E2/E3 resistance zone is touched;
- bearish legacy BR70 trigger: `close < open` and `(high-close)/(high-low) >= 0.70`;
- SELL at next M1 open;
- wick above main Z4 is allowed;
- only confirmed M1 close strictly above frozen `main_zhi` invalidates;
- TP = first touch of the next lower causal Z4 frozen at breakout, at its upper boundary.

Historical windows:
- H1: 2024-08-01 → 2025-08-01 UTC;
- H2: 2025-08-01 → 2026-08-01 UTC.

Sessions:
- US 08:00–17:00 New York;
- Asia broad 18:00–03:00 New York;
- Asia Core standalone 21:00–03:00 New York;
- Europe 03:00–08:00 New York.

All expectancy and PF values below are structural, before spread, commissions and slippage. `NEITHER` observations are not included in terminal TP/SL expectancy.

## Primary session results

| Session | H1 terminal | H1 TP rate | H1 Exp.R | H1 PF_R | H2 terminal | H2 TP rate | H2 Exp.R | H2 PF_R | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| US 08–17 | 134 | 43.28% | +0.005 | 1.01 | 153 | 32.68% | -0.181 | 0.73 | NO — deteriorates in H2 |
| Asia 18–03 | 86 | 37.21% | +0.059 | 1.09 | 127 | 38.58% | +0.051 | 1.08 | EXPLORATORY — weak but directionally stable positive expectancy |
| Asia Core 21–03 standalone | 52 | 32.69% | -0.048 | 0.93 | 77 | 33.77% | -0.157 | 0.76 | NO |
| Europe 03–08 | 60 | 28.33% | -0.157 | 0.78 | 51 | 43.14% | +0.221 | 1.39 | NO — H1/H2 reversal |

No primary session-level SELL setup warrants production promotion from this retrospective study.

## Prespecified E1 / E2 / E3 results

### US 08–17

| E | H1 TP/terminal | H1 rate | H1 Exp.R | H2 TP/terminal | H2 rate | H2 Exp.R |
|---|---:|---:|---:|---:|---:|---:|
| E1 | 46/112 | 41.07% | -0.069 | 40/128 | 31.25% | -0.190 |
| E2 | 9/17 | 52.94% | +0.153 | 10/21 | 47.62% | +0.030 |
| E3 | 3/5 | 60.00% | +1.154 | 0/4 | 0.00% | -1.000 |

E1 is not good. E3 is clearly too sparse and reverses. E2 is the only US rank with positive structural expectancy in both H1 and H2, but the effect is small in H2 and sample sizes are modest. Treat as **new candidate only**, not validation.

### Asia broad 18–03

| E | H1 TP/terminal | H1 rate | H1 Exp.R | H2 TP/terminal | H2 rate | H2 Exp.R |
|---|---:|---:|---:|---:|---:|---:|
| E1 | 28/77 | 36.36% | +0.006 | 40/104 | 38.46% | +0.032 |
| E2 | 4/8 | 50.00% | +0.703 | 7/17 | 41.18% | +0.346 |
| E3 | 0/1 | 0.00% | -1.000 | 2/6 | 33.33% | -0.454 |

E1 is approximately flat. E2 is positive in both windows, but H1 has only 8 terminal cases. It is therefore **promising but insufficient**, not a promoted filter. E3 is not supported.

### Asia Core 21–03 standalone

| E | H1 TP/terminal | H1 rate | H1 Exp.R | H2 TP/terminal | H2 rate | H2 Exp.R |
|---|---:|---:|---:|---:|---:|---:|
| E1 | 15/49 | 30.61% | -0.120 | 23/65 | 35.38% | -0.118 |
| E2 | 2/2 | 100.00% | +2.189 | 2/9 | 22.22% | -0.334 |
| E3 | 0/1 | 0.00% | -1.000 | 1/3 | 33.33% | -0.459 |

No rank is supported. The H1 E2 result is a tiny-sample artifact and does not replicate in H2.

### Europe 03–08

| E | H1 TP/terminal | H1 rate | H1 Exp.R | H2 TP/terminal | H2 rate | H2 Exp.R |
|---|---:|---:|---:|---:|---:|---:|
| E1 | 16/51 | 31.37% | -0.061 | 22/44 | 50.00% | +0.416 |
| E2 | 1/9 | 11.11% | -0.704 | 0/5 | 0.00% | -1.000 |
| E3 | 0/0 | — | — | 0/2 | 0.00% | -1.000 |

Europe is not stable for SELL. E1 improves sharply in H2 but fails the required H1/H2 consistency. E2/E3 are poor.

## Geometry E ↔ broken main Z4

For SELL, the exact directional analogue of the BUY `ABOVE_MAIN` subgroup is **`BELOW_MAIN`**: the E resistance zone lies fully below the broken main Z4 in original price space.

### US BELOW_MAIN
- H1: 13/24 = 54.17%, Exp.R -0.035;
- H2: 13/31 = 41.94%, Exp.R -0.119.

Not supported.

### Asia broad BELOW_MAIN
- H1: 12/21 = 57.14%, Exp.R +0.500, PF_R 2.17;
- H2: 9/17 = 52.94%, Exp.R +0.162, PF_R 1.34.

This is the most interesting SELL relation observed. However, it is a subgroup conclusion read from the current retrospective outcomes and H2 has only 17 terminal cases. It must therefore be frozen as a candidate and independently confirmed before use.

### Asia Core standalone BELOW_MAIN
- H1: 5/11 = 45.45%, Exp.R +0.191;
- H2: 4/9 = 44.44%, Exp.R -0.093.

Not supported.

### Europe BELOW_MAIN
- H1: 1/5 = 20.00%, Exp.R -0.762;
- H2: 7/11 = 63.64%, Exp.R +0.285.

Strong H1/H2 reversal; not supported.

## Exploratory Asia 18–21 diagnostic

This diagnostic is explicitly **exploratory** and is not promoted by this study. It is reported because the earlier BUY work had already identified 18:00–21:00 as a potentially distinct subperiod.

Using triggers occurring 18:00–21:00 inside the Asia-broad run:
- H1: 13/32 = 40.63%, Exp.R +0.065, PF_R 1.11;
- H2: 23/49 = 46.94%, Exp.R +0.398, PF_R 1.75.

The original-space `BELOW_MAIN` subset in 18–21 is:
- H1: 6/9 = 66.67%, Exp.R +0.555;
- H2: 5/8 = 62.50%, Exp.R +0.449.

Sample sizes are much too small for promotion. The noteworthy point is qualitative: **18–21 is expectancy-positive on both H1 and H2 for SELL**, while the standalone 21–03 SELL session is negative. This pattern is consistent with the earlier BUY-side observation that 18–21 behaved differently from 21–03. A dedicated prospective 18–21 validation is justified; using the subgroup now is not.

## Decision

1. **Do not promote the generic SELL setup** in US, Asia Core or Europe.
2. **Asia broad 18–03 is the only complete SELL session with positive structural expectancy in both H1 and H2**, but the edge is small (+0.059R / +0.051R) and remains exploratory.
3. **E2 is a possible session-specific candidate**, especially in Asia broad and to a lesser degree US, but it is not universal and cannot be promoted from these results.
4. **Asia broad + BELOW_MAIN is the strongest relation candidate** (57.14% then 52.94%, positive Exp.R both halves), but remains unconfirmed.
5. **The 18–21 slice deserves a dedicated frozen test** because it is positive in both SELL halves and had already shown unusual behavior on the BUY side.
6. No Pine/production rule is changed from this retrospective SELL study.

## Evidence and QA

Primary frozen study run: `33190866059`.

All four session jobs completed successfully and produced immutable artifacts:
- US digest: `sha256:b3cc0e687b589536d932a164db93091dcbef01a6ada213bf00daaaf459144e43`;
- Asia broad digest: `sha256:04dee2949ccafb8d0c7fb2880d175b180d84f0e2e376c5d0cce29ab40b2a0933`;
- Asia Core standalone digest: `sha256:ed97c4ae78f3cece4f764bfb0e72230dac5e17ad67d7c4e0252c344916b695f7`;
- Europe digest: `sha256:b0c57985be07e196dc64625d007c69fa9022f7d3cc0b69a6105b54cfdb05691b`.

The original run's aggregation-only job failed after all four session artifacts were complete because the aggregation runner lacked `pandas`. No trade calculation was affected. Evidence-only repair run `33191655664` downloaded those exact immutable artifacts, performed no trading recomputation, and completed successfully.

Final repaired aggregate artifact:
- `z4-break-retrace-e123-sell-noscore-v1-final-repaired`;
- artifact ID `9693990094`;
- digest `sha256:ece625aea520ee6c948535d5dfd34f26e5ec630bdaf77b5745729fdcb0ba3717`.

Production authorization: **NONE_RETROSPECTIVE_SELL_HYPOTHESIS_STUDY**.