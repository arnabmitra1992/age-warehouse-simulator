"""
Tests for fleet sizing (PR-2 pipeline).
"""
import math
import pytest
from src.warehouse_layout import AisleConfig, WarehouseConfig, parse_config
from src.fleet_sizer import FleetSizer, FleetSizingResult, AisleFleetResult
from src.cycle_calculator import CycleCalculator


def make_config(aisles=None, throughput_pallets=500, hours=16.0, head_aisle_mm=4000):
    if aisles is None:
        aisles = [
            AisleConfig(name="SA1", aisle_type="rack", width_mm=2840, depth_mm=15000,
                        shelf_heights_mm=[0, 1200, 2400, 3600]),
            AisleConfig(name="SA2", aisle_type="handover", width_mm=2840, depth_mm=10000),
        ]
    return WarehouseConfig(
        name="Test Warehouse",
        width_mm=30000,
        length_mm=50000,
        head_aisle_width_mm=head_aisle_mm,
        inbound_dock_count=2,
        outbound_dock_count=2,
        aisles=aisles,
        throughput_pallets_per_day=throughput_pallets,
        operating_hours=hours,
        utilization_target=0.80,
    )


class TestFleetSizer:
    def test_basic_fleet_sizing(self):
        config = make_config()
        sizer = FleetSizer(config)
        result = sizer.size_fleet()
        assert isinstance(result, FleetSizingResult)
        assert result.total_agvs >= 1

    def test_fleet_result_has_aisle_results(self):
        config = make_config()
        sizer = FleetSizer(config)
        result = sizer.size_fleet()
        assert len(result.aisle_results) >= 1

    def test_xpl_agv_for_handover(self):
        config = make_config(aisles=[
            AisleConfig(name="HA1", aisle_type="handover", width_mm=2840, depth_mm=10000)
        ])
        sizer = FleetSizer(config)
        result = sizer.size_fleet()
        assert any(r.agv_type == "XPL_201" for r in result.aisle_results)

    def test_xqe_agv_for_rack(self):
        config = make_config(aisles=[
            AisleConfig(name="RA1", aisle_type="rack", width_mm=2840, depth_mm=15000,
                        shelf_heights_mm=[0, 1200, 2400, 3600])
        ])
        sizer = FleetSizer(config)
        result = sizer.size_fleet()
        assert any(r.agv_type == "XQE_122" for r in result.aisle_results)

    def test_xqe_agv_for_stacking(self):
        config = make_config(aisles=[
            AisleConfig(name="ST1", aisle_type="ground_stacking", width_mm=3000,
                        depth_mm=15000, stacking_levels=3)
        ])
        sizer = FleetSizer(config)
        result = sizer.size_fleet()
        assert any(r.agv_type == "XQE_122" for r in result.aisle_results)

    def test_required_agvs_positive(self):
        config = make_config()
        sizer = FleetSizer(config)
        result = sizer.size_fleet()
        for r in result.aisle_results:
            assert r.required_agvs >= 1

    def test_utilization_within_bounds(self):
        config = make_config()
        sizer = FleetSizer(config)
        result = sizer.size_fleet()
        for r in result.aisle_results:
            assert 0.0 <= r.utilization <= 1.0

    def test_higher_throughput_needs_more_agvs(self):
        config_low = make_config(throughput_pallets=200)
        config_high = make_config(throughput_pallets=2000)
        result_low = FleetSizer(config_low).size_fleet()
        result_high = FleetSizer(config_high).size_fleet()
        assert result_high.total_agvs >= result_low.total_agvs

    def test_bottleneck_detection(self):
        config = make_config(aisles=[
            AisleConfig(name="SA1", aisle_type="rack", width_mm=2840, depth_mm=15000,
                        shelf_heights_mm=[0, 1200, 2400, 3600]),
            AisleConfig(name="SA2", aisle_type="handover", width_mm=2840, depth_mm=10000),
        ])
        sizer = FleetSizer(config)
        result = sizer.size_fleet()
        assert isinstance(result.bottleneck_aisles, list)
        assert len(result.bottleneck_aisles) >= 1

    def test_to_dict_structure(self):
        config = make_config()
        result = FleetSizer(config).size_fleet()
        d = result.to_dict()
        assert "warehouse" in d
        assert "total_agvs" in d
        assert "aisle_results" in d

    def test_total_agvs_sum(self):
        config = make_config()
        result = FleetSizer(config).size_fleet()
        assert result.total_agvs == result.total_xpl_agvs + result.total_xqe_agvs

    def test_narrow_aisle_excluded(self):
        # Aisle < 2.5m: should be excluded (XNA only, handled by legacy pipeline)
        config = make_config(aisles=[
            AisleConfig(name="NA1", aisle_type="rack", width_mm=1770, depth_mm=10000)
        ])
        sizer = FleetSizer(config)
        result = sizer.size_fleet()
        assert result.total_agvs == 0

    def test_fleet_sizing_formula(self):
        # Manual calculation verification
        config = make_config(aisles=[
            AisleConfig(name="SA1", aisle_type="rack", width_mm=2840, depth_mm=15000,
                        shelf_heights_mm=[0, 1200, 2400, 3600])
        ], throughput_pallets=500, hours=16.0)
        sizer = FleetSizer(config)
        result = sizer.size_fleet()
        r = result.aisle_results[0]
        # Verify: agvs_needed = ceil(throughput / (tasks_per_agv * utilization))
        expected = math.ceil(result.throughput_per_hour / (r.tasks_per_agv_per_hour * result.utilization_target))
        assert r.required_agvs == expected

    def test_print_report_runs(self, capsys):
        config = make_config()
        result = FleetSizer(config).size_fleet()
        result.print_report()
        captured = capsys.readouterr()
        assert "FLEET SIZING REPORT" in captured.out

    def test_aisle_fleet_result_to_dict(self):
        r = AisleFleetResult(
            aisle_name="SA1", aisle_type="rack", agv_type="XQE_122",
            workflow="xqe_rack", cycle_time_s=320.0, tasks_per_agv_per_hour=11.25,
            required_agvs=3, utilization=0.78, throughput_per_hour=31.25,
        )
        d = r.to_dict()
        assert d["aisle"] == "SA1"
        assert d["required_agvs"] == 3

    def test_override_throughput(self):
        config = make_config(throughput_pallets=500)
        sizer = FleetSizer(config)
        result_override = sizer.size_fleet(throughput_per_hour=100.0)
        assert result_override.throughput_per_hour == pytest.approx(100.0)

    def test_override_utilization(self):
        config = make_config()
        sizer = FleetSizer(config)
        result = sizer.size_fleet(utilization_target=0.50)
        assert result.utilization_target == pytest.approx(0.50)

    def test_throughput_per_hour_property(self):
        config = make_config(throughput_pallets=800, hours=8.0)
        assert config.throughput_per_hour == pytest.approx(100.0)

    def test_mixed_aisle_types(self):
        config = make_config(aisles=[
            AisleConfig(name="SA1", aisle_type="rack", width_mm=2840, depth_mm=15000,
                        shelf_heights_mm=[0, 1200, 2400, 3600]),
            AisleConfig(name="SA2", aisle_type="ground_stacking", width_mm=3000,
                        depth_mm=15000, stacking_levels=3),
            AisleConfig(name="SA3", aisle_type="handover", width_mm=2840, depth_mm=10000),
        ])
        result = FleetSizer(config).size_fleet()
        agv_types = {r.agv_type for r in result.aisle_results}
        assert "XQE_122" in agv_types
        assert "XPL_201" in agv_types
