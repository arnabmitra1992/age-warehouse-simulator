"""
Tests for physics-based cycle time calculations.
"""

import sys
import os
import math
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cycle_calculator import (
    CycleCalculator,
    CycleTimeResult,
    PICKUP_TIME_S,
    DROPOFF_TIME_S,
    TURN_TIME_S,
    LIFTING_SPEED_M_S,
    _combine,
)


class TestCycleCalculatorBasics:
    calc = CycleCalculator()

    def test_travel_time_simple(self):
        t = self.calc.travel_time(100.0, 1.0)
        assert t == pytest.approx(100.0)

    def test_travel_time_zero_distance(self):
        assert self.calc.travel_time(0.0, 1.0) == 0.0

    def test_travel_time_zero_speed(self):
        assert self.calc.travel_time(10.0, 0.0) == 0.0

    def test_lift_time_basic(self):
        t = self.calc.lift_time(2.0, 0.2)
        assert t == pytest.approx(10.0)

    def test_lift_time_zero_height(self):
        assert self.calc.lift_time(0.0, 0.2) == 0.0

    def test_turn_time_calculation(self):
        assert self.calc.turn_time(0) == 0.0
        assert self.calc.turn_time(1) == pytest.approx(TURN_TIME_S)
        assert self.calc.turn_time(4) == pytest.approx(4 * TURN_TIME_S)


class TestHorizontalLeg:
    calc = CycleCalculator()

    def test_empty_forward_xqe(self):
        r = self.calc.horizontal_leg("XQE_122", 50.0, is_loaded=False)
        # XQE forward speed = 1.0 m/s
        assert r.forward_travel_s == pytest.approx(50.0)
        assert r.reverse_travel_s == pytest.approx(0.0)

    def test_loaded_reverse_xqe(self):
        r = self.calc.horizontal_leg("XQE_122", 50.0, is_loaded=True)
        # XQE reverse speed = 0.3 m/s
        assert r.reverse_travel_s == pytest.approx(50.0 / 0.3)
        assert r.forward_travel_s == pytest.approx(0.0)

    def test_empty_forward_xpl(self):
        r = self.calc.horizontal_leg("XPL_201", 100.0, is_loaded=False)
        # XPL forward speed = 1.5 m/s
        assert r.forward_travel_s == pytest.approx(100.0 / 1.5)

    def test_loaded_reverse_xpl(self):
        r = self.calc.horizontal_leg("XPL_201", 60.0, is_loaded=True)
        # XPL reverse speed = 0.5 m/s
        assert r.reverse_travel_s == pytest.approx(60.0 / 0.5)

    def test_xna_equal_speeds(self):
        r_empty = self.calc.horizontal_leg("XNA", 30.0, is_loaded=False)
        r_loaded = self.calc.horizontal_leg("XNA", 30.0, is_loaded=True)
        # XNA forward = reverse = 1.0 m/s
        assert r_empty.forward_travel_s == pytest.approx(30.0)
        assert r_loaded.reverse_travel_s == pytest.approx(30.0)

    def test_turns_add_to_result(self):
        r = self.calc.horizontal_leg("XQE_122", 10.0, num_turns=3)
        assert r.turn_s == pytest.approx(3 * TURN_TIME_S)

    def test_total_with_turns(self):
        r = self.calc.horizontal_leg("XQE_122", 10.0, is_loaded=False, num_turns=2)
        expected = 10.0 / 1.0 + 2 * TURN_TIME_S
        assert r.total_s == pytest.approx(expected)


