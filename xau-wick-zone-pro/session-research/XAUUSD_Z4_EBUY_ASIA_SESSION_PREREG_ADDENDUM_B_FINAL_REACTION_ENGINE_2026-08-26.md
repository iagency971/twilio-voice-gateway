# XAUUSD Z4 / E-BUY — Asia v2 prereg addendum B: final repaired reaction engine

**Frozen:** 2026-08-26, while the Asia v2 outcome-blind architecture grid is still running and before any valid Asia v2 reaction result is inspected.

If Asia v2 authorizes a reaction study, the valid reaction implementation must use the project's final pre-outcome reaction repairs, not the older raw v1.0 trigger engine.

Required reaction chain:

- `xau_ebuy_reaction_dev_v1_0_3_final_preoutcome.py` semantics;
- therefore include the v1.0.1 sequential runtime-state repair inherited by that chain;
- include the v1.0.2 conservative contact-bar treatment, including `AMBIGUOUS_CONTACT_BAR` handling where applicable;
- include the v1.0.3 repaired ambiguity-aware summaries;
- retain the Asia-specific causal contact chronology, `18:00–03:00 America/New_York` session end, session-start identity, frozen contact geometry/target and max one fresh contact per display episode per Asia session.

The existing `xau_ebuy_asia_reaction_v1_0.py` may be reused for Asia-specific state/session/contact plumbing only after its imported reaction `base` is replaced by the final repaired v1.0.3 base. Any Asia v2 reaction artifact generated with the older raw v1.0 base is methodologically superseded and must not be used for the verdict.

No reaction outcome, TP1 rate, invalidation rate, MFE/MAE or profitability information is used to make this repair.