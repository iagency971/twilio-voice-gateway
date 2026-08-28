# XAUUSD standalone Z4-gap BR70 SELL — exploratory decision

Date: 2026-08-28  
Branch: `agent/xau-wick-zone-pro-dev`  
Status: **EXPLORATORY RULE WORTH PROSPECTIVE CONFIRMATION — NOT PRODUCTION VALIDATED**

## Origin and scientific status

This rule was formulated only after the matched non-E control showed that E1/E2/E3 contact was not incrementally supported for the direct SELL concept. Therefore H1/H2 below are retrospective exploratory evidence, not an independent validation.

Preregistration frozen before these standalone outcomes:
`XAUUSD_Z4_GAP_BR70_DIRECT_SELL_PREREG_v1_0_2026-08-28.md`, blob `8358749cab0a4cef1cc5afc429e3b72fd665b86a`.

Frozen engine:
`xau_z4_gap_br70_direct_sell_v1_0.py`, blob `3fba3c8fd0918897979d02b51a9b7d188ae66c75`.

## Frozen standalone rule

No E zone is used.

- causal adjacent Z4 intervals define an open price gap;
- trigger high lies strictly inside that gap;
- bearish BR70: `close < open` and `(high-close)/(high-low) >= 0.70`;
- no prerequisite breakout;
- entry next M1 open, still inside the frozen gap;
- TP = upper boundary of adjacent lower Z4;
- invalidation = confirmed M1 close strictly above lower boundary of adjacent upper Z4; wick above allowed;
- one fire per structural gap identity per session;
- unresolved at session end = `NEITHER` for the structural outcome study.

## Results

| Session | H1 terminal N | H1 TP | H1 Exp.R | H1 PF_R | H2 terminal N | H2 TP | H2 Exp.R | H2 PF_R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| US 08-17 | 1455 | 59.79% | **+0.096R** | 1.24 | 1422 | 53.73% | **+0.060R** | 1.13 |
| Asia 18-03 | 1314 | 54.26% | **+0.067R** | 1.15 | 1354 | 54.36% | **+0.051R** | 1.11 |
| Asia Core 21-03 | 990 | 53.54% | **+0.071R** | 1.15 | 976 | 56.66% | **+0.114R** | 1.26 |
| Europe 03-08 | 896 | 54.80% | **-0.017R** | 0.96 | 837 | 55.79% | **+0.069R** | 1.16 |

Terminal-N-weighted pooled structural expectancy:
- H1: **+0.061R**;
- H2: **+0.070R**.

### One position at a time

| Session | H1 Exp.R | H2 Exp.R |
|---|---:|---:|
| US | +0.073R | +0.025R |
| Asia 18-03 | +0.079R | +0.064R |
| Asia Core 21-03 | +0.021R | +0.148R |
| Europe | -0.030R | +0.056R |

Pooled terminal-N-weighted one-position expectancy:
- H1: **+0.044R**;
- H2: **+0.067R**.

## Prespecified exploratory coherence criterion

- positive H1 expectancy in at least 3/4 sessions: **PASS (3/4)**;
- positive H2 expectancy in at least 3/4 sessions: **PASS (4/4)**;
- pooled H1 expectancy positive: **PASS**;
- pooled H2 expectancy positive: **PASS**;
- pooled one-position H1 non-negative: **PASS**;
- pooled one-position H2 non-negative: **PASS**.

Verdict: `EXPLORATORY_Z4_GAP_BR70_RULE_WORTH_PROSPECTIVE_CONFIRMATION`.

## Important interpretation

Replacing the E stop with a fully causal structural stop on the adjacent upper Z4 dramatically reduces the apparent expectancy versus the earlier direct-E ledger, but does **not** eliminate it historically. This supports the control-study interpretation that the reusable signal is the Z4-gap bearish-rejection geometry, not E contact itself.

The effect is modest. Therefore costs, slippage and explicit liquidation of session-end `NEITHER` positions are first-order issues and must be checked before any prospective promotion design.

## Evidence

Workflow run: `33203080123`.

Final aggregate artifact: `z4-gap-br70-direct-sell-v1-final`, artifact id `9698635633`, digest `sha256:33b17c856cfb5aa4cda8adc0709f8ca3f2c3d16cad285aba3874018e7cfbccbc`.

Session artifact digests:
- US: `sha256:6c1fd428670d8de41e3267a0fde1c953ae42ed4c6fa2c4d063dc5d8e85dd07d7`;
- Asia broad: `sha256:20bba7f9492ec0a468bdb57913ff363ed14802fca77f2fc96c58197b72e6daf8`;
- Asia Core: `sha256:e5a1c5981a092fa1a9baa773b442ca3179c8488a65c447825214fff34cf4a08d`;
- Europe: `sha256:0429c8a87a33d46e00a4ab50cf071ecf31418eeb3e080b341fa4711d5206f9d1`.

Production authorization: **NONE_POST_CONTROL_EXPLORATORY**.
