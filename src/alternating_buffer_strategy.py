"""
Alternating Buffer Column strategy for ground-stacking storage.

Layout: Rows x Columns x Levels.
One column is kept empty at the start of each day as a buffer.
The buffer column alternates every day (e.g., col 11 on Day 1, col 1 on Day 2).

Day patterns are defined in the config under Shuffle_Configuration.day_patterns.
Each pattern specifies:
  - inbound_column_order: ordered list of columns for inbound placement
  - outbound_column_order: ordered list of columns for outbound retrieval

Outbound gate: a pallet is only eligible if age_hours >= min_age_hours_for_outbound.

outbound_column_mode:
  - "hard"       (default): outbound only scans columns in the day's outbound_column_order.
  - "preference": outbound first tries columns in outbound_column_order; if demand is not
                  met, falls back to remaining columns scanned in the same direction
                  (ascending if preferred list is ascending, descending otherwise).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class BufferPallet:
    """One pallet occupying a storage slot."""
    row: int
    col: int
    level: int
    put_time_hour: float  # simulation hour when the pallet was stored

    def age_hours(self, current_hour: float) -> float:
        return current_hour - self.put_time_hour


class AlternatingBufferStorage:
    """
    Ground-stacking storage model for the alternating buffer column strategy.

    Coordinates (row, col, level) are 1-based.
    Rows run from 1 (front/entry) to ``num_rows`` (back).
    Columns run from 1 to ``num_columns``.
    Levels run from 1 (bottom) to ``num_levels`` (top).

    Within a column lane (same col, same level), pallets at lower row numbers
    must be moved before a pallet at a higher row number can be accessed.
    Inbound always places into the first vacant slot according to the day's
    inbound_column_order (column-major: fill a column top-to-bottom before
    moving to the next column).
    """

    def __init__(
        self,
        num_rows: int,
        num_columns: int,
        num_levels: int,
        min_age_hours_for_outbound: float = 24.0,
        outbound_column_mode: str = "hard",
    ):
        if outbound_column_mode not in ("hard", "preference"):
            raise ValueError(
                f"outbound_column_mode must be 'hard' or 'preference', got {outbound_column_mode!r}"
            )
        self.num_rows = num_rows
        self.num_columns = num_columns
        self.num_levels = num_levels
        self.min_age_hours_for_outbound = min_age_hours_for_outbound
        self.outbound_column_mode = outbound_column_mode

        # Slot occupancy: key -> pallet or None
        self._slots: Dict[Tuple[int, int, int], Optional[BufferPallet]] = {}
        for r in range(1, num_rows + 1):
            for c in range(1, num_columns + 1):
                for lv in range(1, num_levels + 1):
                    self._slots[(r, c, lv)] = None

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def total_positions(self) -> int:
        return self.num_rows * self.num_columns * self.num_levels

    @property
    def occupied_count(self) -> int:
        return sum(1 for p in self._slots.values() if p is not None)

    @property
    def occupancy_fraction(self) -> float:
        return self.occupied_count / max(1, self.total_positions)

    def is_occupied(self, row: int, col: int, level: int) -> bool:
        return self._slots[(row, col, level)] is not None

    def get_pallet(self, row: int, col: int, level: int) -> Optional[BufferPallet]:
        return self._slots[(row, col, level)]

    # ------------------------------------------------------------------
    # Initial fill (pre-age pallets to make them immediately eligible)
    # ------------------------------------------------------------------

    def prefill_columns(
        self,
        columns: List[int],
        put_time_hour: float = -24.0,
    ) -> int:
        """
        Fill the given columns completely with pallets aged at ``put_time_hour``.
        Fills level-by-level (level 1 first), row-by-row (row 1 first) within
        each column.

        A small stagger (``-count``) is applied so that each pallet has a
        unique timestamp.  Row 1 (front) gets the most recent pre-fill
        timestamp; higher rows (back) get progressively older timestamps,
        which reflects FIFO pre-fill: back-row pallets arrived earlier.

        Returns the number of pallets placed.
        """
        count = 0
        total = sum(
            1
            for col in columns
            for _ in range(self.num_rows * self.num_levels)
        )
        for col in columns:
            for row in range(1, self.num_rows + 1):
                for lv in range(1, self.num_levels + 1):
                    if self._slots[(row, col, lv)] is None:
                        # Earlier rows (row 1) get the newest pre-fill timestamp;
                        # later rows (row N) get progressively older timestamps.
                        slot_put_time = put_time_hour - (total - 1 - count)
                        self._slots[(row, col, lv)] = BufferPallet(
                            row=row,
                            col=col,
                            level=lv,
                            put_time_hour=slot_put_time,
                        )
                        count += 1
        return count

    # ------------------------------------------------------------------
    # Inbound placement
    # ------------------------------------------------------------------

    def inbound_put(
        self,
        inbound_column_order: List[int],
        current_hour: float,
    ) -> bool:
        """
        Place one pallet according to ``inbound_column_order``.
        Fills each column front-to-back (row 1 → num_rows), bottom-to-top
        (level 1 → num_levels) before moving to the next column.
        Returns True if a slot was found, False if storage is full.
        """
        for col in inbound_column_order:
            for row in range(1, self.num_rows + 1):
                for lv in range(1, self.num_levels + 1):
                    if self._slots[(row, col, lv)] is None:
                        self._slots[(row, col, lv)] = BufferPallet(
                            row=row,
                            col=col,
                            level=lv,
                            put_time_hour=current_hour,
                        )
                        return True
        return False

    # ------------------------------------------------------------------
    # Outbound retrieval
    # ------------------------------------------------------------------

    def _first_eligible_in_column(
        self,
        col: int,
        current_hour: float,
    ) -> Optional[Tuple[int, int, int]]:
        """
        Return the (row, col, level) of the first accessible, aged pallet in
        ``col``, or None.

        Accessible means no other pallet occupies a lower row in the same
        (col, level) lane.  We scan row 1 → num_rows; the first row that has
        an occupied slot at *any* level is the front of that lane.  A pallet
        is eligible if its age >= min_age_hours_for_outbound.

        We scan levels 1 → num_levels for each row.
        """
        for row in range(1, self.num_rows + 1):
            for lv in range(1, self.num_levels + 1):
                pallet = self._slots[(row, col, lv)]
                if pallet is not None:
                    if pallet.age_hours(current_hour) >= self.min_age_hours_for_outbound:
                        return (row, col, lv)
                    # Pallet exists but not aged enough — still blocks deeper pallets
                    # in the same (col, level) lane, but we continue scanning the
                    # same row's other levels and then deeper rows.
        return None

    def _fallback_column_order(self, preferred_cols: List[int]) -> List[int]:
        """
        Compute the fallback column scan order (columns not in preferred_cols)
        using the same direction as preferred_cols.

        Direction is determined by whether the list is ascending or descending:
          - descending → sort remaining columns descending
          - ascending  → sort remaining columns ascending
        """
        preferred_set = set(preferred_cols)
        remaining = [c for c in range(1, self.num_columns + 1) if c not in preferred_set]
        if not remaining:
            return []
        # Determine direction from preferred list
        if len(preferred_cols) >= 2 and preferred_cols[0] > preferred_cols[-1]:
            # descending
            remaining.sort(reverse=True)
        else:
            # ascending (or single-element preferred list → default ascending)
            remaining.sort()
        return remaining

    def outbound_get(
        self,
        preferred_column_order: List[int],
        current_hour: float,
    ) -> Optional[Tuple[int, int, int]]:
        """
        Retrieve one eligible pallet.

        In ``hard`` mode: only scan ``preferred_column_order``.
        In ``preference`` mode: scan preferred first; if nothing found, scan
        fallback columns in the same direction.

        Returns the (row, col, level) key of the retrieved pallet, or None if
        no eligible pallet exists.
        """
        # Try preferred columns
        for col in preferred_column_order:
            slot = self._first_eligible_in_column(col, current_hour)
            if slot is not None:
                self._slots[slot] = None
                return slot

        if self.outbound_column_mode == "preference":
            fallback = self._fallback_column_order(preferred_column_order)
            for col in fallback:
                slot = self._first_eligible_in_column(col, current_hour)
                if slot is not None:
                    self._slots[slot] = None
                    return slot

        return None


# ---------------------------------------------------------------------------
# Day pattern helper
# ---------------------------------------------------------------------------

@dataclass
class DayPattern:
    """Inbound and outbound column orders for one day-type."""
    inbound_column_order: List[int]
    outbound_column_order: List[int]


def day_pattern_from_dict(d: dict) -> DayPattern:
    return DayPattern(
        inbound_column_order=list(d["inbound_column_order"]),
        outbound_column_order=list(d["outbound_column_order"]),
    )


# ---------------------------------------------------------------------------
# Top-level simulation runner
# ---------------------------------------------------------------------------

def run_alternating_buffer_simulation(
    config: dict,
    num_days: int = 2,
    verbose: bool = False,
) -> dict:
    """
    Run a multi-day alternating buffer column simulation.

    Parameters
    ----------
    config:
        Full simulator config dict.  Must contain a ``Shuffle_Configuration``
        section.
    num_days:
        Number of days to simulate.
    verbose:
        If True, print hourly progress.

    Returns
    -------
    dict with keys:
        total_inbound, total_outbound, total_missed_outbound,
        avg_occupancy, day_results (list of per-day dicts)
    """
    shuffle_cfg = config.get("Shuffle_Configuration", {})
    rows = config["Ground_Stacking_Configuration"].get("Rows", 12)
    columns = config["Ground_Stacking_Configuration"].get("Columns", 11)
    levels = config["Ground_Stacking_Configuration"].get("Levels", 3)
    min_age = shuffle_cfg.get("min_age_hours_for_outbound", 24)
    mode = shuffle_cfg.get("outbound_column_mode", "hard")
    operating_hours = config["Throughput_Configuration"].get("Operating_Hours", 10)
    daily_inbound = config["Throughput_Configuration"].get("Total_Daily_Inbound_Pallets", 360)
    # Round to nearest integer; any remainder is silently absorbed each hour.
    pallets_per_hour = round(daily_inbound / operating_hours)

    day_patterns_raw = shuffle_cfg.get("day_patterns", [])
    if not day_patterns_raw:
        raise ValueError("Shuffle_Configuration.day_patterns must not be empty")
    day_patterns = [day_pattern_from_dict(p) for p in day_patterns_raw]

    storage = AlternatingBufferStorage(
        num_rows=rows,
        num_columns=columns,
        num_levels=levels,
        min_age_hours_for_outbound=min_age,
        outbound_column_mode=mode,
    )

    # Pre-fill: fill all columns except the first day's buffer column
    initial_fill_columns_cfg = shuffle_cfg.get("initial_fill_columns")
    if initial_fill_columns_cfg is not None:
        storage.prefill_columns(initial_fill_columns_cfg, put_time_hour=-24.0)
    else:
        # Default: fill all columns not in Day 1's inbound list that are also
        # not the buffer column.  Simplest: fill columns present in day 1
        # outbound order (they are the non-buffer columns).
        outbound_day1 = day_patterns[0].outbound_column_order
        storage.prefill_columns(outbound_day1, put_time_hour=-24.0)

    total_inbound = 0
    total_outbound = 0
    total_missed_outbound = 0
    day_results = []

    for day_index in range(num_days):
        pattern = day_patterns[day_index % len(day_patterns)]
        day_inbound = 0
        day_outbound = 0
        day_missed = 0
        occupancy_sum = 0.0

        for hour_in_day in range(operating_hours):
            current_hour = day_index * operating_hours + hour_in_day

            # Outbound first
            for _ in range(pallets_per_hour):
                result = storage.outbound_get(
                    preferred_column_order=pattern.outbound_column_order,
                    current_hour=current_hour,
                )
                if result is not None:
                    day_outbound += 1
                else:
                    day_missed += 1

            # Then inbound
            for _ in range(pallets_per_hour):
                placed = storage.inbound_put(
                    inbound_column_order=pattern.inbound_column_order,
                    current_hour=current_hour,
                )
                if placed:
                    day_inbound += 1

            occupancy_sum += storage.occupancy_fraction

            if verbose:
                print(
                    f"Day {day_index+1} Hour {hour_in_day+1:2d}: "
                    f"In={day_inbound} Out={day_outbound} Missed={day_missed} "
                    f"Occ={storage.occupancy_fraction*100:.1f}%"
                )

        day_results.append(
            {
                "day": day_index + 1,
                "inbound": day_inbound,
                "outbound": day_outbound,
                "missed_outbound": day_missed,
                "avg_occupancy": occupancy_sum / operating_hours,
            }
        )
        total_inbound += day_inbound
        total_outbound += day_outbound
        total_missed_outbound += day_missed

    avg_occ = sum(d["avg_occupancy"] for d in day_results) / max(1, len(day_results))
    return {
        "total_inbound": total_inbound,
        "total_outbound": total_outbound,
        "total_missed_outbound": total_missed_outbound,
        "avg_occupancy": avg_occ,
        "day_results": day_results,
    }