class TestRackStorageLeg:
    calc = CycleCalculator()

    def test_xqe_rack_storage_basic(self):
        r = self.calc.rack_storage_leg(
            "XQE_122",
            depth_m=10.0,
            lift_height_m=2.0,
            is_inbound=True,
            num_entry_turns=2,
        )
        # Reverse in + reverse out: 2 × 10 / 0.3
        assert r.reverse_travel_s == pytest.approx(20.0 / 0.3)
        # Lift up + down: 2 × 2.0 / 0.2
        assert r.lift_up_s == pytest.approx(10.0)
        assert r.lift_down_s == pytest.approx(10.0)
        # Pickup + dropoff
        assert r.pickup_s == pytest.approx(PICKUP_TIME_S)
        assert r.dropoff_s == pytest.approx(DROPOFF_TIME_S)
        # Turns
        assert r.turn_s == pytest.approx(2 * TURN_TIME_S)

    def test_xna_rack_storage(self):
        r = self.calc.rack_storage_leg(
            "XNA",
            depth_m=5.0,
            lift_height_m=3.0,
            is_inbound=True,
            num_entry_turns=2,
        )
        # XNA reverse = 1.0 m/s
        assert r.reverse_travel_s == pytest.approx(10.0)
        assert r.lift_up_s == pytest.approx(3.0 / 0.2)
        assert r.lift_down_s == pytest.approx(3.0 / 0.2)

    def test_no_lift_if_height_zero(self):
        r = self.calc.rack_storage_leg("XQE_122", 10.0, 0.0, True, 2)
        assert r.lift_up_s == 0.0
        assert r.lift_down_s == 0.0

    def test_total_formula(self):
        depth = 8.0
        lift = 1.5
        turns = 2
        r = self.calc.rack_storage_leg("XQE_122", depth, lift, True, turns)
        expected = (
            2 * depth / 0.3         # reverse in + out
            + 2 * lift / 0.2        # lift up + down
            + PICKUP_TIME_S
            + DROPOFF_TIME_S
            + turns * TURN_TIME_S
        )
        assert r.total_s == pytest.approx(expected)


class TestStackingLeg:
    calc = CycleCalculator()

    def test_stacking_same_as_rack_for_xqe(self):
        rack_r = self.calc.rack_storage_leg("XQE_122", 5.0, 1.2, True, 2)
        stk_r = self.calc.stacking_leg("XQE_122", 5.0, 1.2, True, 2)
        # Total should be the same (different phase label only)
        assert rack_r.total_s == pytest.approx(stk_r.total_s)

    def test_stacking_phase_label(self):
        r = self.calc.stacking_leg("XQE_122", 5.0, 1.0, is_inbound=True)
        assert r.phase == "stacking_store"

    def test_stacking_retrieval_phase_label(self):
        r = self.calc.stacking_leg("XQE_122", 5.0, 1.0, is_inbound=False)
        assert r.phase == "stacking_retrieve"


class TestInboundXNACycle:
    calc = CycleCalculator()

    def test_returns_two_phases(self):
        phases = self.calc.inbound_xna_cycle(
            d_inbound_to_handover_m=20.0,
            d_handover_to_rack_m=5.0,
            avg_rack_depth_m=8.0,
            avg_lift_height_m=2.0,
        )
        assert "xpl_inbound_to_handover" in phases
        assert "xna_handover_to_rack" in phases

    def test_xpl_phase_agv_type(self):
        phases = self.calc.inbound_xna_cycle(20.0, 5.0, 8.0, 2.0)
        assert phases["xpl_inbound_to_handover"].agv_type == "XPL_201"

    def test_xna_phase_agv_type(self):
        phases = self.calc.inbound_xna_cycle(20.0, 5.0, 8.0, 2.0)
        assert phases["xna_handover_to_rack"].agv_type == "XNA"

    def test_cycle_times_positive(self):
        phases = self.calc.inbound_xna_cycle(20.0, 5.0, 8.0, 2.0)
        for p in phases.values():
            assert p.total_s > 0


class TestInboundXQENoHandover:
    calc = CycleCalculator()

    def test_returns_single_result(self):
        r = self.calc.inbound_xqe_no_handover_cycle(
            d_inbound_to_rack_m=20.0,
            avg_rack_depth_m=8.0,
            avg_lift_height_m=2.0,
        )
        assert isinstance(r, CycleTimeResult)

    def test_xqe_agv_type(self):
        r = self.calc.inbound_xqe_no_handover_cycle(20.0, 8.0, 2.0)
        assert r.agv_type == "XQE_122"

    def test_total_positive(self):
        r = self.calc.inbound_xqe_no_handover_cycle(20.0, 8.0, 2.0)
        assert r.total_s > 0


