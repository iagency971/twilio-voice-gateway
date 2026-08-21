#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).with_name("run_v1.py")
source = path.read_text()
old = "d.index.normalize().eq(day)"
new = "(d.index.normalize() == day)"
if source.count(old) != 1:
    raise RuntimeError(f"Expected exactly one Pandas DatetimeIndex.eq occurrence, found {source.count(old)}")
source = source.replace(old, new)
exec(compile(source, str(path), "exec"), {"__name__": "__main__", "__file__": str(path)})
