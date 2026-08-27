#!/usr/bin/env python3
from pathlib import Path

base = Path(__file__).resolve().parent / 'xau_ebuy_bull_candle_geometry_v1_0.py'
src = base.read_text(encoding='utf-8')
old = "tns=raw.time.astype('int64').to_numpy()"
new = "tns=raw.time.dt.tz_convert('UTC').dt.tz_localize(None).to_numpy(dtype='datetime64[ns]').astype('int64')"
if src.count(old) != 1:
    raise RuntimeError(f'expected exactly one timestamp anchor, got {src.count(old)}')
patched = src.replace(old, new, 1)
ns = {'__name__': '__main__', '__file__': str(base)}
exec(compile(patched, str(base), 'exec'), ns)
