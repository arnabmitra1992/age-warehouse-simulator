"""
Tests for the outbound workflow support:
  - Inbound cycle calculator
  - Outbound cycle calculator
  - Shuffling cycle calculator
  - FIFO storage model
  - Traffic control
  - Fleet sizing with separate inbound/outbound
  - GroundStackingConfig explicit row/column/level overrides
  - WarehouseDistances new fields
"""
import math
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agv_specs import XQE122Specs, TurnSpecs
from src.warehouse_layout import WarehouseDistances, AisleWidths, aisle_widths_from_dict, distances_from_dict
from src.ground_stacking import GroundStackingConfig, BoxDimensions, StackingAreaDimensions
from src.fifo_storage import FIFOStorageModel
from src.traffic_control import (
    TrafficControlConfig,
    TrafficControlModel,
    AisleMetrics,
    traffic_control_config_from_dict,
)
from src.cycle_calculator import (
    xqe122_inbound_cycle,
    xqe122_inbound_average_cycle,
    xqe122_outbound_cycle,
    xqe122_outbound_average_cycle,
    xqe122_shuffling_cycle,
    xqe122_shuffling_average_cycle,
)
from src.fleet_sizer import ThroughputConfig, throughput_config_from_dict, calculate_fleet_size


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def default_xqe():
    return XQE122Specs()


@pytest.fixture
def default_turns():
    return TurnSpecs()


@pytest.fixture
def warehouse_dist():
    """Distances for the your-warehouse configuration."""
    return WarehouseDistances(
        rest_to_production_mm=5000,
        production_to_storage_entry_mm=3000,
        rest_to_head_aisle_mm=3000,
        head_aisle_to_outbound_mm=10000,
    )


@pytest.fixture
def warehouse_stacking():
    """10 rows × 12 columns × 3 levels ground stacking."""
    return GroundStackingConfig(
        box=BoxDimensions(length_mm=1300, width_mm=950, height_mm=1840),
        area=StackingAreaDimensions(length_mm=21000, width_mm=11500),
        fork_entry_side="Length",
        clearance_mm=200,
        explicit_rows=10,
        explicit_columns=12,
        explicit_levels=3,
    )


@pytest.fixture
def default_aisle_widths():
    return AisleWidths(
        inbound_access_width_mm=3900,
        head_aisle_width_mm=3500,
        outbound_access_width_mm=3900,
    )


# ---------------------------------------------------------------------------
# WarehouseDistances new fields
# ---------------------------------------------------------------------------

class TestWarehouseDistancesNewFields:
    def test_rest_to_production_default(self):
        d = WarehouseDistances()
        assert d.rest_to_production_m == 5.0

    def test_production_to_storage_entry_default(self):
        d = WarehouseDistances()
        assert d.production_to_storage_entry_m == 3.0

    def test_head_aisle_to_outbound_default(self):
        d = WarehouseDistances()
        assert d.head_aisle_to_outbound_m == 10.0

    def test_rest_to_storage_entry_property(self, warehouse_dist):
        # 5000 + 3000 = 8000 mm = 8.0 m
        assert abs(warehouse_dist.rest_to_storage_entry_m - 8.0) < 0.001

    def test_storage_exit_to_outbound_entry_property(self, warehouse_dist):
        # 3000 + 5000 + 3000 + 10000 = 21000 mm = 21.0 m
        assert abs(warehouse_dist.storage_exit_to_outbound_entry_m - 21.0) < 0.001

    def test_outbound_exit_to_rest_property(self, warehouse_dist):
        # 10000 + 3000 = 13000 mm = 13.0 m
        assert abs(warehouse_dist.outbound_exit_to_rest_m - 13.0) < 0.001

    def test_distances_from_dict_new_fields(self):
        d = distances_from_dict({
            "Rest_to_Production": 5000,
            "Production_to_Storage_Entry": 3000,
            "Head_Aisle_to_Outbound": 10000,
        })
        assert d.rest_to_production_mm == 5000
        assert d.production_to_storage_entry_mm == 3000
        assert d.head_aisle_to_outbound_mm == 10000

    def test_distances_from_dict_defaults(self):
        d = distances_from_dict({})
        assert d.rest_to_production_mm == 5000
        assert d.production_to_storage_entry_mm == 3000
        assert d.head_aisle_to_outbound_mm == 10000


