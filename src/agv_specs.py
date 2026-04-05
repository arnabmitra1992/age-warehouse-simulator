"""
AGV Specifications for XQE_122 and XPL_201 vehicles.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class XQE122Specs:
    """XQE_122 Racking Robot specifications."""
    forward_speed_ms: float = 1.0       # m/s
    reverse_speed_ms: float = 0.3       # m/s
    lift_speed_ms: float = 0.2          # m/s
    max_lift_height_mm: float = 4500    # mm
    pickup_time_s: float = 30           # seconds
    dropoff_time_s: float = 30          # seconds
    fork_type: str = "backward"         # reverse entry
    name: str = "XQE_122"

    @property
    def max_lift_height_m(self) -> float:
        return self.max_lift_height_mm / 1000.0


@dataclass
class XPL201Specs:
    """XPL_201 Handover Robot specifications."""
    forward_speed_ms: float = 1.5       # m/s
    reverse_speed_ms: float = 0.5       # m/s
    pickup_time_s: float = 30           # seconds
    dropoff_time_s: float = 30          # seconds
    name: str = "XPL_201"


@dataclass
class TurnSpecs:
    """Shared turn operation specifications."""
    turn_90_degrees_s: float = 10       # seconds per 90° turn


# Default instances
DEFAULT_XQE122 = XQE122Specs()
DEFAULT_XPL201 = XPL201Specs()
DEFAULT_TURNS = TurnSpecs()


def xqe122_from_dict(d: dict) -> XQE122Specs:
    """Create XQE122Specs from a configuration dictionary."""
    return XQE122Specs(
        forward_speed_ms=d.get("forward_speed_ms", 1.0),
        reverse_speed_ms=d.get("reverse_speed_ms", 0.3),
        lift_speed_ms=d.get("lift_speed_ms", 0.2),
        max_lift_height_mm=d.get("max_lift_height_mm", 4500),
        pickup_time_s=d.get("pickup_time_s", 30),
        dropoff_time_s=d.get("dropoff_time_s", 30),
    )


def xpl201_from_dict(d: dict) -> XPL201Specs:
    """Create XPL201Specs from a configuration dictionary."""
    return XPL201Specs(
        forward_speed_ms=d.get("forward_speed_ms", 1.5),
        reverse_speed_ms=d.get("reverse_speed_ms", 0.5),
        pickup_time_s=d.get("pickup_time_s", 30),
        dropoff_time_s=d.get("dropoff_time_s", 30),
    )
