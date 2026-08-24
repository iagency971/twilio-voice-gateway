import math
import sys
from pathlib import Path

import numpy as np

# Import the frozen Z4 engine and replace ONLY its Gaussian smoothing primitive.
# Everything else (vseg, peaks, bounds, features, lineage, outcomes) remains
# byte-for-byte the engine logic. The parity comparator never reads outcomes.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import xau_zone_episode_dev_z4 as z4  # noqa: E402


def box_pass_truncated(x, radius):
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n == 0 or radius <= 0:
        return x.copy()
    p = np.concatenate(([0.0], np.cumsum(x, dtype=float)))
    idx = np.arange(n, dtype=np.int64)
    left = np.maximum(0, idx - radius)
    right = np.minimum(n - 1, idx + radius)
    return (p[right + 1] - p[left]) / (right - left + 1)


def pine_box3_gaussian_proxy(x, sigma, *args, **kwargs):
    # Pine math.round for non-negative values is emulated as floor(x+0.5).
    sigma = float(sigma)
    if sigma <= 0:
        radius = 0
    else:
        raw = (math.sqrt(1.0 + 4.0 * sigma * sigma) - 1.0) / 2.0
        radius = int(math.floor(raw + 0.5))
    y = np.asarray(x, dtype=float)
    for _ in range(3):
        y = box_pass_truncated(y, radius)
    return y


z4.gaussian_filter1d = pine_box3_gaussian_proxy

if __name__ == '__main__':
    z4.main()
