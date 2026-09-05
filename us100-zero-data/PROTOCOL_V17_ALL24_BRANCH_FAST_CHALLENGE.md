# V17 — All-24 model×direction fast-challenge search

## Objective
Search the full 12-model universe at model×direction granularity for a causally deployable US100 FTMO candidate that minimizes Step-1 time subject to FTMO drawdown buffers. No paid market data.

## Atomic universe
All model×direction branches actually produced by the 12 frozen models are eligible. No preselection to the prior six-model candidate.

## No weekday/session optimization in V17
V16/V16b showed no broad weekday/session filter with stable evidence across DEV/2024/2025. Therefore V17 does NOT tune weekdays or time buckets. Those remain diagnostic only.

## Data / source
Same free USTEC M1 source and frozen external strategy commit as V16.

## Causality
Use V16 causal conflict rule: same-bar priority/RR resolution, then 3-bar causal cooldown; future signals never replace past signals.

## Selection window and status of later data
Ranking/search is computed from 2021–2023 DEV only. 2024 and available Jan–Apr 2025 are reported afterward as descriptive stability checks because their outcomes have already been viewed in prior diagnostics; they are not claimed as fresh OOS. FTMO Free Trial forward remains the true prospective validation.

## Search stages
1. Generate all frozen model signals/features once.
2. Use the existing V16 causal DEV executed ledger for a fast beam-screen of branch subsets.
3. Keep a diverse shortlist across subset sizes and implied FTMO speed.
4. Re-run each shortlisted subset as a TRUE strategy: filter allowed model×direction branches BEFORE causal conflict resolution, then quality filter, then next-bar-open single-position engine.
5. Use a parity-preserving fast engine index lookup; verify its trade ledger exactly matches the frozen engine on one reference arm before candidate ranking.

## Risk grid
Fixed risk/trade: 0.25%, 0.30%, 0.35%, 0.40%, 0.45%, 0.50%, 0.55%, 0.60%, 0.65%, 0.70%, 0.75%, 0.80%, 0.85%, 0.90%, 0.95%, 1.00%.

## DEV admissibility gates
For each true-rerun subset/risk pair:
- at least 300 executed DEV trades
- positive STRESS expectancy
- STRESS PF >= 1.25
- each of 2021, 2022, 2023 STRESS total R > 0
- scaled STRESS max closed-trade DD < 8.5% of account
- scaled worst intraday closed-P&L day < 4.0% of account
- no historical -10% total-loss breach on the DEV chronological path
- no historical -5% daily-loss breach on DEV chronological closed-P&L path

No minimum trades/day. Remove-best-10% is reported, not used as a hard selection gate.

## Ranking
Primary: lowest implied Step-1 trading sessions under STRESS at the fastest admissible risk.
Tie-breakers: higher STRESS PF, lower scaled DD, higher STRESS R/session, fewer branches.

## Post-selection descriptive checks
Freeze the selected branch set and risk before reporting 2024/2025 details. Report 2024, 2025, full-period metrics and 5/10/20-session block-bootstrap FTMO simulation with -1R and -1.25R floating probes. These historical checks are descriptive; Free Trial forward is mandatory before paid Challenge use.
