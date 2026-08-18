# XAUUSD / COMEX — DEV_RANK1 zero-cost gate ready for targeted Pro review

Date: 2026-08-18
Status: **NO PAID DEV_RANK1 DOWNLOAD AUTHORIZED**.

## What the post-Pro zero-cost work corrected

1. Paid DEV pilot sessions were reassigned correctly: four rank-1 and two rank-2 DEV sessions may be reused; six exposed confirm/test pilot sessions remain QA-only and are replaced deterministically in-stratum.
2. Panel weights were regenerated after those role corrections.
3. The original DEV coverage helper contained a research-day bug. It used `date(local-17h)` instead of the canonical XAU engine key. The corrected key is New York local date advanced by one day when local hour >=17:00.
4. Correct DEV_RANK1 coverage is 31,710 events across all 96 selected sessions, not the superseded 25,458/76 figure.
5. Historical GC auction close is 17:15 ET before 2015-09-21 and 17:00 ET thereafter; profiles use the era-correct auction session.
6. Pilot tape QA passed price-grid, positive-size, sequence and flag checks. Native side=N remains explicit; no primary imputation.
7. Low/zero GC dates are retained rather than replaced. Closures, holidays, sparse sessions and coverage-suspect sessions receive QA/missingness flags.
8. `GC.v.0` was found to be unsuitable as a sole session contract around some rolls. A causal V0/N0 roll diagnosis was completed without XAU outcomes.
9. BBO-1m remains removed from the immediate purchase.
10. Exact prior-session tape is not automatically bought for every selected date. Each selected source session creates native COMEX levels at its own close; future retest tape is deferred to Stage 2.

## Corrected DEV_RANK1 coverage

96 analytical sessions, 2011–2018, all containing canonical XAU events.

- FVG_ONLY: 29,797 events / 96 sessions / 8 years
- OBJECTIVE_ONLY: 704 / 96 / 8
- CONFLUENCE: 655 / 96 / 8
- DOZ_ONLY: 426 / 90 / 8
- MEMORY_ONLY: 128 / 38 / 8

Sparse cells are preregistered as inconclusive. Examples:

- DOZ_ONLY × ACCEPTANCE_RETEST: 5 events / 5 sessions / 4 years
- MEMORY_ONLY × ACCEPTANCE_RETEST: 4 / 3 / 3
- OBJECTIVE_ONLY × ACCEPTANCE_RETEST: 14 / 12 / 6
- MEMORY_ONLY × FAILED_AUCTION: 16 / 6 / 5

Largest exact confluences:

- OBJECTIVE_LIQUIDITY+FVG: 267 / 94 sessions
- MEMORY+FVG: 190 / 64
- DISPLACEMENT_ORIGIN+FVG: 131 / 66

Other exact confluences contain only 2–21 events and remain standalone-inconclusive.

## Data availability policy

Selected dates are not replaced merely because COMEX is closed/short/sparse.

Known examples:

- 2011-12-26 and 2014-01-20: GC.FUT parent has zero data; retain selected dates with COMEX features missing.
- 2012-11-22: legitimate extremely sparse/holiday-type activity; retain.
- 2014-06-13: sparse whole-family coverage; retain with coverage flag.
- 2015-02-05: normal trade tape but anomalously incomplete OHLCV-1m; reconstruct selected-session M1 from raw trades and flag continuous M1 gap.

## Roll problem discovered

At DEV_RANK1 session start, V0 and N0 point to the same contract on 86/96 sessions and different contracts on 10/96.

On the 10 divergences, frozen-contract full-session metadata shows N0 has more trades on 6 and V0 on 4. Some V0 failures are extreme:

- 2017-11-30: V0 530 trades vs N0 114,827
- 2012-03-30: 2,486 vs 66,770
- 2017-07-28: 6,895 vs 73,238

V0 can also win materially:

- 2014-01-24: V0 98,024 vs N0 12,074
- 2017-07-24: V0 62,453 vs N0 10,472

No XAU outcomes were used to make these comparisons.

## Contract candidates for Pro review

### Candidate A — N0_FROZEN_ONLY

At canonical session start, resolve `GC.n.0` to one raw instrument and keep that raw contract for all session trade/profile features.

Continuous context: `GC.n.0 / ohlcv-1m`.

Exact metadata quote:

