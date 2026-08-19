# CHECKPOINT — COMEX native reaction PRE-PRO ready

Date: 2026-08-19
Branch: `agent/xau-comex-acquisition-plan`
Status: READY FOR PRO METHODOLOGICAL GATE — REACTION OUTCOMES STILL SEALED

## Completed prerequisite

The native exact-contact phase is closed and immutable for this gate:

- 368 / 368 native levels classified;
- 238 exact J+1 contacts;
- 130 resolved J+1 no-contact;
- final 368 status SHA-256: `8a825b0bc1deba51959b78ab6e62206fe49232e76329558e83949bf6d3d4151a`.

Canonical contact checkpoint:

- `CHECKPOINT_COMEX_NATIVE_N2_EXACT_CONTACT_COMPLETE_2026-08-19.md`

## PRE-PRO reaction draft created

- `COMEX_DEV_RANK1_NATIVE_REACTION_PROTOCOL_PREPRO_v0_9.md`

The draft explicitly separates:

- Track A: reaction conditional on first exact J+1 contact;
- Track B: lifetime / first contact J+2+ / later retests.

No US-only filter is present. Contact time/session is context, not an optimized inclusion filter.

## Main PRE-PRO design

Track A is proposed on the same raw GC instrument that created the level.

- `t0` = exact first raw GC trade at the frozen level tick;
- approach side is determined causally from the last off-level raw trade before `t0`, with prior M1-close fallback;
- signed away/through reaction is independent of level type;
- exact residual contact-minute tape may be used where already owned;
- subsequent reaction uses completed N1 M1 bars only;
- candidate bar-aligned horizons: residual minute, B1, B5, B15, B30, B60, session close;
- continuous outcomes proposed: away MFE, through penetration, reaction balance, signed endpoint displacement;
- no binary win/rejection label is authorized before Pro;
- no M1 stop/target first-hit ordering may be inferred when both outcomes occur in the same minute;
- inference remains clustered by source/retest trading date.

Blocking PRE-PRO issue: matched-control construction must be chosen by Pro before any edge claim or full reaction execution.

## Zero-outcome data readiness QA

Run: `32253418465`
Conclusion: SUCCESS

Canonical result:

- `xau-final-results/comex_dev_rank1_native_reaction_prepro_readiness_v0_9/readiness.json`

QA result:

- `ready_for_pro_method_review=true`;
- `reaction_outcomes_computed=false`;
- `mfe_mae_computed=false`;
- `market_data_api_called=false`;
- `market_data_download_performed=false`;
- 92 complete N1 J+1 session blocks available;
- 238 / 238 exact-contact events have unique N1 session coverage;
- 238 / 238 exact-contact events have their N2 contact raw file;
- N2 raw integrity failures: 0;
- N2 contact-interval failures: 0.

The source-session-range normalizer provenance has intentionally not yet been certified. If Pro approves that normalizer, a final zero-outcome provenance QA must be completed before reaction execution.

## Pro gate prompt

Use:

- `PRO_GATE_COMEX_NATIVE_REACTION_PROTOCOL_2026-08-19.md`

Pro must decide before any reaction results are computed:

1. final event/approach definition;
2. exact horizon family and one primary horizon;
3. one primary continuous endpoint;
4. causal volatility normalizer;
5. matched-control construction and all parameters;
6. cluster inference and multiplicity handling;
7. deterministic DEV_RANK1 -> DEV_RANK2 promotion / NO_GO gate;
8. whether extra exact control tape is scientifically necessary;
9. timing and contract-roll rules for the separate Track-B J+2+ lifetime study.

## Locked state

- reaction extraction: NOT AUTHORIZED;
- MFE/MAE computation: NOT AUTHORIZED;
- new Databento spend: NOT AUTHORIZED;
- Track-B later-session acquisition: NOT AUTHORIZED;
- DEV_RANK2: CLOSED;
- RETRO_CONFIRM: CLOSED;
- LOCKED_COMEX_TEST: CLOSED;
- existing-POI COMEX B1/B2 path: remains CLOSED / NO_GO.

## Next action

Switch to Pro and perform only the methodological gate using the prepared Pro prompt. After Pro returns its decisions, incorporate them into `COMEX_DEV_RANK1_NATIVE_REACTION_PROTOCOL_v1.md`, freeze it, then return to Très élevé for mechanical execution.
