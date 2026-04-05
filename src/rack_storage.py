"""
Rack storage calculations: position layout and storage capacity.

Euro pallet racks:
  - Position spacing = 950 mm (800 mm pallet + 75 mm + 75 mm gaps)
  - Reverse entry (backward fork)
"""
import math
from dataclasses import dataclass
from typing import List, Tuple


POSITION_SPACING_MM = 950      # default spacing between pallet positions
REVERSE_ENTRY_DEPTH_MM = 1500  # distance robot backs into shelf position


@dataclass
class RackConfig:
    rack_length_mm: float = 20000
    position_spacing_mm: float = POSITION_SPACING_MM
    shelf_height_spacing_mm: float = 1300   # height between shelf levels
    num_levels: int = 3                     # number of shelf levels above ground

    @property
    def positions_per_shelf(self) -> int:
        return math.floor(self.rack_length_mm / self.position_spacing_mm)

    @property
    def total_positions(self) -> int:
        return self.positions_per_shelf * self.num_levels

    def shelf_height_m(self, level: int) -> float:
        """Height (m) to lift to for shelf at given level (1-based)."""
        return (level * self.shelf_height_spacing_mm) / 1000.0

    def distance_to_position_m(self, position_n: int, aisle_entry_m: float = 0.0) -> float:
        """
        Distance (m) from aisle entry to the centre of position N (1-based).

        distance = aisle_entry + (position_n * spacing_m) - half_spacing
        """
        spacing_m = self.position_spacing_mm / 1000.0
        return aisle_entry_m + (position_n * spacing_m) - (spacing_m / 2.0)

    def distance_from_position_to_exit_m(self, position_n: int, aisle_entry_m: float = 0.0) -> float:
        """Distance (m) from the centre of position N back to aisle exit."""
        rack_length_m = self.rack_length_mm / 1000.0
        return rack_length_m - self.distance_to_position_m(position_n, aisle_entry_m)

    def all_positions(self) -> List[Tuple[int, int]]:
        """Return list of (level, position) tuples for every slot in the rack."""
        positions = []
        for level in range(1, self.num_levels + 1):
            for pos in range(1, self.positions_per_shelf + 1):
                positions.append((level, pos))
        return positions


def rack_config_from_dict(d: dict) -> RackConfig:
    """Create RackConfig from configuration dictionary."""
    shelf_spacing = d.get("Shelf_Height_Spacing_mm", 1300)
    max_lift_mm = 4500
    num_levels = math.floor(max_lift_mm / shelf_spacing)
    return RackConfig(
        rack_length_mm=d.get("Rack_Length_mm", 20000),
        position_spacing_mm=d.get("Position_Spacing_mm", POSITION_SPACING_MM),
        shelf_height_spacing_mm=shelf_spacing,
        num_levels=num_levels,
    )
