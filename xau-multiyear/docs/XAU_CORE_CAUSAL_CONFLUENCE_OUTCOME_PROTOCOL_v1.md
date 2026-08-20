# XAU CORE CAUSAL CONFLUENCE OUTCOME PROTOCOL v1

Date frozen: 2026-08-20  
Decision authority: Pro outcome-blind authorization review  
Status: **`CAUSAL_CORE_OUTCOME_V1_AUTHORIZED`**  
Decision: **`A — AUTHORIZE_PNL_OPEN`**

## 1. Scope and outcome blindness

This protocol authorizes one canonical economic opening of the frozen causal core:

`DOZ + OBJECTIVE_LIQUIDITY -> CAUSAL_CLEAN_REJECTION -> STRUCTURAL`

It does **not** authorize live trading, a prop-firm challenge, M5, COMEX continuation, parameter search, subgroup rescue, or new market-data purchases.

No TP, SL, exit, P&L, PF, win rate, drawdown, MFE or MAE was inspected while this protocol was written.

## 2. Immutable pre-outcome binding

- repository: `iagency971/twilio-voice-gateway`
- branch: `agent/xau-core-evidence-audit-v1`
- pre-outcome workflow: `32360173450`
- pre-outcome source commit: `106a0252e8292dd2dd690a7e336d9f493420ccc1`
- freeze artifact commit: `b1882c5873c638cd1f5fb92ffcf7d42fe87f5e86`
- freeze manifest SHA-256: `7a46a6847e8b574afa3576714349dbeaa8ec4d7ae2b1a39f4356a03e68fa4197`
- event manifest SHA-256: `39ed2f7eac7465d46344bef85d64d3b897f0b56af66448e537fba1bfff315aeb`
- frozen events: `498`
- active years: `15/15`
- side relation: `496 SAME_SIDE`, `2 OPPOSITE_SIDE`

The event population may not be recomputed, reselected, filtered, deduplicated differently, or repaired after outcome opening.

Before reading any post-entry bar, the executor must verify the freeze manifest, event manifest, all 15 annual input hashes, event row count, event IDs, causal counters, shuffle identity and exact population identity. Any mismatch returns:

`CAUSAL_CORE_OUTCOME_V1_INVALID_BINDING_ABORT`

and stops before outcomes.

## 3. Market-data and quote model

Use the same already-used public Dukascopy XAUUSD M1 BID/ASK monthly files and the exact annual input hashes stored in the frozen manifest.

M1 timestamp semantics remain:

`BAR_START_UTC`

The source mid OHLC is the stored arithmetic mean of matching source BID and ASK OHLC fields.

The actual source BID/ASK fields serve to:

1. prove quote availability at the frozen entry timestamp;
2. preserve the pre-outcome zone-width and provenance construction;
3. verify the frozen entry quote fields.

Economic execution uses the historical standardized fixed-spread overlay around the frozen source mid OHLC. The source spread is **not** added a second time.

### Frozen scenarios

| Scenario | Role | Total spread USD/oz | Round-turn commission USD per 100 oz lot |
|---|---|---:|---:|
| `S10_C6` | sensitivity | 0.10 | 6.00 |
| `S11_C6_PRIMARY` | primary | 0.11 | 6.00 |
| `S12_C6` | sensitivity | 0.12 | 6.00 |
| `S18_C9_STRESS` | stress | 0.18 | 9.00 |

For every source mid OHLC value:

- scenario BID = mid − spread/2;
- scenario ASK = mid + spread/2.

No additional slippage is added in V1. Spread is already embedded once in the executable quote path.

## 4. Entry

The frozen `entry_time` is authoritative.

- `SUPPORT` anchor -> `LONG`;
- `RESISTANCE` anchor -> `SHORT`;
- LONG entry = scenario ASK open at the frozen `entry_time`;
- SHORT entry = scenario BID open at the frozen `entry_time`.

The entry minute was already frozen as the first valid opening BID/ASK quote among confirmation +1, +2 or +3 minutes. The executor may not search again.

If the source opening BID/ASK or source mid open at the frozen timestamp is missing, non-finite, inconsistent, or does not match the frozen entry row, the run hard-fails. The event may not be delayed or dropped.

## 5. Structural stop and 1R

