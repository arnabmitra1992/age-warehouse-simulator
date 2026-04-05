"""
XQE_122 Ground Stacking Workflow Module
=========================================
Calculates cycle times for XQE_122 ground stacking tasks.

Workflow:
  Rest → Inbound (forward 1.0 m/s) → reverse 1.5 m → PICKUP (30 s) →
  forward out → head aisle → stacking area (forward 1.0 m/s) →
  navigate to (Row R, Col C) → reverse into position → lift to Level × box_height →
  DROPOFF (30 s) → forward → return to Rest (forward 1.0 m/s) → reverse park

Effective dimensions (200 mm clearance on each side):
  Columns = floor((area_width_mm  - 400) / (box_width_mm  + 400))
  Rows    = floor((area_length_mm - 400) / (box_length_mm + 400))
  Levels  = floor(4500 / box_height_mm)   (max stack 4.5 m for XQE_122)

Position distances within the stacking area:
  distance to column C = (C - 1) × (box_width_mm  + 400) / 1000  m  + 0.2 m clearance
  distance to row    R = (R - 1) × (box_length_mm + 400) / 1000  m  + 0.2 m clearance
  lift height          = level × box_height_mm / 1000  m

XQE_122 speeds:
  forward_speed = 1.0 m/s
  reverse_speed = 0.3 m/s
  lifting_speed = 0.2 m/s
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Physical parameters
# ---------------------------------------------------------------------------

_XQE_FWD_SPEED: float = 1.0
_XQE_REV_SPEED: float = 0.3
_XQE_LIFT_SPEED: float = 0.2
_MAX_LIFT_M: float = 4.5           # XQE_122 max lift height
_CLEARANCE_MM: float = 200.0       # clearance on each side
_APPROACH_DIST_M: float = 1.5
_DOCK_APPROACH_S: float = _APPROACH_DIST_M / _XQE_REV_SPEED  # 5 s
_TURN_90_S: float = 10.0
_PICKUP_S: float = 30.0
_DROPOFF_S: float = 30.0


# ---------------------------------------------------------------------------
# Stacking area capacity helpers
# ---------------------------------------------------------------------------

def stacking_capacity(
    area_width_mm: float,
    area_length_mm: float,
    box_width_mm: float,
    box_length_mm: float,
    box_height_mm: float,
) -> Tuple[int, int, int]:
    """
    Compute the number of (columns, rows, levels) in a ground stacking area.

    Parameters
    ----------
    area_width_mm, area_length_mm : float
        Stacking area dimensions in millimetres.
    box_width_mm, box_length_mm, box_height_mm : float
        Box dimensions in millimetres.

    Returns
    -------
    (columns, rows, levels) : tuple of int
    """
    columns = max(1, int((area_width_mm - 2 * _CLEARANCE_MM) / (box_width_mm + 2 * _CLEARANCE_MM)))
    rows = max(1, int((area_length_mm - 2 * _CLEARANCE_MM) / (box_length_mm + 2 * _CLEARANCE_MM)))
    levels = max(1, int((_MAX_LIFT_M * 1000) / box_height_mm))
    return columns, rows, levels


def position_distance_m(
    col: int,
    row: int,
    box_width_mm: float,
    box_length_mm: float,
) -> Tuple[float, float]:
    """
    Return (col_distance_m, row_distance_m) for a given (col, row) position.

    Based on 200 mm clearance between boxes and area border:
      col_dist = (col - 1) × (box_width + 400) / 1000 + 0.2
      row_dist = (row - 1) × (box_length + 400) / 1000 + 0.2
    """
    if col < 1 or row < 1:
        raise ValueError(f"col and row must be >= 1, got col={col}, row={row}")
    col_dist = (col - 1) * (box_width_mm + 2 * _CLEARANCE_MM) / 1000.0 + _CLEARANCE_MM / 1000.0
    row_dist = (row - 1) * (box_length_mm + 2 * _CLEARANCE_MM) / 1000.0 + _CLEARANCE_MM / 1000.0
    return col_dist, row_dist


def lift_height_m(level: int, box_height_mm: float) -> float:
    """Lift height for stacking on top of `level` existing boxes."""
    if level < 0:
        raise ValueError(f"level must be >= 0, got {level}")
    return level * box_height_mm / 1000.0


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class GroundStackingCycleResult:
    """Detailed breakdown of one XQE_122 ground stacking cycle."""

    d_rest_to_inbound: float
    d_inbound_to_stacking: float
    d_col: float
    d_row: float
    lift_height: float
    col: int
    row: int
    level: int

    travel_rest_to_inbound_s: float = 0.0
    dock_approach_s: float = _DOCK_APPROACH_S
    pickup_s: float = _PICKUP_S
    dock_depart_s: float = _DOCK_APPROACH_S
    travel_inbound_to_stacking_s: float = 0.0
    travel_to_col_s: float = 0.0
    travel_to_row_s: float = 0.0
    reverse_into_pos_s: float = _DOCK_APPROACH_S
    lift_up_s: float = 0.0
    dropoff_s: float = _DROPOFF_S
    forward_out_s: float = _DOCK_APPROACH_S
    travel_back_to_rest_s: float = 0.0
    rest_park_s: float = _DOCK_APPROACH_S

    @property
    def lift_down_s(self) -> float:
        return self.lift_up_s

    @property
    def total_cycle_time(self) -> float:
        return (
            self.travel_rest_to_inbound_s
            + self.dock_approach_s
            + self.pickup_s
            + self.dock_depart_s
            + self.travel_inbound_to_stacking_s
            + self.travel_to_col_s
            + self.travel_to_row_s
            + self.reverse_into_pos_s
            + self.lift_up_s
            + self.dropoff_s
            + self.forward_out_s
            + self.travel_back_to_rest_s
            + self.lift_down_s
            + self.rest_park_s
        )

    def to_dict(self) -> dict:
        return {
            "workflow": "XQE_122_Ground_Stacking",
            "position": {"col": self.col, "row": self.row, "level": self.level},
            "lift_height_m": round(self.lift_height, 3),
            "total_cycle_time_s": round(self.total_cycle_time, 2),
            "distances_m": {
                "rest_to_inbound": round(self.d_rest_to_inbound, 3),
                "inbound_to_stacking": round(self.d_inbound_to_stacking, 3),
                "to_column": round(self.d_col, 3),
                "to_row": round(self.d_row, 3),
            },
            "components_s": {
                "travel_rest_to_inbound": round(self.travel_rest_to_inbound_s, 2),
                "dock_approach": round(self.dock_approach_s, 2),
                "pickup": round(self.pickup_s, 2),
                "dock_depart": round(self.dock_depart_s, 2),
                "travel_inbound_to_stacking": round(self.travel_inbound_to_stacking_s, 2),
                "travel_to_col": round(self.travel_to_col_s, 2),
                "travel_to_row": round(self.travel_to_row_s, 2),
                "reverse_into_pos": round(self.reverse_into_pos_s, 2),
                "lift_up": round(self.lift_up_s, 2),
                "dropoff": round(self.dropoff_s, 2),
                "forward_out": round(self.forward_out_s, 2),
                "travel_back": round(self.travel_back_to_rest_s, 2),
                "lift_down": round(self.lift_down_s, 2),
                "rest_park": round(self.rest_park_s, 2),
            },
        }

    def print_breakdown(self) -> None:
        print(f"\n{'─' * 60}")
        print(f"  XQE_122 Ground Stacking – (Col {self.col}, Row {self.row},"
              f" Level {self.level}, H={self.lift_height:.2f} m)")
        print(f"{'─' * 60}")
        print(f"  fwd={_XQE_FWD_SPEED} m/s  rev={_XQE_REV_SPEED} m/s  "
              f"lift={_XQE_LIFT_SPEED} m/s")
        print()
        rows = [
            ("Rest → Inbound  (fwd)",       self.travel_rest_to_inbound_s),
            ("Reverse into dock",            self.dock_approach_s),
            ("Pickup",                       self.pickup_s),
            ("Forward out of dock",          self.dock_depart_s),
            ("Inbound → Stacking  (fwd)",    self.travel_inbound_to_stacking_s),
            (f"Forward to column {self.col}", self.travel_to_col_s),
            (f"Forward to row {self.row}",   self.travel_to_row_s),
            ("Reverse into position",        self.reverse_into_pos_s),
            (f"Lift to {self.lift_height:.2f} m", self.lift_up_s),
            ("Dropoff",                      self.dropoff_s),
            ("Forward out",                  self.forward_out_s),
            ("Return to Rest  (fwd)",        self.travel_back_to_rest_s),
            ("Lower mast",                   self.lift_down_s),
            ("Reverse into rest park",       self.rest_park_s),
        ]
        for label, t in rows:
            print(f"  {label:<38} {t:>7.1f} s")
        print(f"{'─' * 60}")
        print(f"  TOTAL CYCLE TIME                        {self.total_cycle_time:>7.1f} s"
              f"  ({self.total_cycle_time / 60:.1f} min)")
        print(f"{'─' * 60}\n")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def xqe_ground_stacking_cycle(
    d_rest_to_inbound: float,
    d_inbound_to_stacking: float,
    box_width_mm: float,
    box_length_mm: float,
    box_height_mm: float,
    col: int = 1,
    row: int = 1,
    level: int = 0,
) -> GroundStackingCycleResult:
    """
    Calculate XQE_122 ground stacking cycle time for a specific position.

    Parameters
    ----------
    d_rest_to_inbound : float
        Distance from rest area to inbound dock (metres).
    d_inbound_to_stacking : float
        Distance from inbound dock to stacking area entry (metres).
    box_width_mm, box_length_mm, box_height_mm : float
        Box dimensions in millimetres.
    col : int
        Target column (1-based).
    row : int
        Target row (1-based).
    level : int
        Stack level to place on top of (0 = ground level).

    Returns
    -------
    GroundStackingCycleResult
    """
    lh = lift_height_m(level, box_height_mm)
    if lh > _MAX_LIFT_M:
        raise ValueError(
            f"Lift height {lh:.2f} m (level={level}, box_height={box_height_mm} mm) "
            f"exceeds XQE_122 maximum ({_MAX_LIFT_M} m)"
        )

    d_col, d_row = position_distance_m(col, row, box_width_mm, box_length_mm)
    d_back = d_inbound_to_stacking + d_col + d_row

    result = GroundStackingCycleResult(
        d_rest_to_inbound=d_rest_to_inbound,
        d_inbound_to_stacking=d_inbound_to_stacking,
        d_col=d_col,
        d_row=d_row,
        lift_height=lh,
        col=col,
        row=row,
        level=level,
    )

    result.travel_rest_to_inbound_s = d_rest_to_inbound / _XQE_FWD_SPEED
    result.travel_inbound_to_stacking_s = d_inbound_to_stacking / _XQE_FWD_SPEED
    result.travel_to_col_s = d_col / _XQE_FWD_SPEED
    result.travel_to_row_s = d_row / _XQE_FWD_SPEED
    result.lift_up_s = lh / _XQE_LIFT_SPEED if lh > 0 else 0.0
    result.travel_back_to_rest_s = d_back / _XQE_FWD_SPEED

    return result


def xqe_ground_stacking_cycle_avg(
    d_rest_to_inbound: float,
    d_inbound_to_stacking: float,
    area_width_mm: float,
    area_length_mm: float,
    box_width_mm: float,
    box_length_mm: float,
    box_height_mm: float,
) -> float:
    """
    Return the average cycle time across all positions and levels in a stacking area.

    Averages over (col, row) at the geometric centre and over all valid levels.

    Returns
    -------
    float
        Average cycle time in seconds.
    """
    cols, rows, levels = stacking_capacity(
        area_width_mm, area_length_mm, box_width_mm, box_length_mm, box_height_mm
    )
    mid_col = max(1, (cols + 1) // 2)
    mid_row = max(1, (rows + 1) // 2)
    times = []
    for lvl in range(levels):
        try:
            r = xqe_ground_stacking_cycle(
                d_rest_to_inbound=d_rest_to_inbound,
                d_inbound_to_stacking=d_inbound_to_stacking,
                box_width_mm=box_width_mm,
                box_length_mm=box_length_mm,
                box_height_mm=box_height_mm,
                col=mid_col,
                row=mid_row,
                level=lvl,
            )
            times.append(r.total_cycle_time)
        except ValueError:
            break
    if not times:
        raise ValueError("Could not compute any valid stacking cycles")
    return sum(times) / len(times)
