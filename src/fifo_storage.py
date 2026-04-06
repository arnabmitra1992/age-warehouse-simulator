"""
FIFO ground-stacking storage model.

Storage fills front-to-back (row 1 = front/newest, row N = back/oldest).
Outbound retrieval is back-to-front (row N first = oldest first).

Shuffling is required when front pallets block access to an older back pallet
within the same column lane.
"""
from __future__ import annotations

import math
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


class FIFOStorageModel:
    """
    Model of a ground-stacking storage area with FIFO ordering.

    Rows are numbered 1 (front/entry side) to ``num_rows`` (back).
    Columns are numbered 1 to ``num_columns``.
    Levels are numbered 1 to ``num_levels``.

    Inbound fills: assigns the next available slot starting from row 1.
    Outbound retrieves: picks the pallet with the lowest fill_order (oldest)
    that is accessible from the front (all positions in front rows of the same
    column/level cleared, or in a different column).
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
    # FIFO fill (inbound): fill from row 1 (front) toward row N (back)
    # ------------------------------------------------------------------

    def inbound_put(self) -> Optional[Tuple[int, int, int]]:
        """
        Place a new pallet in the next available front-to-back slot.
        Returns (row, col, level) of the placed position, or None if full.

        Fill order: iterate rows front→back, columns left→right, levels bottom→top.
        """
        for row in range(1, self.num_rows + 1):
            for col in range(1, self.num_columns + 1):
                for level in range(1, self.num_levels + 1):
                    s = self._slots[(row, col, level)]
                    if not s.is_occupied:
                        self._counter += 1
                        s.fill_order = self._counter
                        return (row, col, level)
        return None  # storage full

    # ------------------------------------------------------------------
    # FIFO retrieval (outbound): oldest pallet (lowest fill_order) first
    # ------------------------------------------------------------------

    def blocking_pallets(self, target_row: int, col: int, level: int) -> List[PalletSlot]:
        """
        Return the list of occupied slots that block access to ``target_row``
        in the given column/level.  Blocking pallets are in rows 1 …
        target_row-1 of the same column/level that are occupied.

        The list is ordered from the front-most (row 1) to the one just
        before the target row (row target_row - 1).
        """
        blockers = []
        for r in range(1, target_row):
            s = self._slots[(r, col, level)]
            if s.is_occupied:
                blockers.append(s)
        return blockers

    def oldest_accessible_slot(self) -> Optional[PalletSlot]:
        """
        Return the oldest occupied slot that can be accessed without shuffling,
        i.e. the occupied slot with the lowest fill_order where no earlier
        same-column/level slot blocks access (row < its row is empty).
        If none exists without shuffling, return the globally oldest slot.
        """
        occupied = [s for s in self._slots.values() if s.is_occupied]
        if not occupied:
            return None
        # Try to find the oldest that has no blockers
        occupied_sorted = sorted(occupied, key=lambda s: s.fill_order)
        for slot in occupied_sorted:
            if not self.blocking_pallets(slot.row, slot.col, slot.level):
                return slot
        # All occupied slots have blockers; return globally oldest
        return occupied_sorted[0]

    def outbound_get(self) -> Optional[Tuple[int, int, int]]:
        """
        Remove and return the oldest pallet (lowest fill_order).
        No shuffling is performed here; call ``blocking_pallets`` first to
        determine if shuffling is needed.
        Returns (row, col, level) of the removed pallet, or None if empty.
        """
        occupied = [s for s in self._slots.values() if s.is_occupied]
        if not occupied:
            return None
        oldest = min(occupied, key=lambda s: s.fill_order)
        oldest.fill_order = None
        return (oldest.row, oldest.col, oldest.level)

    def shuffle_pallet(self, from_row: int, col: int, level: int) -> Optional[Tuple[int, int, int]]:
        """
        Move the pallet at (from_row, col, level) forward to the nearest
        empty slot in the same column/level (row < from_row) or to any
        empty slot in the storage.

        Returns the (new_row, col, level) destination, or None if no empty
        slot exists.
        """
        source = self._slots[(from_row, col, level)]
        if not source.is_occupied:
            return None
        # Prefer an empty slot in the same column/level at a lower row number
        for r in range(1, from_row):
            candidate = self._slots[(r, col, level)]
            if not candidate.is_occupied:
                candidate.fill_order = source.fill_order
                source.fill_order = None
                return (r, col, level)
        # Fall back: any empty slot in the storage
        for row in range(1, self.num_rows + 1):
            for c in range(1, self.num_columns + 1):
                for lv in range(1, self.num_levels + 1):
                    candidate = self._slots[(row, c, lv)]
                    if not candidate.is_occupied and (row, c, lv) != (from_row, col, level):
                        candidate.fill_order = source.fill_order
                        source.fill_order = None
                        return (row, c, lv)
        return None  # no empty slot

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def expected_shuffles_for_retrieval(self, target_row: int, col: int, level: int) -> int:
        """Return the number of blocking pallets for a specific target position."""
        return len(self.blocking_pallets(target_row, col, level))

    def average_shuffles_per_outbound(self) -> float:
        """
        Estimate the average number of shuffle operations required per outbound
        retrieval given the current storage state.

        For each occupied slot, count how many pallets block it.  The average
        over all occupied slots gives the expected shuffles per retrieval.
        """
        occupied = [s for s in self._slots.values() if s.is_occupied]
        if not occupied:
            return 0.0
        total_blocks = sum(
            len(self.blocking_pallets(s.row, s.col, s.level)) for s in occupied
        )
        return total_blocks / len(occupied)

    def shuffling_fraction(self, occupancy: Optional[float] = None) -> float:
        """
        Fraction of outbound retrievals that require at least one shuffle,
        estimated analytically for a storage with the given occupancy.

        When ``occupancy`` is None the current state occupancy is used.
        The model assumes uniform random fill of all positions; a retrieval
        requires a shuffle if the target slot has at least one blocking pallet.
        """
        if occupancy is None:
            occupancy = self.occupancy_fraction
        # Probability that at least one slot in rows 1..R-1 (same col/level)
        # is occupied, averaged over all retrieval positions weighted by their
        # likelihood of being the FIFO target.
        if self.num_rows <= 1:
            return 0.0
        # For row R (1-based) to be the oldest accessible, rows 1..R-1 must
        # be empty.  The fraction of retrievals needing shuffles equals the
        # probability that the target row has at least one blocker.
        # Simple estimate: fraction = 1 - (1 - occupancy)^(avg blocking rows)
        avg_blocking_rows = (self.num_rows - 1) / 2.0
        prob_no_blocker = (1.0 - occupancy) ** avg_blocking_rows
        return 1.0 - prob_no_blocker
