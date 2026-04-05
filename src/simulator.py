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
from .warehouse_layout import WarehouseDistances, distances_from_dict
from .rack_storage import RackConfig, rack_config_from_dict
from .ground_stacking import GroundStackingConfig, ground_stacking_config_from_dict
from .cycle_calculator import (
    xpl201_handover_cycle,
    xqe122_rack_average_cycle,
    xqe122_stacking_average_cycle,
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
    rack_capacity_report,
    stacking_capacity_report,
    cycle_time_report,
    fleet_report,
    performance_report,
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

    @property
    def total_fleet_size(self) -> int:
        total = 0
        for r in [self.xpl_fleet, self.xqe_rack_fleet, self.xqe_stack_fleet]:
            if r:
                total += r.fleet_size
        return total

    def to_dict(self) -> Dict[str, Any]:
        return {
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
        self.rack = rack_config_from_dict(self.config.get("Rack_Configuration", {}))
        self.stacking = ground_stacking_config_from_dict(
            self.config.get("Ground_Stacking_Configuration", {})
        )
        self.throughput = throughput_config_from_dict(
            self.config.get("Throughput_Configuration", {})
        )

    def run(self) -> SimulationResults:
        """Execute the full simulation and return results."""
        self.throughput.validate()
        results = SimulationResults()
        results.rack_config = self.rack
        results.stacking_config = self.stacking
        results.throughput_config = self.throughput

        # Cycle time calculations
        results.xpl_cycle = xpl201_handover_cycle(self.xpl, self.turns, self.distances)
        results.xqe_rack_cycle = xqe122_rack_average_cycle(
            self.xqe, self.turns, self.distances, self.rack
        )
        results.xqe_stack_cycle = xqe122_stacking_average_cycle(
            self.xqe, self.turns, self.distances, self.stacking
        )

        # Fleet sizing
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
        return results

    def full_report(self, results: Optional[SimulationResults] = None) -> str:
        """Generate a complete text report."""
        if results is None:
            results = self.run()

        sections = [
            xpl201_workflow_diagram(),
            xqe122_rack_workflow_diagram(),
            xqe122_stacking_workflow_diagram(),
            rack_capacity_report(results.rack_config),
            stacking_capacity_report(results.stacking_config),
            cycle_time_report("XPL_201 HANDOVER CYCLE TIME", results.xpl_cycle),
            cycle_time_report("XQE_122 RACK STORAGE AVERAGE CYCLE TIME", results.xqe_rack_cycle),
            cycle_time_report("XQE_122 GROUND STACKING AVERAGE CYCLE TIME", results.xqe_stack_cycle),
            fleet_report([results.xpl_fleet, results.xqe_rack_fleet, results.xqe_stack_fleet]),
            performance_report(
                results.throughput_config,
                results.xpl_cycle,
                results.xqe_rack_cycle,
                results.xqe_stack_cycle,
            ),
        ]
        return "\n".join(sections)


def load_config(path: str) -> Dict[str, Any]:
    """Load a JSON configuration file."""
    with open(path, "r") as f:
        return json.load(f)
