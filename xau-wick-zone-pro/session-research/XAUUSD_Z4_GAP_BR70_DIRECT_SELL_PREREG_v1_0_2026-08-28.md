# XAUUSD standalone Z4-gap BR70 SELL — preregistration v1.0

Date: 2026-08-28
Branch: `agent/xau-wick-zone-pro-dev`
Status: **FROZEN BEFORE STANDALONE-STRATEGY OUTCOMES**

## Scientific status

This hypothesis was formulated **after** the matched non-E control showed that direct E contact was not incrementally supported over comparable bearish rejections in the same Z4 gap geometry.

Therefore any H1/H2 results from 2024-08 through 2026-07 are **retrospective exploratory only** and cannot validate or promote the strategy. They are used to determine whether the structurally natural standalone formulation is coherent enough to freeze prospectively.

No E1/E2/E3 data, score, rank, family or contact is used for signal eligibility.

## Frozen setup

For each selected session independently:

1. use the exact causal C5 Z4 geometry already frozen in the project;
2. consider adjacent Z4 intervals ordered by price;
3. a trigger-bar high must lie strictly in the open gap between one lower Z4 and the adjacent upper Z4:
   `lower_zhi < trigger_high < upper_zlo`;
4. bearish trigger = legacy BR70:
   `close < open` and `(high-close)/(high-low) >= 0.70`;
5. no prerequisite Z4 breakout and no E requirement/exclusion;
6. target must not already have been touched on the trigger bar;
7. entry = next M1 open within the same session;
8. entry must remain strictly inside the same frozen gap:
   `lower_zhi < entry < upper_zlo`.

## Target and invalidation

Frozen at trigger:

- TP = first touch of adjacent lower Z4 upper boundary `lower_zhi`;
- structural invalidation = confirmed M1 close strictly above adjacent upper Z4 lower boundary `upper_zlo`;
- wick into/above the upper Z4 is allowed until an M1 close is strictly above `upper_zlo`;
- same-M1 TP touch and close-invalidation = `AMBIGUOUS`;
- scan ends at end of same session; unresolved = `NEITHER`.

Nominal structural RR = `(entry - lower_zhi) / (upper_zlo - entry)`.

This rule has no fitted distance parameter.

## Gap identity / duplicate control

A structural gap may fire at most once per session.

Two gap observations are considered the same structural gap when both their lower-Z4 intervals and upper-Z4 intervals respectively overlap, OR each pair of centers remains within `0.25 * max(v_old,v_new)` using causal local M1 volatility.

The gap is consumed on the first qualifying BR70 trigger, even if no executable next-open trade results, mirroring the one-fire-per-structural-identity discipline used in prior E research.

## Windows

- H1: 2024-08-01 to 2025-08-01 UTC;
- H2: 2025-08-01 to 2026-08-01 UTC.

Sessions in America/New_York:

- US 08:00–17:00;
- Asia broad 18:00–03:00;
- Asia Core 21:00–03:00;
- Europe 03:00–08:00.

## Prespecified outputs

For every session and H1/H2:

- qualifying gap BR70 triggers;
- executed trades;
- TP / invalidation / neither / ambiguous;
- terminal TP rate;
- structural expectancy in R before costs;
- PF_R;
- median/p10/p90 nominal RR;
- median stop distance and target distance in local-volatility units;
- signals per session distribution;
- one-position-at-a-time diagnostic, taking the next eligible executed trade only after the selected trade resolves.

Pooled results may be shown as descriptive support only.

## Retrospective coherence criterion

Because this is post-control exploratory research, there is no production gate.

The rule is considered worth freezing prospectively only if:

- expectancy is positive in both H1 and H2 in at least 3 of 4 sessions;
- pooled H1 and H2 expectancy are both positive;
- one-position-at-a-time expectancy does not reverse materially negative in either pooled half.

Even if this criterion passes, status remains:
`EXPLORATORY_Z4_GAP_BR70_RULE_WORTH_PROSPECTIVE_CONFIRMATION`.

Production authorization: **NONE_POST_CONTROL_EXPLORATORY**.
