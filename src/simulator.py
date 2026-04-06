"""
Main simulation orchestrator.
Combines all modules to produce a complete simulation report.
"""
import json
import csv
import io
from dataclasses import asdict
from typing import Dict, Any, Optional

from .agv_specs import XQE122Specs, XPL201Specs, TurnSpecs, xqe122_from_dict, xpl201_from_dict
from .warehouse_layout import WarehouseDistances, AisleWidths, distances_from_dict, aisle_widths_from_dict
from .rack_storage import RackConfig, rack_config_from_dict
from .ground_stacking import GroundStackingConfig, ground_stacking_config_from_dict
from .fifo_storage import FIFOStorageModel
from .traffic_control import TrafficControlConfig, TrafficControlModel, traffic_control_config_from_dict
from .cycle_calculator import (
    xpl201_handover_cycle,
    xqe122_rack_average_cycle,
    xqe122_stacking_average_cycle,
    xqe122_inbound_average_cycle,
    xqe122_outbound_average_cycle,
    xqe122_shuffling_average_cycle,
    CycleResult,
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
                "total": self.total_fleet_size,
            },
        }
        # Outbound workflow metrics (if computed)
        if self.inbound_cycle or self.outbound_cycle:
            base["outbound_workflow"] = {
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

        # --- Legacy cycle time calculations (kept for backward compatibility) ---
        results.xpl_cycle = xpl201_handover_cycle(self.xpl, self.turns, self.distances)
        results.xqe_rack_cycle = xqe122_rack_average_cycle(
            self.xqe, self.turns, self.distances, self.rack
        )
        results.xqe_stack_cycle = xqe122_stacking_average_cycle(
            self.xqe, self.turns, self.distances, self.stacking
        )

        # --- Legacy fleet sizing ---
        results.xpl_fleet = calculate_fleet_size(
            daily_pallets=self.throughput.xpl201_daily_pallets,
            avg_cycle_time_s=results.xpl_cycle.total_time_s,
            operating_hours=self.throughput.operating_hours,
            utilization_target=self.throughput.utilization_target,
            vehicle_type="XPL_201",
            workflow="Handover",
        )
        results.xqe_rack_fleet = calculate_fleet_size(
            daily_pallets=self.throughput.xqe_rack_daily_pallets,
            avg_cycle_time_s=results.xqe_rack_cycle.total_time_s,
            operating_hours=self.throughput.operating_hours,
            utilization_target=self.throughput.utilization_target,
            vehicle_type="XQE_122",
            workflow="Rack Storage",
        )
        results.xqe_stack_fleet = calculate_fleet_size(
            daily_pallets=self.throughput.xqe_stacking_daily_pallets,
            avg_cycle_time_s=results.xqe_stack_cycle.total_time_s,
            operating_hours=self.throughput.operating_hours,
            utilization_target=self.throughput.utilization_target,
            vehicle_type="XQE_122",
            workflow="Ground Stacking",
        )

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
        
        # Dynamic simulation with variable hourly ratios (Option C)
        results.avg_shuffles_per_outbound = self._simulate_dynamic_shuffles(
            results.fifo_model,
            self.throughput.operating_hours
        )

        # Fleet sizing for inbound / outbound
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

        # Traffic control model
        total_agvs = results.total_outbound_fleet_size or 1
        results.traffic_model = TrafficControlModel(
            aisle_widths=self.aisle_widths,
            config=self.traffic_cfg,
            total_agv_count=total_agvs,
            inbound_cycle_s=results.inbound_cycle.total_time_s,
            outbound_cycle_s=results.outbound_cycle.total_time_s,
            operating_hours=self.throughput.operating_hours,
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
            )
        )
        return "\n".join(sections)


def load_config(path: str) -> Dict[str, Any]:
    """Load a JSON configuration file."""
    with open(path, "r") as f:
        return json.load(f)
