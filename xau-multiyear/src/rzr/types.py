from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import pandas as pd


class ZoneFamily(str, Enum):
    MEMORY = "MEMORY"
    OBJECTIVE_LIQUIDITY = "OBJECTIVE_LIQUIDITY"
    AUCTION_VOLUME = "AUCTION_VOLUME"
    DISPLACEMENT_ORIGIN = "DISPLACEMENT_ORIGIN"
    FVG = "FVG"
    FLIP = "FLIP"


class ZoneSide(str, Enum):
    SUPPORT = "SUPPORT"
    RESISTANCE = "RESISTANCE"
    NEUTRAL = "NEUTRAL"


class ZoneState(str, Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    CONTACTED = "CONTACTED"
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"
    FLIPPED = "FLIPPED"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True)
class Zone:
    zone_id: str
    family: ZoneFamily
    variant: str
    side: ZoneSide
    origin_time: pd.Timestamp
    known_time: pd.Timestamp
    lower: float
    upper: float
    center: float
    source_tf: str
    metadata_json: str = "{}"

    def __post_init__(self) -> None:
        if self.upper <= self.lower:
            raise ValueError("Zone upper must be > lower")
        if not (self.lower <= self.center <= self.upper):
            raise ValueError("Zone center must lie inside bounds")
        if self.known_time < self.origin_time:
            raise ValueError("known_time cannot precede origin_time")


@dataclass(frozen=True)
class Contact:
    zone_id: str
    contact_time: pd.Timestamp
    side: ZoneSide
    lower: float
    upper: float
    penetration_depth: float
    sigma60: float
    approach_direction: int
    session: str
