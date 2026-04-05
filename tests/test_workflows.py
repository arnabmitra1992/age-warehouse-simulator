"""
Tests for rack storage and ground stacking workflow calculations.
"""
import math
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.rack_storage import RackConfig, POSITION_SPACING_MM
from src.ground_stacking import (
    GroundStackingConfig, BoxDimensions, StackingAreaDimensions,
    MAX_LIFT_HEIGHT_MM, CLEARANCE_MM,
)


class TestRackConfig:
    def test_positions_per_shelf_default(self):
        rack = RackConfig(rack_length_mm=20000, position_spacing_mm=950)
        assert rack.positions_per_shelf == math.floor(20000 / 950)

    def test_positions_per_shelf_exact(self):
        rack = RackConfig(rack_length_mm=9500, position_spacing_mm=950)
        assert rack.positions_per_shelf == 10

    def test_total_positions(self):
        rack = RackConfig(rack_length_mm=9500, position_spacing_mm=950, num_levels=3)
        assert rack.total_positions == 10 * 3

    def test_shelf_height_level1(self):
        rack = RackConfig(shelf_height_spacing_mm=1300)
        assert abs(rack.shelf_height_m(1) - 1.3) < 0.0001

    def test_shelf_height_level3(self):
        rack = RackConfig(shelf_height_spacing_mm=1300)
        assert abs(rack.shelf_height_m(3) - 3.9) < 0.0001

    def test_distance_to_position_1(self):
        rack = RackConfig(position_spacing_mm=950)
        # Position 1 centre = 0 + (1 * 0.95) - 0.475 = 0.475 m
        expected = 0.475
        assert abs(rack.distance_to_position_m(1) - expected) < 0.001

    def test_distance_to_position_n(self):
        rack = RackConfig(position_spacing_mm=950)
        spacing_m = 0.95
        for n in range(1, 6):
            expected = n * spacing_m - spacing_m / 2
            assert abs(rack.distance_to_position_m(n) - expected) < 0.001

    def test_distance_from_position_to_exit(self):
        rack = RackConfig(rack_length_mm=9500, position_spacing_mm=950)
        # Position 10 is the last; its exit distance should be ~0.475 m
        exit_dist = rack.distance_from_position_to_exit_m(10)
        assert exit_dist > 0

    def test_position_and_exit_distances_sum_to_rack_length(self):
        rack = RackConfig(rack_length_mm=9500, position_spacing_mm=950, num_levels=1)
        for pos in range(1, rack.positions_per_shelf + 1):
            d_in = rack.distance_to_position_m(pos)
            d_out = rack.distance_from_position_to_exit_m(pos)
            total = d_in + d_out
            expected = rack.rack_length_mm / 1000.0
            assert abs(total - expected) < 0.001, f"Position {pos}: {total} != {expected}"

    def test_all_positions_count(self):
        rack = RackConfig(rack_length_mm=9500, position_spacing_mm=950, num_levels=3)
        positions = rack.all_positions()
        assert len(positions) == 30

    def test_all_positions_structure(self):
        rack = RackConfig(rack_length_mm=9500, position_spacing_mm=950, num_levels=2)
        for level, pos in rack.all_positions():
            assert 1 <= level <= rack.num_levels
            assert 1 <= pos <= rack.positions_per_shelf


