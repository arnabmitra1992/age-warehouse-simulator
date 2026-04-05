"""
Fleet Sizing Calculator Module
================================
Calculates the minimum number of AGVs required to achieve a target throughput,
considering utilization targets, cycle times, and AGV type compatibility.

Fleet Sizing Formula:
  cycle_time         = total time for one pallet move (seconds)
  tasks_per_agv_hr   = 3600 / cycle_time
  agvs_needed        = ceil(tasks_per_hour / (tasks_per_agv_hr × utilization_target))

Additional analysis:
  - Compare multiple AGV types for a given warehouse
  - Identify bottleneck aisles
  - Recommend optimal AGV mix
  - Generate sizing report for multiple throughput levels
"""

import math
import logging

# Weight applied to the utilization deviation penalty when scoring AGV types for
# the recommendation algorithm.  Higher values favour AGVs whose utilization is
# closer to the target over raw fleet size minimisation.
_UTILIZATION_WEIGHT_FACTOR = 5
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .agv_specs import AGV_SPECS, TASK_PARAMETERS, get_compatible_agv_types, XNA_MAX_AISLE_WIDTH
from .graph_generator import WarehouseGraph
from .physics import AGVPhysics, TaskCycleResult
from .simulation_engine import SimulationEngine, SimulationResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AisleAnalysis:
    """Fleet sizing analysis for a single aisle."""

    aisle_name: str
    storage_type: str
    aisle_width: float
    aisle_depth: float
    compatible_agvs: List[str]
    cycle_times: Dict[str, float] = field(default_factory=dict)   # agv_type → cycle_time (s)
    tasks_per_hour_per_agv: Dict[str, float] = field(default_factory=dict)

    def best_agv(self) -> Optional[str]:
        """Return the AGV type with the shortest cycle time."""
        if not self.cycle_times:
            return None
        return min(self.cycle_times, key=self.cycle_times.get)


@dataclass
class FleetSizingResult:
    """Complete fleet sizing result for a warehouse at a given throughput."""

    tasks_per_hour: float
    utilization_target: float

    # Per AGV type: recommended fleet size
    fleet_size_per_agv: Dict[str, int] = field(default_factory=dict)

    # Per AGV type: avg utilization at recommended fleet size
    utilization_per_agv: Dict[str, float] = field(default_factory=dict)

    # Per AGV type: avg cycle time
    cycle_time_per_agv: Dict[str, float] = field(default_factory=dict)

    # Per AGV type: tasks each AGV can handle per hour
    tasks_per_agv_per_hour: Dict[str, float] = field(default_factory=dict)

    # Detailed aisle analysis
    aisle_analyses: List[AisleAnalysis] = field(default_factory=list)

    # Simulation results (if run)
    simulation_results: Dict[str, SimulationResult] = field(default_factory=dict)

    # Bottleneck information
    bottleneck_aisles: List[str] = field(default_factory=list)

    # Recommended AGV type for this warehouse/throughput combination
    recommended_agv: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "tasks_per_hour": self.tasks_per_hour,
            "utilization_target_pct": self.utilization_target * 100,
            "recommended_agv": self.recommended_agv,
            "fleet_sizes": self.fleet_size_per_agv,
            "utilization_pct": {k: round(v * 100, 1) for k, v in self.utilization_per_agv.items()},
            "avg_cycle_time_s": {k: round(v, 1) for k, v in self.cycle_time_per_agv.items()},
            "tasks_per_agv_per_hour": {
                k: round(v, 2) for k, v in self.tasks_per_agv_per_hour.items()
            },
            "bottleneck_aisles": self.bottleneck_aisles,
        }

    def print_report(self) -> None:
        print(f"\n{'=' * 66}")
        print(f"  FLEET SIZING REPORT")
        print(f"  Target throughput : {self.tasks_per_hour:.0f} tasks/hour")
        print(f"  Target utilization: {self.utilization_target * 100:.0f}%")
        print(f"{'=' * 66}")
        print(f"  {'AGV TYPE':<12} {'FLEET':>6} {'CYCLE':>8} {'TASKS/HR':>9} {'UTIL%':>7}")
        print(f"  {'':12} {'SIZE':>6} {'TIME(s)':>8} {'PER AGV':>9} {'':>7}")
        print(f"  {'-' * 44}")
        for agv_type in sorted(self.fleet_size_per_agv):
            fl = self.fleet_size_per_agv[agv_type]
            ct = self.cycle_time_per_agv.get(agv_type, 0)
            tph = self.tasks_per_agv_per_hour.get(agv_type, 0)
            util = self.utilization_per_agv.get(agv_type, 0) * 100
            marker = " ★" if agv_type == self.recommended_agv else ""
            print(f"  {agv_type:<12} {fl:>6} {ct:>8.1f} {tph:>9.2f} {util:>7.1f}{marker}")

        if self.recommended_agv:
            print(f"\n  ★ Recommended: {self.recommended_agv}")

        if self.bottleneck_aisles:
            print(f"\n  Bottleneck aisles: {', '.join(self.bottleneck_aisles)}")

        print(f"{'=' * 66}\n")


