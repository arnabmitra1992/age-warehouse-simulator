"""
Unit tests for the lane-sequenced block storage policy.

Covers:
  - Inbound fill order: column 1 completely filled before column 2.
  - Outbound drain order: column 1 drained first; within a column rows
    front-to-back and levels top-down.
  - No shuffling: avg_shuffles_per_outbound always returns 0 and blocking_pallets
    always returns [].
  - Backward compatibility: default simulator config still uses FIFO/shuffle mode.
  - Simulator integration: lane_sequence config produces 0 shuffling fleet.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.lane_sequence_storage import LaneSequenceStorageModel


# ---------------------------------------------------------------------------
# Inbound fill order
# ---------------------------------------------------------------------------

class TestLaneSequenceInbound:
    def test_first_put_goes_to_col1_row1_level1(self):
        m = LaneSequenceStorageModel(num_rows=3, num_columns=3, num_levels=2)
        pos = m.inbound_put()
        assert pos == (1, 1, 1)

    def test_second_put_goes_to_col1_row1_level2(self):
        m = LaneSequenceStorageModel(num_rows=3, num_columns=3, num_levels=2)
        m.inbound_put()
        pos = m.inbound_put()
        assert pos == (1, 1, 2)

    def test_fills_col1_before_col2(self):
        """Column 1 (all rows × all levels) must be full before column 2 gets any pallet."""
        num_rows, num_cols, num_levels = 4, 3, 2
        m = LaneSequenceStorageModel(num_rows=num_rows, num_columns=num_cols, num_levels=num_levels)
        slots_per_col = num_rows * num_levels  # 8

        for _ in range(slots_per_col):
            pos = m.inbound_put()
            assert pos is not None
            assert pos[1] == 1, f"Expected col 1 during initial fill, got {pos}"

        # Next pallet should go to column 2
        pos = m.inbound_put()
        assert pos is not None
        assert pos[1] == 2

    def test_within_col_rows_filled_front_to_back(self):
        m = LaneSequenceStorageModel(num_rows=5, num_columns=2, num_levels=1)
        rows_seen = []
        for _ in range(5):
            pos = m.inbound_put()
            rows_seen.append(pos[0])
        assert rows_seen == [1, 2, 3, 4, 5]

    def test_within_row_levels_filled_bottom_to_top(self):
        m = LaneSequenceStorageModel(num_rows=1, num_columns=1, num_levels=4)
        levels_seen = []
        for _ in range(4):
            pos = m.inbound_put()
            levels_seen.append(pos[2])
        assert levels_seen == [1, 2, 3, 4]

    def test_returns_none_when_full(self):
        m = LaneSequenceStorageModel(num_rows=2, num_columns=2, num_levels=2)
        for _ in range(8):
            m.inbound_put()
        assert m.inbound_put() is None

    def test_occupied_count_increments(self):
        m = LaneSequenceStorageModel(num_rows=3, num_columns=3, num_levels=1)
        for i in range(1, 6):
            m.inbound_put()
            assert m.occupied_count == i

    def test_occupancy_fraction_correct(self):
        m = LaneSequenceStorageModel(num_rows=4, num_columns=1, num_levels=1)
        m.inbound_put()
        m.inbound_put()
        assert abs(m.occupancy_fraction - 0.5) < 1e-9


# ---------------------------------------------------------------------------
# Outbound drain order
# ---------------------------------------------------------------------------

class TestLaneSequenceOutbound:
    def test_drains_col1_before_col2(self):
        """After filling two columns, outbound should drain col 1 first."""
        num_rows, num_cols, num_levels = 2, 3, 1
        m = LaneSequenceStorageModel(num_rows=num_rows, num_columns=num_cols, num_levels=num_levels)
        # Fill col 1 and col 2 completely
        for _ in range(num_rows * 2):
            m.inbound_put()

        for _ in range(num_rows):
            pos = m.outbound_get()
            assert pos is not None
            assert pos[1] == 1, f"Expected col 1 drain, got {pos}"

        # Next retrieval should come from column 2
        pos = m.outbound_get()
        assert pos is not None
        assert pos[1] == 2

    def test_within_col_drains_front_row_first(self):
        m = LaneSequenceStorageModel(num_rows=3, num_columns=1, num_levels=1)
        for _ in range(3):
            m.inbound_put()
        rows_retrieved = [m.outbound_get()[0] for _ in range(3)]
        assert rows_retrieved == [1, 2, 3]

    def test_within_row_drains_top_level_first(self):
        """Within a row, levels must be drained top-down (num_levels → 1)."""
        m = LaneSequenceStorageModel(num_rows=1, num_columns=1, num_levels=4)
        for _ in range(4):
            m.inbound_put()
        levels_retrieved = [m.outbound_get()[2] for _ in range(4)]
        assert levels_retrieved == [4, 3, 2, 1]

    def test_returns_none_when_empty(self):
        m = LaneSequenceStorageModel(num_rows=2, num_columns=2, num_levels=1)
        assert m.outbound_get() is None

    def test_occupied_count_decrements(self):
        m = LaneSequenceStorageModel(num_rows=3, num_columns=1, num_levels=1)
        for _ in range(3):
            m.inbound_put()
        for i in range(2, -1, -1):
            m.outbound_get()
            assert m.occupied_count == i

    def test_full_fill_then_drain_cycle(self):
        m = LaneSequenceStorageModel(num_rows=3, num_columns=2, num_levels=2)
        total = m.total_positions
        for _ in range(total):
            m.inbound_put()
        assert m.occupancy_fraction == 1.0
        for _ in range(total):
            assert m.outbound_get() is not None
        assert m.occupied_count == 0
        assert m.outbound_get() is None


# ---------------------------------------------------------------------------
# No shuffling
# ---------------------------------------------------------------------------

class TestLaneSequenceNoShuffling:
    def test_blocking_pallets_always_empty(self):
        m = LaneSequenceStorageModel(num_rows=5, num_columns=3, num_levels=2)
        for _ in range(10):
            m.inbound_put()
        # Check various positions
        assert m.blocking_pallets(3, 1, 1) == []
        assert m.blocking_pallets(5, 2, 2) == []
        assert m.blocking_pallets(1, 1, 1) == []

    def test_average_shuffles_per_outbound_is_zero(self):
        m = LaneSequenceStorageModel(num_rows=5, num_columns=4, num_levels=3)
        for _ in range(30):
            m.inbound_put()
        assert m.average_shuffles_per_outbound() == 0.0

    def test_avg_shuffles_method_alias_is_zero(self):
        m = LaneSequenceStorageModel(num_rows=5, num_columns=4, num_levels=3)
        assert m.avg_shuffles_per_outbound() == 0.0

    def test_shuffles_zero_on_empty_model(self):
        m = LaneSequenceStorageModel(num_rows=2, num_columns=2, num_levels=2)
        assert m.average_shuffles_per_outbound() == 0.0


# ---------------------------------------------------------------------------
# Simulator integration
# ---------------------------------------------------------------------------

class TestSimulatorIntegrationLaneSequence:
    """Verify that WarehouseSimulator produces 0 shuffling fleet in lane_sequence mode."""

    @pytest.fixture
    def base_config(self):
        return {
            "AGV_Specifications": {
                "XQE_122": {},
                "XPL_201": {},
                "Turn_90_degrees_s": 10,
            },
            "Warehouse_Layout": {
                "Distances_mm": {},
                "Aisle_Widths_mm": {},
            },
            "Rack_Configuration": {
                "Aisles": 2,
                "Positions_per_side": 5,
                "Levels": 3,
                "Aisle_Length_mm": 20000,
                "Position_Width_mm": 1000,
            },
            "Ground_Stacking_Configuration": {
                "Rows": 5,
                "Columns": 6,
                "Levels": 2,
                "Box_Dimensions": {"Length_mm": 1200, "Width_mm": 800, "Height_mm": 1500},
                "Storage_Area_Dimensions": {"Length_mm": 10000, "Width_mm": 8000},
            },
            "Throughput_Configuration": {
                "Total_Daily_Pallets": 100,
                "Operating_Hours": 10,
                "XPL201_Fraction": 0.1,
                "XQE_Rack_Fraction": 0.2,
                "XQE_Stacking_Fraction": 0.7,
                "Utilization_Target": 0.85,
                "Inbound_Fraction": 0.5,
            },
            "Traffic_Control": {},
        }

    def test_lane_sequence_zero_shuffling_fleet(self, base_config):
        from src.simulator import WarehouseSimulator
        base_config["Block_Storage_Policy"] = {"strategy": "lane_sequence"}
        sim = WarehouseSimulator(base_config)
        results = sim.run()
        assert results.block_storage_policy == "lane_sequence"
        assert results.avg_shuffles_per_outbound == 0.0
        assert results.shuffling_fleet is not None
        assert results.shuffling_fleet.fleet_size == 0

    def test_default_config_uses_fifo_policy(self, base_config):
        from src.simulator import WarehouseSimulator
        # No Block_Storage_Policy key → should default to "fifo"
        sim = WarehouseSimulator(base_config)
        results = sim.run()
        assert results.block_storage_policy == "fifo"

    def test_to_dict_includes_policy(self, base_config):
        from src.simulator import WarehouseSimulator
        base_config["Block_Storage_Policy"] = {"strategy": "lane_sequence"}
        sim = WarehouseSimulator(base_config)
        results = sim.run()
        d = results.to_dict()
        assert "outbound_workflow" in d
        assert d["outbound_workflow"]["block_storage_policy"] == "lane_sequence"

    def test_full_report_contains_policy_label(self, base_config):
        from src.simulator import WarehouseSimulator
        base_config["Block_Storage_Policy"] = {"strategy": "lane_sequence"}
        sim = WarehouseSimulator(base_config)
        report = sim.full_report()
        assert "Lane-Sequence" in report

    def test_full_report_fifo_policy_label(self, base_config):
        from src.simulator import WarehouseSimulator
        sim = WarehouseSimulator(base_config)
        report = sim.full_report()
        assert "FIFO" in report
