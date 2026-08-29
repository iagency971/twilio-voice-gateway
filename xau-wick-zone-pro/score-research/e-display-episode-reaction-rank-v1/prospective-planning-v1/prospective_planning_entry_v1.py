#!/usr/bin/env python3
from pathlib import Path
import prospective_planning_tool_v1 as core

# Canonical repository path repair: PKG.parents[1] is xau-wick-zone-pro.
core.ENTRY = core.PKG.parents[1] / 'entry-research'
core.ENGINE = core.ENTRY / 'geometry-shifted-grid-parity' / 'xau_z4_c5_geometry_shifted_grid_equivalent.py'

if __name__ == '__main__':
    core.main()
