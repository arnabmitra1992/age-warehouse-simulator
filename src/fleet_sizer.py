"""
Fleet Sizer Module
===================
Calculates fleet sizes for XPL_201 handover, XQE_122 rack storage, and
XQE_122 ground stacking workflows using the PR-2 cycle times.

Fleet sizing formula:
  tasks_per_agv_hr = 3600 / cycle_time_s
  agvs_needed      = ceil(tasks_per_hour / (tasks_per_agv_hr × utilization))

Workflow split is driven by the throughput config in the warehouse layout:
  xpl_percentage           → fraction of tasks going through handover
  xqe_rack_percentage      → fraction going to rack storage
  xqe_stacking_percentage  → fraction going to ground stacking
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .warehouse_layout import WarehouseLayout
from .cycle_calculator import CycleCalculator


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class WorkflowFleetResult:
    """Fleet sizing result for a single workflow."""

    workflow_key: str      # e.g. 'XPL_201_Handover', 'XQE_122_Rack_Aisle 1', ...
    agv_type: str
    tasks_per_hour: float
    cycle_time_s: float
    utilization_target: float

    fleet_size: int = 0
    tasks_per_agv_hr: float = 0.0
    achieved_utilization: float = 0.0

    def to_dict(self) -> dict:
        return {
            "workflow": self.workflow_key,
            "agv_type": self.agv_type,
            "tasks_per_hour": round(self.tasks_per_hour, 2),
            "cycle_time_s": round(self.cycle_time_s, 2),
            "fleet_size": self.fleet_size,
            "tasks_per_agv_hr": round(self.tasks_per_agv_hr, 2),
            "utilization_pct": round(self.achieved_utilization * 100, 1),
            "utilization_target_pct": round(self.utilization_target * 100, 1),
        }


@dataclass
class FleetSizingReport:
    """Complete fleet sizing report for a warehouse configuration."""

    warehouse_name: str
    total_tasks_per_hour: float
    utilization_target: float
    workflow_results: List[WorkflowFleetResult] = field(default_factory=list)
    cycle_times: Dict[str, float] = field(default_factory=dict)

    @property
    def total_fleet(self) -> int:
        return sum(r.fleet_size for r in self.workflow_results)

    def to_dict(self) -> dict:
        return {
            "warehouse": self.warehouse_name,
            "total_tasks_per_hour": self.total_tasks_per_hour,
            "utilization_target_pct": round(self.utilization_target * 100, 1),
            "total_fleet": self.total_fleet,
            "cycle_times_s": {k: round(v, 2) for k, v in self.cycle_times.items()},
            "workflows": [r.to_dict() for r in self.workflow_results],
        }


# ---------------------------------------------------------------------------
# FleetSizer
# ---------------------------------------------------------------------------

class FleetSizer:
    """
    Sizes the AGV fleet for the three PR-2 workflows.

    Parameters
    ----------
    layout : WarehouseLayout
        Loaded warehouse layout with throughput config.
    utilization_target : float
        Target AGV utilization, default read from layout or 0.75.
    """

    _AGV_WORKFLOW_MAP: Dict[str, str] = {
        "XPL_201_Handover": "XPL_201",
    }

    def __init__(
        self,
        layout: WarehouseLayout,
        utilization_target: Optional[float] = None,
    ) -> None:
        self.layout = layout
        self.calc = CycleCalculator(layout)
        tpt = layout.throughput_config
        self.utilization_target = (
            utilization_target
            if utilization_target is not None
            else float(tpt.get("utilization_target", 0.75))
        )

    def size_fleet(self, tasks_per_hour: Optional[float] = None) -> FleetSizingReport:
        """
        Calculate fleet sizes for all workflows.

        Parameters
        ----------
        tasks_per_hour : float, optional
            Override total tasks/hour.  If None, uses the layout's throughput config
            (daily_pallets / operating_hours).

        Returns
        -------
        FleetSizingReport
        """
        tpt = self.layout.throughput_config
        if tasks_per_hour is None:
            daily = float(tpt.get("daily_pallets", 1000))
            hours = float(tpt.get("operating_hours", 16))
            tasks_per_hour = daily / hours

        # Workflow split
        xpl_pct = float(tpt.get("xpl_percentage", 30)) / 100.0
        xqe_rack_pct = float(tpt.get("xqe_rack_percentage", 50)) / 100.0
        xqe_stack_pct = float(tpt.get("xqe_stacking_percentage", 20)) / 100.0

        # Normalise if they don't add up to 1
        total_pct = xpl_pct + xqe_rack_pct + xqe_stack_pct
        if total_pct > 0:
            xpl_pct /= total_pct
            xqe_rack_pct /= total_pct
            xqe_stack_pct /= total_pct

        cycle_times = self.calc.all_cycle_times()
        report = FleetSizingReport(
            warehouse_name=self.layout.name,
            total_tasks_per_hour=tasks_per_hour,
            utilization_target=self.utilization_target,
            cycle_times=cycle_times,
        )

        # --- Handover workflow ---
        if "XPL_201_Handover" in cycle_times:
            ct = cycle_times["XPL_201_Handover"]
            tph_workflow = tasks_per_hour * xpl_pct
            report.workflow_results.append(
                self._size_workflow("XPL_201_Handover", "XPL_201", ct, tph_workflow)
            )

        # --- Rack storage workflow(s) ---
        rack_keys = sorted(k for k in cycle_times if k.startswith("XQE_122_Rack_"))
        if rack_keys:
            avg_rack_ct = sum(cycle_times[k] for k in rack_keys) / len(rack_keys)
            tph_workflow = tasks_per_hour * xqe_rack_pct
            report.workflow_results.append(
                self._size_workflow("XQE_122_Rack_Storage", "XQE_122", avg_rack_ct, tph_workflow)
            )

        # --- Ground stacking workflow(s) ---
        stack_keys = sorted(k for k in cycle_times if k.startswith("XQE_122_Stacking_"))
        if stack_keys:
            avg_stack_ct = sum(cycle_times[k] for k in stack_keys) / len(stack_keys)
            tph_workflow = tasks_per_hour * xqe_stack_pct
            report.workflow_results.append(
                self._size_workflow("XQE_122_Ground_Stacking", "XQE_122", avg_stack_ct, tph_workflow)
            )

        return report

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _size_workflow(
        self,
        workflow_key: str,
        agv_type: str,
        cycle_time_s: float,
        tasks_per_hour: float,
    ) -> WorkflowFleetResult:
        tph_per_agv = 3600.0 / cycle_time_s
        fleet = math.ceil(tasks_per_hour / (tph_per_agv * self.utilization_target))
        fleet = max(fleet, 1)
        achieved_util = tasks_per_hour / (fleet * tph_per_agv) if fleet > 0 else 0.0

        return WorkflowFleetResult(
            workflow_key=workflow_key,
            agv_type=agv_type,
            tasks_per_hour=tasks_per_hour,
            cycle_time_s=cycle_time_s,
            utilization_target=self.utilization_target,
            fleet_size=fleet,
            tasks_per_agv_hr=tph_per_agv,
            achieved_utilization=min(achieved_util, 1.0),
        )