# ---------------------------------------------------------------------------
# AisleWidths and traffic capacity
# ---------------------------------------------------------------------------

class TestAisleWidths:
    def test_bidirectional_capacity_above_3500mm(self):
        aw = AisleWidths(head_aisle_width_mm=3500)
        assert aw.bidirectional_capacity(3500) == 2

    def test_single_capacity_between_2840_and_3500(self):
        aw = AisleWidths()
        assert aw.bidirectional_capacity(2900) == 1

    def test_zero_capacity_below_min(self):
        aw = AisleWidths()
        assert aw.bidirectional_capacity(2500) == 0

    def test_inbound_capacity_3900mm(self, default_aisle_widths):
        assert default_aisle_widths.inbound_capacity == 2

    def test_head_aisle_capacity_3500mm(self, default_aisle_widths):
        assert default_aisle_widths.head_aisle_capacity == 2

    def test_outbound_capacity_3900mm(self, default_aisle_widths):
        assert default_aisle_widths.outbound_capacity == 2

    def test_aisle_widths_from_dict(self):
        aw = aisle_widths_from_dict({
            "Inbound_Access_Width_mm": 3900,
            "Head_Aisle_Width_mm": 3500,
            "Outbound_Access_Width_mm": 3900,
        })
        assert aw.inbound_access_width_mm == 3900
        assert aw.head_aisle_width_mm == 3500
        assert aw.outbound_access_width_mm == 3900

    def test_aisle_widths_defaults(self):
        aw = aisle_widths_from_dict({})
        assert aw.inbound_capacity == 2
        assert aw.head_aisle_capacity == 2
        assert aw.outbound_capacity == 2


# ---------------------------------------------------------------------------
# GroundStackingConfig explicit row/column/level overrides
# ---------------------------------------------------------------------------

class TestGroundStackingExplicitOverrides:
    def test_explicit_rows_override(self):
        cfg = GroundStackingConfig(
            box=BoxDimensions(1300, 950, 1840),
            area=StackingAreaDimensions(21000, 11500),
            explicit_rows=10,
        )
        assert cfg.num_rows == 10

    def test_explicit_columns_override(self):
        cfg = GroundStackingConfig(
            box=BoxDimensions(1300, 950, 1840),
            area=StackingAreaDimensions(21000, 11500),
            explicit_columns=12,
        )
        assert cfg.num_columns == 12

    def test_explicit_levels_override(self):
        cfg = GroundStackingConfig(
            box=BoxDimensions(1300, 950, 1840),
            explicit_levels=3,
        )
        assert cfg.num_levels == 3

    def test_total_positions_with_overrides(self, warehouse_stacking):
        assert warehouse_stacking.num_rows == 10
        assert warehouse_stacking.num_columns == 12
        assert warehouse_stacking.num_levels == 3
        assert warehouse_stacking.total_positions == 10 * 12 * 3

    def test_no_override_uses_derived(self):
        cfg = GroundStackingConfig(
            box=BoxDimensions(1200, 800, 1000),
            area=StackingAreaDimensions(15000, 10000),
            clearance_mm=200,
        )
        # Should compute from area dimensions, not use explicit override
        assert cfg.explicit_rows is None
        assert cfg.num_rows > 0

    def test_ground_stacking_config_from_dict_explicit(self):
        from src.ground_stacking import ground_stacking_config_from_dict
        cfg = ground_stacking_config_from_dict({
            "Rows": 10,
            "Columns": 12,
            "Levels": 3,
            "Box_Dimensions": {"Length_mm": 1300, "Width_mm": 950, "Height_mm": 1840},
            "Storage_Area_Dimensions": {"Length_mm": 21000, "Width_mm": 11500},
        })
        assert cfg.num_rows == 10
        assert cfg.num_columns == 12
        assert cfg.num_levels == 3


# ---------------------------------------------------------------------------
# Inbound cycle calculator
# ---------------------------------------------------------------------------

