#!/usr/bin/env python3
"""Execution adapter for XAU_REJECTED_STRATEGY_HETEROGENEITY_PROTOCOL_v1.

The frozen core-audit helper returns membership as `member_zone_id`; the V1
heterogeneity runner expects the join key `zone_id`. This adapter changes only
that column name before delegating to the frozen V1 runner. No market, signal,
entry, subgroup or outcome rule is changed.
"""
from __future__ import annotations

import run_xau_rejected_heterogeneity_annual_v1 as runner

_original = runner.collapse_with_membership


def collapse_with_membership_adapter(*args, **kwargs):
    stacks, membership = _original(*args, **kwargs)
    if "member_zone_id" in membership.columns and "zone_id" not in membership.columns:
        membership = membership.rename(columns={"member_zone_id": "zone_id"})
    return stacks, membership


runner.collapse_with_membership = collapse_with_membership_adapter

if __name__ == "__main__":
    runner.main()
