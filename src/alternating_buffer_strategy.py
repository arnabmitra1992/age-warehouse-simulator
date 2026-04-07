"""
Alternating Buffer Column strategy with 24-hour aging constraint.

Policy overview
---------------
Layout:  12 rows × 11 columns × 3 levels  (396 slots total).
One-day production = 10 columns × 12 rows × 3 levels = 360 pallets.
One column (36 slots) is kept empty as a rolling buffer at the start of
each operating day.

The buffer column alternates between column 11 (odd days) and column 1
(even days), producing mirrored inbound/outbound scan orders:

  Day 1 (and every odd day):
    - Buffer column at start of day: 11 (empty)
    - Outbound retrieval order: 10 → 1  (strict column scan)
    - Inbound placement order:  11 → 2

  Day 2 (and every even day):
    - Buffer column at start of day:  1 (empty)
    - Outbound retrieval order:  2 → 11  (strict column scan)
    - Inbound placement order:   1 → 10

Aging constraint
----------------
A pallet may only be selected for outbound once its age ≥
``min_age_hours_for_outbound`` (default 24 h).  Age is tracked via a
``put_time_hour`` timestamp stored on each slot.

At simulation start the warehouse is pre-filled with pallets whose
``put_time_hour <= -min_age_hours_for_outbound`` so that outbound can
run immediately on Day 1.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AgedPalletSlot:
    """One storage slot that tracks pallet age via a placement timestamp."""

    row: int
    col: int
    level: int
    fill_order: Optional[int] = None       # None = empty
    put_time_hour: Optional[float] = None  # simulation hour when pallet placed

    @property
    def is_occupied(self) -> bool:
        return self.fill_order is not None

    def age_hours(self, current_hour: float) -> Optional[float]:
        """Return pallet age in hours, or None if slot is empty."""
        if self.put_time_hour is None:
            return None
        return current_hour - self.put_time_hour


# ---------------------------------------------------------------------------
# Day pattern helper
# ---------------------------------------------------------------------------

def get_day_pattern(day_index: int, num_columns: int = 11) -> Tuple[List[int], List[int]]:
    """
    Return ``(outbound_columns, inbound_columns)`` for a given 1-based day index.

    Day 1 (odd): outbound 10→1, inbound 11→2
    Day 2 (even): outbound 2→11, inbound 1→10

    The pattern generalises to any ``num_columns`` (default 11):
    - Odd days:  outbound = num_columns-1 → 1, inbound = num_columns → 2
    - Even days: outbound = 2 → num_columns, inbound = 1 → num_columns-1
    """
    n = num_columns
    if day_index % 2 == 1:  # odd day (Day 1, 3, 5, …)
        outbound_cols = list(range(n - 1, 0, -1))   # [10, 9, …, 1]
        inbound_cols = list(range(n, 1, -1))         # [11, 10, …, 2]
    else:                   # even day (Day 2, 4, 6, …)
        outbound_cols = list(range(2, n + 1))        # [2, 3, …, 11]
        inbound_cols = list(range(1, n))             # [1, 2, …, 10]
    return outbound_cols, inbound_cols


# ---------------------------------------------------------------------------
# Storage model
# ---------------------------------------------------------------------------

class AlternatingBufferStorage:
    """
    Ground-stacking storage with aging timestamps and the alternating
    buffer-column policy.

    Parameters
    ----------
    num_rows:
        Number of rows (depth of each column lane).
    num_columns:
        Total number of columns (including the one buffer column).
    num_levels:
        Number of stacking levels per position.
    min_age_hours_for_outbound:
        Minimum pallet age (hours) before it is eligible for outbound.
    """

    def __init__(
        self,
        num_rows: int,
        num_columns: int,
        num_levels: int,
        min_age_hours_for_outbound: float = 24.0,
    ) -> None:
        self.num_rows = num_rows
        self.num_columns = num_columns
        self.num_levels = num_levels
        self.min_age_hours = min_age_hours_for_outbound
        self._counter = 0
        self._slots: Dict[Tuple[int, int, int], AgedPalletSlot] = {}
        for r in range(1, num_rows + 1):
            for c in range(1, num_columns + 1):
                for lv in range(1, num_levels + 1):
                    self._slots[(r, c, lv)] = AgedPalletSlot(row=r, col=c, level=lv)

    # ------------------------------------------------------------------
    # Capacity helpers
    # ------------------------------------------------------------------

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

    def slot(self, row: int, col: int, level: int) -> AgedPalletSlot:
        return self._slots[(row, col, level)]

    # ------------------------------------------------------------------
    # Pre-fill (initial inventory already aged ≥ 24 h)
    # ------------------------------------------------------------------

    def prefill_aged_inventory(
        self,
        columns: List[int],
        put_time_hour: float = -24.0,
    ) -> int:
        """
        Fill all slots in the specified *columns* with aged pallets.

        Parameters
        ----------
        columns:
            Column numbers to fill.
        put_time_hour:
            Timestamp to assign every pre-filled pallet.  Must satisfy
            ``0 - put_time_hour >= min_age_hours_for_outbound`` so the
            pallets are eligible from hour 0.

        Returns
        -------
        int
            Number of pallets placed.
        """
        count = 0
        for col in columns:
            for row in range(1, self.num_rows + 1):
                for lv in range(1, self.num_levels + 1):
                    s = self._slots[(row, col, lv)]
                    if not s.is_occupied:
                        self._counter += 1
                        s.fill_order = self._counter
                        s.put_time_hour = put_time_hour
                        count += 1
        return count

    # ------------------------------------------------------------------
    # Inbound placement (column-order policy)
    # ------------------------------------------------------------------

    def inbound_put(
        self,
        current_hour: float,
        column_order: List[int],
    ) -> Optional[Tuple[int, int, int]]:
        """
        Place one inbound pallet following *column_order*.

        Scans columns in the given order, then rows front-to-back
        (row 1 first), then levels bottom-to-top.  Returns the
        ``(row, col, level)`` of the placed slot, or *None* if the
        specified columns are all full.
        """
        for col in column_order:
            for row in range(1, self.num_rows + 1):
                for lv in range(1, self.num_levels + 1):
                    s = self._slots[(row, col, lv)]
                    if not s.is_occupied:
                        self._counter += 1
                        s.fill_order = self._counter
                        s.put_time_hour = current_hour
                        return (row, col, lv)
        return None  # all target columns full

    # ------------------------------------------------------------------
    # Outbound retrieval (strict column scan + aging gate)
    # ------------------------------------------------------------------

    def outbound_get(
        self,
        current_hour: float,
        column_order: List[int],
    ) -> Optional[Tuple[int, int, int]]:
        """
        Retrieve and remove one pallet using a strict column scan.

        The scan visits columns in *column_order*.  Within each column it
        picks the **first** slot (row 1 → row N, level 1 → level N) that
        is occupied and whose age satisfies the minimum requirement.

        Parameters
        ----------
        current_hour:
            Current simulation time (hours).
        column_order:
            Column numbers to scan in order.

        Returns
        -------
        tuple or None
            ``(row, col, level)`` of the removed pallet, or *None* if no
            eligible pallet is found.
        """
        for col in column_order:
            for row in range(1, self.num_rows + 1):
                for lv in range(1, self.num_levels + 1):
                    s = self._slots[(row, col, lv)]
                    if s.is_occupied:
                        age = s.age_hours(current_hour)
                        if age is not None and age >= self.min_age_hours:
                            s.fill_order = None
                            s.put_time_hour = None
                            return (row, col, lv)
        return None  # no eligible pallet found

    def count_eligible_for_outbound(self, current_hour: float) -> int:
        """Return how many pallets currently satisfy the aging gate."""
        return sum(
            1
            for s in self._slots.values()
            if s.is_occupied
            and s.age_hours(current_hour) is not None
            and s.age_hours(current_hour) >= self.min_age_hours
        )


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

def simulate_alternating_buffer(
    storage: AlternatingBufferStorage,
    num_days: int,
    operating_hours_per_day: int,
    inbound_per_hour: int,
    outbound_per_hour: int,
) -> Dict:
    """
    Run the alternating buffer-column simulation for *num_days* days.

    Each day:
    1. Determine the column pattern (via day index).
    2. For each operating hour, alternate inbound/outbound:
       - Outbound uses strict column scan (column_order from pattern).
       - Inbound places into column_order from pattern.
    3. Log key metrics.

    Returns
    -------
    dict
        Summary metrics with keys:
        ``total_inbound``, ``total_outbound``, ``missed_outbound``,
        ``day_results`` (list of per-day dicts).
    """
    n_cols = storage.num_columns
    total_inbound = 0
    total_outbound = 0
    total_missed = 0
    day_results = []

    for day in range(1, num_days + 1):
        outbound_cols, inbound_cols = get_day_pattern(day, n_cols)
        day_outbound = 0
        day_inbound = 0
        day_missed = 0
        day_start_hour = (day - 1) * operating_hours_per_day

        logger.info(
            "Day %d | buffer_col=%s | outbound=%s | inbound=%s",
            day,
            n_cols if day % 2 == 1 else 1,
            outbound_cols,
            inbound_cols,
        )

        for hour_in_day in range(operating_hours_per_day):
            current_hour = day_start_hour + hour_in_day

            # Outbound first (strict scan)
            for _ in range(outbound_per_hour):
                result = storage.outbound_get(current_hour, outbound_cols)
                if result is not None:
                    day_outbound += 1
                else:
                    day_missed += 1
                    logger.debug(
                        "Hour %.1f: outbound missed (no eligible pallet)", current_hour
                    )

            # Inbound second
            for _ in range(inbound_per_hour):
                result = storage.inbound_put(current_hour, inbound_cols)
                if result is not None:
                    day_inbound += 1

        total_inbound += day_inbound
        total_outbound += day_outbound
        total_missed += day_missed

        day_results.append(
            {
                "day": day,
                "outbound_columns": outbound_cols,
                "inbound_columns": inbound_cols,
                "inbound": day_inbound,
                "outbound": day_outbound,
                "missed_outbound": day_missed,
                "end_occupancy": storage.occupied_count,
            }
        )
        logger.info(
            "Day %d summary | inbound=%d | outbound=%d | missed=%d | occupancy=%d/%d",
            day,
            day_inbound,
            day_outbound,
            day_missed,
            storage.occupied_count,
            storage.total_positions,
        )

    return {
        "total_inbound": total_inbound,
        "total_outbound": total_outbound,
        "missed_outbound": total_missed,
        "day_results": day_results,
    }
