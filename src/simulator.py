"""
Warehouse AGV Simulator – Main Orchestrator (PR-2 pipeline)
============================================================
Ties together layout loading, rack/stacking capacity, cycle time
calculations, and fleet sizing into a single easy-to-use interface.

Usage (Python API):
    from src.simulator import WarehouseSimulator

    sim = WarehouseSimulator("config/config_medium.json")
    report = sim.run(inbound_tasks=60, outbound_tasks=50)
    report.print_report()
    sim.visualize(report, output_dir="output/medium")

Usage (CLI):
    python main.py run --config config/config_medium.json \\
        --inbound-throughput 60 --outbound-throughput 50
"""

from __future__ import annotations

import json
import os
from typing import Optional

from .warehouse_layout import WarehouseLayoutLoader, WarehouseConfig
from .rack_storage import RackStorage
from .ground_stacking import GroundStackingMultipleLevels
from .cycle_calculator import CycleCalculator
from .fleet_sizer import FleetSizer, FleetSizingReport


class WarehouseSimulator:
    """
    End-to-end warehouse AGV simulator.

    Parameters
    ----------
    config_path : str
        Path to a JSON configuration file (mm-based distances).
    config_dict : dict, optional
        Pre-loaded configuration dict (overrides config_path if provided).
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        config_dict: Optional[dict] = None,
    ) -> None:
        loader = WarehouseLayoutLoader()
        if config_dict is not None:
            self.config: WarehouseConfig = loader.load_dict(config_dict)
        elif config_path is not None:
            self.config = loader.load(config_path)
        else:
            raise ValueError("Either config_path or config_dict must be provided.")

        self._rack_storage: Optional[RackStorage] = None
        self._ground_stacking: Optional[GroundStackingMultipleLevels] = None
        self._setup_storage()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_storage(self) -> None:
        cfg = self.config
        if cfg.rack:
            self._rack_storage = RackStorage(
                aisle_depth_m=cfg.rack.aisle_depth_m,
                pallet_spacing_m=cfg.rack.pallet_spacing_m,
                shelves=cfg.rack.shelves,
            )
        if cfg.stacking:
            self._ground_stacking = GroundStackingMultipleLevels(
                rows=cfg.stacking.rows,
                cols=cfg.stacking.cols,
                levels=cfg.stacking.levels,
                level_height_m=cfg.stacking.level_height_m,
                area_length_m=cfg.stacking.area_length_m,
                area_width_m=cfg.stacking.area_width_m,
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        inbound_tasks: Optional[int] = None,
        outbound_tasks: Optional[int] = None,
        inbound_hours: Optional[float] = None,
        outbound_hours: Optional[float] = None,
        inbound_utilization: Optional[float] = None,
        outbound_utilization: Optional[float] = None,
    ) -> FleetSizingReport:
        """
        Run the full fleet sizing simulation.

        Parameters
        ----------
        inbound_tasks : int, optional
            Daily inbound tasks (overrides config value).
        outbound_tasks : int, optional
            Daily outbound tasks (overrides config value).
        inbound_hours : float, optional
            Inbound operating hours per day (overrides config value).
        outbound_hours : float, optional
            Outbound operating hours per day (overrides config value).
        inbound_utilization : float, optional
            Inbound utilization target 0–1 (overrides config value).
        outbound_utilization : float, optional
            Outbound utilization target 0–1 (overrides config value).

        Returns
        -------
        FleetSizingReport
        """
        sizer = FleetSizer(
            config=self.config,
            inbound_tasks_per_day=inbound_tasks,
            outbound_tasks_per_day=outbound_tasks,
            inbound_hours=inbound_hours,
            outbound_hours=outbound_hours,
            inbound_utilization=inbound_utilization,
            outbound_utilization=outbound_utilization,
        )
        return sizer.calculate()

    def visualize(
        self,
        report: FleetSizingReport,
        output_dir: str = "output",
    ) -> None:
        """
        Generate publication-quality charts for a completed report.

        Parameters
        ----------
        report : FleetSizingReport
        output_dir : str
            Directory where charts are saved.
        """
        try:
            from .visualizer import SimulatorVisualizer
            vis = SimulatorVisualizer(self.config)
            vis.generate_all(report, output_dir=output_dir)
        except ImportError:
            print("  ⚠ Visualization unavailable – matplotlib not installed.")

    def print_capacity_summary(self) -> None:
        """Print storage capacity summary."""
        cfg = self.config
        print(f"\n{'─' * 60}")
        print(f"  Warehouse: {cfg.name}")
        print(f"  Dimensions: {cfg.width_m:.0f} m × {cfg.length_m:.0f} m")
        if self._rack_storage:
            print(f"\n{self._rack_storage.summary()}")
        if self._ground_stacking:
            print(f"\n{self._ground_stacking.summary()}")
        print(f"{'─' * 60}")

    def save_report(
        self,
        report: FleetSizingReport,
        output_dir: str = "output",
    ) -> str:
        """Save report as JSON and return the file path."""
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "fleet_sizing_report.json")
        with open(path, "w") as fh:
            json.dump(report.to_dict(), fh, indent=2)
        return path
