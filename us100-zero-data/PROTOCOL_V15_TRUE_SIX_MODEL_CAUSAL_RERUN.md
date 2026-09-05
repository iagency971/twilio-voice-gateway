# V15 — True six-model rerun and causal-conflict audit

## Why this audit exists
Two implementation-parity issues were identified before FTMO deployment:

1. The V12/V13 six-model candidate was selected by filtering the executed trade ledger of the full 12-model engine. Removed models may have affected conflict resolution and single-position occupancy, so that filtered ledger is not guaranteed to equal a true six-model rerun.
2. The frozen source `MultiModelGenerator._resolve_conflicts()` can replace an earlier signal with a later signal that occurs within the next 1–2 bars when the later signal has better priority/RR. That is non-causal for real-time execution.

V15 measures both effects without changing any model signal rule, parameter, feature, session or exit rule.

## Frozen six-model candidate
- ema_rev
- kalman_mom
- open_drive
- ou_rev
- pd_rev
- pm_mom

## Data and source
- Same free USTEC M1 source commit as V5–V14: `CodyOutcast/Academic-Paper-Data-Source@50052606c16d71850755e6dbdda02d43b4399c2b`.
- Same source years: 2021, 2022, 2023, 2024 and available Jan–Apr 2025.
- Same New York wall-clock conversion used by V5.
- External model code frozen at `s-k-28/nq-es-trader-5k-payout@d472d6b442764c2adafbba4bbeb96881c100e3e0`.
- Same exact-minute CFD spread rescore as V5.3; STRESS = 2× observed spread cost.

## Arms
### ARM A — TRUE6_ORIGINAL_RESOLVER
Instantiate only the six frozen models, but retain the original frozen conflict resolver exactly. Purpose: measure the error introduced by filtering the 12-model executed ledger instead of rerunning six models.

### ARM B — TRUE6_CAUSAL_RESOLVER
Instantiate only the same six models and replace only conflict resolution with a causal rule:
- signals on the same bar are all contemporaneously knowable; select the lowest-priority-number signal, then higher RR on ties;
- after accepting a bar's signal, ignore candidate signals on the following 1–2 bars (`cooldown_bars=3`), because they were not knowable when the earlier signal was accepted;
- never replace a previously accepted signal with a future signal.

All model rules, quality scoring, ATR stop widening, engine next-bar-open entry, single-position rule, BE/trailing/time exits and all other behavior remain frozen.

## Outputs
For each arm:
- total trades, trades/complete RTH session
- PRIMARY/STRESS mean R, total R, PF, WR, max DD, losing streak
- by-year PRIMARY/STRESS
- by-model and direction counts/P&L
- remove-best-10% descriptive stress
- fixed 0.80% implied Step-1 pace
- historical scaled max DD at 0.80%

Also report signal counts before/after conflict resolution and deltas between ARM A, ARM B, and the prior filtered six-model V14 ledger.

## Interpretation
This is a methodology/parity repair, not a new model optimization. If the causal true-six arm materially deteriorates, V12/V13 must not be used to justify FTMO deployment. If it remains strong, only ARM B is eligible for the MT5 Free Trial implementation.
