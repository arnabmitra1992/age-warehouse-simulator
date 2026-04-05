"""
Simulator Orchestrator (PR-2 Pipeline)
=========================================
Main simulation entry point for the mm-based configuration pipeline.
Loads a JSON config, calculates cycle times, sizes the fleet, and
produces a summary report.
"""
import json
import os
from typing import Optional

from .warehouse_layout import WarehouseConfig, load_config, parse_config
from .fleet_sizer import FleetSizer, FleetSizingResult
from .cycle_calculator import CycleCalculator


def is_mm_config(data: dict) -> bool:
    """
    Return True if the JSON data looks like a mm-based (PR-2) config,
    False if it looks like a metres-based (legacy) config.
    """
    if "width_mm" in data or "length_mm" in data:
        return True
    if isinstance(data.get("warehouse"), dict):
        wh = data["warehouse"]
        if "width_mm" in wh or "length_mm" in wh:
            return True
    if "throughput" in data and isinstance(data["throughput"], dict):
        return True
    aisles = data.get("aisles", [])
    if aisles and isinstance(aisles[0], dict):
        if "width_mm" in aisles[0] or "depth_mm" in aisles[0]:
            return True
    return False


class WarehouseSimulator:
    """
    Warehouse AGV Simulator (mm-based pipeline).

    Orchestrates the full pipeline:
    1. Load warehouse config (JSON, mm-based)
    2. Calculate cycle times per workflow
    3. Size AGV fleet per aisle
    4. Generate report
    """

    def __init__(self, config: WarehouseConfig):
        self.config = config
        self.fleet_sizer = FleetSizer(config)
        self.cycle_calculator = CycleCalculator(
            head_aisle_width_m=config.head_aisle_width_mm / 1000.0
        )

    @classmethod
    def from_file(cls, path: str) -> "WarehouseSimulator":
        """Load simulator from a JSON config file."""
        config = load_config(path)
        return cls(config)

    @classmethod
    def from_dict(cls, data: dict) -> "WarehouseSimulator":
        """Load simulator from a config dict."""
        config = parse_config(data)
        return cls(config)

    def run(
        self,
        throughput_per_hour: Optional[float] = None,
        utilization_target: Optional[float] = None,
        verbose: bool = True,
    ) -> FleetSizingResult:
        """
        Run the full simulation pipeline.

        Parameters
        ----------
        throughput_per_hour : float, optional
            Override throughput target. Defaults to config value.
        utilization_target : float, optional
            Override utilization target. Defaults to config value.
        verbose : bool
            Print report to stdout.

        Returns
        -------
        FleetSizingResult
        """
        result = self.fleet_sizer.size_fleet(
            throughput_per_hour=throughput_per_hour,
            utilization_target=utilization_target,
        )
        if verbose:
            result.print_report()
        return result

    def get_cycle_times(self) -> dict:
        """Get cycle times for all aisles."""
        results = {}
        for aisle in self.config.aisles:
            ct = self.cycle_calculator.calculate_for_aisle(aisle)
            results[aisle.name] = ct.to_dict()
        return results
