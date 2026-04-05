"""
XQE_122 Rack Storage Workflow
==============================
Euro pallet slot spacing: 950 mm centre-to-centre.
Shelf heights: typically 0, 1200, 2400, 3600 mm (floor + 3 levels).

XQE_122 physics:
  - Empty travel into aisle: REVERSE (fork-first), 0.3 m/s
  - Loaded travel out of aisle: REVERSE, 0.3 m/s
  - Head aisle (no load): FORWARD, 1.0 m/s
  - Lift speed: 0.2 m/s
  - Typical cycle: 300-350 seconds
"""
from dataclasses import dataclass, field
from typing import List

EURO_PALLET_SLOT_SPACING_MM = 950   # mm centre-to-centre
XQE_FORWARD_SPEED = 1.0     # m/s
XQE_REVERSE_SPEED = 0.3     # m/s
XQE_LIFT_SPEED = 0.2        # m/s
PICKUP_TIME = 30            # s
DROPOFF_TIME = 30           # s
TURN_TIME = 10              # s per 90-degree turn

DEFAULT_SHELF_HEIGHTS_MM = [0, 1200, 2400, 3600]   # mm

@dataclass
class RackStorageCycleResult:
    """Result of a single XQE_122 rack storage cycle."""
    d_head_aisle_m: float     # head aisle travel distance (m)
    d_aisle_m: float          # aisle travel distance to slot (m)
    lift_height_m: float      # lift height (m)
    num_turns: int = 2
    shelf_level: int = 0      # 0=floor, 1=first shelf, etc.

    @property
    def forward_travel_time(self) -> float:
        return self.d_head_aisle_m / XQE_FORWARD_SPEED

    @property
    def reverse_travel_time(self) -> float:
        return 2 * self.d_aisle_m / XQE_REVERSE_SPEED

    @property
    def lift_time(self) -> float:
        return 2 * self.lift_height_m / XQE_LIFT_SPEED

    @property
    def turn_time(self) -> float:
        return self.num_turns * TURN_TIME

    @property
    def total_cycle_time(self) -> float:
        return (
            self.forward_travel_time
            + self.reverse_travel_time
            + self.lift_time
            + PICKUP_TIME
            + DROPOFF_TIME
            + self.turn_time
        )

    def to_dict(self) -> dict:
        return {
            "workflow": "XQE_122_RackStorage",
            "shelf_level": self.shelf_level,
            "total_cycle_time_s": round(self.total_cycle_time, 2),
            "components": {
                "forward_travel_s": round(self.forward_travel_time, 2),
                "reverse_travel_s": round(self.reverse_travel_time, 2),
                "lift_s": round(self.lift_time, 2),
                "pickup_s": PICKUP_TIME,
                "dropoff_s": DROPOFF_TIME,
                "turns_s": round(self.turn_time, 2),
                "num_turns": self.num_turns,
            },
            "distances_m": {
                "head_aisle": round(self.d_head_aisle_m, 2),
                "aisle": round(self.d_aisle_m, 2),
                "lift_height": round(self.lift_height_m, 2),
            }
        }

@dataclass
class RackLayoutInfo:
    """Rack layout information derived from aisle configuration."""
    aisle_depth_mm: float
    shelf_heights_mm: List[float] = field(default_factory=lambda: list(DEFAULT_SHELF_HEIGHTS_MM))

    @property
    def num_slots_per_side(self) -> int:
        return max(1, int(self.aisle_depth_mm / EURO_PALLET_SLOT_SPACING_MM))

    @property
    def avg_depth_m(self) -> float:
        return (self.aisle_depth_mm / 2) / 1000.0

    @property
    def avg_shelf_height_m(self) -> float:
        if not self.shelf_heights_mm:
            return 1.2
        return sum(self.shelf_heights_mm) / len(self.shelf_heights_mm) / 1000.0


def calculate_rack_storage_cycle(
    d_head_aisle_m: float,
    d_aisle_m: float,
    lift_height_m: float,
    num_turns: int = 2,
    shelf_level: int = 0,
) -> RackStorageCycleResult:
    """
    Calculate XQE_122 rack storage cycle time.

    Parameters
    ----------
    d_head_aisle_m : float
        Distance travelled in head aisle (metres).
    d_aisle_m : float
        Distance from aisle entry to rack slot (metres).
    lift_height_m : float
        Height to lift pallet to shelf (metres).
    num_turns : int
        Number of 90-degree turns (default 2: into and out of aisle).
    shelf_level : int
        Shelf level index (0=floor, 1=first shelf, ...).

    Returns
    -------
    RackStorageCycleResult with typical total around 300-350 seconds.
    """
    return RackStorageCycleResult(
        d_head_aisle_m=d_head_aisle_m,
        d_aisle_m=d_aisle_m,
        lift_height_m=lift_height_m,
        num_turns=num_turns,
        shelf_level=shelf_level,
    )
