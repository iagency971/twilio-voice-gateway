# XAUUSD Z4 → Pine grid-step compression — result v0.1

**Status: PASS**  
**Selected Pine grid step: 0.05 USD**  
**Future outcomes used: NO**

The candidates `{0.02, 0.05, 0.10}` and all thresholds were preregistered before the comparisons. The deterministic rule was to choose the largest candidate passing every criterion.

- `0.02`: PASS.
- `0.05`: PASS.
- `0.10`: FAIL because p95 center error was **0.3214 vseg > 0.25** and matched top-1 zone agreement was **82.40% < 85%**.

Therefore the frozen choice is **0.05 USD**. No threshold was relaxed.

At 0.05 vs exact 0.01 Z4:

- exact-zone match: **92.52%**
- proxy-zone match: **98.72%**
- median IoU: **0.9739**
- p10 IoU: **0.9063**
- median center error: **0.0382 vseg**
- p95 center error: **0.1786 vseg**
- raw M0GL Pearson: **0.99734**
- raw M0GL Spearman: **0.99836**
- median score error: **0.00231**
- p95 score error: **0.03138**
- top-1 zone agreement: **87.13%**

The GitHub workflow's final aggregation script had a filename typo after all three proxy comparisons had already completed. The immutable job log and `XAUUSD_Z4_PINE_GRID_STEP_RESULT_ATTESTATION_v0_1.json` preserve the three results and frozen selection.
