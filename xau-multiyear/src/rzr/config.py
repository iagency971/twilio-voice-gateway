from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class ResearchConfig:
    timezone: str = "America/New_York"
    reference_spread: float = 0.18
    point_zone_sigma_mult: float = 0.10
    point_zone_sigma_sensitivity: Tuple[float, ...] = (0.075, 0.10, 0.15)
    reaction_thresholds: Tuple[float, ...] = (0.25, 0.50, 1.00, 1.50)
    primary_reaction_threshold: float = 0.50
    failed_auction_minutes: Tuple[int, ...] = (5, 15, 30)
    failed_auction_primary_minutes: int = 15
    acceptance_minutes: int = 5
    acceptance_min_closes: int = 3
    stack_overlap_threshold: float = 0.50
    directional_change_deltas: Tuple[float, ...] = (0.5, 1.0, 2.0)
    round_number_steps: Tuple[float, ...] = (1.0, 5.0, 10.0, 25.0)
    memory_min_separation_minutes: int = 15
    do_z_timeframes: Tuple[str, ...] = ("15min", "30min", "1h")
    doz_displacement_quantile: float = 0.90
    doz_efficiency_min: float = 0.60
    doz_base_max_bars: int = 5
    doz_displacement_max_bars: int = 3
    fixed_r_surface: Tuple[float, ...] = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
    control_seed: int = 971
    control_exclude_known_zones: bool = False
    controls_per_contact: int = 5
    control_sigma_tolerance: float = 0.20
    control_match_local_hour: bool = True
    control_match_approach: bool = True
    control_require_quote_active: bool = True
    control_distance_sigma_min: float = 0.75
    control_distance_sigma_max: float = 3.0
