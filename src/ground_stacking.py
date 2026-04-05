"""
Ground Stacking with Multiple Levels Module
============================================
Models pallets stacked in a grid on the warehouse floor.

Layout:
  - Rows    (length-wise positions along the stacking area)
  - Columns (width-wise positions across the stacking area)
  - Levels  (vertical stack height – Level 1 = floor, Level N = top)

Only **XQE_122** can service ground stacking with multiple levels.
XSC **cannot** perform floor stacking.

Level height is determined by pallet + overhang (typically ~1 200 mm per level).
The AGV travels to the column entry, then lifts to the required level.

Position addressing: (row, col, level) – all 0-based.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class StackPosition:
    """A single grid position within the stacking area."""

    row: int          # 0-based
    col: int          # 0-based
    level: int        # 0-based (0 = floor level)

    distance_from_entry_m: float   # horizontal distance from area entry to this column
    height_m: float                 # floor-to-fork height for this level

    occupied: bool = False
    pallet_id: Optional[str] = None

    @property
    def position_id(self) -> str:
        return f"R{self.row:02d}C{self.col:02d}L{self.level:02d}"

    def lift_time_s(self, lifting_speed_m_s: float = 0.2) -> float:
        """Time to lift (or lower) to this level."""
        return self.height_m / lifting_speed_m_s

    def lift_and_lower_time_s(self, lifting_speed_m_s: float = 0.2) -> float:
        return 2.0 * self.lift_time_s(lifting_speed_m_s)


# ---------------------------------------------------------------------------
# Ground Stacking class
# ---------------------------------------------------------------------------

class GroundStackingMultipleLevels:
    """
    Multi-level ground stacking area serviced exclusively by XQE_122.

    Parameters
    ----------
    rows : int
        Number of rows (length-wise positions) in the stacking area.
    cols : int
        Number of columns (width-wise positions) in the stacking area.
    levels : int
        Maximum number of stacking levels (1 = floor only).
    level_height_m : float
        Height increment per level in metres (e.g. 1.2 m for 1 200 mm pallets).
    area_length_m : float
        Total length of the stacking area (m).  Used for distance calculations.
    area_width_m : float
        Total width of the stacking area (m).
    """

    AGV_TYPE: str = "XQE_122"   # Only XQE can floor-stack with multiple levels

    def __init__(
        self,
        rows: int,
        cols: int,
        levels: int,
        level_height_m: float,
        area_length_m: float,
        area_width_m: float,
    ) -> None:
        self.rows = rows
        self.cols = cols
        self.levels = levels
        self.level_height_m = level_height_m
        self.area_length_m = area_length_m
        self.area_width_m = area_width_m

        # Spacing between rows / columns
        self._row_pitch_m = area_length_m / max(rows, 1)
        self._col_pitch_m = area_width_m / max(cols, 1)

        # Build the position grid
        self.positions: List[StackPosition] = self._create_positions()

    # ------------------------------------------------------------------

    def _create_positions(self) -> List[StackPosition]:
        positions = []
        for row in range(self.rows):
            for col in range(self.cols):
                # Distance from stacking area entry = row pitch offset
                dist_m = (row + 0.5) * self._row_pitch_m
                for level in range(self.levels):
                    h_m = (level + 1) * self.level_height_m   # level 0 = 1× height
                    positions.append(
                        StackPosition(
                            row=row,
                            col=col,
                            level=level,
                            distance_from_entry_m=dist_m,
                            height_m=h_m,
                        )
                    )
        return positions

    # ------------------------------------------------------------------
    # Capacity and query helpers
    # ------------------------------------------------------------------

    @property
    def total_capacity(self) -> int:
        return len(self.positions)

    @property
    def max_stack_height_m(self) -> float:
        return self.levels * self.level_height_m

    @property
    def avg_depth_m(self) -> float:
        if not self.positions:
            return 0.0
        return sum(p.distance_from_entry_m for p in self.positions) / len(self.positions)

    @property
    def avg_lift_height_m(self) -> float:
        if not self.positions:
            return 0.0
        return sum(p.height_m for p in self.positions) / len(self.positions)

    def avg_cycle_distances(self) -> Tuple[float, float]:
        """
        Return (avg_depth_m, avg_lift_height_m) for cycle-time calculation.
        """
        return self.avg_depth_m, self.avg_lift_height_m

    def get_position(self, row: int, col: int, level: int) -> Optional[StackPosition]:
        for pos in self.positions:
            if pos.row == row and pos.col == col and pos.level == level:
                return pos
        return None

    # ------------------------------------------------------------------
    # Human-readable summary
    # ------------------------------------------------------------------

    def summary(self) -> str:
        lines = [
            f"Ground Stacking (Multiple Levels): "
            f"{self.rows} rows × {self.cols} cols × {self.levels} levels "
            f"= {self.total_capacity} positions",
            f"  Area        : {self.area_length_m:.1f} m × {self.area_width_m:.1f} m",
            f"  Level height: {self.level_height_m:.2f} m / level",
            f"  Max height  : {self.max_stack_height_m:.2f} m",
            f"  AGV type    : {self.AGV_TYPE} ONLY",
        ]
        return "\n".join(lines)
