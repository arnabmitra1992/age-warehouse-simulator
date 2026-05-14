"""
Main simulation orchestrator.
Combines all modules to produce a complete simulation report.
"""
import json
import csv
import io
from dataclasses import asdict
from typing import Dict, Any, Optional

from .agv_specs import (
    XQE122Specs,
    XPL201Specs,
    XNASpecs,
    TurnSpecs,
    xqe122_from_dict,
    xpl201_from_dict,
    xna_from_dict,
)
from .warehouse_layout import WarehouseDistances, AisleWidths, distances_from_dict, aisle_widths_from_dict
from .rack_storage import RackConfig, rack_config_from_dict
from .ground_stacking import GroundStackingConfig, ground_stacking_config_from_dict
from .fifo_storage import FIFOStorageModel
from .lane_sequence_storage import LaneSequenceStorageModel
from .traffic_control import TrafficControlConfig, TrafficControlModel, traffic_control_config_from_dict
from .alternating_buffer_strategy import run_alternating_buffer_simulation
from .cycle_calculator import (
    xpl201_handover_cycle,
    xqe122_rack_average_cycle,
    xqe122_stacking_average_cycle,
    xqe122_inbound_average_cycle,
    xqe122_outbound_average_cycle,
    xqe122_shuffling_average_cycle,
    CycleResult,
    CyclePhase,
)
from .fleet_sizer import (
    ThroughputConfig,
    FleetSizeResult,
    calculate_fleet_size,
    throughput_config_from_dict,
)
from .visualizer import (
    xpl201_workflow_diagram,
    xqe122_rack_workflow_diagram,
    xqe122_stacking_workflow_diagram,
    xqe122_inbound_workflow_diagram,
    xqe122_outbound_workflow_diagram,
    xqe122_shuffling_workflow_diagram,
    rack_capacity_report,
    stacking_capacity_report,
    cycle_time_report,
    fleet_report,
    performance_report,
    outbound_performance_report,
)


