"""
XPL_201 Handover Workflow Module
==================================
Calculates the cycle time for the XPL_201 handover workflow:

  Rest → Inbound dock (forward at 1.5 m/s)
    → Reverse 1.5 m into dock position (30 s pickup)
    → Forward out → Head aisle → Handover zone (forward at 1.5 m/s)
    → Turn 90° (10 s) → Reverse 1.5 m into handover position (30 s dropoff)
    → Forward out → Turn 90° (10 s)
    → Head aisle → Rest area (forward at 1.5 m/s)
    → Reverse into rest park position

XPL_201 speeds:
  forward_speed = 1.5 m/s   (empty travel)
  reverse_speed = 0.3 m/s   (loaded / dock approach)

Fixed dock/position manoeuvre times (1.5 m approach at 0.3 m/s ≈ 5 s each):
  DOCK_APPROACH_S  = 5  (reverse 1.5 m at 0.3 m/s)
  DOCK_DEPART_S    = 5  (forward 1.5 m at 0.3 m/s)
  TURN_90_S        = 10 (one 90° turn)
  PICKUP_S         = 30
  DROPOFF_S        = 30
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# XPL_201 physical parameters
# ---------------------------------------------------------------------------

_XPL_FWD_SPEED: float = 1.5   # m/s – empty travel
_XPL_REV_SPEED: float = 0.3   # m/s – loaded / dock approach
_APPROACH_DIST_M: float = 1.5  # m  – standard dock reverse distance
_DOCK_APPROACH_S: float = _APPROACH_DIST_M / _XPL_REV_SPEED   # 5 s
_TURN_90_S: float = 10.0
_PICKUP_S: float = 30.0
_DROPOFF_S: float = 30.0


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class HandoverCycleResult:
    """Detailed breakdown of one XPL_201 handover cycle."""

    # Input distances (metres)
    d_rest_to_inbound: float
    d_inbound_to_handover: float
    d_handover_to_rest: float

    # Computed time components (seconds)
    travel_rest_to_inbound_s: float = 0.0
    dock_approach_inbound_s: float = _DOCK_APPROACH_S
    pickup_s: float = _PICKUP_S
    dock_depart_inbound_s: float = _DOCK_APPROACH_S
    travel_inbound_to_handover_s: float = 0.0
    turn_to_handover_s: float = _TURN_90_S
    handover_approach_s: float = _DOCK_APPROACH_S
    dropoff_s: float = _DROPOFF_S
    handover_depart_s: float = _DOCK_APPROACH_S
    turn_from_handover_s: float = _TURN_90_S
    travel_handover_to_rest_s: float = 0.0
    rest_park_s: float = _DOCK_APPROACH_S

    @property
    def total_cycle_time(self) -> float:
        """Total cycle time in seconds."""
        return (
            self.travel_rest_to_inbound_s
            + self.dock_approach_inbound_s
            + self.pickup_s
            + self.dock_depart_inbound_s
            + self.travel_inbound_to_handover_s
            + self.turn_to_handover_s
            + self.handover_approach_s
            + self.dropoff_s
            + self.handover_depart_s
            + self.turn_from_handover_s
            + self.travel_handover_to_rest_s
            + self.rest_park_s
        )

    def to_dict(self) -> dict:
        return {
            "workflow": "XPL_201_Handover",
            "total_cycle_time_s": round(self.total_cycle_time, 2),
            "distances_m": {
                "rest_to_inbound": round(self.d_rest_to_inbound, 3),
                "inbound_to_handover": round(self.d_inbound_to_handover, 3),
                "handover_to_rest": round(self.d_handover_to_rest, 3),
            },
            "components_s": {
                "travel_rest_to_inbound": round(self.travel_rest_to_inbound_s, 2),
                "dock_approach_inbound": round(self.dock_approach_inbound_s, 2),
                "pickup": round(self.pickup_s, 2),
                "dock_depart_inbound": round(self.dock_depart_inbound_s, 2),
                "travel_inbound_to_handover": round(self.travel_inbound_to_handover_s, 2),
                "turn_to_handover": round(self.turn_to_handover_s, 2),
                "handover_approach": round(self.handover_approach_s, 2),
                "dropoff": round(self.dropoff_s, 2),
                "handover_depart": round(self.handover_depart_s, 2),
                "turn_from_handover": round(self.turn_from_handover_s, 2),
                "travel_handover_to_rest": round(self.travel_handover_to_rest_s, 2),
                "rest_park": round(self.rest_park_s, 2),
            },
        }

    def print_breakdown(self) -> None:
        print(f"\n{'─' * 58}")
        print("  XPL_201 Handover Cycle Breakdown")
        print(f"{'─' * 58}")
        print(f"  forward speed : {_XPL_FWD_SPEED} m/s    reverse speed: {_XPL_REV_SPEED} m/s")
        print()
        rows = [
            ("Rest → Inbound  (fwd)",   self.travel_rest_to_inbound_s),
            ("Reverse into dock",        self.dock_approach_inbound_s),
            ("Pickup",                   self.pickup_s),
            ("Forward out of dock",      self.dock_depart_inbound_s),
            ("Inbound → Handover (fwd)", self.travel_inbound_to_handover_s),
            ("Turn 90°",                 self.turn_to_handover_s),
            ("Reverse to handover pos",  self.handover_approach_s),
            ("Dropoff",                  self.dropoff_s),
            ("Forward from handover",    self.handover_depart_s),
            ("Turn 90°",                 self.turn_from_handover_s),
            ("Handover → Rest   (fwd)",  self.travel_handover_to_rest_s),
            ("Reverse into rest park",   self.rest_park_s),
        ]
        for label, t in rows:
            print(f"  {label:<30} {t:>7.1f} s")
        print(f"{'─' * 58}")
        print(f"  TOTAL CYCLE TIME               {self.total_cycle_time:>7.1f} s"
              f"  ({self.total_cycle_time / 60:.1f} min)")
        print(f"{'─' * 58}\n")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def xpl_handover_cycle(
    d_rest_to_inbound: float,
    d_inbound_to_handover: float,
    d_handover_to_rest: float,
) -> HandoverCycleResult:
    """
    Calculate the XPL_201 handover cycle time.

    Path:
      Rest → Inbound (forward 1.5 m/s) → reverse 1.5 m → PICKUP (30 s) →
      forward out → head aisle → Handover zone (forward 1.5 m/s) →
      turn 90° (10 s) → reverse 1.5 m → DROPOFF (30 s) →
      forward out → turn 90° (10 s) → Rest (forward 1.5 m/s) → reverse park

    Parameters
    ----------
    d_rest_to_inbound : float
        Distance from rest area to inbound dock (metres).
    d_inbound_to_handover : float
        Distance from inbound dock to handover zone (metres).
    d_handover_to_rest : float
        Distance from handover zone back to rest area (metres).

    Returns
    -------
    HandoverCycleResult
        Detailed cycle time breakdown.
    """
    result = HandoverCycleResult(
        d_rest_to_inbound=d_rest_to_inbound,
        d_inbound_to_handover=d_inbound_to_handover,
        d_handover_to_rest=d_handover_to_rest,
    )

    result.travel_rest_to_inbound_s = d_rest_to_inbound / _XPL_FWD_SPEED
    # dock approach / depart are fixed at 5 s each (already set in dataclass defaults)
    result.travel_inbound_to_handover_s = d_inbound_to_handover / _XPL_FWD_SPEED
    result.travel_handover_to_rest_s = d_handover_to_rest / _XPL_FWD_SPEED

    return result
