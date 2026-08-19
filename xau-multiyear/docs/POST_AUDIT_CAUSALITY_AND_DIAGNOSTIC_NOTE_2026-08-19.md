# POST-AUDIT NOTE — causality sensitivity and diagnostic findings

Date: 2026-08-19
Branch: `agent/xau-core-evidence-audit-v1`

## Status

This note is **post-audit diagnostic interpretation**. It does not replace the frozen Pro authority or the machine verdict `CORE_INTERNAL_AUDIT_PASS_FOR_EXTERNAL_REPLICATION` produced by `XAU_CORE_EVIDENCE_AUDIT_V1`.

It records one causality defect revealed by the newly frozen age diagnostics and a sensitivity analysis that removes that single event. No subgroup is promoted to a trading filter here.

## 1. Audit result

The 2011–2025 canonical 304-event core passed aggregate parity and all frozen Pro gates A–E. All six RR values 0.5/1.0/1.5/2.0/2.5/3.0 passed the temporal gate. External replication is authorized by the frozen machine verdict; live readiness, M5, COMEX continuation and new market-data spend remain unauthorized.

RR1.5 descriptive reference:
- primary S11_C6: N=304, mean +0.279918R/trade, PF 1.647019, sum +85.095123R;
- stress S18_C9: N=304, mean +0.189605R/trade, PF 1.408390, sum +57.639985R;
- date-cluster bootstrap primary mean 95% CI: [+0.147881, +0.410500];
- date-cluster bootstrap stress mean 95% CI: [+0.057564, +0.318615].

## 2. One causality defect exposed by the age diagnostic

Exactly one of the 304 canonical events has a deterministic DOZ diagnostic anchor whose `known_time` is later than both the representative stack contact and the trade entry:

- source year: 2022;
- event_id: `5dcbc6fbe6dcc88b61360af7`;
- stack_id: `STACK_00121712`;
- contact: `2022-06-22T07:13:00Z`;
- entry: `2022-06-22T07:14:00Z`;
- DOZ anchor: `DOZ_LAST_00003081`;
- DOZ known_time: `2022-06-22T07:15:00Z`;
- DOZ tradable age at contact: -2 minutes;
- DOZ tradable age at entry: -1 minute;
- objective anchor was already known at `07:00Z`.

Cause: the canonical stacker merges constituent contacts within the frozen two-minute contact tolerance. Here an objective-liquidity contact at 07:13 and a DOZ contact/availability at 07:15 became one stack, allowing the canonical `DOZ_OBJECTIVE_ONLY` label to include a DOZ that was not yet tradable at the 07:14 entry.

This is a real causal-integrity defect in that single canonical event, not merely a display issue.

## 3. Outcome-blind causal exclusion sensitivity

A post-audit sensitivity removes the single event above from every scenario and RR without changing any other rule. This creates a 303-event causal-clean sensitivity panel.

At RR1.5:
- primary: N=303, mean +0.275984R/trade, PF 1.635826, sum +83.623050R, date-cluster bootstrap mean 95% CI [+0.142583, +0.406929];
- stress: N=303, mean +0.185417R/trade, PF 1.398054, sum +56.181205R, date-cluster bootstrap mean 95% CI [+0.054090, +0.314749].

Re-evaluating the same frozen gate logic on this 303-event sensitivity leaves all major gates passing:
- broad RR/statistical: PASS (6/6 primary cells and 6/6 stress PF cells);
- temporal: PASS for all six RR values;
- concentration: PASS;
- single-position portfolio replay: PASS.

Therefore the single causality defect must be repaired before external replication, but the historical edge is not an artefact of that event.

## 4. Frozen diagnostic findings at RR1.5 (hypothesis generation only)

### Direction
Primary:
- LONG: N=154, +0.364854R/trade, PF 1.882498, 13/15 positive years;
- SHORT: N=150, +0.192718R/trade, PF 1.426052, 9/15 positive years.

Stress:
- LONG: +0.261411R/trade, PF 1.574643;
- SHORT: +0.115884R/trade, PF 1.244539.

Both directions remain positive across all 12 primary/stress × six-RR diagnostic cells; LONG is consistently stronger.

