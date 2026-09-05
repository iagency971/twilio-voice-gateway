# V5.3 Exact-Spread Datetime Key Bugfix

Status: `IMPLEMENTATION_FIX_REQUIRED_BEFORE_ACCEPTING_V5_ECONOMICS`

The V5.2 rescore completed, but QA reported `fallback_trade_count = 3482 / 3482` (100%). This contradicts the source archive, where nearly all trade entry/exit minutes are present.

Root cause: the exact-spread dictionary used integer datetime representations from a pandas datetime Series while the lookup used `Timestamp.value`. Under the runtime pandas version these can use different internal resolutions (for example microseconds vs nanoseconds), so equal wall-clock timestamps did not produce equal integer keys.

This is a deterministic implementation defect in the exact-spread lookup, not a strategy or economic choice.

Fix: represent exact minute keys canonically as `YYYY-MM-DD HH:MM` strings on both the source spread series and requested trade timestamp. The already-frozen V5.2 rule remains unchanged:
1. exact required minute spread when present;
2. otherwise same-New-York-calendar-date median spread;
3. otherwise abort.

The frozen raw trade ledger SHA-256 must remain `c2c705318ff19aee4fb1137b7ec2102e98a848b297701b334e1b777a0d5b7d31`.

The V5.2 economic result produced with 100% fallback is superseded and must not be used for a decision. V5.3 changes only exact-spread key representation and reruns the lightweight rescore; the external 12-model engine is not rerun.