class TestGroundStackingConfig:
    def test_effective_box_width_length_entry(self):
        box = BoxDimensions(length_mm=1200, width_mm=800, height_mm=1000)
        cfg = GroundStackingConfig(box=box, fork_entry_side="Length", clearance_mm=200)
        # Length entry: effective_box_width = box.width + 2*clearance = 800 + 400 = 1200
        assert cfg.effective_box_width_mm == 800 + 400

    def test_effective_box_width_width_entry(self):
        box = BoxDimensions(length_mm=1200, width_mm=800, height_mm=1000)
        cfg = GroundStackingConfig(box=box, fork_entry_side="Width", clearance_mm=200)
        # Width entry side: effective_box_width = box.length + 2*clearance = 1200 + 400 = 1600
        assert cfg.effective_box_width_mm == 1200 + 400

    def test_effective_box_depth_length_entry(self):
        box = BoxDimensions(length_mm=1200, width_mm=800, height_mm=1000)
        cfg = GroundStackingConfig(box=box, fork_entry_side="Length", clearance_mm=200)
        assert cfg.effective_box_depth_mm == 1200 + 400

    def test_num_columns(self):
        box = BoxDimensions(length_mm=1200, width_mm=800, height_mm=1000)
        area = StackingAreaDimensions(length_mm=15000, width_mm=10000)
        cfg = GroundStackingConfig(box=box, area=area, fork_entry_side="Length", clearance_mm=200)
        # effective_width = 1200 mm, usable = 10000 - 400 = 9600
        expected = math.floor((10000 - 400) / (800 + 400))
        assert cfg.num_columns == expected

    def test_num_rows(self):
        box = BoxDimensions(length_mm=1200, width_mm=800, height_mm=1000)
        area = StackingAreaDimensions(length_mm=15000, width_mm=10000)
        cfg = GroundStackingConfig(box=box, area=area, fork_entry_side="Length", clearance_mm=200)
        expected = math.floor((15000 - 400) / (1200 + 400))
        assert cfg.num_rows == expected

    def test_num_levels(self):
        box = BoxDimensions(length_mm=1200, width_mm=800, height_mm=1000)
        cfg = GroundStackingConfig(box=box)
        expected = math.floor(MAX_LIFT_HEIGHT_MM / 1000)
        assert cfg.num_levels == expected

    def test_total_positions(self):
        box = BoxDimensions(length_mm=1200, width_mm=800, height_mm=1000)
        area = StackingAreaDimensions(length_mm=15000, width_mm=10000)
        cfg = GroundStackingConfig(box=box, area=area, fork_entry_side="Length", clearance_mm=200)
        assert cfg.total_positions == cfg.num_rows * cfg.num_columns * cfg.num_levels

    def test_column_distance_col1(self):
        box = BoxDimensions(length_mm=1200, width_mm=800, height_mm=1000)
        cfg = GroundStackingConfig(box=box, clearance_mm=200)
        # col 1: (0 * eff_w + eff_w/2 + 200) mm
        eff_w = cfg.effective_box_width_mm
        expected_mm = eff_w / 2 + 200
        assert abs(cfg.column_distance_m(1) * 1000 - expected_mm) < 0.01

    def test_row_distance_row1(self):
        box = BoxDimensions(length_mm=1200, width_mm=800, height_mm=1000)
        cfg = GroundStackingConfig(box=box, clearance_mm=200)
        eff_d = cfg.effective_box_depth_mm
        expected_mm = eff_d / 2 + 200
        assert abs(cfg.row_distance_m(1) * 1000 - expected_mm) < 0.01

    def test_level_height_m(self):
        box = BoxDimensions(length_mm=1200, width_mm=800, height_mm=1000)
        cfg = GroundStackingConfig(box=box)
        assert abs(cfg.level_height_m(1) - 1.0) < 0.0001
        assert abs(cfg.level_height_m(3) - 3.0) < 0.0001

    def test_all_positions_count(self):
        box = BoxDimensions(length_mm=1200, width_mm=800, height_mm=1000)
        area = StackingAreaDimensions(length_mm=5000, width_mm=5000)
        cfg = GroundStackingConfig(box=box, area=area, fork_entry_side="Length", clearance_mm=200)
        assert len(cfg.all_positions()) == cfg.total_positions

    def test_all_positions_structure(self):
        box = BoxDimensions(length_mm=1200, width_mm=800, height_mm=1000)
        area = StackingAreaDimensions(length_mm=5000, width_mm=5000)
        cfg = GroundStackingConfig(box=box, area=area, fork_entry_side="Length", clearance_mm=200)
        for row, col, level in cfg.all_positions():
            assert 1 <= row <= cfg.num_rows
            assert 1 <= col <= cfg.num_columns
            assert 1 <= level <= cfg.num_levels

    def test_zero_positions_when_area_too_small(self):
        box = BoxDimensions(length_mm=5000, width_mm=5000, height_mm=1000)
        area = StackingAreaDimensions(length_mm=1000, width_mm=1000)
        cfg = GroundStackingConfig(box=box, area=area, clearance_mm=200)
        assert cfg.total_positions == 0
