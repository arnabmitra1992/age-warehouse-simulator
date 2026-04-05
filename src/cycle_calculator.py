"""
Unified Cycle Time Calculator
==============================
Provides a single interface for calculating cycle times for all
supported AGV workflows:
  - XPL_201 Handover
  - XQE_122 Rack Storage
  - XQE_122 Ground Stacking

All distances in the input can be in metres or mm (specify unit).
"""
import math
from dataclasses import dataclass
from typing import Dict, Optional, Union

from .handover_workflow import calculate_handover_cycle, HandoverCycleResult
from .rack_storage import calculate_rack_storage_cycle, RackStorageCycleResult, RackLayoutInfo
from .ground_stacking import calculate_ground_stacking_cycle, GroundStackingCycleResult, lift_height_for_level
from .warehouse_layout import AisleConfig

WORKFLOW_XPL_HANDOVER = "xpl_handover"
WORKFLOW_XQE_RACK = "xqe_rack"
WORKFLOW_XQE_STACKING = "xqe_stacking"


@dataclass
class CycleTimeResult:
    """Summary cycle time result for a workflow."""
    workflow: str
    agv_type: str
    aisle_name: str
    avg_cycle_time_s: float
    min_cycle_time_s: float
    max_cycle_time_s: float
    details: dict

    @property
    def tasks_per_hour(self) -> float:
        if self.avg_cycle_time_s <= 0:
            return 0.0
        return 3600.0 / self.avg_cycle_time_s

    def to_dict(self) -> dict:
        return {
            "workflow": self.workflow,
            "agv_type": self.agv_type,
            "aisle": self.aisle_name,
            "avg_cycle_time_s": round(self.avg_cycle_time_s, 2),
            "min_cycle_time_s": round(self.min_cycle_time_s, 2),
            "max_cycle_time_s": round(self.max_cycle_time_s, 2),
            "tasks_per_hour": round(self.tasks_per_hour, 2),
            "details": self.details,
        }


class CycleCalculator:
    """
    Calculates cycle times for all warehouse AGV workflows.

    Takes warehouse layout information and computes realistic
    cycle times using the appropriate AGV physics model.
    """

    def __init__(self, head_aisle_width_m: float = 4.0):
        self.head_aisle_width_m = head_aisle_width_m

    def calculate_for_aisle(
        self,
        aisle: AisleConfig,
        d_head_aisle_m: Optional[float] = None,
        num_turns: int = 2,
    ) -> CycleTimeResult:
        """
        Calculate average cycle time for a given aisle configuration.

        Automatically selects the appropriate workflow based on aisle type.

        Parameters
        ----------
        aisle : AisleConfig
            Aisle configuration with type and dimensions.
        d_head_aisle_m : float, optional
            Distance along head aisle. If None, defaults to head_aisle_width_m / 2.
        num_turns : int
            Number of 90-degree turns in the path.
        """
        if d_head_aisle_m is None:
            d_head_aisle_m = self.head_aisle_width_m / 2.0

        d_aisle_m = aisle.depth_m / 2.0  # average position is halfway

        aisle_type = aisle.aisle_type.lower()

        if aisle_type == "handover":
            return self._calc_handover(aisle, d_head_aisle_m, d_aisle_m, num_turns)
        elif aisle_type == "rack":
            return self._calc_rack(aisle, d_head_aisle_m, d_aisle_m, num_turns)
        elif aisle_type in ("ground_stacking", "stacking"):
            return self._calc_stacking(aisle, d_head_aisle_m, d_aisle_m, num_turns)
        else:
            return self._calc_rack(aisle, d_head_aisle_m, d_aisle_m, num_turns)

    def _calc_handover(
        self, aisle: AisleConfig, d_head_m: float, d_aisle_m: float, num_turns: int
    ) -> CycleTimeResult:
        result = calculate_handover_cycle(
            d_to_dock_m=d_head_m,
            d_to_handover_m=d_aisle_m,
            num_turns=num_turns,
        )
        ct = result.total_cycle_time
        return CycleTimeResult(
            workflow=WORKFLOW_XPL_HANDOVER,
            agv_type="XPL_201",
            aisle_name=aisle.name,
            avg_cycle_time_s=ct,
            min_cycle_time_s=ct * 0.9,
            max_cycle_time_s=ct * 1.1,
            details=result.to_dict(),
        )

    def _calc_rack(
        self, aisle: AisleConfig, d_head_m: float, d_aisle_m: float, num_turns: int
    ) -> CycleTimeResult:
        layout = RackLayoutInfo(
            aisle_depth_mm=aisle.depth_mm,
            shelf_heights_mm=aisle.shelf_heights_mm if aisle.shelf_heights_mm else [0, 1200, 2400, 3600],
        )
        avg_lift_m = layout.avg_shelf_height_m
        result = calculate_rack_storage_cycle(
            d_head_aisle_m=d_head_m,
            d_aisle_m=d_aisle_m,
            lift_height_m=avg_lift_m,
            num_turns=num_turns,
        )
        ct = result.total_cycle_time
        min_h = min(layout.shelf_heights_mm) / 1000.0
        max_h = max(layout.shelf_heights_mm) / 1000.0
        min_result = calculate_rack_storage_cycle(d_head_m, d_aisle_m, min_h, num_turns)
        max_result = calculate_rack_storage_cycle(d_head_m, d_aisle_m, max_h, num_turns)
        return CycleTimeResult(
            workflow=WORKFLOW_XQE_RACK,
            agv_type="XQE_122",
            aisle_name=aisle.name,
            avg_cycle_time_s=ct,
            min_cycle_time_s=min_result.total_cycle_time,
            max_cycle_time_s=max_result.total_cycle_time,
            details=result.to_dict(),
        )

    def _calc_stacking(
        self, aisle: AisleConfig, d_head_m: float, d_aisle_m: float, num_turns: int
    ) -> CycleTimeResult:
        max_levels = max(1, aisle.stacking_levels)
        cycle_times = []
        for level in range(max_levels):
            r = calculate_ground_stacking_cycle(
                d_head_aisle_m=d_head_m,
                d_aisle_m=d_aisle_m,
                stacking_level=level,
                num_turns=num_turns,
            )
            cycle_times.append(r.total_cycle_time)
        avg_ct = sum(cycle_times) / len(cycle_times)
        avg_level = max_levels // 2
        detail_result = calculate_ground_stacking_cycle(d_head_m, d_aisle_m, avg_level, num_turns)
        return CycleTimeResult(
            workflow=WORKFLOW_XQE_STACKING,
            agv_type="XQE_122",
            aisle_name=aisle.name,
            avg_cycle_time_s=avg_ct,
            min_cycle_time_s=min(cycle_times),
            max_cycle_time_s=max(cycle_times),
            details=detail_result.to_dict(),
        )
