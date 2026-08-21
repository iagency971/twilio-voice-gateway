# MNQ 12-Model Post-Freeze Proxy Screen V1

Status before outcomes: `PREOUTCOME_FROZEN_PROXY_SCREEN`
Branch: `agent/mnq-12model-postfreeze-proxy-v1`

## Purpose
Zero-cost screen of the externally published 12-model MNQ/NQ ensemble after its effective code freeze. This is NOT a futures validation because the Jun-Jul source is a near-parity proxy with one known severe source anomaly (2026-06-16). A strong PASS only justifies acquiring/retrieving true CME MNQ/NQ data for final validation.

## External system freeze
Repository: `s-k-28/nq-es-trader-5k-payout`.
Pinned code commit: `d472d6b442764c2adafbba4bbeb96881c100e3e0` (2026-05-31).
Rationale: later public commits are license/README only; this commit is after the May model/risk tuning cycle. The published historical/2026 results are NOT treated as OOS because 2026 data were already used during optimization before this freeze.

The external code is run unchanged through its public `run_multi.py`/`MultiModelGenerator`/`BacktestEngineV2` path. No model, parameter, conflict rule, daily cap, BE rule, ATR rule, or stop/target rule is modified.

## Proxy data
Source: `getdata-finance/nq-1m-ohlcv-stocks-historical-data/main/NQ_1m.csv`.
Required SHA-256: `232fbc18375e6475dbe3b99e6e1504da69c58a962aa7a358b14f4e2b61cf229d`.
- Source timestamps are interpreted as UTC and converted to America/New_York wall-clock before feeding the external code.
- Full Feb-Jul source is retained for warmup; the external repository's 2022-2025 file may additionally provide its normal history warmup.
- Evaluation window ONLY: 2026-06-01 through 2026-07-31 inclusive, after the code freeze.
- Known 2026-06-16 proxy anomaly is NOT removed or repaired.

Independent source-parity audit before this screen found Jun1-Jul27: 39 overlap days, median entry diff 0.25pt, 97.4% entries within 1pt, 92.3% exits within 1pt, 97.4% exits within 2pt, direction agreement 38/39; one catastrophic 2026-06-16 mismatch. Therefore proxy can reject a weak candidate but cannot prove a futures edge.

## Friction rescoring
The external engine's `total_r` does not include full futures commissions and only applies a small adverse exit slip. We keep the external trade path unchanged and subtract an additional round-trip point cost from every completed trade:
- PRIMARY: extra 1.0 NQ index point / trade.
- STRESS: extra 2.0 NQ index points / trade.
For each trade, extra cost in R = extra_points / (risk_ticks * 0.25).
This deliberately charges targets too.

## Predeclared proxy gates
PRIMARY all required:
1. >= 100 completed trades in Jun-Jul.
2. >= 2.0 trades per observed trading day.
3. Mean net expectancy >= +0.10R/trade after PRIMARY rescore.
4. Profit factor >= 1.25.
5. June aggregate R > 0 AND July aggregate R > 0.
6. Closed-trade max drawdown <= 10R.
7. Remove best 5% of trades: remaining mean net expectancy >= 0.

STRESS all required:
8. Mean net expectancy > 0.
9. Profit factor >= 1.10.

Terminal status:
- All pass -> `PROXY_PASS_JUSTIFIES_TRUE_CME_VALIDATION`.
- Otherwise -> `PROXY_NO_GO`; do not buy data to validate this exact ensemble.

Diagnostics only: per-model N/expectancy/PF, long/short, month, exit reason, losing streak. No model removal or filter rescue based on Jun-Jul outcomes.

A proxy PASS is explicitly NOT permission to trade or simulate a prop challenge as validated. Stage 2 requires true CME/broker minute data after the May-31 freeze.