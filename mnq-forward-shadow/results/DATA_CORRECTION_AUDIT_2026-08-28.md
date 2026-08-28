# MNQ Shadow Forward — data-correction audit — 2026-08-28

Scope: pipeline/ledger integrity only. No trading rule, filter, model, direction, stop, target, threshold, friction, or gate was changed.

During the 2026-08-28 zero-cost Yahoo NQ=F rerun, the external engine produced five trades dated 2026-08-25 that had not existed in the already frozen 2026-08-25 ledger. The preregistered protocol requires completed historical days to remain append-only unless a separate pure data-correction audit is documented.

Retroactive rows rejected from the prospective ledger:
- 2026-08-25 11:03:00 | ou_rev | long
- 2026-08-25 11:25:00 | vwap_scalp | long
- 2026-08-25 13:07:00 | vwap_scalp | long
- 2026-08-25 13:10:00 | vwap_scalp | long
- 2026-08-25 14:31:00 | pm_mom | long

The four genuinely new trades from the newly completed 2026-08-28 session were retained. The ledger therefore moved from 18 frozen trades through 2026-08-27 to 22 prospective trades through 2026-08-28, not 27.

`compat_runner.py` now enforces the existing protocol mechanically: it snapshots the frozen ledger before each Yahoo rerun and, after the engine completes, retains all previously frozen rows exactly and accepts only new keys whose entry date is strictly later than the prior frozen maximum day. It then recomputes SUMMARY.json from the append-only ledger.

Market-data cost for this correction: $0. No Databento or paid market-data request was made.
