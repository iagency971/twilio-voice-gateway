#!/usr/bin/env python3
from __future__ import annotations

"""Serialization-only wrapper for XAU core audit annual runner.

Scientific/runtime semantics are inherited unchanged from run_xau_core_audit_annual_v1.
This wrapper only makes strict JSON serialization deterministic when a parity metric
is +inf/-inf (for example PF with no losses). Non-finite values are represented as
explicit strings in parity JSON. The ledger and pass/fail calculations are untouched.
"""

import json as _json
import math

import run_xau_core_audit_annual_v1 as audit

_ORIGINAL_DUMPS = _json.dumps


def _sanitize(value):
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return value
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in value]
    return value


def _safe_dumps(obj, *args, **kwargs):
    kwargs.pop("allow_nan", None)
    return _ORIGINAL_DUMPS(_sanitize(obj), *args, allow_nan=False, **kwargs)


# audit.json references the same stdlib module object. Save original above, then
# replace only dumps for the duration of this process.
audit.json.dumps = _safe_dumps


if __name__ == "__main__":
    audit.main()
