# COMEX supplemental sampling specification v1

Date: 2026-08-18
Status: frozen before any COMEX market-data download.

## Purpose

Avoid buying local tick windows for every XAUUSD event when a frozen full-session COMEX panel already contains the required tape. Full-session data are reused for both (a) COMEX-native zone research and (b) existing-XAU-POI incremental-value research.

This is a sampling rule, not a strategy filter. Every XAUUSD event remains in the canonical event universe and the complete GC M1 layer remains available for every event.

## Family signatures

The event's exact family signature is the ordered subset of:

- DISPLACEMENT_ORIGIN
- OBJECTIVE_LIQUIDITY
- MEMORY
- FVG

Do not collapse all confluences into one class for sampling. In particular DOZ+OBJECTIVE, DOZ+FVG, OBJECTIVE+FVG, MEMORY+FVG and higher-order stacks remain distinct.

## Frozen full-session tiers

Session candidates were ranked before COMEX observation within year x quarter x XAU volatility tercile using the frozen seed `COMEX_SESSION_PANEL_V1_SEED_971`.

Candidate tiers retain rank <= 2, 3 or 4 per stratum. The exact economic frontier will determine which tier is purchased; the rank itself cannot be changed after COMEX is observed.

## Supplemental local-window rule

Only events whose research trading date is not already covered by the purchased session tier are eligible for supplemental local acquisition.

Selection is deterministic using SHA-256 of `COMEX_SUPPLEMENT_V1_SEED_971|event_uid` after applying the following pre-COMEX targets.

### Pure non-FVG families

For each of DISPLACEMENT_ORIGIN only, OBJECTIVE_LIQUIDITY only and MEMORY only, target total detailed-flow coverage (session-covered plus supplemental):

- DEV 2011-2018: 2,000 events per family where population permits;
- VALIDATION 2019-2022: 1,000 events per family where population permits;
- COMEX_FEATURE_HOLDOUT 2023-2025: 1,000 events per family where population permits.

These are precision-oriented initial targets, not claims that each family/model has independent power for every rare behavior.

### FVG-only

No supplemental FVG-only tick windows are purchased in v1 when the full-session panel already supplies tens of thousands of FVG-only events. All FVG-only events remain available in continuous M1 context.

### Abundant two-family FVG confluences

For each of OBJECTIVE_LIQUIDITY+FVG, MEMORY+FVG and DISPLACEMENT_ORIGIN+FVG, target total detailed-flow coverage:

- DEV: 1,500 events per signature;
- VALIDATION: 750 events per signature;
- COMEX_FEATURE_HOLDOUT: 750 events per signature.

### Rare confluences

All other multi-family signatures are retained in detailed-flow coverage where technically available, including all DOZ+OBJECTIVE events. Session-covered observations are reused; every remaining observation outside the panel is selected for a supplemental local window.

The rule is intentionally independent of COMEX values and XAU trade P&L. No family is removed because of its prior profitability.

## Local window

Supplemental detailed-flow windows use the Pro-audited uniform envelope contact -30 minutes through contact +16 minutes. Acquisition boundaries are snapped outward to 10-minute boundaries before Databento metadata quoting because Databento warns that `get_cost` may over-report non-10-minute ranges. The scientific feature window remains the exact -30/+16 subset inside the downloaded envelope.

Adjacent acquisition envelopes may be merged with a fixed 30-minute maximum gap for operational efficiency. Added gap data are not automatically admissible as predictors; feature cutoffs remain causal and model-specific.

## Sequential extension rule

After the initial v1 sample is analyzed, additional detailed-flow observations may be acquired only under a predeclared precision trigger, not because an observed effect is favorable or unfavorable. Examples include a prespecified confidence-interval width or inadequate effective sample size after clustering.

Any extension must preserve the existing deterministic ranks and simply raise a frozen sampling tier/target; it cannot select individual observations based on COMEX outcome.

## Limitations

Rare entry models such as ACCEPTANCE_RETEST can remain underpowered inside individual family signatures even if every historical event is acquired. Data acquisition cannot manufacture events that do not exist. Such effects must be reported as underpowered or estimated in a hierarchical/pooling framework with family interactions, not promoted from tiny cells.
