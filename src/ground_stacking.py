"""
XQE_122 Ground Stacking Workflow
==================================
Ground stacking uses a grid of positions on the warehouse floor.
Pallets are stacked in levels, with 200 mm clearance between levels.

Level-based lifting:
  Level 0: 0 mm (floor)
  Level 1: 1200 + 200 = 1400 mm (pallet height + clearance)
  Level 2: 2 * 1200 + 200 = 2600 mm (2 pallet heights + clearance)
  NOTE: typical pallet height = 1200 mm

Grid positioning: 200 mm clearance between adjacent stacks.

XQE_122 physics:
  - Same as rack storage for travel
  - Lifting: level * (pallet_height + clearance) mm
  - Typical cycle: 280-320 seconds
"""
from dataclasses import dataclass

PALLET_HEIGHT_MM = 1200       # standard euro pallet height
STACK_CLEARANCE_MM = 200      # safety clearance above pallet
GRID_CLEARANCE_MM = 200       # between stacks in the grid

XQE_FORWARD_SPEED = 1.0       # m/s
XQE_REVERSE_SPEED = 0.3       # m/s
XQE_LIFT_SPEED = 0.2          # m/s
PICKUP_TIME = 30              # s
DROPOFF_TIME = 30             # s
TURN_TIME = 10                # s per 90-degree turn


def lift_height_for_level(level: int) -> float:
    """
    Calculate lift height in metres for a given stacking level.

    Level 0: 0 m (floor)
    Level 1: (1200 + 200) / 1000 = 1.4 m
    Level 2: (2 * 1200 + 200) / 1000 = 2.6 m
    etc.
    """
    if level == 0:
        return 0.0
    return (level * PALLET_HEIGHT_MM + STACK_CLEARANCE_MM) / 1000.0


@dataclass
class GroundStackingCycleResult:
    """Result of a single XQE_122 ground stacking cycle."""
    d_head_aisle_m: float     # head aisle travel distance (m)
    d_aisle_m: float          # aisle travel to stack position (m)
    stacking_level: int = 0   # 0=floor, 1,2,3...
    num_turns: int = 2

    @property
    def lift_height_m(self) -> float:
        return lift_height_for_level(self.stacking_level)

    @property
    def forward_travel_time(self) -> float:
        return self.d_head_aisle_m / XQE_FORWARD_SPEED

    @property
    def reverse_travel_time(self) -> float:
        return 2 * self.d_aisle_m / XQE_REVERSE_SPEED

    @property
    def lift_time(self) -> float:
        if self.lift_height_m <= 0:
            return 0.0
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
            "workflow": "XQE_122_GroundStacking",
            "stacking_level": self.stacking_level,
            "lift_height_m": round(self.lift_height_m, 3),
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
            }
        }


def calculate_ground_stacking_cycle(
    d_head_aisle_m: float,
    d_aisle_m: float,
    stacking_level: int = 0,
    num_turns: int = 2,
) -> GroundStackingCycleResult:
    """
    Calculate XQE_122 ground stacking cycle time.

    Parameters
    ----------
    d_head_aisle_m : float
        Distance in head aisle (metres).
    d_aisle_m : float
        Distance from aisle entry to stacking position (metres).
    stacking_level : int
        Level to stack onto (0=floor level, 1=on top of one pallet, ...).
    num_turns : int
        Number of 90-degree turns (default 2).

    Returns
    -------
    GroundStackingCycleResult with typical total around 280-320 seconds.
    """
    return GroundStackingCycleResult(
        d_head_aisle_m=d_head_aisle_m,
        d_aisle_m=d_aisle_m,
        stacking_level=stacking_level,
        num_turns=num_turns,
    )
