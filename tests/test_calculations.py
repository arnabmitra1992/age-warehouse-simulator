"""
Tests for distance/lift/turn calculations and WarehouseLayout loading.

Covers:
  - WarehouseLayout mm-to-m conversions
  - Distance calculations between key warehouse locations
  - Stacking capacity and position distance helpers
  - Rack position helpers
"""

import math
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.warehouse_layout import WarehouseLayout, validate_config
from src.rack_storage import (
    rack_positions_count,
    distance_to_position_m,
    average_position_distance_m,
)
from src.ground_stacking import (
    stacking_capacity,
    position_distance_m,
    lift_height_m,
)


# ---------------------------------------------------------------------------
# Minimal valid config fixture
# ---------------------------------------------------------------------------

MINIMAL_CONFIG = {
    "warehouse": {
        "name": "Test Warehouse",
        "length_mm": 40000,
        "width_mm": 20000,
        "head_aisle_width_mm": 3500,
    },
    "docks": {
        "inbound":  {"x_mm": 0,     "y_mm": 10000},
        "outbound": {"x_mm": 40000, "y_mm": 10000},
    },
    "rest_area":    {"x_mm": 20000, "y_mm": 0},
    "handover_zone":{"x_mm": 20000, "y_mm": 20000},
    "storage_aisles": [
        {
            "name": "Rack A1",
            "type": "rack",
            "width_mm": 2840,
            "length_mm": 20000,
            "entry_x_mm": 10000,
            "entry_y_mm": 5000,
            "rack_length_mm": 15000,
            "shelf_heights": [1.3, 2.6, 3.9],
        },
        {
            "name": "Stack B1",
            "type": "ground_stacking",
            "width_mm": 6000,
            "length_mm": 10000,
            "entry_x_mm": 25000,
            "entry_y_mm": 5000,
            "box_width_mm": 800,
            "box_length_mm": 1200,
            "box_height_mm": 1000,
        },
    ],
    "throughput": {
        "daily_pallets": 600,
        "operating_hours": 10,
        "xpl_percentage": 30,
        "xqe_rack_percentage": 50,
        "xqe_stacking_percentage": 20,
        "utilization_target": 0.75,
    },
}


# ---------------------------------------------------------------------------
# WarehouseLayout loading tests
# ---------------------------------------------------------------------------

class TestWarehouseLayoutLoading:

    def test_load_from_dict(self):
        layout = WarehouseLayout.from_dict(MINIMAL_CONFIG)
        assert layout.name == "Test Warehouse"

    def test_dimensions_in_metres(self):
        layout = WarehouseLayout.from_dict(MINIMAL_CONFIG)
        assert abs(layout.length_m - 40.0) < 0.001
        assert abs(layout.width_m - 20.0) < 0.001

    def test_head_aisle_width(self):
        layout = WarehouseLayout.from_dict(MINIMAL_CONFIG)
        assert abs(layout.head_aisle_width_m - 3.5) < 0.001

    def test_dock_positions(self):
        layout = WarehouseLayout.from_dict(MINIMAL_CONFIG)
        ib = layout.inbound_dock
        assert ib["x_mm"] == 0
        assert ib["y_mm"] == 10000

    def test_storage_aisles(self):
        layout = WarehouseLayout.from_dict(MINIMAL_CONFIG)
        assert len(layout.storage_aisles) == 2

    def test_rack_aisles(self):
        layout = WarehouseLayout.from_dict(MINIMAL_CONFIG)
        racks = layout.rack_aisles()
        assert len(racks) == 1
        assert racks[0]["name"] == "Rack A1"

    def test_ground_stacking_aisles(self):
        layout = WarehouseLayout.from_dict(MINIMAL_CONFIG)
        stacks = layout.ground_stacking_aisles()
        assert len(stacks) == 1
        assert stacks[0]["name"] == "Stack B1"

    def test_aisle_by_name(self):
        layout = WarehouseLayout.from_dict(MINIMAL_CONFIG)
        aisle = layout.aisle_by_name("Rack A1")
        assert aisle is not None
        assert aisle["type"] == "rack"

    def test_aisle_by_name_missing(self):
        layout = WarehouseLayout.from_dict(MINIMAL_CONFIG)
        assert layout.aisle_by_name("NonExistent") is None

    def test_validate_returns_no_errors(self):
        errors = validate_config(MINIMAL_CONFIG)
        assert errors == []

    def test_invalid_config_missing_docks(self):
        bad = {"warehouse": {"length_mm": 10000, "width_mm": 5000}, "storage_aisles": []}
        errors = validate_config(bad)
        assert len(errors) > 0

    def test_invalid_config_raises_on_construction(self):
        bad = {"warehouse": {"name": "X"}, "storage_aisles": []}
        with pytest.raises(ValueError):
            WarehouseLayout.from_dict(bad)

    def test_load_from_file(self, tmp_path):
        """Write a config to a temp file and load it."""
        p = tmp_path / "test_config.json"
        p.write_text(json.dumps(MINIMAL_CONFIG))
        layout = WarehouseLayout.from_file(str(p))
        assert layout.name == "Test Warehouse"

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            WarehouseLayout.from_file("/nonexistent/path/config.json")


