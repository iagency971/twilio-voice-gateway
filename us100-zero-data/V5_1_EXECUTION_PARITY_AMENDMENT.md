# V5.1 Execution-Parity Amendment — pre-outcome

Status: `FROZEN_BEFORE_V5_OUTCOME`

The frozen external model commit and all strategy semantics remain unchanged.

The source feature engine computes Bollinger-width percentile with:

`rolling(...).apply(lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100, raw=False)`

For the large 2021-2025 translation run this creates a pandas Series object for every rolling window and is unnecessarily slow.

V5.1 permits an execution-only replacement by the mathematically equivalent NumPy raw-window expression:

`rolling(...).apply(lambda x: np.count_nonzero(x[-1] <= x) / len(x) * 100, raw=True)`

No period, threshold, min_periods, data value, model rule or output definition changes.

Before the full economic run, the runner must compare the original and accelerated expression on a deterministic sample series containing ordinary values and NaNs and require equality within absolute tolerance 1e-12 (NaNs equal). If parity fails, abort without economic interpretation.

This amendment is solely to reduce compute time; it is not a strategy change and was frozen before any V5 result was observed.