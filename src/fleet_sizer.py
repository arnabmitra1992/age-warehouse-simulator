"""
Fleet Sizer Module (PR-2 Pipeline)
====================================
Fleet sizing for the mm-based configuration pipeline.
Uses cycle times from CycleCalculator to determine AGV fleet requirements.

Fleet sizing formula:
  tasks_per_agv_per_hour = 3600 / cycle_time_s
  agvs_needed = ceil(target_throughput / (tasks_per_agv_per_hour * utilization_target))
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .warehouse_layout import WarehouseConfig, AisleConfig
from .cycle_calculator import CycleCalculator, CycleTimeResult, WORKFLOW_XPL_HANDOVER, WORKFLOW_XQE_RACK, WORKFLOW_XQE_STACKING
from .agv_specs import XNA_MAX_AISLE_WIDTH


@dataclass
class AisleFleetResult:
    """Fleet sizing result for a single aisle."""
    aisle_name: str
    aisle_type: str
    agv_type: str
    workflow: str
    cycle_time_s: float
    tasks_per_agv_per_hour: float
    required_agvs: int
    utilization: float
    throughput_per_hour: float
    is_bottleneck: bool = False

    def to_dict(self) -> dict:
        return {
            "aisle": self.aisle_name,
            "type": self.aisle_type,
            "agv": self.agv_type,
            "workflow": self.workflow,
            "cycle_time_s": round(self.cycle_time_s, 2),
            "tasks_per_agv_per_hour": round(self.tasks_per_agv_per_hour, 2),
            "required_agvs": self.required_agvs,
            "utilization_pct": round(self.utilization * 100, 1),
            "throughput_per_hour": round(self.throughput_per_hour, 2),
            "is_bottleneck": self.is_bottleneck,
        }


@dataclass
class FleetSizingResult:
    """Complete fleet sizing result for a warehouse."""
    warehouse_name: str
    throughput_per_hour: float
    utilization_target: float
    aisle_results: List[AisleFleetResult] = field(default_factory=list)
    total_xpl_agvs: int = 0
    total_xqe_agvs: int = 0
    bottleneck_aisles: List[str] = field(default_factory=list)

    @property
    def total_agvs(self) -> int:
        return self.total_xpl_agvs + self.total_xqe_agvs

    def to_dict(self) -> dict:
        return {
            "warehouse": self.warehouse_name,
            "throughput_per_hour": round(self.throughput_per_hour, 2),
            "utilization_target_pct": round(self.utilization_target * 100, 1),
            "total_xpl_201_agvs": self.total_xpl_agvs,
            "total_xqe_122_agvs": self.total_xqe_agvs,
            "total_agvs": self.total_agvs,
            "bottleneck_aisles": self.bottleneck_aisles,
            "aisle_results": [r.to_dict() for r in self.aisle_results],
        }

    def print_report(self) -> None:
        print(f"\n{'=' * 65}")
        print(f"  FLEET SIZING REPORT: {self.warehouse_name}")
        print(f"{'=' * 65}")
        print(f"  Target throughput: {self.throughput_per_hour:.1f} pallets/hour")
        print(f"  Utilization target: {self.utilization_target*100:.0f}%")
        print()
        print(f"  {'Aisle':<12} {'Type':<12} {'AGV':<12} {'Cycle(s)':<10} {'AGVs':<6} {'Util%':<8}")
        print(f"  {'-'*12} {'-'*12} {'-'*12} {'-'*10} {'-'*6} {'-'*8}")
        for r in self.aisle_results:
            flag = " ← BOTTLENECK" if r.is_bottleneck else ""
            print(f"  {r.aisle_name:<12} {r.aisle_type:<12} {r.agv_type:<12} "
                  f"{r.cycle_time_s:<10.1f} {r.required_agvs:<6} {r.utilization*100:<8.1f}{flag}")
        print()
        print(f"  XPL_201 AGVs required: {self.total_xpl_agvs}")
        print(f"  XQE_122 AGVs required: {self.total_xqe_agvs}")
        print(f"  TOTAL AGVs required:   {self.total_agvs}")
        if self.bottleneck_aisles:
            print(f"\n  Bottleneck aisles: {', '.join(self.bottleneck_aisles)}")
        print(f"{'=' * 65}\n")


class FleetSizer:
    """
    Fleet sizing calculator for the mm-based pipeline.

    Determines the number of XPL_201 and XQE_122 AGVs needed to meet
    a target throughput, with bottleneck detection.
    """

    def __init__(self, config: WarehouseConfig):
        self.config = config
        self.calculator = CycleCalculator(
            head_aisle_width_m=config.head_aisle_width_mm / 1000.0
        )

    def size_fleet(
        self,
        throughput_per_hour: Optional[float] = None,
        utilization_target: Optional[float] = None,
    ) -> FleetSizingResult:
        """
        Size the AGV fleet for the configured warehouse.

        Parameters
        ----------
        throughput_per_hour : float, optional
            Target throughput in pallets/hour. Defaults to config value.
        utilization_target : float, optional
            Target AGV utilization (0-1). Defaults to config value.

        Returns
        -------
        FleetSizingResult with per-aisle breakdown and totals.
        """
        if throughput_per_hour is None:
            throughput_per_hour = self.config.throughput_per_hour
        if utilization_target is None:
            utilization_target = self.config.utilization_target

        aisle_results = []

        for aisle in self.config.aisles:
            agv_type = self._select_agv(aisle)
            if agv_type is None:
                continue

            ct_result = self.calculator.calculate_for_aisle(aisle)
            cycle_time_s = ct_result.avg_cycle_time_s

            tasks_per_agv_hr = 3600.0 / cycle_time_s if cycle_time_s > 0 else 0
            agvs_needed = math.ceil(
                throughput_per_hour / (tasks_per_agv_hr * utilization_target)
            ) if tasks_per_agv_hr > 0 else 1

            actual_util = throughput_per_hour / (agvs_needed * tasks_per_agv_hr) if tasks_per_agv_hr > 0 else 0

            aisle_result = AisleFleetResult(
                aisle_name=aisle.name,
                aisle_type=aisle.aisle_type,
                agv_type=agv_type,
                workflow=ct_result.workflow,
                cycle_time_s=cycle_time_s,
                tasks_per_agv_per_hour=tasks_per_agv_hr,
                required_agvs=agvs_needed,
                utilization=actual_util,
                throughput_per_hour=throughput_per_hour,
            )
            aisle_results.append(aisle_result)

        if aisle_results:
            min_tph = min(r.tasks_per_agv_per_hour for r in aisle_results if r.tasks_per_agv_per_hour > 0)
            bottleneck_threshold = min_tph * 1.1
            for r in aisle_results:
                if r.tasks_per_agv_per_hour <= bottleneck_threshold:
                    r.is_bottleneck = True

        bottleneck_aisles = [r.aisle_name for r in aisle_results if r.is_bottleneck]

        total_xpl = sum(r.required_agvs for r in aisle_results if r.agv_type == "XPL_201")
        total_xqe = sum(r.required_agvs for r in aisle_results if r.agv_type == "XQE_122")

        return FleetSizingResult(
            warehouse_name=self.config.name,
            throughput_per_hour=throughput_per_hour,
            utilization_target=utilization_target,
            aisle_results=aisle_results,
            total_xpl_agvs=total_xpl,
            total_xqe_agvs=total_xqe,
            bottleneck_aisles=bottleneck_aisles,
        )

    def _select_agv(self, aisle: AisleConfig) -> Optional[str]:
        """
        Select the appropriate AGV type for an aisle.

        XNA models: ONLY for aisles < 2.5m width.
        XPL_201: For handover and ground operations (width >= 2.6m).
        XQE_122: For rack and stacking (width >= 2.84m).
        """
        aisle_type = aisle.aisle_type.lower()
        width_m = aisle.width_m

        # XNA constraint: only for narrow aisles < 2.5m
        if width_m < XNA_MAX_AISLE_WIDTH:
            return None

        if aisle_type in ("handover", "ground_storage"):
            if width_m >= 2.6:
                return "XPL_201"
        elif aisle_type in ("rack",):
            if width_m >= 2.84:
                return "XQE_122"
        elif aisle_type in ("ground_stacking", "stacking"):
            if width_m >= 2.84:
                return "XQE_122"
            elif width_m >= 2.6:
                return "XPL_201"

        return "XQE_122"  # default
