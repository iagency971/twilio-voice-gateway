# CHECKPOINT — authoritative executable pre-outcome binding

Date: 2026-08-19  
Repository: `iagency971/twilio-voice-gateway`  
Branch: `agent/xau-comex-acquisition-plan`

## Purpose

This note resolves a documentation-only drift discovered immediately before opening Track-A outcomes.

The human-readable `CHECKPOINT_COMEX_NATIVE_REACTION_PREOUTCOME_FREEZE_COMPLETE_2026-08-19.md` retained SHA values from an earlier successful freeze publication. The executable pre-outcome directory was subsequently regenerated/published outcome-blind by GitHub Actions. No W5/W15/W60/SC or other reaction result had been opened in either freeze.

The **machine-readable executable authority** for outcome execution is therefore the current pair:

- `xau-final-results/comex_dev_rank1_native_reaction_preoutcome_final_v1/FREEZE_PUBLICATION.json`
- `xau-final-results/comex_dev_rank1_native_reaction_preoutcome_final_v1/preoutcome_freeze_manifest.json`

with the independent checksum file:

- `xau-final-results/comex_dev_rank1_native_reaction_preoutcome_final_v1/preoutcome_freeze_manifest.sha256`

## Authoritative binding immediately before Track A

- artifact freeze commit: `93930f82c3168dfd02a05edc57b78811739db9eb`
- preoutcome freeze manifest SHA-256: `60713b922eefe24dd8fbc306c1f26cc2557c829ccd0080649afbc9071972ca47`
- generation parent of artifact freeze commit: `6af339ba52b1398af0fafd52b3e251e09754529a`
- support status: `SUPPORT_GATE_REPAIRED_AND_PASS`
- matched events: 227
- matched treated dates: 81
- W15 opened at this checkpoint: **false**
- reaction outcomes computed at this checkpoint: **false**
- market-data API/download/new spend: **none**

The Track-A executor must verify the manifest SHA against both `FREEZE_PUBLICATION.json` and `preoutcome_freeze_manifest.sha256`, then verify every generated pre-outcome artifact hash and regenerate the deterministic frozen matching with exact identity before opening post-anchor prices.

The stale SHA block in the older human checkpoint is non-executable and must not be used as the binding for Track-A results.
