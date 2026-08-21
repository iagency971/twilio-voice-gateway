#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).with_name("run_v1.py")
source = path.read_text()
old = "d.index.normalize().eq(day)"
new = "(d.index.normalize() == day)"
if source.count(old) != 1:
    raise RuntimeError(f"Expected exactly one Pandas DatetimeIndex.eq occurrence, found {source.count(old)}")
source = source.replace(old, new)
# Reporting compatibility only: an all-winner slice has PF=+inf, which strict JSON
# refuses to serialize. Replace only the representation with a very large finite
# sentinel; all PF gates remain mathematically equivalent.
old_pf = 'float("inf") if pos>0 else None'
new_pf = '1e99 if pos>0 else None'
if source.count(old_pf) != 1:
    raise RuntimeError(f"Expected exactly one infinite-PF expression, found {source.count(old_pf)}")
source = source.replace(old_pf, new_pf)
exec(compile(source, str(path), "exec"), {"__name__": "__main__", "__file__": str(path)})
