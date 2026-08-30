# V2 pre-outcome implementation repair R2

Date: 2026-08-30
Scope unchanged: XAUUSD M1 / BUY only / US 08:00–17:00 New York / displayed E1-E2-E3.

## Trigger

The first V2 workflow run `33282591026` stopped in the complete outcome-blind package stage. No V2 reaction label, DEV model, validation label, replication label or V2 performance statistic was generated or read.

Two implementation defects were established from pre-outcome evidence only.

## Defect 1 — overlap parity used non-canonical inputs

The frozen Pro gate requires exact display parity against the canonical v0.4 overlap Aug-2024 through Jul-2026. The canonical V1 parity was built with:

- BID M1 Jan-2024 through Jul-2026 as causal warm-up;
- the exact 24 frozen C5 Z4 artifacts from run `33139524456`;
- target display interval Aug-2024 through Jul-2026.

The first V2 implementation instead recomputed Z4 from BID M1 Jun-2024 through Jul-2026 inside its parity function. It therefore compared detector outputs produced from different causal inputs and failed row-count parity: 88,727 instrumented rows versus 88,557 canonical rows.

### R2 correction

Parity only now uses the exact canonical V1 causal inputs: Jan-2024 through Jul-2026 BID M1 plus the frozen 24-month C5 Z4 artifact. No scoring-period Z4 rule is changed; DEV/VAL/REP continue to use the frozen V2 geometry-only generator required by the Pro gate.

## Defect 2 — placebo generator imposed an extra real-recipient-slot condition

The Pro gate states that family and original E1/E2/E3 slot are copied from the donor as labels and do not make the placebo a real zone. The first implementation nevertheless required a real E with the same slot to exist at the recipient start snapshot.

That extra condition is not part of the intended neutral transplantation and is in tension with the neutrality requirement. It made the control design practically infeasible before outcomes:

- DEV donor episodes: 67,200;
- donors with five controls: 0;
- donors with at least two controls: 177 (0.263%).

This could never satisfy the frozen downstream requirement of at least 1,000 primary matched real contacts.

### R2 correction

The recipient-real-slot-presence requirement is removed and nothing else in placebo matching changes. The donor slot remains copied as the frozen label. The following remain unchanged:

- same 5-minute NY start slot;
- same NY weekday;
- same upper-Z4-count bucket;
- log-volatility caliper 0.20;
- nearest-upper-Z4-distance caliper 0.25v;
- 15/60/240 trend nearest-neighbour variables;
- recipient session separation;
- deterministic SHA-256 tie break;
- complete normalized donor geometry path;
- full real E/Z4 neutrality exclusion and 0.20v center exclusion;
- maximum five controls;
- identical labeler and width-neutral outcome;
- all DEV/VAL/REP gates.

## Scientific status

These are pre-outcome implementation repairs. They do not change the research question, the reaction endpoint, the matching calipers, the score features, the nuisance controls, the models, the chronological windows or any success threshold.

If the repaired package still cannot produce a feasible neutral-control population, the workflow must fail before DEV outcomes are opened and the placebo design must return to methodological review. No outcome may be used to relax matching.