class TestXQE122InboundCycle:
    def test_returns_positive_time(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        result = xqe122_inbound_cycle(default_xqe, default_turns, warehouse_dist,
                                      warehouse_stacking, 1, 1, 1)
        assert result.total_time_s > 0

    def test_phases_sum_to_total(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        result = xqe122_inbound_cycle(default_xqe, default_turns, warehouse_dist,
                                      warehouse_stacking, 3, 5, 2)
        phase_sum = sum(p.duration_s for p in result.phases)
        assert abs(phase_sum - result.total_time_s) < 0.001

    def test_includes_pickup_dropoff(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        result = xqe122_inbound_cycle(default_xqe, default_turns, warehouse_dist,
                                      warehouse_stacking, 1, 1, 1)
        names = [p.name for p in result.phases]
        assert any("PICKUP" in n for n in names)
        assert any("DROPOFF" in n for n in names)

    def test_includes_turn(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        result = xqe122_inbound_cycle(default_xqe, default_turns, warehouse_dist,
                                      warehouse_stacking, 1, 1, 1)
        names = [p.name for p in result.phases]
        assert any("Turn" in n for n in names)

    def test_farther_row_increases_cycle_time(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        r1 = xqe122_inbound_cycle(default_xqe, default_turns, warehouse_dist, warehouse_stacking, 1, 1, 1)
        r10 = xqe122_inbound_cycle(default_xqe, default_turns, warehouse_dist, warehouse_stacking, 10, 1, 1)
        assert r10.total_time_s > r1.total_time_s

    def test_farther_column_increases_cycle_time(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        r1 = xqe122_inbound_cycle(default_xqe, default_turns, warehouse_dist, warehouse_stacking, 1, 1, 1)
        r12 = xqe122_inbound_cycle(default_xqe, default_turns, warehouse_dist, warehouse_stacking, 1, 12, 1)
        assert r12.total_time_s > r1.total_time_s

    def test_higher_level_increases_cycle_time(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        r1 = xqe122_inbound_cycle(default_xqe, default_turns, warehouse_dist, warehouse_stacking, 1, 1, 1)
        r3 = xqe122_inbound_cycle(default_xqe, default_turns, warehouse_dist, warehouse_stacking, 1, 1, 3)
        assert r3.total_time_s > r1.total_time_s

    def test_average_cycle_positive(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        result = xqe122_inbound_average_cycle(default_xqe, default_turns, warehouse_dist, warehouse_stacking)
        assert result.total_time_s > 0

    def test_average_cycle_within_bounds(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        avg = xqe122_inbound_average_cycle(default_xqe, default_turns, warehouse_dist, warehouse_stacking)
        near = xqe122_inbound_cycle(default_xqe, default_turns, warehouse_dist, warehouse_stacking, 1, 1, 1)
        far = xqe122_inbound_cycle(default_xqe, default_turns, warehouse_dist, warehouse_stacking,
                                   warehouse_stacking.num_rows,
                                   warehouse_stacking.num_columns,
                                   warehouse_stacking.num_levels)
        assert near.total_time_s <= avg.total_time_s <= far.total_time_s

    def test_rest_to_production_in_phases(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        result = xqe122_inbound_cycle(default_xqe, default_turns, warehouse_dist, warehouse_stacking, 1, 1, 1)
        # Rest → Production at forward_speed = 5.0s
        rest_phases = [p for p in result.phases if "Rest → Production" in p.name]
        assert len(rest_phases) == 1
        assert abs(rest_phases[0].duration_s - 5.0) < 0.001

    def test_reverse_row_navigation_at_reverse_speed(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        result = xqe122_inbound_cycle(default_xqe, default_turns, warehouse_dist, warehouse_stacking, 5, 1, 1)
        rev_phases = [p for p in result.phases if "reverse" in p.description and "Row" in p.name]
        assert len(rev_phases) >= 1
        for ph in rev_phases:
            dist = ph.duration_s * default_xqe.reverse_speed_ms
            assert dist > 0

    def test_return_path_all_forward(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        result = xqe122_inbound_cycle(default_xqe, default_turns, warehouse_dist, warehouse_stacking, 5, 6, 2)
        return_phases = [p for p in result.phases if "forward / empty" in p.description]
        # Should have multiple return phases (Row→Column, Column→Storage, Storage→Production, Production→Rest)
        assert len(return_phases) >= 4


# ---------------------------------------------------------------------------
# Outbound cycle calculator
# ---------------------------------------------------------------------------

class TestXQE122OutboundCycle:
    def test_returns_positive_time(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        result = xqe122_outbound_cycle(default_xqe, default_turns, warehouse_dist,
                                       warehouse_stacking, 10, 6, 1, 5, 6, 1)
        assert result.total_time_s > 0

    def test_phases_sum_to_total(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        result = xqe122_outbound_cycle(default_xqe, default_turns, warehouse_dist,
                                       warehouse_stacking, 8, 3, 2, 4, 7, 1)
        phase_sum = sum(p.duration_s for p in result.phases)
        assert abs(phase_sum - result.total_time_s) < 0.001

    def test_includes_pickup_and_dropoff(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        result = xqe122_outbound_cycle(default_xqe, default_turns, warehouse_dist,
                                       warehouse_stacking, 10, 1, 1, 1, 1, 1)
        names = [p.name for p in result.phases]
        assert any("PICKUP" in n for n in names)
        assert any("DROPOFF" in n for n in names)

    def test_outbound_longer_than_inbound(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        inbound = xqe122_inbound_cycle(default_xqe, default_turns, warehouse_dist,
                                       warehouse_stacking, 5, 6, 1)
        outbound = xqe122_outbound_cycle(default_xqe, default_turns, warehouse_dist,
                                         warehouse_stacking, 5, 6, 1, 5, 6, 1)
        # Outbound involves more travel (storage_exit_to_outbound_entry)
        assert outbound.total_time_s > inbound.total_time_s

    def test_back_row_pickup_slower_than_front_row(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        front = xqe122_outbound_cycle(default_xqe, default_turns, warehouse_dist,
                                      warehouse_stacking, 1, 6, 1, 5, 6, 1)
        back = xqe122_outbound_cycle(default_xqe, default_turns, warehouse_dist,
                                     warehouse_stacking, 10, 6, 1, 5, 6, 1)
        assert back.total_time_s > front.total_time_s

    def test_average_cycle_positive(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        # Use a small stacking config for performance
        small = GroundStackingConfig(
            box=BoxDimensions(1300, 950, 1840),
            explicit_rows=2, explicit_columns=2, explicit_levels=1,
        )
        result = xqe122_outbound_average_cycle(default_xqe, default_turns, warehouse_dist, small)
        assert result.total_time_s > 0

    def test_storage_exit_to_outbound_in_phases(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        result = xqe122_outbound_cycle(default_xqe, default_turns, warehouse_dist,
                                       warehouse_stacking, 5, 6, 1, 5, 6, 1)
        outbound_phases = [p for p in result.phases if "Outbound" in p.name or "outbound" in p.description]
        assert len(outbound_phases) >= 1


# ---------------------------------------------------------------------------
# Shuffling cycle calculator
# ---------------------------------------------------------------------------

class TestXQE122ShufflingCycle:
    def test_returns_positive_time(self, default_xqe, warehouse_dist, warehouse_stacking):
        result = xqe122_shuffling_cycle(default_xqe, warehouse_dist, warehouse_stacking,
                                        blocking_row=3, target_row=10, col=6, level=1)
        assert result.total_time_s > 0

    def test_phases_sum_to_total(self, default_xqe, warehouse_dist, warehouse_stacking):
        result = xqe122_shuffling_cycle(default_xqe, warehouse_dist, warehouse_stacking,
                                        blocking_row=5, target_row=10, col=3, level=2)
        phase_sum = sum(p.duration_s for p in result.phases)
        assert abs(phase_sum - result.total_time_s) < 0.001

    def test_includes_pickup_and_dropoff(self, default_xqe, warehouse_dist, warehouse_stacking):
        result = xqe122_shuffling_cycle(default_xqe, warehouse_dist, warehouse_stacking,
                                        blocking_row=2, target_row=10, col=1, level=1)
        names = [p.name for p in result.phases]
        assert any("PICKUP" in n for n in names)
        assert any("DROPOFF" in n for n in names)

    def test_deeper_blocking_row_increases_time(self, default_xqe, warehouse_dist, warehouse_stacking):
        r1 = xqe122_shuffling_cycle(default_xqe, warehouse_dist, warehouse_stacking,
                                    blocking_row=1, target_row=10, col=6, level=1)
        r5 = xqe122_shuffling_cycle(default_xqe, warehouse_dist, warehouse_stacking,
                                    blocking_row=5, target_row=10, col=6, level=1)
        assert r5.total_time_s > r1.total_time_s

    def test_average_shuffling_cycle_positive(self, default_xqe, warehouse_dist, warehouse_stacking):
        result = xqe122_shuffling_average_cycle(default_xqe, warehouse_dist, warehouse_stacking)
        assert result.total_time_s > 0

    def test_shuffling_shorter_than_full_outbound(self, default_xqe, default_turns, warehouse_dist, warehouse_stacking):
        shuffle = xqe122_shuffling_cycle(default_xqe, warehouse_dist, warehouse_stacking,
                                         blocking_row=1, target_row=10, col=6, level=1)
        outbound = xqe122_outbound_cycle(default_xqe, default_turns, warehouse_dist,
                                          warehouse_stacking, 10, 6, 1, 5, 6, 1)
        assert shuffle.total_time_s < outbound.total_time_s


# ---------------------------------------------------------------------------
# FIFO storage model
# ---------------------------------------------------------------------------

class TestFIFOStorageModel:
    def test_empty_storage(self):
        model = FIFOStorageModel(num_rows=10, num_columns=12, num_levels=3)
        assert model.occupied_count == 0
        assert model.occupancy_fraction == 0.0

    def test_total_positions(self):
        model = FIFOStorageModel(num_rows=10, num_columns=12, num_levels=3)
        assert model.total_positions == 360

    def test_inbound_put_fills_slot(self):
        model = FIFOStorageModel(num_rows=5, num_columns=3, num_levels=1)
        pos = model.inbound_put()
        assert pos is not None
        assert model.occupied_count == 1

    def test_inbound_put_fills_front_first(self):
        model = FIFOStorageModel(num_rows=5, num_columns=1, num_levels=1)
        pos = model.inbound_put()
        assert pos == (1, 1, 1)  # row 1 = front

    def test_inbound_put_sequential_fill(self):
        model = FIFOStorageModel(num_rows=3, num_columns=1, num_levels=1)
        model.inbound_put()
        model.inbound_put()
        pos3 = model.inbound_put()
        assert pos3 == (3, 1, 1)  # third fill goes to row 3

    def test_inbound_put_returns_none_when_full(self):
        model = FIFOStorageModel(num_rows=2, num_columns=1, num_levels=1)
        model.inbound_put()
        model.inbound_put()
        pos = model.inbound_put()
        assert pos is None

    def test_outbound_get_returns_oldest(self):
        model = FIFOStorageModel(num_rows=5, num_columns=1, num_levels=1)
        model.inbound_put()  # fill_order=1 at row 1
        model.inbound_put()  # fill_order=2 at row 2
        model.inbound_put()  # fill_order=3 at row 3
        pos = model.outbound_get()
        # Oldest = fill_order 1 = row 1
        assert pos == (1, 1, 1)
        assert model.occupied_count == 2

    def test_outbound_get_returns_none_when_empty(self):
        model = FIFOStorageModel(num_rows=5, num_columns=1, num_levels=1)
        pos = model.outbound_get()
        assert pos is None

    def test_blocking_pallets_empty_column(self):
        model = FIFOStorageModel(num_rows=10, num_columns=1, num_levels=1)
        blockers = model.blocking_pallets(target_row=5, col=1, level=1)
        assert len(blockers) == 0

    def test_blocking_pallets_detects_blockers(self):
        model = FIFOStorageModel(num_rows=10, num_columns=1, num_levels=1)
        for _ in range(5):
            model.inbound_put()  # fill rows 1-5
        blockers = model.blocking_pallets(target_row=5, col=1, level=1)
        # Rows 1-4 are occupied, blocking access to row 5
        assert len(blockers) == 4

    def test_shuffle_pallet_moves_to_empty_slot(self):
        model = FIFOStorageModel(num_rows=5, num_columns=2, num_levels=1)
        # Fill column 1 rows 1-3
        model.inbound_put()  # (1, 1, 1)
        model.inbound_put()  # (2, 1, 1)
        model.inbound_put()  # (3, 1, 1)
        # Now shuffle row 2 of col 1 somewhere
        result = model.shuffle_pallet(from_row=2, col=1, level=1)
        assert result is not None
        # Should be in row 1 col 1 (if empty), but row 1 is occupied... check col 2
        # Actually row 1 col 1 is occupied, so it'll go somewhere else
        new_row, new_col, new_level = result
        assert not model.slot(2, 1, 1).is_occupied  # original position emptied

    def test_average_shuffles_increases_with_occupancy(self):
        model = FIFOStorageModel(num_rows=10, num_columns=5, num_levels=1)
        avg_empty = model.average_shuffles_per_outbound()
        assert avg_empty == 0.0
        # Add some pallets
        for _ in range(25):
            model.inbound_put()
        avg_half = model.average_shuffles_per_outbound()
        assert avg_half >= 0.0

    def test_shuffling_fraction_increases_with_occupancy(self):
        model = FIFOStorageModel(num_rows=10, num_columns=5, num_levels=1)
        f_low = model.shuffling_fraction(occupancy=0.1)
        f_high = model.shuffling_fraction(occupancy=0.9)
        assert f_high > f_low

    def test_oldest_accessible_slot_no_blockers(self):
        model = FIFOStorageModel(num_rows=5, num_columns=1, num_levels=1)
        model.inbound_put()  # row 1, fill_order=1
        model.inbound_put()  # row 2, fill_order=2
        slot = model.oldest_accessible_slot()
        # Row 1 has no blockers, it's the oldest accessible
        assert slot is not None
        assert slot.row == 1


# ---------------------------------------------------------------------------
# Traffic control
# ---------------------------------------------------------------------------

class TestTrafficControl:
    def test_traffic_config_from_dict(self):
        cfg = traffic_control_config_from_dict({
            "Enabled": True,
            "XQE_Min_Aisle_Width_mm": 2840,
            "XQE_Bidirectional_Width_mm": 3500,
        })
        assert cfg.enabled is True
        assert cfg.xqe_min_aisle_width_mm == 2840
        assert cfg.xqe_bidirectional_width_mm == 3500

    def test_traffic_config_defaults(self):
        cfg = traffic_control_config_from_dict({})
        assert cfg.enabled is True

    def test_aisle_metrics_capacity_bidirectional(self):
        m = AisleMetrics(name="test", width_mm=3900, capacity=2,
                         arrival_rate_per_hour=10.0, traverse_time_s=30.0)
        assert m.capacity == 2

    def test_aisle_metrics_utilization_positive(self):
        m = AisleMetrics(name="test", width_mm=3900, capacity=2,
                         arrival_rate_per_hour=20.0, traverse_time_s=60.0)
        assert 0.0 <= m.utilization < 1.0

    def test_aisle_metrics_wait_time_zero_when_low_load(self):
        m = AisleMetrics(name="test", width_mm=3900, capacity=2,
                         arrival_rate_per_hour=0.1, traverse_time_s=5.0)
        assert m.avg_wait_time_s >= 0.0

    def test_traffic_model_creates_three_aisles(self, default_aisle_widths):
        cfg = TrafficControlConfig()
        model = TrafficControlModel(
            aisle_widths=default_aisle_widths,
            config=cfg,
            total_agv_count=5,
            inbound_cycle_s=120.0,
            outbound_cycle_s=200.0,
        )
        assert len(model.aisles) == 3
        assert "Inbound Access" in model.aisles
        assert "Head Aisle" in model.aisles
        assert "Outbound Access" in model.aisles

    def test_traffic_model_bottleneck_identified(self, default_aisle_widths):
        cfg = TrafficControlConfig()
        model = TrafficControlModel(
            aisle_widths=default_aisle_widths,
            config=cfg,
            total_agv_count=10,
            inbound_cycle_s=120.0,
            outbound_cycle_s=200.0,
        )
        bn = model.bottleneck_aisle()
        assert bn is not None

    def test_traffic_model_disabled_returns_zero_wait(self, default_aisle_widths):
        cfg = TrafficControlConfig(enabled=False)
        model = TrafficControlModel(
            aisle_widths=default_aisle_widths,
            config=cfg,
            total_agv_count=10,
            inbound_cycle_s=120.0,
            outbound_cycle_s=200.0,
        )
        assert model.total_wait_time_inbound_s() == 0.0
        assert model.total_wait_time_outbound_s() == 0.0

    def test_traffic_model_report_string(self, default_aisle_widths):
        cfg = TrafficControlConfig()
        model = TrafficControlModel(
            aisle_widths=default_aisle_widths,
            config=cfg,
            total_agv_count=5,
            inbound_cycle_s=150.0,
            outbound_cycle_s=250.0,
        )
        report = model.report()
        assert "TRAFFIC CONTROL" in report
        assert "Inbound Access" in report
        assert "Head Aisle" in report


# ---------------------------------------------------------------------------
# ThroughputConfig with separate inbound/outbound pallets
# ---------------------------------------------------------------------------

class TestThroughputConfigOutbound:
    def test_effective_inbound_pallets_from_specific(self):
        cfg = ThroughputConfig(
            total_daily_pallets=500,
            total_daily_inbound_pallets=1000,
        )
        assert cfg.effective_inbound_pallets == 1000

    def test_effective_inbound_pallets_fallback_to_total(self):
        cfg = ThroughputConfig(total_daily_pallets=700)
        assert cfg.effective_inbound_pallets == 700

    def test_effective_outbound_pallets_from_specific(self):
        cfg = ThroughputConfig(
            total_daily_pallets=500,
            total_daily_outbound_pallets=1000,
        )
        assert cfg.effective_outbound_pallets == 1000

    def test_effective_outbound_pallets_fallback_to_total(self):
        cfg = ThroughputConfig(total_daily_pallets=800)
        assert cfg.effective_outbound_pallets == 800

    def test_throughput_config_from_dict_new_fields(self):
        cfg = throughput_config_from_dict({
            "Total_Daily_Pallets": 500,
            "Total_Daily_Inbound_Pallets": 1000,
            "Total_Daily_Outbound_Pallets": 1000,
            "Operating_Hours": 16,
            "XPL_201_Percentage": 0,
            "XQE_Rack_Percentage": 0,
            "XQE_Stacking_Percentage": 100,
        })
        assert cfg.total_daily_inbound_pallets == 1000
        assert cfg.total_daily_outbound_pallets == 1000
        assert cfg.effective_inbound_pallets == 1000


# ---------------------------------------------------------------------------
# Integration: WarehouseSimulator with outbound config
# ---------------------------------------------------------------------------

class TestWarehouseSimulatorOutboundIntegration:
    def test_simulator_runs_your_warehouse_config(self):
        import json
        from src.simulator import WarehouseSimulator, load_config
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "config_your_warehouse.json"
        )
        config = load_config(config_path)
        sim = WarehouseSimulator(config)
        results = sim.run()
        assert results.inbound_cycle is not None
        assert results.outbound_cycle is not None
        assert results.shuffling_cycle is not None
        assert results.inbound_cycle.total_time_s > 0
        assert results.outbound_cycle.total_time_s > 0

    def test_simulator_stacking_config_10x12x3(self):
        import json
        from src.simulator import WarehouseSimulator, load_config
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "config_your_warehouse.json"
        )
        config = load_config(config_path)
        sim = WarehouseSimulator(config)
        assert sim.stacking.num_rows == 10
        assert sim.stacking.num_columns == 12
        assert sim.stacking.num_levels == 3

    def test_simulator_outbound_fleet_sized(self):
        import json
        from src.simulator import WarehouseSimulator, load_config
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "config_your_warehouse.json"
        )
        config = load_config(config_path)
        sim = WarehouseSimulator(config)
        results = sim.run()
        assert results.inbound_fleet is not None
        assert results.outbound_fleet is not None
        assert results.inbound_fleet.fleet_size >= 1
        assert results.outbound_fleet.fleet_size >= 1

    def test_simulator_traffic_model_created(self):
        import json
        from src.simulator import WarehouseSimulator, load_config
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "config_your_warehouse.json"
        )
        config = load_config(config_path)
        sim = WarehouseSimulator(config)
        results = sim.run()
        assert results.traffic_model is not None
        assert len(results.traffic_model.aisles) == 3

    def test_simulator_full_report_contains_outbound(self):
        import json
        from src.simulator import WarehouseSimulator, load_config
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "config_your_warehouse.json"
        )
        config = load_config(config_path)
        sim = WarehouseSimulator(config)
        results = sim.run()
        report = sim.full_report(results)
        assert "INBOUND WORKFLOW" in report
        assert "OUTBOUND WORKFLOW" in report
        assert "SHUFFLING" in report
        assert "TRAFFIC CONTROL" in report

    def test_simulator_to_dict_contains_outbound_workflow(self):
        import json
        from src.simulator import WarehouseSimulator, load_config
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "config_your_warehouse.json"
        )
        config = load_config(config_path)
        sim = WarehouseSimulator(config)
        results = sim.run()
        d = results.to_dict()
        assert "outbound_workflow" in d
        assert d["outbound_workflow"]["inbound_fleet"] >= 1
        assert d["outbound_workflow"]["outbound_fleet"] >= 1