# ---------------------------------------------------------------------------
# Distance calculation tests
# ---------------------------------------------------------------------------

class TestDistanceCalculations:

    def setup_method(self):
        self.layout = WarehouseLayout.from_dict(MINIMAL_CONFIG)

    def test_rest_to_inbound_distance(self):
        """rest=(20000,0), inbound=(0,10000) → √(20000²+10000²) mm → m"""
        expected_m = math.sqrt(20000**2 + 10000**2) / 1000.0
        assert abs(self.layout.d_rest_to_inbound_m - expected_m) < 0.001

    def test_inbound_to_handover_distance(self):
        """inbound=(0,10000), handover=(20000,20000)"""
        expected_m = math.sqrt(20000**2 + 10000**2) / 1000.0
        assert abs(self.layout.d_inbound_to_handover_m - expected_m) < 0.001

    def test_handover_to_rest_distance(self):
        """handover=(20000,20000), rest=(20000,0) → 20 m"""
        assert abs(self.layout.d_handover_to_rest_m - 20.0) < 0.001

    def test_inbound_to_aisle_distance(self):
        """inbound=(0,10000), Rack A1 entry=(10000,5000)"""
        aisle = self.layout.aisle_by_name("Rack A1")
        d = self.layout.d_inbound_to_aisle_m(aisle)
        expected = math.sqrt(10000**2 + 5000**2) / 1000.0
        assert abs(d - expected) < 0.001


# ---------------------------------------------------------------------------
# Rack position helpers
# ---------------------------------------------------------------------------

class TestRackPositionHelpers:

    def test_positions_count_20m_rack(self):
        # 20 000 mm / 950 mm = 21.05 → 21 positions
        assert rack_positions_count(20000) == 21

    def test_positions_count_rounding(self):
        assert rack_positions_count(9500) == 10
        assert rack_positions_count(1900) == 2

    def test_distance_to_first_position(self):
        d = distance_to_position_m(1)
        assert abs(d - 0.475) < 0.001  # 950/2 mm

    def test_distance_increases_with_position(self):
        d1 = distance_to_position_m(1)
        d5 = distance_to_position_m(5)
        assert d5 > d1

    def test_average_position_distance(self):
        # 10 000 mm rack → avg = 5 000 mm = 5 m
        avg = average_position_distance_m(10000)
        assert abs(avg - 5.0) < 0.001


# ---------------------------------------------------------------------------
# Ground stacking helpers
# ---------------------------------------------------------------------------

class TestGroundStackingHelpers:

    def test_stacking_levels_1000mm_boxes(self):
        """4 500 mm max / 1 000 mm per box = 4 levels."""
        _, _, levels = stacking_capacity(10000, 20000, 800, 1200, 1000)
        assert levels == 4

    def test_stacking_levels_500mm_boxes(self):
        """4 500 mm / 500 mm = 9 levels."""
        _, _, levels = stacking_capacity(10000, 20000, 800, 1200, 500)
        assert levels == 9

    def test_column_count_correct(self):
        # (10000 - 400) / (800 + 400) = 9600/1200 = 8.0 → 8 columns
        cols, _, _ = stacking_capacity(10000, 20000, 800, 1200, 1000)
        assert cols == 8

    def test_lift_height_zero_at_level_0(self):
        assert lift_height_m(0, 1000) == 0.0

    def test_lift_height_two_levels(self):
        assert abs(lift_height_m(2, 1000) - 2.0) < 0.001

    def test_position_distance_col1_row1(self):
        dc, dr = position_distance_m(1, 1, 800, 1200)
        assert abs(dc - 0.2) < 0.001
        assert abs(dr - 0.2) < 0.001

    def test_position_distance_increases(self):
        dc1, _ = position_distance_m(1, 1, 800, 1200)
        dc3, _ = position_distance_m(3, 1, 800, 1200)
        assert dc3 > dc1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
