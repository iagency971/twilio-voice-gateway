# XAUUSD E1/E2/E3 direct SELL between/above Z4 — preregistration v1.0

Date: 2026-08-28
Branch: `agent/xau-wick-zone-pro-dev`
Status: **FROZEN BEFORE OUTCOMES**

## Question

Study direct SELL entries on causal M1 E1/E2/E3 resistance zones **without any prerequisite Z4 breakout**.

Eligible E geometry in original price space is limited to:

1. `BETWEEN_Z4_STRICT`: the entire E interval lies strictly in the open gap between two adjacent causal Z4 intervals;
2. `ABOVE_HIGHEST_Z4_STRICT`: the entire E interval lies strictly above the upper boundary of the highest causal Z4.

Any E overlapping a Z4 is excluded from the primary study.

## Frozen E architecture

The SELL E architecture is the exact sign-reflection (`p -> -p`) of the frozen causal sticky E-BUY architecture:

- `xau_ebuy_coverage_v0_1.py` blob `ef45037d2a99a705ddf9bfbc3ebc666f88119a80`;
- `xau_ebuy_coverage_v0_4_sticky.py` blob `bfb0d65efce0f5773b2045eaf4c31ed6bc07740f`;
- architecture: Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50;
- max three sticky zones, labelled E1/E2/E3 by current displayed rank.

No E score, no E threshold, no family filter and no refit are allowed.

## Frozen trade mechanics

For each session independently:

- a current causal sticky E1/E2/E3 SELL resistance zone must be above the current price and belong to one of the two primary geometry classes;
- the M1 trigger bar must touch/intersect that E zone;
- trigger = legacy bearish rejection for exact directional comparability: `close < open` and `(high-close)/(high-low) >= 0.70`;
- if one candle touches multiple displayed E zones, use the lowest rank number only (`E1` before `E2` before `E3`) to prevent duplicate same-candle entries;
- one structural E identity may fire only once per session; identity is considered the same when intervals overlap or centers remain within `0.25 * max(v_old,v_new)`;
- entry = next M1 open, and must remain inside the selected session;
- no trade if the target was already touched on the trigger bar;
- no trade if next-open is already at/beyond the target or above the E upper boundary.

### Target

- `BETWEEN_Z4_STRICT`: the target is the adjacent causal Z4 immediately below E, frozen at trigger; TP occurs on first touch of that lower Z4 upper boundary (`target_zhi`).
- `ABOVE_HIGHEST_Z4_STRICT`: the target is the highest causal Z4, frozen at trigger; TP occurs on first touch of its upper boundary (`target_zhi`).

### Invalidation

- structural invalidation is the selected E upper boundary (`e_zhi`) frozen at trigger;
- wick above E is allowed;
- only a confirmed M1 close strictly above frozen `e_zhi` invalidates;
- if TP touch and close-invalidation occur on the same M1, outcome = `AMBIGUOUS`.

Trade outcomes are scanned only until the end of that same session. `NEITHER` remains unresolved for terminal TP-rate purposes.

## Windows

- H1: `2024-08-01T00:00:00Z` to `2025-08-01T00:00:00Z`;
- H2: `2025-08-01T00:00:00Z` to `2026-08-01T00:00:00Z`.

Sessions, all in `America/New_York`:

- US: 08:00–17:00;
- ASIA_BROAD: 18:00–03:00;
- ASIA_CORE_STANDALONE: 21:00–03:00, with no state inherited from 18:00–21:00;
- EUROPE: 03:00–08:00.

## Prespecified outputs

For every session and H1/H2:

- candidate touches, executed trades, TP, invalidation, neither, ambiguous;
- terminal TP rate;
- normalized structural expectancy in R where winner = frozen target distance / frozen stop distance and loser = -1R;
- theoretical PF_R;
- separate results for `BETWEEN_Z4_STRICT` and `ABOVE_HIGHEST_Z4_STRICT`;
- separate E1/E2/E3 results;
- interaction table geometry x E rank;
- pooled H1+H2 only as descriptive support.

No subgroup discovered from these outcomes may be promoted from this retrospective study. Any promising subgroup must be frozen and confirmed independently.

Production authorization from this study: **NONE_RETROSPECTIVE_DIRECT_ESELL_RESEARCH**.
