"""
Simulator Module
=================
Orchestrates the PR-2 simulation pipeline:

  1. Load warehouse layout (new JSON config format)
  2. Calculate cycle times for all three workflows
  3. Size fleet for the required throughput
  4. Produce the simulation report

Usage:
  from src.simulator import Simulator
  sim = Simulator("config/config_large.json")
  report = sim.run(tasks_per_hour=50)
  sim.print_report(report)
"""

from typing import Optional

from .warehouse_layout import WarehouseLayout, load_layout
from .cycle_calculator import CycleCalculator
from .fleet_sizer import FleetSizer, FleetSizingReport
from .agv_specs import NARROW_AISLE_THRESHOLD_M, AGV_SPECS


class Simulator:
    """
    Runs the complete PR-2 warehouse AGV simulation pipeline.

    Parameters
    ----------
    config_path : str
        Path to the new-format warehouse config JSON.
    """

    def __init__(self, config_path: str) -> None:
        self.layout = load_layout(config_path)
        self.calc = CycleCalculator(self.layout)

    @classmethod
    def from_layout(cls, layout: WarehouseLayout) -> "Simulator":
        """Construct a Simulator from an already-loaded WarehouseLayout."""
        sim = cls.__new__(cls)
        sim.layout = layout
        sim.calc = CycleCalculator(layout)
        return sim

    def run(self, tasks_per_hour: Optional[float] = None) -> FleetSizingReport:
        """
        Run the simulation and return a FleetSizingReport.

        Parameters
        ----------
        tasks_per_hour : float, optional
            Target throughput.  If None, read from layout throughput config.
        """
        sizer = FleetSizer(self.layout)
        return sizer.size_fleet(tasks_per_hour=tasks_per_hour)

    def print_report(self, report: FleetSizingReport) -> None:
        """Print a formatted simulation report to stdout."""
        lw = self.layout.width_m
        ll = self.layout.length_m

        print(f"\n{'═' * 63}")
        print(f"  Warehouse: {report.warehouse_name} ({ll:.0f}m × {lw:.0f}m)")
        print(f"  Target throughput: {report.total_tasks_per_hour:.0f} tasks/hour")
        print(f"{'═' * 63}")

        # --- Aisle analysis ---
        print("\nAISLE ANALYSIS")
        print(f"{'─' * 63}")
        for aisle in self.layout.storage_aisles:
            name = aisle.get("name", "?")
            atype = aisle.get("type", "?")
            width_m = aisle.get("width_mm", 0) / 1000.0
            is_narrow = width_m < NARROW_AISLE_THRESHOLD_M

            if is_narrow:
                compatible = ["XNA_151 (best)", "XNA_121"]
            else:
                max_h = max(
                    (float(h) for h in aisle.get("shelf_heights", [0])),
                    default=0.0,
                )
                if max_h > 4.5:
                    compatible = ["XQE_122"]
                else:
                    compatible = ["XQE_122", "XPL_201"]

            print(f"\n  {name} ({width_m:.2f}m wide, {atype})")
            print(f"    Compatible AGVs : {', '.join(compatible)}")

            if atype == "rack":
                heights = aisle.get("shelf_heights", [])
                if heights:
                    max_h = max(float(h) for h in heights)
                    rec = "XNA_151" if is_narrow else "XQE_122"
                    print(f"    Recommended     : {rec} (lift to {max_h:.1f}m)")
            elif atype == "ground_stacking":
                print(f"    Recommended     : XQE_122 (stacking)")

        print(f"\n{'═' * 63}")

        # --- Cycle time analysis ---
        print("\nCYCLE TIME ANALYSIS")
        print(f"{'─' * 63}")
        for key, ct in sorted(report.cycle_times.items(), key=lambda x: x[1]):
            label = _format_workflow_label(key)
            print(f"  {label:<30} {ct:>8.1f} seconds")

        print(f"\n{'═' * 63}")

        # --- Fleet sizing ---
        print(f"\nFLEET SIZING ({report.total_tasks_per_hour:.0f} tasks/hour)")
        print(f"{'─' * 63}")
        for r in report.workflow_results:
            label = _format_workflow_label(r.workflow_key)
            util_pct = r.achieved_utilization * 100
            print(f"  {r.agv_type} {label:<20} "
                  f"{r.fleet_size:>3} units ({util_pct:.0f}% util)")

        print(f"\n  Total Fleet: {report.total_fleet} AGVs")
        print(f"{'═' * 63}\n")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _format_workflow_label(key: str) -> str:
    """Convert a workflow key to a concise display label."""
    mapping = {
        "XPL_201_Handover": "XPL_201 Handover:",
        "XQE_122_Rack_Storage": "XQE_122 Rack (avg):",
        "XQE_122_Ground_Stacking": "XQE_122 Stacking:",
    }
    if key in mapping:
        return mapping[key]
    # Strip leading AGV prefix and normalise
    parts = key.split("_", 2)
    if len(parts) >= 3:
        return f"{parts[0]}_{parts[1]} {parts[2]}:"
    return key + ":"
