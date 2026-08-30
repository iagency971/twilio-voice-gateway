#!/usr/bin/env python3
from __future__ import annotations

"""Outcome-blind implementation repair for the frozen V2 placebo design.

The Pro gate explicitly says that family and original E1/E2/E3 slot are copied
from the donor as labels; they must not require a real E to exist in the
recipient session.  The first implementation accidentally imposed that extra
recipient-real-slot-presence condition, which made the neutral control design
nearly infeasible before any outcome was opened.

This wrapper is deliberately minimal and fail-closed: it verifies the exact
Git blob of the frozen first implementation, removes only the two lines that
create/enforce recipient real-slot presence, then executes every other line
unchanged.  The original source and this repair are both hashed by the V2
pre-outcome freeze.
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE / "xau_e_zone_v2_placebos.py"
EXPECTED_GIT_BLOB = "d19a295509a45dd9c255e1410f8c70fd7833bef3"

actual = subprocess.check_output(["git", "hash-object", str(ORIGINAL)], text=True).strip()
if actual != EXPECTED_GIT_BLOB:
    raise RuntimeError(f"PLACEBO_R2_SOURCE_GUARD_FAIL expected={EXPECTED_GIT_BLOB} actual={actual}")

src = ORIGINAL.read_text()
needle_a = "    # Require that the original E display slot exists in the recipient context.\n    slot_presence=set((str(r.session_date_ny),int(r.minute_of_session),int(r.display_slot_rank)) for _,r in f.iterrows())\n"
needle_b = "            if (s,minute,slot) not in slot_presence:continue\n"
if src.count(needle_a) != 1 or src.count(needle_b) != 1:
    raise RuntimeError("PLACEBO_R2_PATCH_ANCHOR_FAIL")

patched = src.replace(
    needle_a,
    "    # R2: slot is a donor label per the frozen Pro gate; recipient real-slot presence is not required.\n",
).replace(needle_b, "")

ns = {"__name__": "__main__", "__file__": str(ORIGINAL)}
exec(compile(patched, str(ORIGINAL) + "#PLACEBO_R2", "exec"), ns, ns)

# Append an auditable implementation-repair marker to the generated manifest.
if "--manifest" in sys.argv:
    mp = Path(sys.argv[sys.argv.index("--manifest") + 1])
    m = json.loads(mp.read_text())
    m["implementation_repair"] = "R2_REMOVE_ERRONEOUS_RECIPIENT_REAL_SLOT_PRESENCE_REQUIREMENT"
    m["recipient_real_slot_presence_required"] = False
    m["donor_family_and_slot_copied_as_labels_only"] = True
    mp.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")
