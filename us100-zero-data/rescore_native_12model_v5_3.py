#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).with_name("rescore_native_12model_v5_2.py")
TMP = Path("/tmp/rescore_native_12model_v5_3_runtime.py")

text = SRC.read_text()
old_exact = 'exact = dict(zip(sp.datetime.astype("int64"), sp.spread_price.astype(float)))'
new_exact = 'exact = dict(zip(sp.datetime.dt.strftime("%Y-%m-%d %H:%M"), sp.spread_price.astype(float)))'
old_key = 'key = required.value'
new_key = 'key = required.strftime("%Y-%m-%d %H:%M")'

if text.count(old_exact) != 1 or text.count(old_key) != 1:
    raise RuntimeError("V5.3 expected V5.2 exact-spread expressions not found exactly once")

text = text.replace(old_exact, new_exact, 1).replace(old_key, new_key, 1)
text = text.replace('"classification": "V5_2_ZERO_PAID_DATA_RESCORE_FROM_FROZEN_RAW_LEDGER"',
                    '"classification": "V5_3_EXACT_MINUTE_KEY_BUGFIX_FROM_FROZEN_RAW_LEDGER"', 1)
text = text.replace('"No external 12-model rerun was performed in V5.2."',
                    '"No external 12-model rerun was performed in V5.3."', 1)
TMP.write_text(text)

p = subprocess.run([sys.executable, str(TMP)])
raise SystemExit(p.returncode)
