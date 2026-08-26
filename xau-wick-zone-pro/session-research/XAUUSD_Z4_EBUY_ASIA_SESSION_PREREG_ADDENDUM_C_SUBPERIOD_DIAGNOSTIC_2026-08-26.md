# XAUUSD Z4 / E-BUY — Asia diagnostic addendum C: fixed subperiod localization

**Frozen:** 2026-08-26, after Asia v2 outcome-blind architecture grid completed with 45 candidates and zero H1+H2 passers, and before inspecting any new Asia subperiod metrics.

Purpose: locate the outcome-blind H1 coverage deficit of the current Asia v1 architecture. This diagnostic does not reopen v1/v2 selection, does not authorize reaction outcomes, and does not change the Asia 18:00–03:00 NY session.

Use the immutable Asia v1 displayed-candidate table from run `33018338282` and reconstruct the exact eligible C5 snapshot universe from the same frozen source-faithful C5 Z4 geometry and exact Dukascopy BID hashes.

Fixed subperiods, already named before this diagnostic in the Asia v2 preregistration:
- `ASIA_EARLY`: 18:00–21:00 New York;
- `ASIA_LATE_PRE_MIDNIGHT`: 21:00–00:00 New York;
- `ASIA_POST_MIDNIGHT`: 00:00–03:00 New York.

For H1 and H2 separately report for each subperiod:
- eligible snapshot count;
- share of eligible snapshots with zero displayed zone;
- displayed-zone count mean/median/p90;
- coverage <=0.5v / 1.0v / 1.5v / 2.0v;
- nearest displayed-zone distance median/p90 where a zone exists;
- displayed family mix.

Also report H2-minus-H1 coverage differences by subperiod. No TP1, invalidation, BULL_REJECTION, MFE/MAE or E-score information may be opened.

Interpretation is diagnostic only. A future restricted-session or Asia-specific architecture gate would require a new preregistration; these diagnostics may not retroactively rescue Asia v1/v2.