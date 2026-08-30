# V2 R4 pre-outcome implementation repair — normalized-width floating round-trip

Date: 2026-08-30

## Scope

XAUUSD M1 / BUY only / US 08:00–17:00 New York / displayed E1-E2-E3 / frozen control design `R4_D5_MINIMAL_DENSE`.

No V2 future reaction outcome has been opened. The authoritative sequential run `33319636531` stopped during REP PREOUTCOME QA; DEV labels, model, VAL outcomes and REP outcomes were never generated.

## Trigger

After the exact-neutrality QA repair, DEV and VAL passed every R4 PREOUTCOME gate. REP passed every gate except `matching_width_exact`, which used:

`np.allclose(donor_zone_width_v, recipient_transplanted_zone_width_v, rtol=0, atol=2e-12)`

The fixed `2e-12` tolerance was an implementation QA constant. It is not a Pro-authorized matching caliper, outcome threshold, statistical gate or design parameter.

## Outcome-blind diagnostic

Dedicated run `33321902439`, job `99285222973`, rebuilt REP from commit-pinned M1 and the frozen R4 generator without reading any future reaction outcome.

On 136,253 controls:

- only 6 rows have absolute normalized-width delta > `2e-12`;
- 0 rows exceed `5e-12`;
- maximum absolute delta = `3.035488527203256e-12`;
- maximum relative delta = `1.6085166385514637e-11`;
- median delta = `1.2129186544029835e-13`;
- p99 delta = `8.381895177933535e-13`.

Frozen evidence: `R4_REP_WIDTH_FLOAT_DIAGNOSTIC_2026-08-30.json`.

## Why this is numerical round-trip, not geometry drift

For every selected recipient snapshot the R4 generator keeps the donor half-widths normalized by donor `v`, then materializes recipient price-space bounds:

- `lo = recipient_center - donor_lower_half_width_v * recipient_v`
- `hi = recipient_center + donor_upper_half_width_v * recipient_v`

The matching table then reports recipient normalized width as `(hi - lo) / recipient_v`.

Mathematically this equals the donor normalized width. In float64 it contains cancellation from subtracting two Gold price-level numbers, followed by division by `v`, plus deterministic decimal serialization/parse round-trip. A fixed absolute tolerance independent of the price/v scale is therefore not a principled test of geometric preservation.

No recipient session, control rank, matching distance, causal level, zlo, zhi, path, caliper or neutrality decision changes under this repair.

## Repair

Replace the arbitrary `2e-12` authority check by a deterministic row-wise IEEE-754 reconstruction bound:

`bound = 64 * eps_float64 * max(1, |zlo|, |zhi|, |center|) / v_snapshot`

where `zlo`, `zhi`, `center` and `v_snapshot` are taken from the materialized first placebo snapshot for that control.

The factor 64 is a conservative operation/serialization budget for the chained subtraction, multiplication, addition, second subtraction, division and CSV binary-decimal-binary round-trip. It scales with the actual cancellation condition number `price/v` rather than with an empirically tuned period-specific threshold.

Mandatory assertions:

1. `abs(donor_zone_width_v - recipient_transplanted_zone_width_v) <= bound` for every matching row;
2. the stored recipient normalized width equals `(first_placebo_zhi - first_placebo_zlo) / first_placebo_v` within the same machine-scale bound;
3. the old fixed `2e-12` result and delta distribution remain report-only diagnostics;
4. all original R4 design, neutrality, balance, coverage, path, deterministic-selection and chronological gates remain unchanged.

If the machine-scale bound fails on any row, stop before DEV and investigate. Do not enlarge the bound from observed outcomes or change R4 matching.

## Scientific status

This is an outcome-blind implementation QA repair only. It does not relax any scientific R4 requirement. It changes how exact mathematical width preservation is verified in floating arithmetic; it does not change the preserved geometry itself.
