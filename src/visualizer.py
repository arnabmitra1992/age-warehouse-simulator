"""
Visualizer Module
==================
Text-based report output for the PR-2 fleet sizer.
Reuses this module as a thin wrapper over the Simulator's print_report()
and also exports a convenience function for standalone use.
"""

from .simulator import Simulator
from .fleet_sizer import FleetSizingReport
from .warehouse_layout import WarehouseLayout


def print_fleet_report(report: FleetSizingReport, layout: WarehouseLayout) -> None:
    """Print a formatted fleet sizing report."""
    sim = Simulator.from_layout(layout)
    sim.print_report(report)
