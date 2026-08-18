# COMEX screening power note v1

Date: 2026-08-18
Status: design note only; no COMEX market-data download.

## Scope

This note is a screening bound, not a full power calculation for the future multivariate COMEX model. The calculation assumes a binary outcome, two equal-sized groups, two-sided alpha 0.05, 80% power, and independent observations. Actual model power will depend on clustering, feature distribution, calibration, P&L variance and temporal dependence.

For a representative baseline event probability of 70%, approximate sample size required **per group** is:

| Absolute difference | n per group |
|---:|---:|
| +3 percentage points | 3,554 |
| +4 pp | 1,977 |
| +5 pp | 1,251 |
| +6 pp | 859 |
| +7 pp | 623 |
| +10 pp | 294 |

At a 50% baseline the corresponding +5 pp requirement is approximately 1,565 per group; at an 80% baseline it is approximately 906 per group.

## Interpretation for screening package V2

- Counts below these orders of magnitude are not proof of absence of COMEX value.
- Rare entry-model/family cells, especially ACCEPTANCE_RETEST in pure DOZ and some MEMORY/OBJECTIVE splits, are population-limited and must be reported as underpowered/inconclusive where appropriate.
- The V2 deterministic sample floors are acquisition/screening targets, not claims of formal statistical sufficiency.
- FVG-only obtains a large tick sample from the complete-session panel; no all-event FVG local-tick download is required for first-stage screening.
- A final feature set still requires walk-forward/OOS evaluation and genuinely prospective validation after the final specification is frozen.

## Method

Normal-approximation two-proportion sample-size equation:

`n = [z_(1-alpha/2)*sqrt(2*pbar*(1-pbar)) + z_power*sqrt(p1*(1-p1)+p2*(1-p2))]^2 / (p2-p1)^2`

with equal group sizes.
