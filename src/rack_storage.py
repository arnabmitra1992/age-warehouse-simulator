"""
Rack Storage Module
====================
Models Euro-pallet rack storage with multiple shelf heights.

Euro pallet dimensions: 1200 mm × 800 mm (standard)
Pallet pitch (spacing between pallet centres): 950 mm

A rack aisle has:
  - One or more *shelves* stacked vertically, each at a defined height.
  - Multiple *bays* along the aisle depth, each holding one pallet per shelf.
  - The AGV accesses pallets by travelling into the aisle (reverse, fork-first)
    and lifting to the required shelf height.

Position addressing: (bay_index, shelf_index) where bay 0 is nearest the aisle
entry and shelf 0 is the ground level (lowest).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RackShelf:
    """A single shelf level in a rack."""
    shelf_index: int
    height_m: float          # height above floor at which pallet rests
    description: str = ""

    def lift_time_s(self, lifting_speed_m_s: float = 0.2) -> float:
        """Time to lift (up) or lower (down) a pallet to this shelf height."""
        return self.height_m / lifting_speed_m_s


@dataclass
class RackBay:
    """One bay position along the aisle depth."""
    bay_index: int
    distance_from_entry_m: float   # distance from aisle entry to this bay
    occupied: bool = False
    pallet_id: Optional[str] = None


@dataclass
class RackPosition:
    """Unique rack storage position (bay + shelf)."""
    bay: RackBay
    shelf: RackShelf

    @property
    def position_id(self) -> str:
        return f"B{self.bay.bay_index:02d}S{self.shelf.shelf_index:02d}"

    @property
    def distance_from_entry_m(self) -> float:
        return self.bay.distance_from_entry_m

    @property
    def height_m(self) -> float:
        return self.shelf.height_m

    def lift_time_s(self, lifting_speed_m_s: float = 0.2) -> float:
        return self.shelf.lift_time_s(lifting_speed_m_s)

    def lift_and_lower_time_s(self, lifting_speed_m_s: float = 0.2) -> float:
        return 2.0 * self.lift_time_s(lifting_speed_m_s)


# ---------------------------------------------------------------------------
# Rack Storage class
# ---------------------------------------------------------------------------

class RackStorage:
    """
    Euro-pallet rack storage with configurable shelves and bays.

    Parameters
    ----------
    aisle_depth_m : float
        Total depth of the storage aisle (m).
    pallet_spacing_m : float
        Centre-to-centre spacing between pallet bays (default 0.95 m).
    shelves : list of dict
        Each dict has ``height_mm`` and optionally ``description``.
        If empty, a single ground-level shelf at 0.3 m is created.
    """

    EURO_PALLET_PITCH_M: float = 0.95    # 950 mm standard pallet pitch

    def __init__(
        self,
        aisle_depth_m: float,
        pallet_spacing_m: float = EURO_PALLET_PITCH_M,
        shelves: Optional[List[dict]] = None,
    ) -> None:
        self.aisle_depth_m = aisle_depth_m
        self.pallet_spacing_m = pallet_spacing_m

        # Build shelves
        if shelves:
            self.shelves: List[RackShelf] = [
                RackShelf(
                    shelf_index=i,
                    height_m=s["height_mm"] / 1000.0,
                    description=s.get("description", f"Level {i + 1}"),
                )
                for i, s in enumerate(shelves)
            ]
        else:
            # Default: single ground-level shelf
            self.shelves = [RackShelf(0, 0.3, "Ground level")]

        # Build bays
        self.bays: List[RackBay] = self._create_bays()

        # All positions grid
        self.positions: List[RackPosition] = [
            RackPosition(bay=bay, shelf=shelf)
            for bay in self.bays
            for shelf in self.shelves
        ]

    # ------------------------------------------------------------------

    def _create_bays(self) -> List[RackBay]:
        """Create bay positions along the aisle, spaced by pallet_spacing_m."""
        bays = []
        distance = self.pallet_spacing_m / 2.0   # first bay is half-pitch from entry
        idx = 0
        while distance <= self.aisle_depth_m:
            bays.append(RackBay(bay_index=idx, distance_from_entry_m=distance))
            distance += self.pallet_spacing_m
            idx += 1
        return bays

    # ------------------------------------------------------------------
    # Capacity and position queries
    # ------------------------------------------------------------------

    @property
    def num_bays(self) -> int:
        return len(self.bays)

    @property
    def num_shelves(self) -> int:
        return len(self.shelves)

    @property
    def total_capacity(self) -> int:
        return len(self.positions)

    @property
    def max_shelf_height_m(self) -> float:
        if not self.shelves:
            return 0.0
        return max(s.height_m for s in self.shelves)

    @property
    def avg_shelf_height_m(self) -> float:
        if not self.shelves:
            return 0.0
        return sum(s.height_m for s in self.shelves) / len(self.shelves)

    @property
    def avg_bay_depth_m(self) -> float:
        if not self.bays:
            return 0.0
        return sum(b.distance_from_entry_m for b in self.bays) / len(self.bays)

    def get_position(self, bay_index: int, shelf_index: int) -> Optional[RackPosition]:
        for pos in self.positions:
            if pos.bay.bay_index == bay_index and pos.shelf.shelf_index == shelf_index:
                return pos
        return None

    def avg_cycle_distances(self) -> Tuple[float, float]:
        """
        Return (avg_depth_m, avg_lift_height_m) for cycle-time calculation.

        avg_depth_m      – average distance from aisle entry to a storage position
        avg_lift_height_m – average shelf height across all positions
        """
        if not self.positions:
            return 0.0, 0.0
        avg_depth = sum(p.distance_from_entry_m for p in self.positions) / len(self.positions)
        avg_height = sum(p.height_m for p in self.positions) / len(self.positions)
        return avg_depth, avg_height

    # ------------------------------------------------------------------
    # Human-readable summary
    # ------------------------------------------------------------------

    def summary(self) -> str:
        lines = [
            f"Rack Storage: {self.num_bays} bays × {self.num_shelves} shelves "
            f"= {self.total_capacity} positions",
            f"  Aisle depth : {self.aisle_depth_m:.1f} m",
            f"  Pallet pitch: {self.pallet_spacing_m:.3f} m",
        ]
        for sh in self.shelves:
            lines.append(f"  Shelf {sh.shelf_index}: {sh.height_m:.2f} m ({sh.description})")
        return "\n".join(lines)
