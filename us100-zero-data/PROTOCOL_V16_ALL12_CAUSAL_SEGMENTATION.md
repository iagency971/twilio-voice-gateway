# V16 — All-12 causal rerun and full segmentation

## Scope correction
The six-model V12/V13 candidate is NOT the final search universe. V16 restores all 12 original frozen models and audits every model, direction and time segment before any new selection.

## Frozen source universe
External model code: `s-k-28/nq-es-trader-5k-payout@d472d6b442764c2adafbba4bbeb96881c100e3e0`.
Models:
- ema_rev
- kalman_mom
- open_drive
- or_rev
- ou_lunch
- ou_rev
- pd_rev
- pm_mom
- sweep
- trend
- vwap_rev
- vwap_scalp

Data: same free USTEC M1 source/commit and 2021–2025 available window used by V5–V15. No paid data.

## Causal execution repair
Signals are generated with all original frozen model rules, quant features, quality filters, ATR stop widening and model priorities unchanged.

Conflict resolution is made causally deployable:
- signals on the same bar are contemporaneously knowable; select lowest numerical priority, then higher RR on ties;
- once a bar's signal is accepted, candidates on the following 1–2 bars are ignored (`cooldown_bars=3`);
- a future signal may never replace an already accepted signal.

Engine remains next-bar-open, single-position, same exits and risk-profile rules. Same exact-minute CFD spread rescore; STRESS uses 2× observed spread cost.

## Required diagnostics on the causal all-12 executed ledger
- overall
- model
- direction
- model × direction (all 24 branches where present)
- New York entry bucket: 09:30–10:30, 10:30–12:00, 12:00–13:30, 13:30–15:00, 15:00–16:00
- model × direction × session bucket
- entry hour
- weekday
- model × direction × weekday
- exit reason
- risk-width quartile
- DEV 2021–2023 / 2024 / Jan–Apr 2025 stability for model, direction, model×direction and session

Metrics: N, PRIMARY/STRESS mean R, sum R, PF, WR, max DD, losing streak, trade share, R share, scaled DD at reference 0.80%.

## Marginal diagnostics
For each model, model×direction, direction, session and weekday: recompute the remaining causal ledger after removing that segment and report changes in STRESS total R, PF, DD and fixed-0.80%-risk implied Step-1 pace.

## Selection discipline
V16 is diagnostic only. No segment discovered here is retroactively validated. Any new subset/filter formed from V16 must be treated as a new hypothesis and rerun as a true strategy with causal conflict resolution, then validated prospectively on FTMO Free Trial/forward.