- raw session trades, including one N0 top-up for paid 2013-05-29: USD 9.830145299435
- continuous N0 OHLCV-1m 2010-06-06→2019-01-01: USD 10.679362416267
- **new purchase quote: USD 20.509507715702**
- recommended hard cap: **USD 20.52**
- pilot already spent: USD 4.01
- projected cumulative project spend: USD 24.519507715702
- nominal credit left from USD125: USD 100.480492284298

Paid rank-1 sessions reused without duplicate purchase: 2013-02-07, 2017-10-31, 2018-01-02. Paid 2013-05-29 needs the N0 alternate raw contract if N0 is primary.

### Candidate B — DUAL_V0_N0_CAUSAL_ACTIVE

At session start resolve both V0 and N0.

- if mappings coincide: acquire once;
- if mappings differ: acquire both raw contracts;
- never merge the two contracts into one profile/CVD.

At each intraday decision:

- compare cumulative traded volume from canonical session start through the immediately preceding completed minute;
- choose the candidate with greater causal cumulative volume;
- tie-break N0;
- build all local/session-to-date trade-flow/profile features from that selected raw contract only.

At session close, for a COMEX-native source zone, full-session volume is already known, so choose the full-session volume winner before generating terminal POC/VA/VWAP levels.

Exact extra cost for the nine unpurchased V0 alternates: USD 0.316417872906. Paid V0 2013-05-29 is already available as the tenth divergent-session alternate.

Exact metadata quote:

- **new purchase quote: USD 20.825925588608**
- recommended hard cap: **USD 20.84**
- projected project spend including pilot: USD 24.835925588608
- nominal credit left: USD 100.164074411392

Incremental cost versus N0 only: **USD 0.316417872906**.

## Candidate recommendation entering Pro

**DUAL_V0_N0_CAUSAL_ACTIVE is the preferred candidate for adversarial Pro review**, because the additional cost is only USD 0.3164 and it removes the need to assume that either previous-day volume rank or previous-day open-interest rank is universally superior around rolls.

This is not an authorization to buy it. The active-contract rule itself must be challenged in Pro before spending.

## Frozen side policy

Primary:

- native A/B retained;
- native N retained explicitly;
- no TBBO side imputation;
- N_volume_share;
- native delta;
- delta lower/upper bounds;
- delta_sign_robust;
- interval CVD;
- reset at canonical GC session/contract boundaries.

## Frozen statistical policy

- DEV_RANK1 discovery only;
- trading date/session is independent cluster;
- leave-one-year-out within 2011–2018;
- post-stratification by year×quarter×vol_band;
- family-specific analysis; pooled model must family-balance/hierarchically control FVG dominance;
- B0 XAU baseline → B1 M1 context → B2 trades/auction nested comparison;
- frozen ridge model classes and hyperparameter grid;
- sparse cells INCONCLUSIVE;
- DEV_RANK2 replication only, not further tuning;
- CONFIRM and LOCKED_TEST stay unopened.

## Artifacts controlling this gate

- `xau-multiyear/docs/COMEX_DEV_RANK1_POST_PILOT_PRO_AUDIT_v1.md`
- `xau-multiyear/docs/COMEX_DEV_RANK1_ANALYSIS_PREREG_v1.md`
- `xau-multiyear/docs/COMEX_DEV_RANK1_FEATURE_SPEC_v1.md`
- `xau-multiyear/docs/COMEX_DEV_RANK1_FEATURE_SPEC_CANONICAL_v1_1.md`
- `xau-multiyear/docs/COMEX_DEV_RANK1_FEATURE_SPEC_CANONICAL_v1_2.md`
- `xau-multiyear/docs/COMEX_DEV_RANK1_COVERAGE_ADDENDUM_v1.md`
- `xau-multiyear/docs/COMEX_DEV_RANK1_AVAILABILITY_POLICY_v1.md`
- `xau-multiyear/docs/COMEX_DEV_RANK1_ROLL_POLICY_CANDIDATE_v1.md`
- `xau-final-results/comex_dev_rank1_gate_v1/dev_rank1_coverage_correct_daykey.json`
- `xau-final-results/comex_dev_rank1_gate_v1/frozen_session_contracts_v2.json`
- `xau-final-results/comex_dev_rank1_gate_v1/dev_rank1_exact_raw_contract_quote.json`
- `xau-final-results/comex_v4_pilot12_acquisition/pilot_flags_qa.json`

No DEV_RANK1 market data has been purchased or downloaded during this zero-cost correction phase.
