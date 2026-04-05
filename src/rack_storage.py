"""
XQE_122 Rack Storage Workflow Module
======================================
Calculates the cycle time for XQE_122 rack storage tasks.

Workflow:
  Rest → Inbound dock (forward 1.0 m/s) → reverse 1.5 m → PICKUP (30 s) →
  forward out → head aisle → rack aisle entry → forward to position N →
  turn 90° (10 s) → reverse 1.5 m → lift to shelf_height → DROPOFF (30 s) →
  forward 1.5 m → turn 90° (10 s) → forward back to aisle exit →
  head aisle → Rest (forward 1.0 m/s) → reverse park (5 s)

Storage position formula:
  Euro pallet standard = 950 mm slot width
  Positions per side   = floor(rack_length_mm / 950)
  Distance to position N = aisle_entry_offset_m + (N × 0.95 m) − 0.475 m offset
  Average position distance = rack_length_m / 2

XQE_122 speeds:
  forward_speed  = 1.0 m/s
  reverse_speed  = 0.3 m/s
  lifting_speed  = 0.2 m/s

Fixed manoeuvre times:
  DOCK_APPROACH_S = 5  s  (1.5 m at 0.3 m/s)
  TURN_90_S       = 10 s
  PICKUP_S        = 30 s
  DROPOFF_S       = 30 s
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# XQE_122 physical parameters
# ---------------------------------------------------------------------------

_XQE_FWD_SPEED: float = 1.0    # m/s – empty travel
_XQE_REV_SPEED: float = 0.3    # m/s – loaded / reverse into position
_XQE_LIFT_SPEED: float = 0.2   # m/s
_EURO_PALLET_SLOT_M: float = 0.95   # Euro pallet standard slot width
_APPROACH_DIST_M: float = 1.5
_DOCK_APPROACH_S: float = _APPROACH_DIST_M / _XQE_REV_SPEED   # 5 s
_TURN_90_S: float = 10.0
_PICKUP_S: float = 30.0
_DROPOFF_S: float = 30.0


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class RackStorageCycleResult:
    """Detailed breakdown of one XQE_122 rack storage cycle."""

    d_rest_to_inbound: float
    d_inbound_to_rack_entry: float
    d_to_position: float        # distance from aisle entry to slot N
    shelf_height: float
    position_n: int

    travel_rest_to_inbound_s: float = 0.0
    dock_approach_s: float = _DOCK_APPROACH_S
    pickup_s: float = _PICKUP_S
    dock_depart_s: float = _DOCK_APPROACH_S
    travel_inbound_to_aisle_s: float = 0.0
    travel_to_position_s: float = 0.0
    turn_into_slot_s: float = _TURN_90_S
    slot_reverse_s: float = _DOCK_APPROACH_S
    lift_up_s: float = 0.0
    dropoff_s: float = _DROPOFF_S
    slot_forward_s: float = _DOCK_APPROACH_S
    turn_out_of_slot_s: float = _TURN_90_S
    travel_back_to_inbound_s: float = 0.0
    rest_park_s: float = _DOCK_APPROACH_S

    @property
    def lift_down_s(self) -> float:
        """Lowering time equals lifting time."""
        return self.lift_up_s

    @property
    def total_cycle_time(self) -> float:
        return (
            self.travel_rest_to_inbound_s
            + self.dock_approach_s
            + self.pickup_s
            + self.dock_depart_s
            + self.travel_inbound_to_aisle_s
            + self.travel_to_position_s
            + self.turn_into_slot_s
            + self.slot_reverse_s
            + self.lift_up_s
            + self.dropoff_s
            + self.slot_forward_s
            + self.turn_out_of_slot_s
            + self.travel_back_to_inbound_s
            + self.lift_down_s
            + self.rest_park_s
        )

    def to_dict(self) -> dict:
        return {
            "workflow": "XQE_122_Rack_Storage",
            "position_n": self.position_n,
            "shelf_height_m": round(self.shelf_height, 3),
            "total_cycle_time_s": round(self.total_cycle_time, 2),
            "distances_m": {
                "rest_to_inbound": round(self.d_rest_to_inbound, 3),
                "inbound_to_rack_entry": round(self.d_inbound_to_rack_entry, 3),
                "to_position": round(self.d_to_position, 3),
            },
            "components_s": {
                "travel_rest_to_inbound": round(self.travel_rest_to_inbound_s, 2),
                "dock_approach": round(self.dock_approach_s, 2),
                "pickup": round(self.pickup_s, 2),
                "dock_depart": round(self.dock_depart_s, 2),
                "travel_inbound_to_aisle": round(self.travel_inbound_to_aisle_s, 2),
                "travel_to_position": round(self.travel_to_position_s, 2),
                "turn_into_slot": round(self.turn_into_slot_s, 2),
                "slot_reverse": round(self.slot_reverse_s, 2),
                "lift_up": round(self.lift_up_s, 2),
                "dropoff": round(self.dropoff_s, 2),
                "slot_forward": round(self.slot_forward_s, 2),
                "turn_out_of_slot": round(self.turn_out_of_slot_s, 2),
                "travel_back": round(self.travel_back_to_inbound_s, 2),
                "lift_down": round(self.lift_down_s, 2),
                "rest_park": round(self.rest_park_s, 2),
            },
        }

    def print_breakdown(self) -> None:
        print(f"\n{'─' * 60}")
        print(f"  XQE_122 Rack Storage Cycle – Position {self.position_n}"
              f", Height {self.shelf_height:.2f} m")
        print(f"{'─' * 60}")
        print(f"  fwd={_XQE_FWD_SPEED} m/s  rev={_XQE_REV_SPEED} m/s  "
              f"lift={_XQE_LIFT_SPEED} m/s")
        print()
        rows = [
            ("Rest → Inbound  (fwd)",     self.travel_rest_to_inbound_s),
            ("Reverse into dock",          self.dock_approach_s),
            ("Pickup",                     self.pickup_s),
            ("Forward out of dock",        self.dock_depart_s),
            ("Inbound → Aisle entry (fwd)", self.travel_inbound_to_aisle_s),
            (f"Forward to position {self.position_n}", self.travel_to_position_s),
            ("Turn 90° into slot",         self.turn_into_slot_s),
            ("Reverse 1.5 m into slot",    self.slot_reverse_s),
            (f"Lift to {self.shelf_height:.2f} m", self.lift_up_s),
            ("Dropoff",                    self.dropoff_s),
            ("Forward out of slot",        self.slot_forward_s),
            ("Turn 90° back to aisle",     self.turn_out_of_slot_s),
            ("Forward back to inbound",    self.travel_back_to_inbound_s),
            ("Lower mast",                 self.lift_down_s),
            ("Reverse into rest park",     self.rest_park_s),
        ]
        for label, t in rows:
            print(f"  {label:<36} {t:>7.1f} s")
        print(f"{'─' * 60}")
        print(f"  TOTAL CYCLE TIME                      {self.total_cycle_time:>7.1f} s"
              f"  ({self.total_cycle_time / 60:.1f} min)")
        print(f"{'─' * 60}\n")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def rack_positions_count(rack_length_mm: float) -> int:
    """Return number of Euro-pallet storage positions in a rack of given length."""
    return max(1, int(rack_length_mm / (_EURO_PALLET_SLOT_M * 1000)))


def distance_to_position_m(position_n: int) -> float:
    """
    Distance from aisle entry to rack slot N (metres).

    Based on Euro-pallet standard (950 mm per slot):
      d = N × 0.95 m - 0.475 m (centre of first slot is at 0.475 m)
    """
    if position_n < 1:
        raise ValueError(f"position_n must be >= 1, got {position_n}")
    return position_n * _EURO_PALLET_SLOT_M - _EURO_PALLET_SLOT_M / 2.0


def average_position_distance_m(rack_length_mm: float) -> float:
    """Average distance to a random rack slot (half the rack length)."""
    return (rack_length_mm * 1e-3) / 2.0


def xqe_rack_storage_cycle(
    d_rest_to_inbound: float,
    d_inbound_to_rack_entry: float,
    shelf_height: float,
    rack_length_mm: float = 20000.0,
    position_n: Optional[int] = None,
) -> RackStorageCycleResult:
    """
    Calculate XQE_122 rack storage cycle time.

    Parameters
    ----------
    d_rest_to_inbound : float
        Distance from rest area to inbound dock (metres).
    d_inbound_to_rack_entry : float
        Distance from inbound dock to rack aisle entry (metres).
    shelf_height : float
        Target shelf height in metres (lift height).
    rack_length_mm : float
        Total rack length in millimetres (default 20 000 mm).
    position_n : int, optional
        Specific rack slot number to target (1-based).  If None, the average
        slot (middle of rack) is used.

    Returns
    -------
    RackStorageCycleResult
    """
    if shelf_height < 0:
        raise ValueError(f"shelf_height must be >= 0, got {shelf_height}")
    if shelf_height > 4.5:
        raise ValueError(
            f"shelf_height {shelf_height:.2f} m exceeds XQE_122 max lift (4.5 m)"
        )

    n_positions = rack_positions_count(rack_length_mm)
    if position_n is None:
        # Use middle position as the representative average
        position_n = max(1, n_positions // 2)
    elif position_n > n_positions:
        raise ValueError(
            f"position_n {position_n} exceeds rack capacity ({n_positions} positions)"
        )

    d_to_pos = distance_to_position_m(position_n)

    result = RackStorageCycleResult(
        d_rest_to_inbound=d_rest_to_inbound,
        d_inbound_to_rack_entry=d_inbound_to_rack_entry,
        d_to_position=d_to_pos,
        shelf_height=shelf_height,
        position_n=position_n,
    )

    result.travel_rest_to_inbound_s = d_rest_to_inbound / _XQE_FWD_SPEED
    result.travel_inbound_to_aisle_s = d_inbound_to_rack_entry / _XQE_FWD_SPEED
    result.travel_to_position_s = d_to_pos / _XQE_FWD_SPEED
    result.lift_up_s = shelf_height / _XQE_LIFT_SPEED
    result.travel_back_to_inbound_s = (d_inbound_to_rack_entry + d_to_pos) / _XQE_FWD_SPEED

    return result


def xqe_rack_storage_cycle_avg(
    d_rest_to_inbound: float,
    d_inbound_to_rack_entry: float,
    shelf_heights: List[float],
    rack_length_mm: float = 20000.0,
) -> float:
    """
    Return the average cycle time across all shelf heights and average position.

    Parameters
    ----------
    shelf_heights : list of float
        All shelf heights present in the rack (metres).

    Returns
    -------
    float
        Average cycle time in seconds.
    """
    if not shelf_heights:
        raise ValueError("shelf_heights must not be empty")
    valid = [h for h in shelf_heights if 0 <= h <= 4.5]
    if not valid:
        raise ValueError("No valid shelf heights (<= 4.5 m) provided for XQE_122")
    times = []
    for h in valid:
        r = xqe_rack_storage_cycle(
            d_rest_to_inbound=d_rest_to_inbound,
            d_inbound_to_rack_entry=d_inbound_to_rack_entry,
            shelf_height=h,
            rack_length_mm=rack_length_mm,
        )
        times.append(r.total_cycle_time)
    return sum(times) / len(times)