class TestInboundXQEWithHandover:
    calc = CycleCalculator()

    def test_returns_two_phases(self):
        phases = self.calc.inbound_xqe_with_handover_cycle(
            d_inbound_to_handover_m=60.0,
            d_handover_to_rack_m=10.0,
            avg_rack_depth_m=8.0,
            avg_lift_height_m=2.0,
        )
        assert "xpl_inbound_to_handover" in phases
        assert "xqe_handover_to_rack" in phases

    def test_xpl_phase_agv(self):
        phases = self.calc.inbound_xqe_with_handover_cycle(60.0, 10.0, 8.0, 2.0)
        assert phases["xpl_inbound_to_handover"].agv_type == "XPL_201"

    def test_xqe_phase_agv(self):
        phases = self.calc.inbound_xqe_with_handover_cycle(60.0, 10.0, 8.0, 2.0)
        assert phases["xqe_handover_to_rack"].agv_type == "XQE_122"


class TestOutboundXQENoHandover:
    calc = CycleCalculator()

    def test_returns_single_result(self):
        r = self.calc.outbound_xqe_no_handover_cycle(
            d_rack_to_outbound_m=30.0,
            avg_rack_depth_m=8.0,
            avg_lift_height_m=2.0,
        )
        assert isinstance(r, CycleTimeResult)
        assert r.total_s > 0

    def test_xqe_agv_type(self):
        r = self.calc.outbound_xqe_no_handover_cycle(30.0, 8.0, 2.0)
        assert r.agv_type == "XQE_122"


class TestOutboundXQEWithHandover:
    calc = CycleCalculator()

    def test_returns_two_phases(self):
        phases = self.calc.outbound_xqe_with_handover_cycle(
            d_rack_to_handover_m=10.0,
            d_handover_to_outbound_m=60.0,
            avg_rack_depth_m=8.0,
            avg_lift_height_m=2.0,
        )
        assert "xqe_rack_to_handover" in phases
        assert "xpl_handover_to_outbound" in phases


class TestOutboundXNACycle:
    calc = CycleCalculator()

    def test_returns_two_phases(self):
        phases = self.calc.outbound_xna_cycle(
            d_handover_to_outbound_m=20.0,
            d_handover_to_rack_m=5.0,
            avg_rack_depth_m=8.0,
            avg_lift_height_m=2.0,
        )
        assert "xna_rack_to_handover" in phases
        assert "xpl_handover_to_outbound" in phases

    def test_xna_phase_agv(self):
        phases = self.calc.outbound_xna_cycle(20.0, 5.0, 8.0, 2.0)
        assert phases["xna_rack_to_handover"].agv_type == "XNA"

    def test_xpl_phase_agv(self):
        phases = self.calc.outbound_xna_cycle(20.0, 5.0, 8.0, 2.0)
        assert phases["xpl_handover_to_outbound"].agv_type == "XPL_201"


class TestCycleTimeResultSerialization:
    def test_to_dict_has_required_keys(self):
        r = CycleTimeResult(agv_type="XQE_122", phase="test",
                            forward_travel_s=10.0, pickup_s=30.0)
        d = r.to_dict()
        assert "agv_type" in d
        assert "total_s" in d
        assert "components" in d
        assert "inputs" in d

    def test_total_s_matches_property(self):
        r = CycleTimeResult(
            agv_type="XQE_122", phase="test",
            forward_travel_s=10.0,
            reverse_travel_s=20.0,
            pickup_s=30.0,
            dropoff_s=30.0,
        )
        assert r.to_dict()["total_s"] == pytest.approx(r.total_s)


class TestCombineHelper:
    def test_combine_two_results(self):
        r1 = CycleTimeResult("XQE_122", "p1", forward_travel_s=10.0, pickup_s=30.0)
        r2 = CycleTimeResult("XQE_122", "p2", reverse_travel_s=20.0, dropoff_s=30.0)
        combined = _combine("XQE_122", "combined", r1, r2)
        assert combined.forward_travel_s == pytest.approx(10.0)
        assert combined.reverse_travel_s == pytest.approx(20.0)
        assert combined.pickup_s == pytest.approx(30.0)
        assert combined.dropoff_s == pytest.approx(30.0)
        assert combined.total_s == pytest.approx(90.0)