class SimulationResults:
    """Container for all simulation outputs."""

    def __init__(self):
        self.rack_config: Optional[RackConfig] = None
        self.stacking_config: Optional[GroundStackingConfig] = None
        self.xpl_cycle: Optional[CycleResult] = None
        self.xqe_rack_cycle: Optional[CycleResult] = None
        self.xqe_stack_cycle: Optional[CycleResult] = None
        self.xpl_fleet: Optional[FleetSizeResult] = None
        self.xqe_rack_fleet: Optional[FleetSizeResult] = None
        self.xqe_stack_fleet: Optional[FleetSizeResult] = None
        self.throughput_config: Optional[ThroughputConfig] = None
        # New outbound workflow results
        self.inbound_cycle: Optional[CycleResult] = None
        self.outbound_cycle: Optional[CycleResult] = None
        self.shuffling_cycle: Optional[CycleResult] = None
        self.inbound_fleet: Optional[FleetSizeResult] = None
        self.outbound_fleet: Optional[FleetSizeResult] = None
        self.shuffling_fleet: Optional[FleetSizeResult] = None
        self.avg_shuffles_per_outbound: float = 0.0
        self.fifo_model: Optional[FIFOStorageModel] = None
        self.traffic_model: Optional[TrafficControlModel] = None
        self.block_storage_policy: str = "fifo"  # "fifo", "column_fifo", or "lane_sequence"
        self.rack_vehicle_type: str = "XQE_122"
        self.workload_buckets: Dict[str, float] = {
            "horizontal_xpl": 0.0,
            "horizontal_xqe": 0.0,
            "stacking_xqe": 0.0,
            "horizontal_xpl_inbound": 0.0,
            "horizontal_xpl_outbound": 0.0,
            "horizontal_xqe_inbound": 0.0,
            "horizontal_xqe_outbound": 0.0,
            "stacking_xqe_inbound": 0.0,
            "stacking_xqe_outbound": 0.0,
        }
        self.dispatch_throughput_check: Dict[str, Any] = {}

    @property
    def total_fleet_size(self) -> int:
        total = 0
        for r in [self.xpl_fleet, self.xqe_rack_fleet, self.xqe_stack_fleet]:
            if r:
                total += r.fleet_size
        return total

    @property
    def total_outbound_fleet_size(self) -> int:
        """Total fleet for the inbound + outbound + shuffling workflows."""
        total = 0
        for r in [self.inbound_fleet, self.outbound_fleet, self.shuffling_fleet]:
            if r:
                total += r.fleet_size
        return total

    @property
    def total_dispatch_fleet_size(self) -> int:
        total = 0
        for r in [self.xpl_fleet, self.xqe_rack_fleet, self.xqe_stack_fleet]:
            if r:
                total += r.fleet_size
        return total

    def to_dict(self) -> Dict[str, Any]:
        base = {
            "rack_capacity": {
                "positions_per_shelf": self.rack_config.positions_per_shelf if self.rack_config else 0,
                "num_levels": self.rack_config.num_levels if self.rack_config else 0,
                "total_positions": self.rack_config.total_positions if self.rack_config else 0,
            },
            "stacking_capacity": {
                "rows": self.stacking_config.num_rows if self.stacking_config else 0,
                "columns": self.stacking_config.num_columns if self.stacking_config else 0,
                "levels": self.stacking_config.num_levels if self.stacking_config else 0,
                "total_positions": self.stacking_config.total_positions if self.stacking_config else 0,
            },
            "cycle_times_s": {
                "xpl201_handover": self.xpl_cycle.total_time_s if self.xpl_cycle else 0,
                "xqe122_rack_avg": self.xqe_rack_cycle.total_time_s if self.xqe_rack_cycle else 0,
                "xqe122_stack_avg": self.xqe_stack_cycle.total_time_s if self.xqe_stack_cycle else 0,
            },
            "fleet_sizes": {
                "xpl201": self.xpl_fleet.fleet_size if self.xpl_fleet else 0,
                "xqe122_rack": self.xqe_rack_fleet.fleet_size if self.xqe_rack_fleet else 0,
                "xqe122_stacking": self.xqe_stack_fleet.fleet_size if self.xqe_stack_fleet else 0,
                "rack_vehicle_type": self.rack_vehicle_type,
                "total": self.total_fleet_size,
                "workload_buckets": self.workload_buckets,
                "dispatch_total": self.total_dispatch_fleet_size,
                "dispatch_throughput_check": self.dispatch_throughput_check,
            },
        }
        # Outbound workflow metrics (if computed)
        if self.inbound_cycle or self.outbound_cycle:
            base["outbound_workflow"] = {
                "block_storage_policy": self.block_storage_policy,
                "inbound_cycle_s": self.inbound_cycle.total_time_s if self.inbound_cycle else 0,
                "outbound_cycle_s": self.outbound_cycle.total_time_s if self.outbound_cycle else 0,
                "shuffling_cycle_s": self.shuffling_cycle.total_time_s if self.shuffling_cycle else 0,
                "avg_shuffles_per_outbound": self.avg_shuffles_per_outbound,
                "inbound_fleet": self.inbound_fleet.fleet_size if self.inbound_fleet else 0,
                "outbound_fleet": self.outbound_fleet.fleet_size if self.outbound_fleet else 0,
                "shuffling_fleet": self.shuffling_fleet.fleet_size if self.shuffling_fleet else 0,
                "total_outbound_fleet": self.total_outbound_fleet_size,
            }
        return base

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_csv(self) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["metric", "value"])
        flat = {}
        for section, vals in self.to_dict().items():
            for k, v in vals.items():
                flat[f"{section}.{k}"] = v
        for k, v in flat.items():
            writer.writerow([k, v])
        return buf.getvalue()