# ---------------------------------------------------------------------------
# Fleet sizing calculator
# ---------------------------------------------------------------------------

class FleetSizingCalculator:
    """
    Calculates optimal fleet sizes for all AGV types for a given warehouse layout.

    Parameters
    ----------
    warehouse_graph : WarehouseGraph
        The built warehouse graph.
    layout : dict
        Warehouse layout dict.
    utilization_target : float
        Target AGV utilization (default 0.80 = 80%).
    """

    def __init__(
        self,
        warehouse_graph: WarehouseGraph,
        layout: dict,
        utilization_target: float = TASK_PARAMETERS["target_utilization"],
    ) -> None:
        self.graph = warehouse_graph
        self.layout = layout
        self.utilization_target = utilization_target
        self._engine = SimulationEngine(warehouse_graph, layout)
        self._aisle_map = {
            a["name"]: a for a in layout.get("storage_aisles", [])
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyse_aisles(self) -> List[AisleAnalysis]:
        """
        Analyse each storage aisle: compatible AGV types and cycle times.
        """
        analyses = []
        inbound_dock = self._engine._inbound_dock_id
        outbound_dock = self._engine._outbound_dock_id

        for aisle in self.layout.get("storage_aisles", []):
            name = aisle["name"]
            storage_type = aisle.get("storage_type", "rack")
            width = aisle.get("width", 2.84)
            depth = aisle.get("depth", 20.0)

            compatible = [
                agv_type
                for agv_type, spec in AGV_SPECS.items()
                if storage_type in spec["storage_types"]
                and width >= spec["aisle_width"]
                and not (agv_type in ("XNA_121", "XNA_151") and width >= XNA_MAX_AISLE_WIDTH)
            ]

            analysis = AisleAnalysis(
                aisle_name=name,
                storage_type=storage_type,
                aisle_width=width,
                aisle_depth=depth,
                compatible_agvs=compatible,
            )

            for agv_type in compatible:
                racks = aisle.get("racks", [])
                lift_h = (
                    max(r.get("height", 0.0) for r in racks) / 2.0
                    if racks else 0.0
                )
                try:
                    result = self._engine.calculate_single_task_cycle(
                        agv_type, storage_type, name, lift_h
                    )
                    analysis.cycle_times[agv_type] = result.total_cycle_time
                    analysis.tasks_per_hour_per_agv[agv_type] = (
                        3600.0 / result.total_cycle_time
                    )
                except (ValueError, Exception) as exc:
                    logger.debug("Skip %s / %s: %s", agv_type, name, exc)

            analyses.append(analysis)

        return analyses

    def calculate_fleet_size(
        self,
        tasks_per_hour: float,
        agv_type: Optional[str] = None,
        run_simulation: bool = False,
        simulation_hours: float = 4.0,
    ) -> FleetSizingResult:
        """
        Calculate the minimum fleet size for a given throughput requirement.

        Parameters
        ----------
        tasks_per_hour : float
            Required task rate.
        agv_type : str, optional
            Restrict analysis to a single AGV type. If None, all are analysed.
        run_simulation : bool
            If True, also runs a full simulation for validation.
        simulation_hours : float
            Duration of simulation run (hours).

        Returns
        -------
        FleetSizingResult
        """
        result = FleetSizingResult(
            tasks_per_hour=tasks_per_hour,
            utilization_target=self.utilization_target,
        )

        aisle_analyses = self.analyse_aisles()
        result.aisle_analyses = aisle_analyses

        agv_types = [agv_type] if agv_type else list(AGV_SPECS.keys())

        for at in agv_types:
            avg_cycle_t = self._avg_cycle_time_for_agv(at, aisle_analyses)
            if avg_cycle_t is None:
                logger.debug("%s has no compatible aisles; skipping.", at)
                continue

            tasks_per_agv_hr = 3600.0 / avg_cycle_t
            n_agvs = math.ceil(
                tasks_per_hour / (tasks_per_agv_hr * self.utilization_target)
            )
            achieved_util = (
                tasks_per_hour / (n_agvs * tasks_per_agv_hr)
                if n_agvs > 0
                else 0.0
            )

            result.fleet_size_per_agv[at] = n_agvs
            result.cycle_time_per_agv[at] = avg_cycle_t
            result.tasks_per_agv_per_hour[at] = tasks_per_agv_hr
            result.utilization_per_agv[at] = min(achieved_util, 1.0)

            if run_simulation:
                sim = self._engine.simulate_throughput(
                    agv_type=at,
                    fleet_size=n_agvs,
                    tasks_per_hour=tasks_per_hour,
                    simulation_hours=simulation_hours,
                )
                result.simulation_results[at] = sim

        # Identify bottleneck aisles (highest usage relative to positions)
        result.bottleneck_aisles = self._identify_bottlenecks(
            aisle_analyses, tasks_per_hour
        )

        # Recommend best AGV type (smallest fleet, or best cycle time)
        result.recommended_agv = self._recommend_agv(result)

        return result

    def throughput_sensitivity(
        self,
        agv_type: str,
        throughput_range: List[float],
    ) -> List[Tuple[float, int, float]]:
        """
        Calculate fleet sizes across a range of throughput targets.

        Returns
        -------
        List of (tasks_per_hour, fleet_size, utilization) tuples.
        """
        results = []
        aisle_analyses = self.analyse_aisles()
        avg_cycle = self._avg_cycle_time_for_agv(agv_type, aisle_analyses)
        if avg_cycle is None:
            return results

        tasks_per_agv_hr = 3600.0 / avg_cycle

        for tph in throughput_range:
            n = math.ceil(tph / (tasks_per_agv_hr * self.utilization_target))
            util = tph / (n * tasks_per_agv_hr) if n > 0 else 0.0
            results.append((tph, n, min(util, 1.0)))

        return results

    def print_aisle_analysis(self, analyses: List[AisleAnalysis]) -> None:
        """Print a formatted aisle-by-aisle compatibility and cycle time table."""
        print(f"\n{'=' * 76}")
        print("  AISLE ANALYSIS")
        print(f"{'=' * 76}")
        print(f"  {'AISLE':<8} {'TYPE':<16} {'W(m)':>5} {'D(m)':>6}  "
              f"{'COMPATIBLE AGVs & CYCLE TIMES'}")
        print(f"  {'-' * 72}")
        for a in analyses:
            agv_info = "  ".join(
                f"{agv_type}: {ct:.0f}s"
                for agv_type, ct in sorted(a.cycle_times.items(), key=lambda x: x[1])
            ) or "NONE"
            print(f"  {a.aisle_name:<8} {a.storage_type:<16} "
                  f"{a.aisle_width:>5.2f} {a.aisle_depth:>6.1f}  {agv_info}")
        print(f"{'=' * 76}\n")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _avg_cycle_time_for_agv(
        self, agv_type: str, aisle_analyses: List[AisleAnalysis]
    ) -> Optional[float]:
        """Compute weighted average cycle time for an AGV across all compatible aisles."""
        times = []
        for a in aisle_analyses:
            if agv_type in a.cycle_times:
                times.append(a.cycle_times[agv_type])
        if not times:
            return None
        return sum(times) / len(times)

    def _identify_bottlenecks(
        self, aisle_analyses: List[AisleAnalysis], tasks_per_hour: float
    ) -> List[str]:
        """
        Identify aisles with limited AGV compatibility or very long cycle times.
        """
        bottlenecks = []
        for a in aisle_analyses:
            if not a.compatible_agvs:
                bottlenecks.append(a.aisle_name)
            elif a.cycle_times:
                min_ct = min(a.cycle_times.values())
                max_tph_aisle = 3600.0 / min_ct
                if max_tph_aisle < tasks_per_hour * 0.3:
                    bottlenecks.append(a.aisle_name)
        return bottlenecks

    def _recommend_agv(self, result: FleetSizingResult) -> Optional[str]:
        """
        Recommend the best AGV type based on smallest fleet + best utilization.
        Prefers fleet sizes ≤ 10 with utilization closest to target.
        """
        if not result.fleet_size_per_agv:
            return None

        # Score = fleet_size + penalty for being far from target utilization
        target = self.utilization_target
        scored = []
        for agv_type, fleet in result.fleet_size_per_agv.items():
            util = result.utilization_per_agv.get(agv_type, 0)
            util_diff = abs(util - target)
            score = fleet + util_diff * _UTILIZATION_WEIGHT_FACTOR
            scored.append((score, agv_type))

        scored.sort()
        return scored[0][1] if scored else None
