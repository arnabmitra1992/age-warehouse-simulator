"""
Lane-sequenced block storage model.

Inbound fill strategy
---------------------
Fill column 1 completely (row 1 → row N, within each row level 1 → top), then
column 2, and so on.  Each new pallet is assigned an incrementing fill_order so
the arrival sequence is preserved for auditing, but the *pick* order is driven
by position, not fill_order.

Outbound pick strategy
----------------------
Empty the lowest-indexed column that still contains pallets first.  Within a
column the pick order is:
  - Row 1 (front/aisle side) before row 2 … row N (back).
  - Within a row: highest level first (top-down), so the topmost pallet is
    always removed before the one below it.

Because we always access from the front row downwards, and the outbound scan
visits row 1 before row 2, no pallet is ever physically blocked by another
pallet in the same lane.  Consequently ``avg_shuffles_per_outbound`` is always
**0.0** and no shuffling fleet is required.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class PalletSlot:
    """One storage slot identified by (row, col, level)."""
    row: int
    col: int
    level: int
    fill_order: Optional[int] = None    # None = empty; integer = arrival sequence

    @property
    def is_occupied(self) -> bool:
        return self.fill_order is not None


class LaneSequenceStorageModel:
    """
    Ground-stacking model with lane-sequenced fill and drain policies.

    Rows are numbered 1 (front/aisle side) to ``num_rows`` (back).
    Columns (lanes) are numbered 1 to ``num_columns``.
    Levels are numbered 1 (ground) to ``num_levels`` (top).

    This model provides the same public interface as ``FIFOStorageModel`` so it
    can be used as a drop-in replacement in the simulator.
    """

    def __init__(self, num_rows: int, num_columns: int, num_levels: int):
        self.num_rows = num_rows
        self.num_columns = num_columns
        self.num_levels = num_levels
        self._counter = 0
        self._slots: Dict[Tuple[int, int, int], PalletSlot] = {}
        for r in range(1, num_rows + 1):
            for c in range(1, num_columns + 1):
                for lv in range(1, num_levels + 1):
                    self._slots[(r, c, lv)] = PalletSlot(row=r, col=c, level=lv)

    # ------------------------------------------------------------------
    # Basic slot access
    # ------------------------------------------------------------------

    def slot(self, row: int, col: int, level: int) -> PalletSlot:
        return self._slots[(row, col, level)]

    @property
    def total_positions(self) -> int:
        return self.num_rows * self.num_columns * self.num_levels

    @property
    def occupied_count(self) -> int:
        return sum(1 for s in self._slots.values() if s.is_occupied)

    @property
    def occupancy_fraction(self) -> float:
        if self.total_positions == 0:
            return 0.0
        return self.occupied_count / self.total_positions

    # ------------------------------------------------------------------
    # Lane-sequence inbound: fill column 1 completely, then column 2 …
    # Within a column: row 1 → row N (front to back), level 1 → top.
    # ------------------------------------------------------------------

    def inbound_put(self) -> Optional[Tuple[int, int, int]]:
        """
        Place a new pallet in the next available slot using lane-sequence order.

        Fill order: columns first (1 → num_columns), then rows front→back
        (1 → num_rows), then levels bottom→top (1 → num_levels).
        Column 1 is completely filled before column 2 is started.

        Returns (row, col, level) of the placed position, or None if full.
        """
        for col in range(1, self.num_columns + 1):
            for row in range(1, self.num_rows + 1):
                for level in range(1, self.num_levels + 1):
                    s = self._slots[(row, col, level)]
                    if not s.is_occupied:
                        self._counter += 1
                        s.fill_order = self._counter
                        return (row, col, level)
        return None  # storage full

    # ------------------------------------------------------------------
    # Lane-sequence outbound: drain lowest column first.
    # Within a column: row 1 → row N, level top → bottom.
    # ------------------------------------------------------------------

    def outbound_get(self) -> Optional[Tuple[int, int, int]]:
        """
        Remove and return the next pallet using lane-sequence drain order.

        Pick order: lowest column index first, within a column row 1 (front)
        before row N, and within a row the highest level (top) before lower
        levels.  No shuffling is ever needed.

        Returns (row, col, level) of the removed pallet, or None if empty.
        """
        for col in range(1, self.num_columns + 1):
            for row in range(1, self.num_rows + 1):
                for level in range(self.num_levels, 0, -1):  # top-down
                    s = self._slots[(row, col, level)]
                    if s.is_occupied:
                        s.fill_order = None
                        return (row, col, level)
        return None  # storage empty

    # ------------------------------------------------------------------
    # Statistics – shuffling is always zero in lane-sequence mode
    # ------------------------------------------------------------------

    def blocking_pallets(self, target_row: int, col: int, level: int) -> List[PalletSlot]:
        """
        Lane-sequence never has blocking pallets.  Always returns an empty list.

        The method signature mirrors ``FIFOStorageModel.blocking_pallets`` for
        interface compatibility.
        """
        return []

    def average_shuffles_per_outbound(self) -> float:
        """Lane-sequence mode requires zero shuffles."""
        return 0.0

    # Keep the same name as FIFOStorageModel for callers that use it directly.
    def avg_shuffles_per_outbound(self) -> float:  # noqa: D102
        return 0.0
