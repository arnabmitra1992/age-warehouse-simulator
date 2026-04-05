"""
XPL_201 Handover Workflow
==========================
Models the XPL_201 pallet truck performing handover operations:
  Rest position → Inbound dock → Handover point → Rest position

The XPL_201 has backward-facing forks:
  - Empty travel (to dock): FORWARD speed (1.5 m/s)
  - Loaded travel (from dock): REVERSE speed (0.3 m/s)
  - No significant lifting (max 20 cm)

Typical cycle: 180-200 seconds for standard warehouse distances.
"""
from dataclasses import dataclass
from typing import Optional

XPL_FORWARD_SPEED = 1.5    # m/s
XPL_REVERSE_SPEED = 0.3    # m/s
PICKUP_TIME = 30           # s
DROPOFF_TIME = 30          # s
TURN_TIME = 10             # s per 90 degree turn

@dataclass
class HandoverCycleResult:
    """Result of a single XPL_201 handover cycle."""
    d_to_dock_m: float        # distance from rest to inbound dock (m)
    d_to_handover_m: float    # distance from dock to handover point (m)
    num_turns: int = 2        # typical: 1 turn at dock + 1 at handover

    @property
    def empty_travel_time(self) -> float:
        return (self.d_to_dock_m + self.d_to_handover_m) / XPL_FORWARD_SPEED

    @property
    def loaded_travel_time(self) -> float:
        return (self.d_to_handover_m + self.d_to_dock_m) / XPL_REVERSE_SPEED

    @property
    def turn_time(self) -> float:
        return self.num_turns * TURN_TIME

    @property
    def total_cycle_time(self) -> float:
        return (
            self.empty_travel_time
            + self.loaded_travel_time
            + PICKUP_TIME
            + DROPOFF_TIME
            + self.turn_time
        )

    def to_dict(self) -> dict:
        return {
            "workflow": "XPL_201_Handover",
            "total_cycle_time_s": round(self.total_cycle_time, 2),
            "components": {
                "empty_travel_s": round(self.empty_travel_time, 2),
                "loaded_travel_s": round(self.loaded_travel_time, 2),
                "pickup_s": PICKUP_TIME,
                "dropoff_s": DROPOFF_TIME,
                "turns_s": round(self.turn_time, 2),
                "num_turns": self.num_turns,
            },
            "distances_m": {
                "to_dock": round(self.d_to_dock_m, 2),
                "to_handover": round(self.d_to_handover_m, 2),
            }
        }


def calculate_handover_cycle(
    d_to_dock_m: float,
    d_to_handover_m: float,
    num_turns: int = 2,
) -> HandoverCycleResult:
    """
    Calculate XPL_201 handover cycle time.

    Parameters
    ----------
    d_to_dock_m : float
        Distance from rest/staging area to inbound dock (metres).
    d_to_handover_m : float
        Distance from dock to handover point / storage staging area (metres).
    num_turns : int
        Number of 90-degree turns in the cycle (default 2).

    Returns
    -------
    HandoverCycleResult with total cycle time around 180-200 seconds.
    """
    return HandoverCycleResult(
        d_to_dock_m=d_to_dock_m,
        d_to_handover_m=d_to_handover_m,
        num_turns=num_turns,
    )