### Entry/contact session
RR1.5 primary:
- NY_AM: N=116, +0.343893R, PF 1.760360;
- ASIA_CME: N=80, +0.314106R, PF 1.829063;
- NY_PM: N=39, +0.275794R, PF 1.651015;
- LONDON: N=61, +0.181430R, PF 1.377239;
- TRANSITION: N=8, -0.218514R, PF 0.394264.

RR1.5 stress:
- NY_AM +0.262989R / PF 1.551560;
- NY_PM +0.258857R / PF 1.602137;
- ASIA_CME +0.213024R / PF 1.516565;
- LONDON +0.036028R / PF 1.066397;
- TRANSITION -0.275224R / PF 0.259376.

Across the 12 primary/stress × six-RR cells, NY_AM and ASIA_CME are positive in 12/12, NY_PM 10/12, LONDON 11/12, TRANSITION 0/12. These are diagnostics only; no session filter is authorized from this sample.

### DOZ tradable age
RR1.5 primary / stress respectively:
- <1h: N=7, -0.123500R / -0.142629R;
- 1–4h: N=14, +0.220681R / +0.182294R;
- 4–12h: N=60, +0.134480R / -0.027443R;
- 12–24h: N=33, +0.398343R / +0.298880R;
- 1–3d: N=73, +0.291548R / +0.238085R;
- 3–7d: N=37, +0.353175R / +0.262910R;
- 7–30d: N=42, +0.494544R / +0.417288R;
- >=30d: N=38, +0.171965R / +0.085154R.

The continuous Spearman relation age vs net-R is weak: +0.0759 primary and +0.0831 stress. Hence there is no evidence of a simple monotonic 'fresher is better' rule. The <1h bucket is tiny and includes the one causality-invalid event before repair; bucket findings are hypothesis generation only.

### DOZ timeframe and variant
RR1.5 primary:
- 30min: N=99, +0.360586R, PF 1.836206;
- 15min: N=130, +0.249610R, PF 1.557672;
- 1h: N=75, +0.225970R, PF 1.553105.

All three timeframes are positive in all 12 primary/stress × six-RR diagnostic cells.

Variant RR1.5 primary / stress:
- DOZ_BODY: N=205, +0.374338R / +0.276638R;
- DOZ_LAST: N=64, +0.141599R / +0.079276R;
- DOZ_BASE: N=35, -0.020185R / -0.118414R.

DOZ_BODY is positive in 12/12 primary/stress × RR cells; DOZ_LAST also 12/12 but weaker; DOZ_BASE only 3/12. This is not authorization to discard DOZ_BASE post hoc.

### Selected session A→B patterns with material N
DOZ activation -> entry, RR1.5 primary / stress:
- LONDON -> NY_AM: N=40, +0.429645R / +0.259868R;
- ASIA_CME -> ASIA_CME: N=21, +0.633766R / +0.598043R;
- ASIA_CME -> NY_AM: N=25, +0.258299R / +0.211500R;
- NY_AM -> NY_PM: N=21, +0.270691R / +0.255913R;
- ASIA_CME -> LONDON: N=21, -0.097818R / -0.350361R;
- NY_AM -> ASIA_CME: N=26, +0.210100R primary but -0.007997R stress.

DOZ origin -> entry also shows LONDON -> NY_AM (N=41, +0.481513R primary / +0.438937R stress) and ASIA_CME -> ASIA_CME (N=17, +0.914457R / +0.886887R) as strong historical patterns, while ASIA_CME -> LONDON (N=16) and NY_PM -> ASIA_CME (N=11) are negative under both primary and stress costs.

Again, these are not validated filters. They are candidate mechanisms for a separately preregistered follow-up only.

## 5. Interpretation

The new audit changes the research position materially:

1. the historical core survives strong internal robustness checks and merits external replication;
2. it is not live-ready;
3. the edge is heterogeneous: LONG > SHORT historically; NY_AM/ASIA_CME > TRANSITION; DOZ_BODY > DOZ_BASE; some A→B session paths differ sharply;
4. simple zone freshness is not supported — some multi-day zones perform better historically than very fresh zones;
5. because every subgroup was opened on the same 2011–2025 panel, none may be used immediately as a production filter;
6. one 2-minute stacking causality defect must be removed or prevented before external replication.
