# V5.2 Spread Fallback Amendment — pre-economic-rescore

Status: `FROZEN_BEFORE_V5_ECONOMIC_RESULT`

The external 12-model engine has already completed and produced the raw immutable trade ledger for V5. No PRIMARY/STRESS economic rescore has yet been completed.

The first rescore attempt aborted because the free USTEC archive has no recorded bar/spread at one trade exit minute (`2021-01-05 10:12:00` New York), and the implementation allowed only exact minute or the previous five minutes.

This amendment changes **only missing-spread handling**. No signal, entry, exit, stop, target, model parameter, model selection, timestamp, trade order, or raw `total_r` is changed.

For each round-trip spread charge:
1. use the recorded spread at the exact required minute when that minute exists;
2. if the exact minute is absent, use the median recorded spread of the same New York calendar date;
3. if the same-date median is unavailable, abort with no economic interpretation.

The fallback never selects a future trade outcome and does not inspect trade profitability. The same fallback spread is multiplied by 1x for PRIMARY and 2x for STRESS.

The already-produced `external_trades_raw.csv` is the sole raw trade ledger for this rescore. The external 12-model engine must **not** be rerun for V5.2.