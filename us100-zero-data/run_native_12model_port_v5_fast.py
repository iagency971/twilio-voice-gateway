#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

import run_native_12model_port_v5 as base


def parity_check() -> dict:
    rng = np.random.default_rng(260822)
    x = pd.Series(rng.normal(size=2000))
    x.iloc[::137] = np.nan
    old = x.rolling(120, min_periods=40).apply(
        lambda w: (w.iloc[-1] <= w).sum() / len(w) * 100, raw=False
    )
    fast = x.rolling(120, min_periods=40).apply(
        lambda w: np.count_nonzero(w[-1] <= w) / len(w) * 100, raw=True
    )
    a = old.to_numpy(dtype=float)
    b = fast.to_numpy(dtype=float)
    ok = bool(np.allclose(a, b, rtol=0.0, atol=1e-12, equal_nan=True))
    finite = np.isfinite(a) & np.isfinite(b)
    max_abs = float(np.max(np.abs(a[finite] - b[finite]))) if finite.any() else 0.0
    return {"pass": ok, "max_abs_diff": max_abs, "n": int(len(x)), "atol": 1e-12}


def ensure_external_fast() -> Path:
    ext = base.EXT
    if not ext.exists():
        subprocess.run(["git", "clone", "--quiet", base.EXT_REPO, str(ext)], check=True)
    subprocess.run(["git", "checkout", "--quiet", "--force", base.EXT_COMMIT], cwd=ext, check=True)
    got = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ext, text=True).strip()
    if got != base.EXT_COMMIT:
        raise RuntimeError(f"external commit mismatch {got}")

    parity = parity_check()
    base.OUT.mkdir(parents=True, exist_ok=True)
    (base.OUT / "EXECUTION_PARITY.json").write_text(json.dumps(parity, indent=2))
    if not parity["pass"]:
        raise RuntimeError(f"V5.1 rolling percentile parity failed: {parity}")

    f = ext / "strategy" / "quant" / "features.py"
    text = f.read_text()
    old = """bbw_pctile = bbw.rolling(pctile_window, min_periods=40).apply(\n        lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100, raw=False\n    )"""
    new = """bbw_pctile = bbw.rolling(pctile_window, min_periods=40).apply(\n        lambda x: np.count_nonzero(x[-1] <= x) / len(x) * 100, raw=True\n    )"""
    if old not in text:
        raise RuntimeError("Expected frozen BB percentile expression not found")
    patched = text.replace(old, new, 1)
    if patched.count(new) != 1:
        raise RuntimeError("Unexpected BB percentile patch count")
    f.write_text(patched)
    return ext


if __name__ == "__main__":
    base.ensure_external = ensure_external_fast
    base.main()