class WarehouseSimulator:
    """Main orchestrator for the warehouse AGV simulation."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._load_specs()

    def _load_specs(self):
        agv_cfg = self.config.get("AGV_Specifications", {})
        self.xqe = xqe122_from_dict(agv_cfg.get("XQE_122", {}))
        self.xpl = xpl201_from_dict(agv_cfg.get("XPL_201", {}))
        self.xna = xna_from_dict(agv_cfg.get("XNA_121", {}))
        self.turns = TurnSpecs(
            turn_90_degrees_s=agv_cfg.get("Turn_90_degrees_s", 10)
        )
        layout_cfg = self.config.get("Warehouse_Layout", {})
        self.distances = distances_from_dict(layout_cfg.get("Distances_mm", {}))
        self.aisle_widths = aisle_widths_from_dict(layout_cfg.get("Aisle_Widths_mm", {}))
        self.rack = rack_config_from_dict(self.config.get("Rack_Configuration", {}))
        self.stacking = ground_stacking_config_from_dict(
            self.config.get("Ground_Stacking_Configuration", {})
        )
        self.throughput = throughput_config_from_dict(
            self.config.get("Throughput_Configuration", {})
        )
        self.traffic_cfg = traffic_control_config_from_dict(
            self.config.get("Traffic_Control", {})
        )

    def _determine_rack_vehicle_type(self) -> str:
        widths_cfg = (
            self.config.get("Warehouse_Layout", {})
            .get("Aisle_Widths_mm", {})
        )
        rack_width_mm = widths_cfg.get("Rack_Aisle_Width_mm", None)
        if rack_width_mm is None:
            rack_width_mm = self.aisle_widths.head_aisle_width_mm
        # Narrow aisle band from project logic: XNA rack operation
        if 1717 <= float(rack_width_mm) <= 2500:
            return "XNA_121"
        return "XQE_122"

    def _derive_workload_buckets(self) -> Dict[str, float]:
        """Derive daily workload buckets from graph mix and inbound/outbound rates."""
        throughput_cfg = self.config.get("Throughput_Configuration", {})
        buckets_cfg = throughput_cfg.get("Workload_Buckets", {}) or {}
        if buckets_cfg:
            hxpl = float(buckets_cfg.get("horizontal_xpl", 0.0))
            hxqe = float(buckets_cfg.get("horizontal_xqe", 0.0))
            sxqe = float(buckets_cfg.get("stacking_xqe", 0.0))
            return {
                "horizontal_xpl": hxpl,
                "horizontal_xqe": hxqe,
                "stacking_xqe": sxqe,
                "horizontal_xpl_inbound": hxpl,
                "horizontal_xpl_outbound": 0.0,
                "horizontal_xqe_inbound": hxqe,
                "horizontal_xqe_outbound": 0.0,
                "stacking_xqe_inbound": sxqe,
                "stacking_xqe_outbound": 0.0,
            }

        inbound_daily = float(self.throughput.effective_inbound_pallets)
        outbound_daily = float(self.throughput.effective_outbound_pallets)
        total_flow_daily = inbound_daily + outbound_daily
        graph_daily = (self.config.get("Generated_From_Graph", {}) or {}).get("throughput_daily", {}) or {}
        graph_total = float(graph_daily.get("total", 0.0) or 0.0)
        graph_handover = float(graph_daily.get("handover", 0.0) or 0.0)
        graph_storage = float((graph_daily.get("rack", 0.0) or 0.0) + (graph_daily.get("stacking", 0.0) or 0.0))

        if graph_total > 0:
            handover_ratio = max(0.0, min(1.0, graph_handover / graph_total))
            direct_ratio = max(0.0, min(1.0, graph_storage / graph_total))
        else:
            # Legacy fallback from percentage split
            handover_ratio = max(0.0, min(1.0, self.throughput.xpl201_percentage / 100.0))
            direct_ratio = max(0.0, 1.0 - handover_ratio)

        horizontal_xpl_inbound = inbound_daily * handover_ratio
        horizontal_xpl_outbound = outbound_daily * handover_ratio
        horizontal_xqe_inbound = inbound_daily * direct_ratio
        horizontal_xqe_outbound = outbound_daily * direct_ratio
        stacking_xqe_inbound = inbound_daily
        stacking_xqe_outbound = outbound_daily
        return {
            # Horizontal transport split between XPL and XQE
            "horizontal_xpl": horizontal_xpl_inbound + horizontal_xpl_outbound,
            "horizontal_xqe": horizontal_xqe_inbound + horizontal_xqe_outbound,
            # Storage handling (putaway/retrieval/stacking) is always XQE group
            "stacking_xqe": stacking_xqe_inbound + stacking_xqe_outbound,
            "horizontal_xpl_inbound": horizontal_xpl_inbound,
            "horizontal_xpl_outbound": horizontal_xpl_outbound,
            "horizontal_xqe_inbound": horizontal_xqe_inbound,
            "horizontal_xqe_outbound": horizontal_xqe_outbound,
            "stacking_xqe_inbound": stacking_xqe_inbound,
            "stacking_xqe_outbound": stacking_xqe_outbound,
        }

    def _size_and_verify_fleet(
        self,
        daily_pallets: float,
        avg_cycle_time_s: float,
        vehicle_type: str,
        workflow: str,
    ) -> FleetSizeResult:
        result = calculate_fleet_size(
            daily_pallets=daily_pallets,
            avg_cycle_time_s=avg_cycle_time_s,
            operating_hours=self.throughput.operating_hours,
            utilization_target=self.throughput.utilization_target,
            vehicle_type=vehicle_type,
            workflow=workflow,
        )
        if avg_cycle_time_s <= 0:
            return result
        # Re-check throughput at utilization target and increment if needed.
        while True:
            achieved_daily_at_target = (
                result.fleet_size
                * (3600.0 / avg_cycle_time_s)
                * self.throughput.operating_hours
                * self.throughput.utilization_target
            )
            if achieved_daily_at_target + 1e-9 >= daily_pallets:
                return result
            result.fleet_size += 1
            result.throughput_per_hour = (3600.0 / avg_cycle_time_s) * result.fleet_size
            required_per_hour = daily_pallets / max(1e-9, self.throughput.operating_hours)
            result.utilization_percent = (
                (required_per_hour / max(1e-9, result.throughput_per_hour)) * 100.0
            )

    def _simulate_dynamic_shuffles(self, fifo_model: FIFOStorageModel, operating_hours: int) -> float:
        """
        Simulate dynamic inbound/outbound with variable ratios throughout the day.
        Returns average shuffles per outbound retrieval.

        Simulates:
        - Hours 1-3: 70% inbound, 30% outbound (morning receiving)
        - Hours 4-7: 50% inbound, 50% outbound (balanced mid-day)
        - Hours 8-10: 30% inbound, 70% outbound (afternoon shipping)

        KEY: Process OUTBOUND FIRST each hour, then INBOUND
        This ensures old pallets (front rows) are retrieved before new ones are added (back rows)
        """
        inbound_per_hour = int(self.throughput.effective_inbound_pallets / operating_hours)
        outbound_per_hour = int(self.throughput.effective_outbound_pallets / operating_hours)

        total_shuffles = 0
        total_retrievals = 0

        for hour in range(1, operating_hours + 1):
            # Variable inbound/outbound ratio based on time of day
            if hour <= 3:
                # Morning: Heavy inbound
                inbound_this_hour = int(inbound_per_hour * 1.4)  # 70% extra (50)
                outbound_this_hour = int(outbound_per_hour * 0.6)  # 30% reduced (21)
            elif hour <= 7:
                # Mid-day: Balanced
                inbound_this_hour = inbound_per_hour  # 36
                outbound_this_hour = outbound_per_hour  # 36
            else:
                # Afternoon: Heavy outbound
                inbound_this_hour = int(inbound_per_hour * 0.6)  # 30% reduced (21)
                outbound_this_hour = int(outbound_per_hour * 1.4)  # 70% extra (50)

            # OUTBOUND FIRST: Retrieve pallets and count actual shuffles
            for _ in range(outbound_this_hour):
                oldest = fifo_model.oldest_accessible_slot()
                if oldest:
                    # Count blocking pallets (each = 1 shuffle move)
                    blockers = fifo_model.blocking_pallets(oldest.row, oldest.col, oldest.level)
                    total_shuffles += len(blockers)

                    # Perform shuffles (move blockers forward)
                    for blocker in blockers:
                        fifo_model.shuffle_pallet(blocker.row, blocker.col, blocker.level)

                    # Now retrieve the oldest pallet
                    fifo_model.outbound_get()
                    total_retrievals += 1

            # INBOUND SECOND: Add pallets to storage (fill front-to-back)
            for _ in range(inbound_this_hour):
                fifo_model.inbound_put()

        return total_shuffles / max(1, total_retrievals)

    def _simulate_two_zone_shuffles(self, fifo_model: FIFOStorageModel, operating_hours: int) -> float:
        """
        Simulate 2-day operation with 10-hour shifts each.
        Pre-fill storage so new inbound blocks old outbound retrieval.
        """
        # PRE-FILL: Fill the last 2 back rows with OLD pallets.
        # This creates a situation where old pallets are deep in storage.
        # Use dynamic back rows derived from the actual model dimensions.
        n = fifo_model.num_rows
        # Rows are 1-indexed (row 1 = front, row n = back).
        # Select the last 2 rows (or fewer if the model has only 1 row).
        # e.g. n=10 → [10, 9]; n=9 → [9, 8]; n=1 → [1]; n=0 → []
        back_rows = list(range(n, max(0, n - 2), -1))
        fill_counter = 0
        for row in back_rows:
            for col in range(1, fifo_model.num_columns + 1):
                for level in range(1, fifo_model.num_levels + 1):
                    fill_counter += 1
                    fifo_model._slots[(row, col, level)].fill_order = fill_counter

        # Now set counter so new inbound starts at 73
        fifo_model._counter = fill_counter

        inbound_per_hour = int(self.throughput.effective_inbound_pallets / (operating_hours // 2))
        outbound_per_hour = int(self.throughput.effective_outbound_pallets / (operating_hours // 2))

        total_shuffles = 0
        total_retrievals = 0
        day_shuffles = [0, 0]
        day_retrievals = [0, 0]

        for hour in range(1, operating_hours + 1):
            day = (hour - 1) // 10
            hour_in_day = ((hour - 1) % 10) + 1

            # Variable inbound/outbound ratio
            if hour_in_day <= 3:
                inbound_this_hour = int(inbound_per_hour * 2.25)  # 90%
                outbound_this_hour = int(outbound_per_hour * 0.25)  # 10%
            elif hour_in_day <= 7:
                inbound_this_hour = inbound_per_hour
                outbound_this_hour = outbound_per_hour
            else:
                inbound_this_hour = int(inbound_per_hour * 0.25)  # 10%
                outbound_this_hour = int(outbound_per_hour * 2.25)  # 90%

            # INBOUND: New pallets fill front rows
            for _ in range(inbound_this_hour):
                fifo_model.inbound_put()

            # OUTBOUND: Retrieve from back rows where old pallets are, even if blocked
            for _ in range(outbound_this_hour):
                # Find oldest pallet in back rows - where we pre-filled old pallets
                oldest_in_back = None
                for row in back_rows:
                    for col in range(1, fifo_model.num_columns + 1):
                        for level in range(1, fifo_model.num_levels + 1):
                            slot = fifo_model._slots[(row, col, level)]
                            if slot.is_occupied:
                                if oldest_in_back is None or slot.fill_order < oldest_in_back.fill_order:
                                    oldest_in_back = slot

                if oldest_in_back:
                    # Count blocking pallets in front of this back-row pallet
                    blockers = fifo_model.blocking_pallets(oldest_in_back.row, oldest_in_back.col, oldest_in_back.level)

                    # DEBUG: Print blocking info
                    if hour == 8 and _ == 0:
                        print(
                            f"  DEBUG Hour {hour}: Oldest_in_back at Row {oldest_in_back.row}, Col {oldest_in_back.col}, "
                            f"Level {oldest_in_back.level} | Fill_order {oldest_in_back.fill_order} | Blockers: {len(blockers)}"
                        )

                    total_shuffles += len(blockers)
                    day_shuffles[day] += len(blockers)

                    # Shuffle blockers out of the way
                    for blocker in blockers:
                        fifo_model.shuffle_pallet(blocker.row, blocker.col, blocker.level)

                    # Now retrieve the back-row pallet
                    fifo_model.outbound_get()
                    total_retrievals += 1
                    day_retrievals[day] += 1

            # Print hourly status
            if hour % 1 == 0:
                print(
                    f"Hour {hour:2d}: Inbound={inbound_this_hour:2d}, Outbound={outbound_this_hour:2d} | "
                    f"Storage={fifo_model.occupied_count:3d}/360 ({fifo_model.occupancy_fraction*100:5.1f}%) | "
                    f"Shuffles={total_shuffles}, Retrievals={total_retrievals}"
                )

        avg_shuffles = total_shuffles / max(1, total_retrievals) if total_retrievals > 0 else 0

        print(f"\n{'='*60}")
        print("=== 2-DAY SHUFFLE SIMULATION RESULTS ===")
        print(f"{'='*60}")
        print(
            f"Day 1 - Shuffles: {day_shuffles[0]:3d} | Retrievals: {day_retrievals[0]:3d} | Avg: "
            f"{day_shuffles[0]/max(1,day_retrievals[0]):.2f}"
        )
        print(
            f"Day 2 - Shuffles: {day_shuffles[1]:3d} | Retrievals: {day_retrievals[1]:3d} | Avg: "
            f"{day_shuffles[1]/max(1,day_retrievals[1]):.2f}"
        )
        print(f"{'='*60}")
        print(f"Total - Shuffles: {total_shuffles} | Retrievals: {total_retrievals}")
        print(f"Overall Avg Shuffles per Retrieval: {avg_shuffles:.2f}")
        print(f"Final Storage: {fifo_model.occupied_count}/{fifo_model.total_positions} occupied")
        print(f"{'='*60}\n")

        return avg_shuffles

    def run(self, traffic_control_enabled: bool = False) -> SimulationResults:
        """Execute the full simulation and return results.

        Parameters
        ----------
        traffic_control_enabled:
            When *True* the traffic-control queuing model is activated and
            aisle wait-time overheads are included in the outbound performance
            report.  Defaults to *False* so that a plain ``sim.run()`` call
            (e.g. from unit-tests or the ``demo`` command) omits the extra
            overhead unless explicitly requested.
        """
        self.traffic_cfg.enabled = traffic_control_enabled
        self.throughput.validate()
        results = SimulationResults()
        results.rack_config = self.rack
        results.stacking_config = self.stacking
        results.throughput_config = self.throughput
        results.workload_buckets = self._derive_workload_buckets()

        # --- Legacy cycle time calculations (kept for backward compatibility) ---
        rack_vehicle_type = self._determine_rack_vehicle_type()
        results.rack_vehicle_type = rack_vehicle_type
        results.xpl_cycle = xpl201_handover_cycle(self.xpl, self.turns, self.distances)
        rack_agv_for_cycle = self.xna if rack_vehicle_type == "XNA_121" else self.xqe
        results.xqe_rack_cycle = xqe122_rack_average_cycle(
            rack_agv_for_cycle, self.turns, self.distances, self.rack
        )
        results.xqe_stack_cycle = xqe122_stacking_average_cycle(
            self.xqe, self.turns, self.distances, self.stacking
        )

        # --- Legacy fleet sizing ---
        results.xpl_fleet = self._size_and_verify_fleet(
            daily_pallets=results.workload_buckets["horizontal_xpl"],
            avg_cycle_time_s=results.xpl_cycle.total_time_s,
            vehicle_type="XPL_201",
            workflow="Horizontal Transport (via handover)",
        )
        results.xqe_rack_fleet = self._size_and_verify_fleet(
            daily_pallets=results.workload_buckets["horizontal_xqe"],
            avg_cycle_time_s=results.xqe_rack_cycle.total_time_s,
            vehicle_type=rack_vehicle_type,
            workflow="Horizontal Transport (direct)",
        )
        results.xqe_stack_fleet = self._size_and_verify_fleet(
            daily_pallets=results.workload_buckets["stacking_xqe"],
            avg_cycle_time_s=results.xqe_stack_cycle.total_time_s,
            vehicle_type="XQE_122",
            workflow="Storage Handling (stacking/putaway/retrieval)",
        )
        xpl_achieved = (
            results.xpl_fleet.fleet_size
            * (3600.0 / max(1e-9, results.xpl_cycle.total_time_s))
            * self.throughput.operating_hours
            * self.throughput.utilization_target
        )
        xqe_h_achieved = (
            results.xqe_rack_fleet.fleet_size
            * (3600.0 / max(1e-9, results.xqe_rack_cycle.total_time_s))
            * self.throughput.operating_hours
            * self.throughput.utilization_target
        )
        xqe_s_achieved = (
            results.xqe_stack_fleet.fleet_size
            * (3600.0 / max(1e-9, results.xqe_stack_cycle.total_time_s))
            * self.throughput.operating_hours
            * self.throughput.utilization_target
        )
        results.dispatch_throughput_check = {
            "horizontal_xpl_target": results.workload_buckets["horizontal_xpl"],
            "horizontal_xpl_achieved": xpl_achieved,
            "horizontal_xqe_target": results.workload_buckets["horizontal_xqe"],
            "horizontal_xqe_achieved": xqe_h_achieved,
            "stacking_xqe_target": results.workload_buckets["stacking_xqe"],
            "stacking_xqe_achieved": xqe_s_achieved,
            "all_targets_met": (
                xpl_achieved + 1e-9 >= results.workload_buckets["horizontal_xpl"]
                and xqe_h_achieved + 1e-9 >= results.workload_buckets["horizontal_xqe"]
                and xqe_s_achieved + 1e-9 >= results.workload_buckets["stacking_xqe"]
            ),
        }

        # --- New inbound / outbound workflow ---
        results.inbound_cycle = xqe122_inbound_average_cycle(
            self.xqe, self.turns, self.distances, self.stacking
        )
        results.outbound_cycle = xqe122_outbound_average_cycle(
            self.xqe, self.turns, self.distances, self.stacking
        )
        results.shuffling_cycle = xqe122_shuffling_average_cycle(
            self.xqe, self.distances, self.stacking
        )

        # FIFO storage model - DYNAMIC simulation with variable inbound/outbound ratio
        results.fifo_model = FIFOStorageModel(
            num_rows=self.stacking.num_rows,
            num_columns=self.stacking.num_columns,
            num_levels=self.stacking.num_levels,
        )

        # Determine block storage policy
        block_policy_cfg = self.config.get("Block_Storage_Policy", {})
        block_policy_raw = block_policy_cfg.get("strategy", "fifo")
        if block_policy_raw in {"column_fifo", "lane_sequence"}:
            block_policy = block_policy_raw
        else:
            block_policy = "fifo"
        results.block_storage_policy = block_policy

        # Dynamic simulation with variable hourly ratios (Option C)
        shuffle_strategy = self.config.get("Shuffle_Configuration", {}).get("strategy", "")
        if block_policy in {"column_fifo", "lane_sequence"}:
            # Column-FIFO / Lane-Sequence modes: no shuffling required
            results.avg_shuffles_per_outbound = 0.0
            # Replace fifo_model with the lane-sequence variant for reporting
            results.fifo_model = LaneSequenceStorageModel(
                num_rows=self.stacking.num_rows,
                num_columns=self.stacking.num_columns,
                num_levels=self.stacking.num_levels,
            )
        elif shuffle_strategy == "alternating_buffer_column_24h":
            alt_result = run_alternating_buffer_simulation(self.config, num_days=2)
            results.avg_shuffles_per_outbound = 0.0
        else:
            results.avg_shuffles_per_outbound = self._simulate_two_zone_shuffles(
                results.fifo_model,
                self.throughput.operating_hours
            )

        # Preliminary fleet sizing (baseline cycles)
        results.inbound_fleet = calculate_fleet_size(
            daily_pallets=self.throughput.effective_inbound_pallets,
            avg_cycle_time_s=results.inbound_cycle.total_time_s,
            operating_hours=self.throughput.operating_hours,
            utilization_target=self.throughput.utilization_target,
            vehicle_type="XQE_122",
            workflow="Inbound",
        )
        results.outbound_fleet = calculate_fleet_size(
            daily_pallets=self.throughput.effective_outbound_pallets,
            avg_cycle_time_s=results.outbound_cycle.total_time_s,
            operating_hours=self.throughput.operating_hours,
            utilization_target=self.throughput.utilization_target,
            vehicle_type="XQE_122",
            workflow="Outbound",
        )
        # Shuffling fleet: extra cycles needed due to FIFO blocking
        shuffling_daily_moves = (
            self.throughput.effective_outbound_pallets * results.avg_shuffles_per_outbound
        )
        results.shuffling_fleet = calculate_fleet_size(
            daily_pallets=max(0.0, shuffling_daily_moves),
            avg_cycle_time_s=results.shuffling_cycle.total_time_s,
            operating_hours=self.throughput.operating_hours,
            utilization_target=self.throughput.utilization_target,
            vehicle_type="XQE_122",
            workflow="Shuffling",
        )

        # Traffic control model (uses baseline cycles for arrival estimation)
        total_agvs = results.total_outbound_fleet_size or 1
        results.traffic_model = TrafficControlModel(
            aisle_widths=self.aisle_widths,
            config=self.traffic_cfg,
            total_agv_count=total_agvs,
            inbound_cycle_s=results.inbound_cycle.total_time_s,
            outbound_cycle_s=results.outbound_cycle.total_time_s,
            operating_hours=self.throughput.operating_hours,
        )

        if traffic_control_enabled and results.traffic_model:
            inbound_wait = results.traffic_model.total_wait_time_inbound_s()
            outbound_wait = results.traffic_model.total_wait_time_outbound_s()
            if inbound_wait > 0:
                results.inbound_cycle.total_time_s += inbound_wait
                results.inbound_cycle.phases.append(
                    CyclePhase("Traffic control wait", inbound_wait, "aisle/intersection delays")
                )
            if outbound_wait > 0:
                results.outbound_cycle.total_time_s += outbound_wait
                results.outbound_cycle.phases.append(
                    CyclePhase("Traffic control wait", outbound_wait, "aisle/intersection delays")
                )

            # Recalculate inbound/outbound fleet sizes with traffic delays
            results.inbound_fleet = calculate_fleet_size(
                daily_pallets=self.throughput.effective_inbound_pallets,
                avg_cycle_time_s=results.inbound_cycle.total_time_s,
                operating_hours=self.throughput.operating_hours,
                utilization_target=self.throughput.utilization_target,
                vehicle_type="XQE_122",
                workflow="Inbound",
            )
            results.outbound_fleet = calculate_fleet_size(
                daily_pallets=self.throughput.effective_outbound_pallets,
                avg_cycle_time_s=results.outbound_cycle.total_time_s,
                operating_hours=self.throughput.operating_hours,
                utilization_target=self.throughput.utilization_target,
                vehicle_type="XQE_122",
                workflow="Outbound",
            )

        return results

    def full_report(self, results: Optional[SimulationResults] = None) -> str:
        """Generate a complete text report."""
        if results is None:
            results = self.run()

        sections = [
            xpl201_workflow_diagram(),
            xqe122_rack_workflow_diagram(),
            xqe122_stacking_workflow_diagram(),
            xqe122_inbound_workflow_diagram(),
            xqe122_outbound_workflow_diagram(),
            xqe122_shuffling_workflow_diagram(),
            rack_capacity_report(results.rack_config),
            stacking_capacity_report(results.stacking_config),
            cycle_time_report("XPL_201 HANDOVER CYCLE TIME", results.xpl_cycle),
            cycle_time_report("XQE_122 RACK STORAGE AVERAGE CYCLE TIME", results.xqe_rack_cycle),
            cycle_time_report("XQE_122 GROUND STACKING AVERAGE CYCLE TIME", results.xqe_stack_cycle),
            cycle_time_report("XQE_122 INBOUND CYCLE TIME (avg)", results.inbound_cycle),
            cycle_time_report("XQE_122 OUTBOUND CYCLE TIME (avg)", results.outbound_cycle),
        ]
        if results.shuffling_cycle and results.shuffling_cycle.total_time_s > 0:
            sections.append(
                cycle_time_report("XQE_122 SHUFFLING CYCLE TIME (avg)", results.shuffling_cycle)
            )
        sections += [
            fleet_report([results.xpl_fleet, results.xqe_rack_fleet, results.xqe_stack_fleet]),
            performance_report(
                results.throughput_config,
                results.xpl_cycle,
                results.xqe_rack_cycle,
                results.xqe_stack_cycle,
                workload_buckets=results.workload_buckets,
                xpl_fleet=results.xpl_fleet,
                xqe_horizontal_fleet=results.xqe_rack_fleet,
                xqe_stacking_fleet=results.xqe_stack_fleet,
                dispatch_throughput_check=results.dispatch_throughput_check,
            ),
        ]
        traffic_text = ""
        if results.traffic_model:
            traffic_text = results.traffic_model.report()
        sections.append(
            outbound_performance_report(
                results.throughput_config,
                results.inbound_cycle,
                results.outbound_cycle,
                results.shuffling_cycle,
                results.inbound_fleet,
                results.outbound_fleet,
                results.shuffling_fleet,
                traffic_report=traffic_text,
                avg_shuffles_per_cycle=results.avg_shuffles_per_outbound,
                block_storage_policy=results.block_storage_policy,
            )
        )
        return "\n".join(sections)


def load_config(path: str) -> Dict[str, Any]:
    """Load a JSON configuration file."""
    with open(path, "r") as f:
        return json.load(f)
