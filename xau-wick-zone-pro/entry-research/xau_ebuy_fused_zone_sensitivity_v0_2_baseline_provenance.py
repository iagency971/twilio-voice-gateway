#!/usr/bin/env python3
from __future__ import annotations

"""Provenance-only v0.2 wrapper around the frozen v0.1 fused-zone sensitivity.

The sensitivity engine, grid, reaction logic, and frozen E_BUY_US model are unchanged.
Only the H1 BASELINE parity constants are corrected from the historical rebuilt-
location counts (16896/7128) to the source-faithful frozen-candidate counts
(16895/7127), per Addendum A frozen on 2026-08-26.
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / 'xau_ebuy_fused_zone_sensitivity_v0_1.py'
ADDENDUM = HERE / 'XAUUSD_Z4_EBUY_FUSED_ZONE_SENSITIVITY_ADDENDUM_A_BASELINE_PROVENANCE_2026-08-26.md'

src = SRC.read_text()
addendum = ADDENDUM.read_text()

old = "checks={'contacts':wr['BASELINE']['contact_episode_count']==16896,'fired':wr['BASELINE']['bull_rejection_fired_count']==7128}"
new = "checks={'contacts':wr['BASELINE']['contact_episode_count']==16895,'fired':wr['BASELINE']['bull_rejection_fired_count']==7127}"

assert src.count(old) == 1, ('unexpected H1 parity guard occurrence count', src.count(old))
assert '0.10v, 0.20v, 0.25v, 0.30v, 0.40v, 0.50v' in addendum
assert '16,895 contacts / 7,127 fired BULL_REJECTION' in addendum
assert 'ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342' in addendum

patched = src.replace(old, new)
assert patched.count(old) == 0 and patched.count(new) == 1

# Preserve __file__ as the original engine so its relative imports resolve
# exactly as in v0.1. No other source transformation is permitted here.
ns = {
    '__name__': '__main__',
    '__file__': str(SRC),
    '__package__': None,
}
exec(compile(patched, str(SRC), 'exec'), ns, ns)
