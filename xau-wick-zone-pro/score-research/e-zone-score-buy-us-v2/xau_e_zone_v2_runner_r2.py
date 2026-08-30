#!/usr/bin/env python3
from __future__ import annotations

"""Method-preserving R2 runner for the targeted BUY-US E-zone V2 study.

Two outcome-blind implementation defects discovered before any V2 label was
opened are corrected here:
  1) overlap parity is evaluated with the exact canonical V1 inputs: Jan-2024
     through Jul-2026 BID M1 plus the frozen 24-month C5 Z4 artifact;
  2) placebo generation is routed through the R2 implementation repair that
     treats E1/E2/E3 as donor labels rather than requiring a real recipient E.

All outcome, matching calipers, neutrality exclusions, models, gates and
chronological windows remain those frozen by the targeted Pro gate.
"""

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import xau_e_zone_v2_pipeline as p

ORIGINAL_PY = p.py


def py_r2(name):
    if name == "xau_e_zone_v2_placebos.py":
        return HERE / "xau_e_zone_v2_placebos_r2.py"
    return ORIGINAL_PY(name)


p.py = py_r2
for extra in [
    "xau_e_zone_v2_placebos_r2.py",
    "xau_e_zone_v2_runner_r2.py",
    "PREOUTCOME_IMPLEMENTATION_REPAIR_R2.md",
]:
    if extra not in p.CODE_FILES:
        p.CODE_FILES.append(extra)


def parity_r2(data, work):
    o = p.outdir(work, "PARITY")
    frozen = Path(os.environ.get("V2_FROZEN_Z4_PKL", ""))
    if not frozen.is_file():
        raise RuntimeError(f"PARITY_R2_FROZEN_Z4_MISSING {frozen}")
    # Canonical V1 used the full Jan-2024 -> Jul-2026 BID warm-up while the
    # scored/parity target itself remains Aug-2024 -> Aug-2026.
    fs = p.files_for(data, "2024-01", "2026-07")
    ref = p.V1 / "E_DISPLAY_PROVENANCE_V1_24M.csv.gz"
    p.run([
        sys.executable,
        p.py("xau_e_zone_v2_instrument.py"),
        "--files", *fs,
        "--z4-pkl", frozen,
        "--output-features", o / "features.csv.gz",
        "--output-display-all", o / "display_all.csv.gz",
        "--output-full-pool", o / "full_pool.csv.gz",
        "--output-context", o / "context.csv.gz",
        "--manifest", o / "instrument_manifest.json",
        "--target-start", "2024-08-01T00:00:00Z",
        "--target-end", "2026-08-01T00:00:00Z",
        "--reference-v04-csv", ref,
    ])
    m = json.load(open(o / "instrument_manifest.json"))
    if not m["geometry_parity"]["pass"]:
        raise RuntimeError(f"PARITY_R2_FAIL {m['geometry_parity']}")
    m["parity_input_repair"] = {
        "bid_window": "2024-01 through 2026-07",
        "frozen_z4_source": str(frozen),
        "canonical_v1_reference": str(ref),
        "outcomes_used": False,
    }
    (o / "instrument_manifest.json").write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")
    return o


p.parity = parity_r2
p.main()
