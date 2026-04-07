"""
Tests for the alternating buffer column strategy with 24-hour aging constraint.

Covers:
  - Pallets with age < 24 h are not outbound-eligible.
  - Day 1 uses outbound order 10→1 and inbound 11→2.
  - Day 2 swaps to outbound 2→11 and inbound 1→10.
  - Initial fill produces 360 aged pallets and keeps buffer column empty.
  - simulate_alternating_buffer end-to-end for a 2-day run.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.alternating_buffer_strategy import (
    AgedPalletSlot,
    AlternatingBufferStorage,
    get_day_pattern,
    simulate_alternating_buffer,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def storage_11x12x3():
    """Standard 12-row × 11-column × 3-level storage, 24-h aging gate."""
    return AlternatingBufferStorage(
        num_rows=12,
        num_columns=11,
        num_levels=3,
        min_age_hours_for_outbound=24.0,
    )


# ---------------------------------------------------------------------------
# AgedPalletSlot
# ---------------------------------------------------------------------------

class TestAgedPalletSlot:
    def test_empty_slot_not_occupied(self):
        s = AgedPalletSlot(row=1, col=1, level=1)
        assert not s.is_occupied

    def test_occupied_slot(self):
        s = AgedPalletSlot(row=1, col=1, level=1, fill_order=1, put_time_hour=0.0)
        assert s.is_occupied

    def test_age_hours_empty(self):
        s = AgedPalletSlot(row=1, col=1, level=1)
        assert s.age_hours(10.0) is None

    def test_age_hours_calculation(self):
        s = AgedPalletSlot(row=1, col=1, level=1, fill_order=1, put_time_hour=-24.0)
        assert s.age_hours(0.0) == 24.0
        assert s.age_hours(6.0) == 30.0

    def test_pallet_below_24h_not_eligible(self):
        """Pallet placed at hour 5 should not be eligible at hour 20 (only 15 h old)."""
        s = AgedPalletSlot(row=1, col=1, level=1, fill_order=1, put_time_hour=5.0)
        age = s.age_hours(20.0)
        assert age is not None
        assert age < 24.0


# ---------------------------------------------------------------------------
# get_day_pattern
# ---------------------------------------------------------------------------

class TestGetDayPattern:
    def test_day1_outbound_order(self):
        """Day 1 outbound: columns 10 → 1."""
        outbound, _ = get_day_pattern(1, num_columns=11)
        assert outbound == list(range(10, 0, -1))  # [10, 9, …, 1]

    def test_day1_inbound_order(self):
        """Day 1 inbound: columns 11 → 2."""
        _, inbound = get_day_pattern(1, num_columns=11)
        assert inbound == list(range(11, 1, -1))  # [11, 10, …, 2]

    def test_day2_outbound_order(self):
        """Day 2 outbound: columns 2 → 11."""
        outbound, _ = get_day_pattern(2, num_columns=11)
        assert outbound == list(range(2, 12))  # [2, 3, …, 11]

    def test_day2_inbound_order(self):
        """Day 2 inbound: columns 1 → 10."""
        _, inbound = get_day_pattern(2, num_columns=11)
        assert inbound == list(range(1, 11))  # [1, 2, …, 10]

    def test_day3_repeats_day1(self):
        """Day 3 (odd) should repeat Day 1 pattern."""
        out1, in1 = get_day_pattern(1)
        out3, in3 = get_day_pattern(3)
        assert out1 == out3
        assert in1 == in3

    def test_day4_repeats_day2(self):
        """Day 4 (even) should repeat Day 2 pattern."""
        out2, in2 = get_day_pattern(2)
        out4, in4 = get_day_pattern(4)
        assert out2 == out4
        assert in2 == in4


# ---------------------------------------------------------------------------
# AlternatingBufferStorage – prefill
# ---------------------------------------------------------------------------

class TestPrefillAgedInventory:
    def test_prefill_360_pallets(self, storage_11x12x3):
        """Pre-fill columns 1–10 → exactly 360 aged pallets."""
        placed = storage_11x12x3.prefill_aged_inventory(
            columns=list(range(1, 11)),
            put_time_hour=-24.0,
        )
        assert placed == 360

    def test_prefill_buffer_column_empty(self, storage_11x12x3):
        """After pre-fill, column 11 must remain entirely empty."""
        storage_11x12x3.prefill_aged_inventory(
            columns=list(range(1, 11)),
            put_time_hour=-24.0,
        )
        for row in range(1, 13):
            for lv in range(1, 4):
                s = storage_11x12x3.slot(row, col=11, level=lv)
                assert not s.is_occupied, (
                    f"Expected column 11 empty but slot (row={row}, lv={lv}) is occupied"
                )

    def test_prefilled_pallets_are_aged(self, storage_11x12x3):
        """All pre-filled pallets must have age ≥ 24 h at hour 0."""
        storage_11x12x3.prefill_aged_inventory(
            columns=list(range(1, 11)),
            put_time_hour=-24.0,
        )
        for row in range(1, 13):
            for col in range(1, 11):
                for lv in range(1, 4):
                    s = storage_11x12x3.slot(row, col, lv)
                    assert s.is_occupied
                    age = s.age_hours(0.0)
                    assert age is not None and age >= 24.0, (
                        f"Pallet at ({row},{col},{lv}) has age={age} < 24"
                    )

    def test_total_positions(self, storage_11x12x3):
        assert storage_11x12x3.total_positions == 12 * 11 * 3  # 396

    def test_occupied_count_after_prefill(self, storage_11x12x3):
        storage_11x12x3.prefill_aged_inventory(
            columns=list(range(1, 11)),
            put_time_hour=-24.0,
        )
        assert storage_11x12x3.occupied_count == 360


# ---------------------------------------------------------------------------
# AlternatingBufferStorage – aging gate (outbound eligibility)
# ---------------------------------------------------------------------------

class TestAgingGate:
    def test_pallet_under_24h_not_eligible(self, storage_11x12x3):
        """A pallet placed at hour 0 must not be retrievable at hour 23."""
        outbound_cols, inbound_cols = get_day_pattern(1)
        storage_11x12x3.inbound_put(current_hour=0.0, column_order=inbound_cols)
        result = storage_11x12x3.outbound_get(current_hour=23.0, column_order=outbound_cols)
        assert result is None, "Pallet placed at hour 0 should not be eligible at hour 23"

    def test_pallet_exactly_24h_eligible(self, storage_11x12x3):
        """A pallet placed at hour 0 should become eligible at hour 24."""
        # Use a single-column order for both inbound and outbound to avoid
        # the Day 1 pattern mismatch (day 1 outbound is 10→1, inbound is 11→2,
        # so col 11 pallets are not in the day 1 outbound scan).
        loc = storage_11x12x3.inbound_put(current_hour=0.0, column_order=[5])
        assert loc is not None
        result = storage_11x12x3.outbound_get(current_hour=24.0, column_order=[5])
        assert result is not None, "Pallet placed at hour 0 should be eligible at hour 24"

    def test_prefilled_pallets_eligible_at_hour0(self, storage_11x12x3):
        """Pre-filled pallets (put_time=-24) must be eligible at hour 0."""
        storage_11x12x3.prefill_aged_inventory(
            columns=list(range(1, 11)),
            put_time_hour=-24.0,
        )
        outbound_cols, _ = get_day_pattern(1)
        result = storage_11x12x3.outbound_get(current_hour=0.0, column_order=outbound_cols)
        assert result is not None

    def test_count_eligible_all_prefilled(self, storage_11x12x3):
        """After pre-fill, all 360 pallets are eligible at hour 0."""
        storage_11x12x3.prefill_aged_inventory(
            columns=list(range(1, 11)),
            put_time_hour=-24.0,
        )
        assert storage_11x12x3.count_eligible_for_outbound(0.0) == 360

    def test_new_inbound_not_eligible_same_hour(self, storage_11x12x3):
        """A new pallet placed in hour 5 has age 0 – not eligible."""
        _, inbound_cols = get_day_pattern(1)
        storage_11x12x3.inbound_put(current_hour=5.0, column_order=inbound_cols)
        assert storage_11x12x3.count_eligible_for_outbound(5.0) == 0


# ---------------------------------------------------------------------------
# AlternatingBufferStorage – inbound column order
# ---------------------------------------------------------------------------

class TestInboundColumnOrder:
    def test_day1_inbound_fills_col11_first(self, storage_11x12x3):
        """Day 1 inbound order [11, 10, …, 2]: first slot should be in column 11."""
        _, inbound_cols = get_day_pattern(1, num_columns=11)
        loc = storage_11x12x3.inbound_put(current_hour=0.0, column_order=inbound_cols)
        assert loc is not None
        _, placed_col, _ = loc
        assert placed_col == 11

    def test_day2_inbound_fills_col1_first(self, storage_11x12x3):
        """Day 2 inbound order [1, 2, …, 10]: first slot should be in column 1."""
        _, inbound_cols = get_day_pattern(2, num_columns=11)
        loc = storage_11x12x3.inbound_put(current_hour=10.0, column_order=inbound_cols)
        assert loc is not None
        _, placed_col, _ = loc
        assert placed_col == 1


# ---------------------------------------------------------------------------
# AlternatingBufferStorage – outbound column order
# ---------------------------------------------------------------------------

class TestOutboundColumnOrder:
    def test_day1_outbound_from_col10_first(self, storage_11x12x3):
        """Day 1 outbound order [10, 9, …, 1]: retrieval must come from column 10."""
        storage_11x12x3.prefill_aged_inventory(
            columns=list(range(1, 11)),
            put_time_hour=-24.0,
        )
        outbound_cols, _ = get_day_pattern(1, num_columns=11)
        loc = storage_11x12x3.outbound_get(current_hour=0.0, column_order=outbound_cols)
        assert loc is not None
        _, retrieved_col, _ = loc
        assert retrieved_col == 10

    def test_day2_outbound_from_col2_first(self, storage_11x12x3):
        """Day 2 outbound order [2, 3, …, 11]: retrieval must come from column 2."""
        storage_11x12x3.prefill_aged_inventory(
            columns=list(range(1, 11)),
            put_time_hour=-24.0,
        )
        outbound_cols, _ = get_day_pattern(2, num_columns=11)
        loc = storage_11x12x3.outbound_get(current_hour=0.0, column_order=outbound_cols)
        assert loc is not None
        _, retrieved_col, _ = loc
        assert retrieved_col == 2


# ---------------------------------------------------------------------------
# simulate_alternating_buffer – 2-day end-to-end
# ---------------------------------------------------------------------------

class TestSimulateAlternatingBuffer:
    def _make_storage(self):
        s = AlternatingBufferStorage(
            num_rows=12, num_columns=11, num_levels=3,
            min_age_hours_for_outbound=24.0,
        )
        s.prefill_aged_inventory(columns=list(range(1, 11)), put_time_hour=-24.0)
        return s

    def test_2day_simulation_runs_without_error(self):
        storage = self._make_storage()
        result = simulate_alternating_buffer(
            storage=storage,
            num_days=2,
            operating_hours_per_day=10,
            inbound_per_hour=36,
            outbound_per_hour=36,
        )
        assert "day_results" in result
        assert len(result["day_results"]) == 2

    def test_day1_outbound_order_in_results(self):
        storage = self._make_storage()
        result = simulate_alternating_buffer(
            storage=storage,
            num_days=1,
            operating_hours_per_day=10,
            inbound_per_hour=36,
            outbound_per_hour=36,
        )
        dr = result["day_results"][0]
        assert dr["outbound_columns"] == list(range(10, 0, -1))
        assert dr["inbound_columns"] == list(range(11, 1, -1))

    def test_day2_outbound_order_in_results(self):
        storage = self._make_storage()
        result = simulate_alternating_buffer(
            storage=storage,
            num_days=2,
            operating_hours_per_day=10,
            inbound_per_hour=36,
            outbound_per_hour=36,
        )
        dr = result["day_results"][1]
        assert dr["outbound_columns"] == list(range(2, 12))
        assert dr["inbound_columns"] == list(range(1, 11))

    def test_day1_zero_missed_outbound(self):
        """With pre-aged inventory Day 1 outbound should have no missed retrievals."""
        storage = self._make_storage()
        result = simulate_alternating_buffer(
            storage=storage,
            num_days=1,
            operating_hours_per_day=10,
            inbound_per_hour=36,
            outbound_per_hour=36,
        )
        dr = result["day_results"][0]
        assert dr["missed_outbound"] == 0

    def test_total_inbound_equals_expected(self):
        """
        Total inbound is limited by available storage space.

        Day 1: 36/h × 10h = 360 pallets placed (cols 11→2, while outbound
               empties cols 10→1 one-by-one).  After day 1, cols 2-11 are
               full with day-1 stock; col 1 is empty.

        Day 2: Only 36 pallets can be placed (col 1 buffer), because none
               of the day-1 stock is aged ≥ 24 h yet, so outbound cannot
               free any space.  Storage becomes full after that.

        Expected total inbound = 360 (day 1) + 36 (day 2) = 396.
        """
        storage = self._make_storage()
        result = simulate_alternating_buffer(
            storage=storage,
            num_days=2,
            operating_hours_per_day=10,
            inbound_per_hour=36,
            outbound_per_hour=36,
        )
        # Day 1 must have placed exactly 360 pallets
        assert result["day_results"][0]["inbound"] == 360
        # Day 2 can only fill the one empty buffer column (36 slots)
        # before storage is full and outbound has no eligible pallets
        assert result["day_results"][1]["inbound"] == 36
        # Total inbound for both days
        assert result["total_inbound"] == 396
