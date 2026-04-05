"""
Fleet Sizer Module
===================
Calculates the minimum number of AGVs required to meet throughput targets,
applying the correct AGV selection and handover decision logic.

Fleet Sizing Formula:
  fleet = ceil( (daily_tasks × avg_cycle_time_s) / (hours × 3600 × utilization) )

AGV Selection Logic (aisle-width-first):
  ≥ 2.84 m  → XQE_122  (distance-based handover)
  2.0–2.84 m → XSC_PENDING (no fleet calculation possible)
  1.717–2.0 m → XNA  (always handover)
  < 1.717 m  → Too narrow (no compatible AGV)

Handover Decisions:
  XNA (narrow aisle): ALWAYS handover, regardless of distance.
  XQE (standard): handover only if inbound↔handover or handover↔outbound ≥ 50 m.
  Ground stacking: XQE_122 ONLY (XSC cannot floor-stack). Same distance logic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .warehouse_layout import (
    WarehouseConfig,
    AisleCompatibilityResult,
    ThroughputConfig,
    HANDOVER_DISTANCE_THRESHOLD_M,
    select_agv_for_rack_aisle,
    select_agv_for_ground_stacking,
    needs_handover_xqe,
)
from .cycle_calculator import CycleCalculator, CycleTimeResult


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------

@dataclass
class WorkflowCycleTime:
    """Cycle time for a specific workflow scenario (AGV + direction + storage)."""

    direction: str           # 'inbound' or 'outbound'
    storage_type: str        # 'rack' or 'stacking'
    agv_type: str
    uses_handover: bool
    avg_cycle_time_s: float
    phases: Dict[str, float] = field(default_factory=dict)  # phase → seconds

    @property
    def avg_cycle_time_min(self) -> float:
        return self.avg_cycle_time_s / 60.0


@dataclass
class FleetRequirement:
    """Fleet count for a specific AGV type and workflow."""

    agv_type: str
    direction: str
    storage_type: str
    fleet_size: int
    daily_tasks: int
    avg_cycle_time_s: float
    operating_hours: float
    utilization: float
    actual_utilization: float


@dataclass
class FleetSizingReport:
    """Complete fleet sizing report for a warehouse configuration."""

    warehouse_name: str

    rack_compatibility: Optional[AisleCompatibilityResult] = None
    stacking_compatibility: AisleCompatibilityResult = field(
        default_factory=lambda: AisleCompatibilityResult(
            "XQE_122", "ok", "Ground stacking – XQE_122 only", compatible_agvs=["XQE_122"]
        )
    )

    inbound_rack_wct: Optional[WorkflowCycleTime] = None
    inbound_stacking_wct: Optional[WorkflowCycleTime] = None
    outbound_rack_wct: Optional[WorkflowCycleTime] = None
    outbound_stacking_wct: Optional[WorkflowCycleTime] = None

    fleet_requirements: List[FleetRequirement] = field(default_factory=list)

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    @property
    def total_xpl_fleet(self) -> int:
        return sum(
            r.fleet_size for r in self.fleet_requirements if r.agv_type == "XPL_201"
        )

    @property
    def total_xqe_fleet(self) -> int:
        return sum(
            r.fleet_size for r in self.fleet_requirements if r.agv_type == "XQE_122"
        )

    @property
    def total_xna_fleet(self) -> int:
        return sum(
            r.fleet_size for r in self.fleet_requirements
            if r.agv_type in ("XNA", "XNA_121", "XNA_151")
        )

    def print_report(self) -> None:
        print(f"\n{'═' * 70}")
        print(f"  FLEET SIZING REPORT – {self.warehouse_name}")
        print(f"{'═' * 70}")

        if self.errors:
            for e in self.errors:
                print(f"  ❌ {e}")
        if self.warnings:
            for w in self.warnings:
                print(f"  ⚠️  {w}")

        if self.rack_compatibility:
            prefix = "✅" if self.rack_compatibility.is_ok else "❌"
            print(f"\n  Rack aisle: {prefix} {self.rack_compatibility.note}")
        print(f"  Stacking  : ✅ {self.stacking_compatibility.note}")

        if not self.is_valid:
            print(f"\n  Cannot calculate fleet – see errors above.")
            print(f"{'═' * 70}\n")
            return

        print(f"\n  {'DIRECTION':<10} {'STORAGE':<12} {'AGV':<10} "
              f"{'HANDOVER':<10} {'CYCLE(s)':>9} {'CYCLE(m)':>9}")
        print(f"  {'-' * 64}")

        for wct in [
            self.inbound_rack_wct, self.inbound_stacking_wct,
            self.outbound_rack_wct, self.outbound_stacking_wct,
        ]:
            if wct is None:
                continue
            hv = "YES" if wct.uses_handover else "NO"
            print(f"  {wct.direction:<10} {wct.storage_type:<12} {wct.agv_type:<10} "
                  f"{hv:<10} {wct.avg_cycle_time_s:>9.1f} {wct.avg_cycle_time_min:>9.2f}")

        print(f"\n  {'DIRECTION':<10} {'STORAGE':<12} {'AGV':<10} "
              f"{'TASKS/DAY':>10} {'FLEET':>6} {'UTIL%':>7}")
        print(f"  {'-' * 60}")

        for req in self.fleet_requirements:
            util_pct = req.actual_utilization * 100
            print(f"  {req.direction:<10} {req.storage_type:<12} {req.agv_type:<10} "
                  f"{req.daily_tasks:>10} {req.fleet_size:>6} {util_pct:>7.1f}")

        print(f"\n  Summary:")
        print(f"    XPL_201 total : {self.total_xpl_fleet}")
        print(f"    XQE_122 total : {self.total_xqe_fleet}")
        print(f"    XNA total     : {self.total_xna_fleet}")
        print(f"{'═' * 70}\n")

    def to_dict(self) -> dict:
        return {
            "warehouse": self.warehouse_name,
            "valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "fleet": {
                "XPL_201": self.total_xpl_fleet,
                "XQE_122": self.total_xqe_fleet,
                "XNA": self.total_xna_fleet,
            },
            "requirements": [
                {
                    "direction": r.direction,
                    "storage_type": r.storage_type,
                    "agv_type": r.agv_type,
                    "fleet_size": r.fleet_size,
                    "daily_tasks": r.daily_tasks,
                    "avg_cycle_time_s": round(r.avg_cycle_time_s, 1),
                    "utilization_pct": round(r.actual_utilization * 100, 1),
                }
                for r in self.fleet_requirements
            ],
        }


# ---------------------------------------------------------------------------
# Fleet Sizer
# ---------------------------------------------------------------------------

class FleetSizer:
    """
    Calculate fleet requirements for a warehouse configuration.

    Parameters
    ----------
    config : WarehouseConfig
        Parsed warehouse configuration.
    inbound_tasks_per_day : int, optional
        Override daily inbound tasks (uses config value if None).
    outbound_tasks_per_day : int, optional
        Override daily outbound tasks (uses config value if None).
    inbound_hours : float, optional
        Override inbound operating hours.
    outbound_hours : float, optional
        Override outbound operating hours.
    inbound_utilization : float, optional
        Override inbound utilization target (0–1).
    outbound_utilization : float, optional
        Override outbound utilization target (0–1).
    """

    def __init__(
        self,
        config: WarehouseConfig,
        inbound_tasks_per_day: Optional[int] = None,
        outbound_tasks_per_day: Optional[int] = None,
        inbound_hours: Optional[float] = None,
        outbound_hours: Optional[float] = None,
        inbound_utilization: Optional[float] = None,
        outbound_utilization: Optional[float] = None,
    ) -> None:
        self.config = config
        self._calc = CycleCalculator()

        # Resolve throughput
        ib_tp = config.inbound_throughput
        ob_tp = config.outbound_throughput

        self.ib_tasks = inbound_tasks_per_day or (ib_tp.daily_tasks if ib_tp else 100)
        self.ob_tasks = outbound_tasks_per_day or (ob_tp.daily_tasks if ob_tp else 100)
        self.ib_hours = inbound_hours or (ib_tp.operating_hours if ib_tp else 8.0)
        self.ob_hours = outbound_hours or (ob_tp.operating_hours if ob_tp else 8.0)
        self.ib_util = inbound_utilization or (ib_tp.utilization if ib_tp else 0.75)
        self.ob_util = outbound_utilization or (ob_tp.utilization if ob_tp else 0.75)

    # ------------------------------------------------------------------
    # Main public API
    # ------------------------------------------------------------------

    def calculate(self) -> FleetSizingReport:
        """Run the complete fleet sizing calculation."""
        report = FleetSizingReport(warehouse_name=self.config.name)
        cfg = self.config

        # ---------------------------------------------------
        # 1. Aisle compatibility check
        # ---------------------------------------------------
        rack_compat = (
            select_agv_for_rack_aisle(cfg.rack.aisle_width_m)
            if cfg.rack else None
        )
        stacking_compat = select_agv_for_ground_stacking()

        report.rack_compatibility = rack_compat
        report.stacking_compatibility = stacking_compat

        if rack_compat and rack_compat.is_blocked:
            report.errors.append(rack_compat.note)
            if rack_compat.status == "xsc_pending":
                report.errors.append(
                    "Cannot calculate rack throughput until XSC specifications are available."
                )

        # ---------------------------------------------------
        # 2. Compute average depths / heights
        # ---------------------------------------------------
        avg_rack_depth_m = 0.0
        avg_rack_height_m = 0.0
        if cfg.rack:
            from .rack_storage import RackStorage
            rs = RackStorage(
                aisle_depth_m=cfg.rack.aisle_depth_m,
                pallet_spacing_m=cfg.rack.pallet_spacing_m,
                shelves=cfg.rack.shelves,
            )
            avg_rack_depth_m, avg_rack_height_m = rs.avg_cycle_distances()

        avg_stack_depth_m = 0.0
        avg_stack_height_m = 0.0
        if cfg.stacking:
            from .ground_stacking import GroundStackingMultipleLevels
            gs = GroundStackingMultipleLevels(
                rows=cfg.stacking.rows,
                cols=cfg.stacking.cols,
                levels=cfg.stacking.levels,
                level_height_m=cfg.stacking.level_height_m,
                area_length_m=cfg.stacking.area_length_m,
                area_width_m=cfg.stacking.area_width_m,
            )
            avg_stack_depth_m, avg_stack_height_m = gs.avg_cycle_distances()

        # ---------------------------------------------------
        # 3. Workflow fractions
        # ---------------------------------------------------
        rack_frac = cfg.rack_fraction if cfg.rack else 0.0
        stack_frac = cfg.stacking_fraction if cfg.stacking else 0.0
        # Normalise fractions if only one storage type present
        total_frac = rack_frac + stack_frac
        if total_frac > 0:
            rack_frac /= total_frac
            stack_frac /= total_frac

        # ---------------------------------------------------
        # 4. Inbound cycle times & fleet
        # ---------------------------------------------------
        # Rack (if rack configured and compatible)
        if cfg.rack and rack_compat and rack_compat.is_ok and rack_frac > 0:
            ib_rack_wct, ib_rack_reqs = self._inbound_rack(
                rack_compat, avg_rack_depth_m, avg_rack_height_m,
                int(math.ceil(self.ib_tasks * rack_frac)),
                self.ib_hours, self.ib_util,
            )
            report.inbound_rack_wct = ib_rack_wct
            report.fleet_requirements.extend(ib_rack_reqs)

        # Ground stacking
        if cfg.stacking and stack_frac > 0:
            ib_stack_wct, ib_stack_reqs = self._inbound_stacking(
                avg_stack_depth_m, avg_stack_height_m,
                int(math.ceil(self.ib_tasks * stack_frac)),
                self.ib_hours, self.ib_util,
            )
            report.inbound_stacking_wct = ib_stack_wct
            report.fleet_requirements.extend(ib_stack_reqs)

        # ---------------------------------------------------
        # 5. Outbound cycle times & fleet
        # ---------------------------------------------------
        if cfg.rack and rack_compat and rack_compat.is_ok and rack_frac > 0:
            ob_rack_wct, ob_rack_reqs = self._outbound_rack(
                rack_compat, avg_rack_depth_m, avg_rack_height_m,
                int(math.ceil(self.ob_tasks * rack_frac)),
                self.ob_hours, self.ob_util,
            )
            report.outbound_rack_wct = ob_rack_wct
            report.fleet_requirements.extend(ob_rack_reqs)

        if cfg.stacking and stack_frac > 0:
            ob_stack_wct, ob_stack_reqs = self._outbound_stacking(
                avg_stack_depth_m, avg_stack_height_m,
                int(math.ceil(self.ob_tasks * stack_frac)),
                self.ob_hours, self.ob_util,
            )
            report.outbound_stacking_wct = ob_stack_wct
            report.fleet_requirements.extend(ob_stack_reqs)

        return report

    # ------------------------------------------------------------------
    # Inbound workflows
    # ------------------------------------------------------------------

    def _inbound_rack(
        self,
        rack_compat: AisleCompatibilityResult,
        avg_depth_m: float,
        avg_height_m: float,
        tasks: int,
        hours: float,
        util: float,
    ) -> Tuple[WorkflowCycleTime, List[FleetRequirement]]:
        cfg = self.config
        reqs: List[FleetRequirement] = []

        if rack_compat.agv_type == "XNA":
            # XNA – ALWAYS handover
            d_ib_handover = cfg.inbound_to_rack_handover_m
            d_handover_rack = cfg.handover_to_rack_m
            phases = self._calc.inbound_xna_cycle(
                d_inbound_to_handover_m=d_ib_handover,
                d_handover_to_rack_m=d_handover_rack,
                avg_rack_depth_m=avg_depth_m,
                avg_lift_height_m=avg_height_m,
            )
            xpl_ct = phases["xpl_inbound_to_handover"].total_s
            xna_ct = phases["xna_handover_to_rack"].total_s

            wct = WorkflowCycleTime(
                direction="inbound", storage_type="rack", agv_type="XNA",
                uses_handover=True,
                avg_cycle_time_s=xpl_ct + xna_ct,
                phases={k: v.total_s for k, v in phases.items()},
            )
            reqs.append(self._req("XPL_201", "inbound", "rack", tasks, hours, util, xpl_ct))
            reqs.append(self._req("XNA", "inbound", "rack", tasks, hours, util, xna_ct))

        else:
            # XQE_122 – distance-based handover
            d_ib_handover = cfg.inbound_to_rack_handover_m
            use_handover = needs_handover_xqe(d_ib_handover)

            if use_handover:
                d_handover_rack = cfg.handover_to_rack_m
                phases = self._calc.inbound_xqe_with_handover_cycle(
                    d_inbound_to_handover_m=d_ib_handover,
                    d_handover_to_rack_m=d_handover_rack,
                    avg_rack_depth_m=avg_depth_m,
                    avg_lift_height_m=avg_height_m,
                )
                xpl_ct = phases["xpl_inbound_to_handover"].total_s
                xqe_ct = phases["xqe_handover_to_rack"].total_s

                wct = WorkflowCycleTime(
                    direction="inbound", storage_type="rack", agv_type="XQE_122",
                    uses_handover=True,
                    avg_cycle_time_s=xpl_ct + xqe_ct,
                    phases={k: v.total_s for k, v in phases.items()},
                )
                reqs.append(self._req("XPL_201", "inbound", "rack", tasks, hours, util, xpl_ct))
                reqs.append(self._req("XQE_122", "inbound", "rack", tasks, hours, util, xqe_ct))
            else:
                # Treat d_ib_handover as direct distance inbound→rack
                ct_result = self._calc.inbound_xqe_no_handover_cycle(
                    d_inbound_to_rack_m=d_ib_handover,
                    avg_rack_depth_m=avg_depth_m,
                    avg_lift_height_m=avg_height_m,
                )
                wct = WorkflowCycleTime(
                    direction="inbound", storage_type="rack", agv_type="XQE_122",
                    uses_handover=False,
                    avg_cycle_time_s=ct_result.total_s,
                    phases={"xqe_inbound_to_rack": ct_result.total_s},
                )
                reqs.append(self._req("XQE_122", "inbound", "rack", tasks, hours, util,
                                      ct_result.total_s))

        return wct, reqs

    def _inbound_stacking(
        self,
        avg_depth_m: float,
        avg_height_m: float,
        tasks: int,
        hours: float,
        util: float,
    ) -> Tuple[WorkflowCycleTime, List[FleetRequirement]]:
        cfg = self.config
        reqs: List[FleetRequirement] = []

        d_ib_handover = cfg.inbound_to_stacking_handover_m
        use_handover = needs_handover_xqe(d_ib_handover)

        if use_handover:
            d_handover_stack = cfg.handover_to_stacking_m
            phases = self._calc.inbound_xqe_stacking_with_handover_cycle(
                d_inbound_to_handover_m=d_ib_handover,
                d_handover_to_stacking_m=d_handover_stack,
                avg_stacking_depth_m=avg_depth_m,
                avg_lift_height_m=avg_height_m,
            )
            xpl_ct = phases["xpl_inbound_to_handover"].total_s
            xqe_ct = phases["xqe_handover_to_stacking"].total_s

            wct = WorkflowCycleTime(
                direction="inbound", storage_type="stacking", agv_type="XQE_122",
                uses_handover=True,
                avg_cycle_time_s=xpl_ct + xqe_ct,
                phases={k: v.total_s for k, v in phases.items()},
            )
            reqs.append(self._req("XPL_201", "inbound", "stacking", tasks, hours, util, xpl_ct))
            reqs.append(self._req("XQE_122", "inbound", "stacking", tasks, hours, util, xqe_ct))
        else:
            ct_result = self._calc.inbound_xqe_stacking_no_handover_cycle(
                d_inbound_to_stacking_m=d_ib_handover,
                avg_stacking_depth_m=avg_depth_m,
                avg_lift_height_m=avg_height_m,
            )
            wct = WorkflowCycleTime(
                direction="inbound", storage_type="stacking", agv_type="XQE_122",
                uses_handover=False,
                avg_cycle_time_s=ct_result.total_s,
                phases={"xqe_inbound_to_stacking": ct_result.total_s},
            )
            reqs.append(self._req("XQE_122", "inbound", "stacking", tasks, hours, util,
                                  ct_result.total_s))

        return wct, reqs

    # ------------------------------------------------------------------
    # Outbound workflows
    # ------------------------------------------------------------------

    def _outbound_rack(
        self,
        rack_compat: AisleCompatibilityResult,
        avg_depth_m: float,
        avg_height_m: float,
        tasks: int,
        hours: float,
        util: float,
    ) -> Tuple[WorkflowCycleTime, List[FleetRequirement]]:
        cfg = self.config
        reqs: List[FleetRequirement] = []

        if rack_compat.agv_type == "XNA":
            d_handover_rack = cfg.handover_to_rack_m
            d_handover_outbound = cfg.rack_handover_to_outbound_m
            phases = self._calc.outbound_xna_cycle(
                d_handover_to_outbound_m=d_handover_outbound,
                d_handover_to_rack_m=d_handover_rack,
                avg_rack_depth_m=avg_depth_m,
                avg_lift_height_m=avg_height_m,
            )
            xna_ct = phases["xna_rack_to_handover"].total_s
            xpl_ct = phases["xpl_handover_to_outbound"].total_s

            wct = WorkflowCycleTime(
                direction="outbound", storage_type="rack", agv_type="XNA",
                uses_handover=True,
                avg_cycle_time_s=xna_ct + xpl_ct,
                phases={k: v.total_s for k, v in phases.items()},
            )
            reqs.append(self._req("XNA", "outbound", "rack", tasks, hours, util, xna_ct))
            reqs.append(self._req("XPL_201", "outbound", "rack", tasks, hours, util, xpl_ct))

        else:
            # XQE_122
            d_handover_outbound = cfg.rack_handover_to_outbound_m
            use_handover = needs_handover_xqe(d_handover_outbound)

            if use_handover:
                d_rack_handover = cfg.handover_to_rack_m
                phases = self._calc.outbound_xqe_with_handover_cycle(
                    d_rack_to_handover_m=d_rack_handover,
                    d_handover_to_outbound_m=d_handover_outbound,
                    avg_rack_depth_m=avg_depth_m,
                    avg_lift_height_m=avg_height_m,
                )
                xqe_ct = phases["xqe_rack_to_handover"].total_s
                xpl_ct = phases["xpl_handover_to_outbound"].total_s

                wct = WorkflowCycleTime(
                    direction="outbound", storage_type="rack", agv_type="XQE_122",
                    uses_handover=True,
                    avg_cycle_time_s=xqe_ct + xpl_ct,
                    phases={k: v.total_s for k, v in phases.items()},
                )
                reqs.append(self._req("XQE_122", "outbound", "rack", tasks, hours, util, xqe_ct))
                reqs.append(self._req("XPL_201", "outbound", "rack", tasks, hours, util, xpl_ct))
            else:
                ct_result = self._calc.outbound_xqe_no_handover_cycle(
                    d_rack_to_outbound_m=d_handover_outbound,
                    avg_rack_depth_m=avg_depth_m,
                    avg_lift_height_m=avg_height_m,
                )
                wct = WorkflowCycleTime(
                    direction="outbound", storage_type="rack", agv_type="XQE_122",
                    uses_handover=False,
                    avg_cycle_time_s=ct_result.total_s,
                    phases={"xqe_rack_to_outbound": ct_result.total_s},
                )
                reqs.append(self._req("XQE_122", "outbound", "rack", tasks, hours, util,
                                      ct_result.total_s))

        return wct, reqs

    def _outbound_stacking(
        self,
        avg_depth_m: float,
        avg_height_m: float,
        tasks: int,
        hours: float,
        util: float,
    ) -> Tuple[WorkflowCycleTime, List[FleetRequirement]]:
        cfg = self.config
        reqs: List[FleetRequirement] = []

        d_handover_outbound = cfg.stacking_handover_to_outbound_m
        use_handover = needs_handover_xqe(d_handover_outbound)

        if use_handover:
            d_stacking_handover = cfg.handover_to_stacking_m
            phases = self._calc.outbound_xqe_stacking_with_handover_cycle(
                d_stacking_to_handover_m=d_stacking_handover,
                d_handover_to_outbound_m=d_handover_outbound,
                avg_stacking_depth_m=avg_depth_m,
                avg_lift_height_m=avg_height_m,
            )
            xqe_ct = phases["xqe_stacking_to_handover"].total_s
            xpl_ct = phases["xpl_handover_to_outbound"].total_s

            wct = WorkflowCycleTime(
                direction="outbound", storage_type="stacking", agv_type="XQE_122",
                uses_handover=True,
                avg_cycle_time_s=xqe_ct + xpl_ct,
                phases={k: v.total_s for k, v in phases.items()},
            )
            reqs.append(self._req("XQE_122", "outbound", "stacking", tasks, hours, util, xqe_ct))
            reqs.append(self._req("XPL_201", "outbound", "stacking", tasks, hours, util, xpl_ct))
        else:
            ct_result = self._calc.outbound_xqe_stacking_no_handover_cycle(
                d_stacking_to_outbound_m=d_handover_outbound,
                avg_stacking_depth_m=avg_depth_m,
                avg_lift_height_m=avg_height_m,
            )
            wct = WorkflowCycleTime(
                direction="outbound", storage_type="stacking", agv_type="XQE_122",
                uses_handover=False,
                avg_cycle_time_s=ct_result.total_s,
                phases={"xqe_stacking_to_outbound": ct_result.total_s},
            )
            reqs.append(self._req("XQE_122", "outbound", "stacking", tasks, hours, util,
                                  ct_result.total_s))

        return wct, reqs

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _req(
        agv_type: str,
        direction: str,
        storage_type: str,
        daily_tasks: int,
        hours: float,
        utilization: float,
        cycle_time_s: float,
    ) -> FleetRequirement:
        """Calculate fleet size using the standard formula."""
        if cycle_time_s <= 0 or daily_tasks <= 0:
            fleet = 0
            actual_util = 0.0
        else:
            available_s = hours * 3600.0 * utilization
            fleet = math.ceil((daily_tasks * cycle_time_s) / available_s)
            if fleet > 0:
                actual_util = (daily_tasks * cycle_time_s) / (fleet * hours * 3600.0)
            else:
                actual_util = 0.0

        return FleetRequirement(
            agv_type=agv_type,
            direction=direction,
            storage_type=storage_type,
            fleet_size=fleet,
            daily_tasks=daily_tasks,
            avg_cycle_time_s=cycle_time_s,
            operating_hours=hours,
            utilization=utilization,
            actual_utilization=min(actual_util, 1.0),
        )