Compute `sigma60` at the frozen entry timestamp with the canonical `rzr.features.robust_sigma60` function. The implementation is shifted by one M1, so the value uses only pre-entry information.

For each scenario:

`buffer = max(2 × scenario_spread, 0.10 × sigma60_at_entry)`

Use only the frozen execution anchor geometry:

- LONG stop = `anchor_lower − buffer`;
- SHORT stop = `anchor_upper + buffer`.

The pair envelope is not used for the stop. No alternative stop may be compared.

Risk:

- LONG `1R_price = entry_price − stop_price`;
- SHORT `1R_price = stop_price − entry_price`.

Risk must be finite and strictly positive for all 498 events in all four scenarios. Otherwise the run returns the integrity-abort status; it may not remove the event.

## 6. Targets

The complete frozen RR surface is:

`0.5 / 1.0 / 1.5 / 2.0 / 2.5 / 3.0`

- LONG target = `entry + RR × risk`;
- SHORT target = `entry − RR × risk`.

The same 498 events must be used for every scenario and every RR. No RR may be selected as the primary winner after opening.

## 7. Exact 120-minute horizon

The horizon is exactly **120 elapsed wall-clock minutes**.

Monitor executable bars whose start timestamps satisfy:

`entry_time <= bar_start < entry_time + 120 minutes`

This is exactly 120 start-stamped M1 intervals when quotes are continuous.

At the deadline, close at the first valid executable scenario quote at or after `entry_time + 120 minutes`.

When the exact deadline quote is missing, wait only for the first valid source opening BID/ASK quote at or after the deadline:

- an adverse opening gap through the stop exits at the worse executable open;
- an opening gap through the target records TP at the target, without favorable price improvement;
- otherwise record `TIME` at the executable scenario open.

This definition prevents a row-count horizon from silently spanning market gaps and prevents an inclusive `+120` start-stamped bar from extending the intended horizon.

## 8. Intrabar and gap conventions

Market-at-open entries may use the full entry M1 bar.

For LONG, evaluate the scenario BID path.  
For SHORT, evaluate the scenario ASK path.

At every bar:

1. evaluate an adverse opening gap;
2. evaluate stop and target range touches;
3. when stop and target are both touched in the same M1, assign `SL`;
4. otherwise assign the single touched boundary.

Gap rules:

- LONG gap below stop -> SL at scenario BID open;
- SHORT gap above stop -> SL at scenario ASK open;
- favorable gap through target -> TP at target, without price improvement.

## 9. Commission and net R

The fixed spread is already embedded in the scenario BID/ASK quotes.

Contract size:

`100 oz per standard lot`

Round-turn commission is subtracted exactly once for TP, SL and TIME outcomes:

`commission_R = commission_round_turn_USD / (100 × risk_price_USD_per_oz)`

Gross R:

- LONG: `(exit_price − entry_price) / risk_price`;
- SHORT: `(entry_price − exit_price) / risk_price`.

Net R:

`net_R = gross_R − commission_R`

No additional fee or slippage is permitted in V1.

## 10. Primary endpoint

Primary endpoint:

**`CAUSAL_CORE_RR_SURFACE_MEAN_NET_R`**

Primary scenario:

`S11_C6_PRIMARY`

For each frozen event, calculate the arithmetic mean of its six net-R outcomes. Then calculate the arithmetic mean of those 498 event-level surface scores.

This gives equal weight to every RR and every event. No best-RR selection is allowed.

Trading date is derived from entry time with the canonical `America/New_York` 17:00 boundary.

### Date-cluster bootstrap

- draws: `20,000`;
- seed: `20260821`;
- RNG: NumPy `default_rng` / PCG64;
- cluster: unique 17:00-New-York trading date;
- resampling: sample dates with replacement and carry all events belonging to each sampled date with that date's multiplicity;
- CI: percentile 2.5% / 97.5%.

### Secondary moving-block bootstrap

Diagnostic only:

- 3-month circular blocks;
- 20,000 draws;
- seed `20260822`;
- months 2011-01 through 2025-12.

## 11. Frozen economic gates

All gates A–F must pass.

### Gate A — Integrity

All required:

- exact freeze SHA;
- exact event-manifest SHA;
- N = 498;
- exact event rows and event IDs;
- exact 15 annual input hashes;
- identical events across all four scenarios and six RR;
- every frozen causal counter remains zero;
- shuffle identity remains PASS;
- no population mutation.

