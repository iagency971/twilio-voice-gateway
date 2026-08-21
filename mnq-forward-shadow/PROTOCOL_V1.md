# MNQ 12-Model Forward Shadow V1

Status: `PRE_FORWARD_FROZEN`
Start of genuinely future window: **2026-08-21**.

## Purpose
Accumulate a prospective, no-retuning shadow ledger while separate strategy research continues. This shadow feed is for fast operational monitoring only; it is NOT validation-grade CME evidence.

## Frozen model
External repository: `s-k-28/nq-es-trader-5k-payout`
Pinned commit: `d472d6b442764c2adafbba4bbeb96881c100e3e0` (2026-05-31).
No model removal, direction filter, stop/target change, threshold change, time-window change, or model weighting change is allowed during the forward.

## Shadow market-data source
- Yahoo Finance `NQ=F`, 1-minute intraday.
- Use only fully completed RTH sessions, America/New_York 09:30-15:59.
- This source previously failed our strict futures-parity gate by a narrow margin and therefore all results are labeled `SHADOW_PROXY_ONLY`.
- No paid Databento request is allowed from this workflow.

## Execution
Run the pinned external engine unchanged.
After the engine produces completed trades, rescore every trade for additional friction:
- PRIMARY: subtract 1.0 NQ point per round trip.
- STRESS: subtract 2.0 NQ points per round trip.
Cost in R = `extra_points / (risk_ticks * 0.25)`.

## Ledger
For each completed trading day >=2026-08-21:
- persist raw external trades;
- persist PRIMARY/STRESS R;
- append without duplicates keyed by entry_time + model + direction;
- never rewrite an already frozen day unless a pure data-correction audit is separately documented.

## Checkpoints
### Early checkpoint — descriptive only
At >=40 completed trades report stats, but classification remains `FORWARD_INSUFFICIENT_FOR_LIVE` regardless of result.

### Research checkpoint
At >=100 completed trades, compute:
- PRIMARY expectancy, PF, win rate, max DD, losing streak;
- STRESS expectancy and PF;
- weekly contribution;
- first-half vs second-half contribution;
- remove-best-10% expectancy;
- model and direction diagnostics as descriptive evidence only.

Predeclared research gates at >=100 trades:
1. PRIMARY expectancy >= +0.10R/trade.
2. PRIMARY PF >= 1.25.
3. PRIMARY max DD <= 10R.
4. At least 60% of completed calendar weeks positive.
5. Remove best 10%: remaining expectancy >= 0.
6. STRESS expectancy > 0.
7. STRESS PF >= 1.10.

Even if all proxy gates pass, status is only `PROXY_FORWARD_PASS_REQUIRES_CME_REMEASUREMENT`; never `LIVE_READY`.

## Official-CME checkpoint
A separate, explicitly authorized Databento workflow may remeasure the same frozen dates on official CME data. Proxy outcomes must never be used to modify the model before that remeasurement.

## Cost policy
This shadow workflow must spend **$0** on market data. Any official CME remeasurement requires a separate cost estimate and explicit authorization before download.
