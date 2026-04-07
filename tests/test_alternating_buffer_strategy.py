"""
Tests for the alternating buffer column strategy.

Covers:
  - AlternatingBufferStorage basic slot management
  - Default outbound_column_mode is "hard" when key is omitted
  - Hard mode only retrieves from preferred columns
  - Preference mode falls back to non-preferred columns when preferred are empty
  - Fallback direction matches the day outbound direction (descending/ascending)
  - run_alternating_buffer_simulation end-to-end for both modes
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.alternating_buffer_strategy import (
    AlternatingBufferStorage,
    BufferPallet,
    DayPattern,
    day_pattern_from_dict,
    run_alternating_buffer_simulation,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def small_storage_hard():
    """3-row × 4-column × 2-level storage, hard mode."""
    return AlternatingBufferStorage(
        num_rows=3,
        num_columns=4,
        num_levels=2,
        min_age_hours_for_outbound=24.0,
        outbound_column_mode="hard",
    )


@pytest.fixture
def small_storage_preference():
    """3-row × 4-column × 2-level storage, preference mode."""
    return AlternatingBufferStorage(
        num_rows=3,
        num_columns=4,
        num_levels=2,
        min_age_hours_for_outbound=24.0,
        outbound_column_mode="preference",
    )


@pytest.fixture
def full_hard_config():
    """Minimal config dict for run_alternating_buffer_simulation (hard mode)."""
    return {
        "Ground_Stacking_Configuration": {"Rows": 12, "Columns": 11, "Levels": 3},
        "Throughput_Configuration": {
            "Total_Daily_Inbound_Pallets": 360,
            "Operating_Hours": 10,
        },
        "Shuffle_Configuration": {
            "strategy": "alternating_buffer_column_24h",
            "min_age_hours_for_outbound": 24,
            "outbound_column_mode": "hard",
            "initial_fill_columns": list(range(1, 11)),
            "day_patterns": [
                {
                    "inbound_column_order": list(range(11, 1, -1)),
                    "outbound_column_order": list(range(10, 0, -1)),
                },
                {
                    "inbound_column_order": list(range(1, 11)),
                    "outbound_column_order": list(range(2, 12)),
                },
            ],
        },
    }


@pytest.fixture
def full_preference_config(full_hard_config):
    """Same as hard config but with outbound_column_mode = preference."""
    import copy
    cfg = copy.deepcopy(full_hard_config)
    cfg["Shuffle_Configuration"]["outbound_column_mode"] = "preference"
    return cfg


# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------

class TestAlternatingBufferStorageConstruction:
    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="outbound_column_mode"):
            AlternatingBufferStorage(
                num_rows=2, num_columns=2, num_levels=1,
                outbound_column_mode="unknown",
            )

    def test_default_mode_is_hard_when_mode_not_specified(self):
        """Constructing without specifying mode should default to 'hard'."""
        storage = AlternatingBufferStorage(num_rows=2, num_columns=2, num_levels=1)
        assert storage.outbound_column_mode == "hard"

    def test_total_positions(self, small_storage_hard):
        assert small_storage_hard.total_positions == 3 * 4 * 2

    def test_initial_occupancy_zero(self, small_storage_hard):
        assert small_storage_hard.occupied_count == 0


# ---------------------------------------------------------------------------
# Default mode = "hard"
# ---------------------------------------------------------------------------

class TestDefaultModeIsHard:
    def test_config_without_mode_key_uses_hard(self):
        """When outbound_column_mode is absent from Shuffle_Configuration, default is hard."""
        config = {
            "Ground_Stacking_Configuration": {"Rows": 3, "Columns": 4, "Levels": 1},
            "Throughput_Configuration": {
                "Total_Daily_Inbound_Pallets": 4,
                "Operating_Hours": 1,
            },
            "Shuffle_Configuration": {
                "strategy": "alternating_buffer_column_24h",
                # outbound_column_mode intentionally omitted
                "initial_fill_columns": [1, 2, 3],
                "day_patterns": [
                    {
                        "inbound_column_order": [4, 3, 2],
                        "outbound_column_order": [3, 2, 1],
                    }
                ],
            },
        }
        # Should not raise; mode defaults to "hard"
        result = run_alternating_buffer_simulation(config, num_days=1)
        assert isinstance(result, dict)
        assert "total_outbound" in result

    def test_storage_default_mode_is_hard(self):
        storage = AlternatingBufferStorage(num_rows=2, num_columns=2, num_levels=1)
        assert storage.outbound_column_mode == "hard"


# ---------------------------------------------------------------------------
# Prefill
# ---------------------------------------------------------------------------

class TestPrefill:
    def test_prefill_fills_requested_columns(self, small_storage_hard):
        count = small_storage_hard.prefill_columns([1, 2], put_time_hour=-24.0)
        # 3 rows * 2 columns * 2 levels = 12
        assert count == 12
        assert small_storage_hard.occupied_count == 12

    def test_prefill_other_columns_remain_empty(self, small_storage_hard):
        small_storage_hard.prefill_columns([1, 2], put_time_hour=-24.0)
        for row in range(1, 4):
            for lv in range(1, 3):
                assert small_storage_hard.get_pallet(row, 3, lv) is None
                assert small_storage_hard.get_pallet(row, 4, lv) is None

    def test_prefill_pallets_are_aged(self, small_storage_hard):
        small_storage_hard.prefill_columns([1], put_time_hour=-24.0)
        # All pallets should have age >= 24 at hour 0
        for row in range(1, 4):
            for lv in range(1, 3):
                pallet = small_storage_hard.get_pallet(row, 1, lv)
                assert pallet is not None
                assert pallet.age_hours(0) >= 24.0


# ---------------------------------------------------------------------------
# Inbound placement
# ---------------------------------------------------------------------------

class TestInboundPut:
    def test_inbound_places_in_first_available_slot(self, small_storage_hard):
        ok = small_storage_hard.inbound_put([1, 2, 3, 4], current_hour=0)
        assert ok is True
        assert small_storage_hard.occupied_count == 1

    def test_inbound_fills_column_order(self, small_storage_hard):
        # Fill 6 pallets; should fill col 1 completely (3 rows × 2 levels = 6) then spill to col 2
        for _ in range(6):
            small_storage_hard.inbound_put([1, 2], current_hour=0)
        # Col 1 should be full
        for row in range(1, 4):
            for lv in range(1, 3):
                assert small_storage_hard.is_occupied(row, 1, lv)
        # Col 2 should be empty
        assert small_storage_hard.occupied_count == 6

    def test_inbound_returns_false_when_full(self):
        storage = AlternatingBufferStorage(num_rows=1, num_columns=1, num_levels=1)
        storage.inbound_put([1], current_hour=0)
        ok = storage.inbound_put([1], current_hour=0)
        assert ok is False


# ---------------------------------------------------------------------------
# Hard mode: outbound only uses preferred columns
# ---------------------------------------------------------------------------

class TestHardModeOutbound:
    def test_hard_mode_returns_none_when_preferred_empty(self, small_storage_hard):
        # Pre-fill col 3 and 4, preferred = [1, 2]
        small_storage_hard.prefill_columns([3, 4], put_time_hour=-24.0)
        result = small_storage_hard.outbound_get(
            preferred_column_order=[1, 2], current_hour=0
        )
        assert result is None

    def test_hard_mode_retrieves_from_preferred(self, small_storage_hard):
        small_storage_hard.prefill_columns([1, 3], put_time_hour=-24.0)
        result = small_storage_hard.outbound_get(
            preferred_column_order=[1, 2], current_hour=0
        )
        assert result is not None
        assert result[1] == 1  # column index

    def test_hard_mode_does_not_fall_back(self, small_storage_hard):
        """When preferred cols are empty, hard mode returns None even if other cols have stock."""
        small_storage_hard.prefill_columns([3, 4], put_time_hour=-24.0)
        result = small_storage_hard.outbound_get(
            preferred_column_order=[1, 2], current_hour=0
        )
        assert result is None
        # Col 3 and 4 still full
        assert small_storage_hard.occupied_count == 12


# ---------------------------------------------------------------------------
# Preference mode: fallback to non-preferred columns
# ---------------------------------------------------------------------------

class TestPreferenceModeOutbound:
    def test_preference_mode_uses_preferred_first(self, small_storage_preference):
        small_storage_preference.prefill_columns([1, 2, 3], put_time_hour=-24.0)
        result = small_storage_preference.outbound_get(
            preferred_column_order=[1, 2], current_hour=0
        )
        assert result is not None
        assert result[1] in (1, 2)

    def test_preference_mode_falls_back_when_preferred_empty(self, small_storage_preference):
        """Preference mode retrieves from non-preferred columns if preferred are empty."""
        # Only fill col 3 and 4 (non-preferred)
        small_storage_preference.prefill_columns([3, 4], put_time_hour=-24.0)
        result = small_storage_preference.outbound_get(
            preferred_column_order=[1, 2], current_hour=0
        )
        assert result is not None
        assert result[1] in (3, 4)

    def test_preference_mode_decrements_count_on_fallback(self, small_storage_preference):
        small_storage_preference.prefill_columns([3, 4], put_time_hour=-24.0)
        before = small_storage_preference.occupied_count
        small_storage_preference.outbound_get(
            preferred_column_order=[1, 2], current_hour=0
        )
        assert small_storage_preference.occupied_count == before - 1

    def test_preference_mode_returns_none_when_all_empty(self, small_storage_preference):
        result = small_storage_preference.outbound_get(
            preferred_column_order=[1, 2], current_hour=0
        )
        assert result is None

    def test_preference_mode_returns_none_when_none_aged(self, small_storage_preference):
        """Even in preference mode, unaged pallets in all columns → None."""
        # Place pallets via inbound_put at current_hour=0; check at current_hour=1
        for col in [1, 2, 3, 4]:
            for _ in range(3):  # fill a few slots per column
                small_storage_preference.inbound_put([col], current_hour=0.0)
        # current_hour = 1 → age = 1h < 24h
        result = small_storage_preference.outbound_get(
            preferred_column_order=[1, 2], current_hour=1.0
        )
        assert result is None


# ---------------------------------------------------------------------------
# Fallback direction matches day outbound direction
# ---------------------------------------------------------------------------

class TestFallbackDirection:
    def test_descending_preferred_yields_descending_fallback(self, small_storage_preference):
        """
        preferred_cols descending (e.g. 4→3) → fallback remaining cols also descending.
        Storage has 4 columns; preferred=[4,3], fallback should be [2,1].
        """
        # Only fill cols 1 and 2 (will be fallback)
        small_storage_preference.prefill_columns([1, 2], put_time_hour=-24.0)
        fallback = small_storage_preference._fallback_column_order([4, 3])
        assert fallback == [2, 1]

    def test_ascending_preferred_yields_ascending_fallback(self, small_storage_preference):
        """
        preferred_cols ascending (e.g. 1→2) → fallback remaining cols also ascending.
        Storage has 4 columns; preferred=[1,2], fallback should be [3,4].
        """
        fallback = small_storage_preference._fallback_column_order([1, 2])
        assert fallback == [3, 4]

    def test_fallback_retrieval_follows_descending_direction(self, small_storage_preference):
        """
        Day 1 outbound order is descending [4,3]; fallback should scan [2,1].
        Only col 1 and 2 are filled; preference mode should retrieve from col 2 first.
        """
        small_storage_preference.prefill_columns([1, 2], put_time_hour=-24.0)
        result = small_storage_preference.outbound_get(
            preferred_column_order=[4, 3], current_hour=0
        )
        # Descending fallback: scan col 2 before col 1
        assert result is not None
        assert result[1] == 2

    def test_fallback_retrieval_follows_ascending_direction(self, small_storage_preference):
        """
        Day 2 outbound order is ascending [1,2]; fallback should scan [3,4].
        Only col 3 and 4 are filled; preference mode should retrieve from col 3 first.
        """
        small_storage_preference.prefill_columns([3, 4], put_time_hour=-24.0)
        result = small_storage_preference.outbound_get(
            preferred_column_order=[1, 2], current_hour=0
        )
        # Ascending fallback: scan col 3 before col 4
        assert result is not None
        assert result[1] == 3


# ---------------------------------------------------------------------------
# Age gate enforcement
# ---------------------------------------------------------------------------

class TestAgeGate:
    def test_unaged_pallet_not_retrieved(self, small_storage_hard):
        small_storage_hard.inbound_put([1], current_hour=0)
        # Only 1 hour has passed; pallet age = 1h < 24h
        result = small_storage_hard.outbound_get(
            preferred_column_order=[1], current_hour=1.0
        )
        assert result is None

    def test_aged_pallet_is_retrieved(self, small_storage_hard):
        small_storage_hard.inbound_put([1], current_hour=0)
        result = small_storage_hard.outbound_get(
            preferred_column_order=[1], current_hour=25.0
        )
        assert result is not None


# ---------------------------------------------------------------------------
# DayPattern helpers
# ---------------------------------------------------------------------------

class TestDayPatternFromDict:
    def test_round_trip(self):
        d = {
            "inbound_column_order": [11, 10, 9],
            "outbound_column_order": [10, 9, 8],
        }
        p = day_pattern_from_dict(d)
        assert p.inbound_column_order == [11, 10, 9]
        assert p.outbound_column_order == [10, 9, 8]


# ---------------------------------------------------------------------------
# End-to-end simulation
# ---------------------------------------------------------------------------

class TestRunAlternatingBufferSimulation:
    def test_hard_mode_runs_without_error(self, full_hard_config):
        result = run_alternating_buffer_simulation(full_hard_config, num_days=2)
        assert "total_inbound" in result
        assert "total_outbound" in result
        assert "total_missed_outbound" in result
        assert len(result["day_results"]) == 2

    def test_preference_mode_runs_without_error(self, full_preference_config):
        result = run_alternating_buffer_simulation(full_preference_config, num_days=2)
        assert "total_inbound" in result
        assert len(result["day_results"]) == 2

    def test_preference_has_fewer_or_equal_missed_than_hard(
        self, full_hard_config, full_preference_config
    ):
        """
        Preference mode should satisfy the same or more outbound demand than hard mode,
        because it can fall back to non-preferred columns.
        """
        hard_result = run_alternating_buffer_simulation(full_hard_config, num_days=2)
        pref_result = run_alternating_buffer_simulation(full_preference_config, num_days=2)
        assert pref_result["total_missed_outbound"] <= hard_result["total_missed_outbound"]

    def test_missing_day_patterns_raises(self, full_hard_config):
        import copy
        cfg = copy.deepcopy(full_hard_config)
        cfg["Shuffle_Configuration"]["day_patterns"] = []
        with pytest.raises(ValueError, match="day_patterns"):
            run_alternating_buffer_simulation(cfg, num_days=1)

    def test_deterministic_results(self, full_hard_config):
        """Simulation is deterministic: two runs with same config produce identical output."""
        r1 = run_alternating_buffer_simulation(full_hard_config, num_days=2)
        r2 = run_alternating_buffer_simulation(full_hard_config, num_days=2)
        assert r1["total_outbound"] == r2["total_outbound"]
        assert r1["total_missed_outbound"] == r2["total_missed_outbound"]

    def test_day1_outbound_works_with_prefilled_aged_pallets(self, full_hard_config):
        """Day 1 outbound should succeed because initial fill uses pre-aged pallets."""
        result = run_alternating_buffer_simulation(full_hard_config, num_days=1)
        day1 = result["day_results"][0]
        assert day1["outbound"] > 0

    def test_avg_occupancy_between_0_and_1(self, full_hard_config):
        result = run_alternating_buffer_simulation(full_hard_config, num_days=2)
        assert 0.0 <= result["avg_occupancy"] <= 1.0
