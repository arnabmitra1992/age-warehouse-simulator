"""
Ground stacking calculations: layout, dimensions, and storage capacity.

The stacking area holds euro boxes/pallets in rows × columns × levels.
Clearance of 200 mm is applied on all sides of each box position.
The fork entry side determines which dimension becomes the travel depth.

Explicit ``rows``, ``columns``, and ``levels`` values (when provided) override
the values derived from the physical area dimensions, allowing the config to
specify an exact layout (e.g. 10 rows × 12 columns × 3 levels).
"""
import math
from dataclasses import dataclass, field
from typing import Optional, Tuple, List

CLEARANCE_MM = 200          # fixed clearance per side
MAX_LIFT_HEIGHT_MM = 4500   # XQE_122 max lift height


@dataclass
class BoxDimensions:
    length_mm: float = 1200
    width_mm: float = 800
    height_mm: float = 1000


@dataclass
class StackingAreaDimensions:
    length_mm: float = 15000
    width_mm: float = 10000


@dataclass
class GroundStackingConfig:
    box: BoxDimensions = None
    area: StackingAreaDimensions = None
    fork_entry_side: str = "Length"   # "Length" or "Width"
    clearance_mm: float = CLEARANCE_MM
    # Optional explicit overrides (when set, derived layout counts are ignored)
    explicit_rows: Optional[int] = None
    explicit_columns: Optional[int] = None
    explicit_levels: Optional[int] = None

    def __post_init__(self):
        if self.box is None:
            self.box = BoxDimensions()
        if self.area is None:
            self.area = StackingAreaDimensions()

    # ------------------------------------------------------------------
    # Effective footprint of one box slot (box + clearance on each side)
    # ------------------------------------------------------------------
    @property
    def effective_box_width_mm(self) -> float:
        """Effective width of each column slot (mm)."""
        if self.fork_entry_side == "Length":
            return self.box.width_mm + 2 * self.clearance_mm
        else:
            return self.box.length_mm + 2 * self.clearance_mm

    @property
    def effective_box_depth_mm(self) -> float:
        """Effective depth of each row slot – fork travel direction (mm)."""
        if self.fork_entry_side == "Length":
            return self.box.length_mm + 2 * self.clearance_mm
        else:
            return self.box.width_mm + 2 * self.clearance_mm

    # ------------------------------------------------------------------
    # Layout counts (explicit overrides take priority)
    # ------------------------------------------------------------------
    @property
    def num_columns(self) -> int:
        if self.explicit_columns is not None:
            return max(0, self.explicit_columns)
        usable_width = self.area.width_mm - 2 * self.clearance_mm
        return max(0, math.floor(usable_width / self.effective_box_width_mm))

    @property
    def num_rows(self) -> int:
        if self.explicit_rows is not None:
            return max(0, self.explicit_rows)
        usable_length = self.area.length_mm - 2 * self.clearance_mm
        return max(0, math.floor(usable_length / self.effective_box_depth_mm))

    @property
    def num_levels(self) -> int:
        if self.explicit_levels is not None:
            return max(1, self.explicit_levels)
        return max(1, math.floor(MAX_LIFT_HEIGHT_MM / self.box.height_mm))

    @property
    def total_positions(self) -> int:
        return self.num_rows * self.num_columns * self.num_levels

    # ------------------------------------------------------------------
    # Position geometry
    # ------------------------------------------------------------------
    def column_distance_m(self, col: int) -> float:
        """
        Distance (m) from stacking area entry to the centre of column C (1-based).
        column_distance = (C-1) * effective_width + effective_width/2 + clearance
        """
        c = self.effective_box_width_mm
        dist_mm = (col - 1) * c + c / 2.0 + self.clearance_mm
        return dist_mm / 1000.0

    def row_distance_m(self, row: int) -> float:
        """
        Distance (m) from stacking area entry to the centre of row R (1-based).
        row_distance = (R-1) * effective_depth + effective_depth/2 + clearance
        """
        d = self.effective_box_depth_mm
        dist_mm = (row - 1) * d + d / 2.0 + self.clearance_mm
        return dist_mm / 1000.0

    def level_height_m(self, level: int) -> float:
        """Lift height (m) for stacking level L (1-based, level 1 = ground)."""
        return (level * self.box.height_mm) / 1000.0

    def all_positions(self) -> List[Tuple[int, int, int]]:
        """Return list of (row, col, level) tuples for every slot."""
        positions = []
        for row in range(1, self.num_rows + 1):
            for col in range(1, self.num_columns + 1):
                for level in range(1, self.num_levels + 1):
                    positions.append((row, col, level))
        return positions


def ground_stacking_config_from_dict(d: dict) -> GroundStackingConfig:
    """Create GroundStackingConfig from configuration dictionary."""
    box_d = d.get("Box_Dimensions", {})
    area_d = d.get("Storage_Area_Dimensions", {})
    box = BoxDimensions(
        length_mm=box_d.get("Length_mm", 1200),
        width_mm=box_d.get("Width_mm", 800),
        height_mm=box_d.get("Height_mm", 1000),
    )
    area = StackingAreaDimensions(
        length_mm=area_d.get("Length_mm", 15000),
        width_mm=area_d.get("Width_mm", 10000),
    )
    return GroundStackingConfig(
        box=box,
        area=area,
        fork_entry_side=d.get("Fork_Entry_Side", "Length"),
        clearance_mm=d.get("Clearance_mm", CLEARANCE_MM),
        explicit_rows=d.get("Rows", None),
        explicit_columns=d.get("Columns", None),
        explicit_levels=d.get("Levels", None),
    )