### Gate B — Primary / broad RR

Under `S11_C6_PRIMARY`:

- RR-surface mean net R >= `+0.10R`;
- RR-surface date-cluster bootstrap 95% lower bound > `0`;
- at least 4/6 RR cells each have:
  - mean net R >= `+0.10R`;
  - PF >= `1.25`;
  - date-cluster bootstrap 95% lower bound > `0`.

### Gate C — Stress

Under `S18_C9_STRESS`:

- all six RR cells have mean net R > `0`;
- at least 4/6 RR cells have PF >= `1.20`;
- stress RR-surface mean net R > `0`.

### Gate D — Temporal robustness

Evaluate each RR independently.

A given RR passes only when:

- all 15 primary leave-one-year-out means are > `0`;
- at least 10/15 primary annual sums are > `0`;
- at least 8/15 stress annual sums are > `0`;
- no primary year exceeds 35% of total absolute annual contribution;
- no stress year exceeds 35% of total absolute annual contribution.

RR1.5 must pass and at least 4/6 RR must pass.

Annual contribution share:

`abs(year_sum_R) / sum(abs(all_year_sum_R))`

### Gate E — Concentration

At RR1.5, independently for primary and stress:

- remove the best `ceil(N × 5%)` trades;
- mean net R after removal must remain > `0`;
- the best 5% may represent at most 50% of total positive R.

Tie-break when net R is equal:

1. net R descending;
2. entry time ascending;
3. event ID ascending.

### Gate F — Single-position portfolio

At RR1.5:

1. sort by entry time, confluence time, event ID;
2. select the earliest event;
3. ignore every later event whose entry time is <= the active exit time;
4. resume only after exit.

Required:

- primary mean net R > `0`;
- primary PF > `1.10`;
- stress mean net R >= `0`;
- unresolved sequencing ambiguity = `false`.

Selected trade count is mandatory diagnostic data but has no new post-outcome threshold.

## 12. Mandatory diagnostics

For every scenario and RR:

- N, mean R, sum R, PF;
- TP%, SL%, TIME%;
- same-bar ambiguity%;
- date-cluster 95% CI.

For RR1.5 primary and stress:

- max drawdown in R;
- longest losing streak;
- best 1%, 5% and 10% contribution;
- result after removing best 5%;
- single-position selected and skipped trade counts.

No drawdown or losing-streak threshold may be invented after opening.

## 13. Absolute post-outcome prohibitions

A failing result may not be rescued by selecting:

- LONG or SHORT;
- SAME_SIDE;
- a session, NY_AM, London or a session transition;
- M15, M30 or H1;
- a zone-age bucket;
- `DOZ_BODY`, `DOZ_LAST` or `DOZ_BASE`;
- an Objective Liquidity subtype;
- a single RR;
- a year;
- any combination of diagnostic dimensions;
- a different stop, cost, horizon, entry, target or ambiguity rule.

Subgroup results are `HYPOTHESIS_GENERATION` only and never alter the primary verdict.

## 14. Terminal statuses

Authorization:

`CAUSAL_CORE_OUTCOME_V1_AUTHORIZED`

Binding/integrity failure before outcomes:

`CAUSAL_CORE_OUTCOME_V1_INVALID_BINDING_ABORT`

All gates PASS:

`CAUSAL_CORE_OUTCOME_V1_PASS_FOR_EXTERNAL_REPLICATION`

At least one economic gate FAIL:

`CAUSAL_CORE_OUTCOME_V1_NO_GO`

A PASS is not live-ready. It authorizes only external broker/feed replication and prospective validation.

A FAIL closes this core as an economic candidate on 2011–2025. It cannot be repaired economically on the same sample.

## 15. One canonical opening

One canonical outcome opening is authorized.

An infrastructure retry is permitted only when the failed attempt stopped before reading any outcome bar and all hashes/code remain identical.

After outcomes have been read, only exact deterministic reproduction is allowed. No population or rule change is permitted.

Machine-readable protocol:

`xau-multiyear/docs/XAU_CORE_CAUSAL_CONFLUENCE_OUTCOME_PROTOCOL_v1.json`

Machine-readable protocol SHA-256:

`112f25ed646ea9695e48268a08e87f74bea3c841b5f788f32a98371b74a86786`
