"""
Simulation Engine Module
=========================
Simulates AGV task operations including concurrent execution, congestion
(aisle blocking), and utilization tracking.

Task types modelled:
  - Inbound task  : pick from inbound dock, store in aisle
  - Outbound task : retrieve from aisle, deliver to outbound dock
  - Transfer task : move pallet from one aisle to another

AGV states:
  - idle       : available for tasks
  - traveling  : moving (forward or reverse)
  - picking    : fork engagement / pickup
  - dropping   : fork disengagement / dropoff
  - lifting    : mast in motion
  - charging   : at charging station
  - waiting    : blocked by another AGV (congestion)
"""

import logging
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .agv_specs import AGV_SPECS, TASK_PARAMETERS
from .graph_generator import WarehouseGraph
from .physics import AGVPhysics, TaskCycleResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class AGVState(Enum):
    IDLE = "idle"
    TRAVELING = "traveling"
    PICKING = "picking"
    DROPPING = "dropping"
    LIFTING = "lifting"
    CHARGING = "charging"
    WAITING = "waiting"


@dataclass
class Task:
    """A single warehouse task (one pallet move)."""

    task_id: int
    task_type: str                    # 'inbound', 'outbound', 'transfer'
    storage_type: str                 # 'rack', 'ground_storage', 'ground_stacking'
    aisle_name: str
    inbound_dock_id: str
    outbound_dock_id: str
    lift_height: float = 0.0          # metres (for rack tasks)
    stack_height: float = 0.0         # metres (for stacking tasks)
    assigned_agv: Optional[str] = None
    start_time: float = 0.0
    end_time: float = 0.0
    cycle_result: Optional[TaskCycleResult] = None
    status: str = "pending"           # pending, assigned, in_progress, complete

    @property
    def cycle_time(self) -> float:
        if self.cycle_result:
            return self.cycle_result.total_cycle_time
        return 0.0


@dataclass
class AGVAgent:
    """An individual AGV in the fleet."""

    agv_id: str
    agv_type: str
    state: AGVState = AGVState.IDLE
    current_location: str = "dock"
    busy_until: float = 0.0           # simulation time when AGV becomes free
    tasks_completed: int = 0
    total_busy_time: float = 0.0
    total_idle_time: float = 0.0
    current_aisle: Optional[str] = None  # aisle currently occupied


@dataclass
class SimulationResult:
    """Aggregated results from a simulation run."""

    agv_type: str
    fleet_size: int
    tasks_per_hour_target: float
    tasks_per_hour_actual: float
    simulation_duration_s: float
    total_tasks_completed: int
    avg_cycle_time_s: float
    min_cycle_time_s: float
    max_cycle_time_s: float
    avg_utilization: float
    per_agv_utilization: Dict[str, float] = field(default_factory=dict)
    congestion_events: int = 0
    aisle_usage_counts: Dict[str, int] = field(default_factory=dict)
    cycle_time_breakdown: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "agv_type": self.agv_type,
            "fleet_size": self.fleet_size,
            "tasks_per_hour_target": self.tasks_per_hour_target,
            "tasks_per_hour_actual": round(self.tasks_per_hour_actual, 2),
            "simulation_duration_s": round(self.simulation_duration_s, 1),
            "total_tasks_completed": self.total_tasks_completed,
            "avg_cycle_time_s": round(self.avg_cycle_time_s, 2),
            "min_cycle_time_s": round(self.min_cycle_time_s, 2),
            "max_cycle_time_s": round(self.max_cycle_time_s, 2),
            "avg_utilization_pct": round(self.avg_utilization * 100, 1),
            "per_agv_utilization_pct": {
                k: round(v * 100, 1) for k, v in self.per_agv_utilization.items()
            },
            "congestion_events": self.congestion_events,
            "aisle_usage_counts": dict(self.aisle_usage_counts),
            "cycle_time_breakdown": self.cycle_time_breakdown,
        }

    def print_summary(self) -> None:
        print(f"\n{'=' * 60}")
        print(f"  SIMULATION RESULTS – {self.agv_type}  (fleet: {self.fleet_size} AGVs)")
        print(f"{'=' * 60}")
        print(f"  Throughput target   : {self.tasks_per_hour_target:.0f} tasks/hr")
        print(f"  Throughput actual   : {self.tasks_per_hour_actual:.1f} tasks/hr")
        print(f"  Tasks completed     : {self.total_tasks_completed}")
        print(f"  Simulation duration : {self.simulation_duration_s / 3600:.2f} hr")
        print(f"  Avg cycle time      : {self.avg_cycle_time_s:.1f} s  "
              f"({self.avg_cycle_time_s / 60:.1f} min)")
        print(f"  Cycle time range    : {self.min_cycle_time_s:.1f}–"
              f"{self.max_cycle_time_s:.1f} s")
        print(f"  Fleet utilization   : {self.avg_utilization * 100:.1f}%")
        print(f"  Congestion events   : {self.congestion_events}")
        if self.aisle_usage_counts:
            print(f"  Top aisles (by use)  :")
            for aisle, cnt in sorted(
                self.aisle_usage_counts.items(), key=lambda x: -x[1]
            )[:5]:
                print(f"    {aisle:<10}: {cnt} tasks")
        print(f"{'=' * 60}\n")


# ---------------------------------------------------------------------------
# Simulation engine
# ---------------------------------------------------------------------------

class SimulationEngine:
    """
    Discrete-time AGV fleet simulation engine.

    Simulates a sequence of tasks and tracks AGV utilization, cycle times,
    and congestion events.  Uses an analytic (formula-based) cycle time
    calculation per the AGVPhysics module for each task, then assigns tasks
    to AGVs in a timeline to model concurrent execution.

    Parameters
    ----------
    warehouse_graph : WarehouseGraph
        The built warehouse graph.
    layout : dict
        Warehouse layout dictionary (used to look up geometry).
    """

    def __init__(
        self,
        warehouse_graph: WarehouseGraph,
        layout: dict,
        congestion_wait_s: float = TASK_PARAMETERS["pickup_time"],
    ) -> None:
        """
        Parameters
        ----------
        warehouse_graph : WarehouseGraph
            The built warehouse graph.
        layout : dict
            Warehouse layout dictionary (used to look up geometry).
        congestion_wait_s : float
            Extra wait time (seconds) added when an aisle is already occupied by
            another AGV.  Defaults to 30 s (equal to pickup_time).
        """
        self.graph = warehouse_graph
        self.layout = layout
        self.congestion_wait_s = congestion_wait_s
        self._aisle_map: Dict[str, dict] = {
            a["name"]: a for a in layout.get("storage_aisles", [])
        }
        self._inbound_dock_id = self._get_primary_dock_id("inbound")
        self._outbound_dock_id = self._get_primary_dock_id("outbound")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def simulate_throughput(
        self,
        agv_type: str,
        fleet_size: int,
        tasks_per_hour: float,
        simulation_hours: float = 8.0,
        task_mix: Optional[Dict[str, float]] = None,
    ) -> SimulationResult:
        """
        Simulate the warehouse operating at a target throughput for a given
        number of hours.

        Parameters
        ----------
        agv_type : str
            AGV model name (e.g., 'XQE_122').
        fleet_size : int
            Number of AGVs in the fleet.
        tasks_per_hour : float
            Target task rate (tasks/hour).
        simulation_hours : float
            Duration of simulation in hours.
        task_mix : dict, optional
            Fraction of each task type, e.g. {'rack': 0.7, 'ground_storage': 0.3}.
            Defaults to all-rack or whatever aisles are available.

        Returns
        -------
        SimulationResult
        """
        task_mix = self._build_task_mix(agv_type, task_mix)
        total_tasks = int(tasks_per_hour * simulation_hours)
        sim_duration_s = simulation_hours * 3600.0
        inter_arrival_s = 3600.0 / tasks_per_hour

        # Create fleet
        fleet = [
            AGVAgent(agv_id=f"{agv_type}_{i+1}", agv_type=agv_type)
            for i in range(fleet_size)
        ]

        # Timeline simulation
        aisle_busy_until: Dict[str, float] = defaultdict(float)  # aisle → free time
        congestion_events = 0
        aisle_usage: Dict[str, int] = defaultdict(int)
        cycle_times: List[float] = []
        tasks_completed = 0
        current_time = 0.0

        for task_idx in range(total_tasks):
            arrival_time = task_idx * inter_arrival_s

            # Pick task type based on mix
            storage_type, aisle_name = self._sample_task(agv_type, task_mix)
            if aisle_name is None:
                continue

            aisle_data = self._aisle_map.get(aisle_name, {})
            lift_h = self._sample_lift_height(aisle_data)

            # Calculate cycle time via physics
            try:
                cycle_result = self._calculate_cycle(
                    agv_type, storage_type, aisle_name, lift_h
                )
            except ValueError as exc:
                logger.warning("Skipping task %d: %s", task_idx, exc)
                continue

            cycle_t = cycle_result.total_cycle_time

            # Find soonest available AGV
            fleet.sort(key=lambda a: a.busy_until)
            agv = fleet[0]
            start_t = max(agv.busy_until, arrival_time)

            # Check aisle congestion
            if aisle_busy_until[aisle_name] > start_t:
                # AGV must wait until the aisle is free, plus a minimum
                # coordination buffer (self.congestion_wait_s).
                wait = aisle_busy_until[aisle_name] - start_t + self.congestion_wait_s
                start_t += wait
                congestion_events += 1

            end_t = start_t + cycle_t

            # Check if within simulation window
            if end_t > sim_duration_s:
                break

            # Update state
            busy_dur = end_t - start_t
            agv.busy_until = end_t
            agv.total_busy_time += busy_dur
            agv.tasks_completed += 1
            aisle_busy_until[aisle_name] = end_t
            aisle_usage[aisle_name] += 1
            cycle_times.append(cycle_t)
            tasks_completed += 1

        # Compute idle time and utilization
        for agv in fleet:
            agv.total_idle_time = sim_duration_s - agv.total_busy_time

        util_per_agv = {
            agv.agv_id: agv.total_busy_time / sim_duration_s
            for agv in fleet
        }
        avg_util = sum(util_per_agv.values()) / len(fleet) if fleet else 0.0

        actual_throughput = (
            tasks_completed / simulation_hours if simulation_hours > 0 else 0.0
        )

        # Sample breakdown from last cycle for reporting
        last_breakdown = None
        if cycle_times:
            last_cycle = self._calculate_cycle(
                agv_type,
                *self._sample_task(agv_type, task_mix),
                self._sample_lift_height(
                    self._aisle_map.get(
                        self._sample_task(agv_type, task_mix)[1], {}
                    )
                ),
            )
            last_breakdown = last_cycle.to_dict()

        return SimulationResult(
            agv_type=agv_type,
            fleet_size=fleet_size,
            tasks_per_hour_target=tasks_per_hour,
            tasks_per_hour_actual=actual_throughput,
            simulation_duration_s=sim_duration_s,
            total_tasks_completed=tasks_completed,
            avg_cycle_time_s=sum(cycle_times) / len(cycle_times) if cycle_times else 0.0,
            min_cycle_time_s=min(cycle_times) if cycle_times else 0.0,
            max_cycle_time_s=max(cycle_times) if cycle_times else 0.0,
            avg_utilization=avg_util,
            per_agv_utilization=util_per_agv,
            congestion_events=congestion_events,
            aisle_usage_counts=dict(aisle_usage),
            cycle_time_breakdown=last_breakdown,
        )

    def calculate_single_task_cycle(
        self,
        agv_type: str,
        storage_type: str,
        aisle_name: str,
        lift_height: float = 0.0,
    ) -> TaskCycleResult:
        """
        Calculate the cycle time for a single task (for quick analysis).
        """
        return self._calculate_cycle(agv_type, storage_type, aisle_name, lift_height)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _calculate_cycle(
        self,
        agv_type: str,
        storage_type: str,
        aisle_name: str,
        lift_height: float,
    ) -> TaskCycleResult:
        """
        Look up aisle geometry from graph and calculate physics-based cycle time.
        """
        physics = AGVPhysics(agv_type)

        # Validate compatibility
        aisle_data = self._aisle_map.get(aisle_name, {})
        aisle_width = aisle_data.get("width", 999.0)
        ok, reason = physics.can_operate_in_aisle(aisle_width, storage_type, lift_height)
        if not ok:
            raise ValueError(f"AGV incompatible with aisle: {reason}")

        # Get head aisle distance and turn count from graph path to aisle entry.
        # The perpendicular distance from head aisle to aisle entry (d_aisle_graph)
        # is typically ~0 when aisles branch directly off the head aisle.
        d_head, _d_aisle_graph, turns = self.graph.get_dock_to_aisle_distances(
            self._inbound_dock_id, aisle_name
        )

        # Actual travel within the storage aisle = half the aisle depth
        # (AGV travels to the average/mid-point storage position).
        aisle_depth = aisle_data.get("depth", 20.0)
        d_aisle = aisle_depth / 2.0

        # Fallback to layout geometry if graph returns zero head distance
        if d_head <= 0:
            d_head, _dummy, turns = self._geometry_from_layout(aisle_name)

        # Use same outbound head distance (symmetric warehouse assumption)
        d_head_out = d_head

        if storage_type == "rack":
            return physics.calculate_rack_task(
                d_head_aisle_inbound=d_head,
                d_aisle=d_aisle,
                d_head_aisle_outbound=d_head_out,
                lift_height=lift_height,
                num_turns=turns,
                aisle_name=aisle_name,
            )
        elif storage_type == "ground_storage":
            return physics.calculate_ground_storage_task(
                d_head_aisle_inbound=d_head,
                d_aisle=d_aisle,
                d_head_aisle_outbound=d_head_out,
                num_turns=turns,
                aisle_name=aisle_name,
            )
        else:  # ground_stacking
            aisle_meta = self._aisle_map.get(aisle_name, {})
            gs_zones = self.layout.get("ground_stacking_zones", [])
            stack_h = 0.0
            for z in gs_zones:
                if z.get("aisle") == aisle_name:
                    stack_h = z.get("max_stack_height", 0.0) / 2
                    break
            return physics.calculate_ground_stacking_task(
                d_head_aisle_inbound=d_head,
                d_aisle=d_aisle,
                d_head_aisle_outbound=d_head_out,
                num_turns=turns,
                stack_height=stack_h,
                aisle_name=aisle_name,
            )

    def _geometry_from_layout(
        self, aisle_name: str
    ) -> Tuple[float, float, int]:
        """
        Fallback: estimate d_head and d_aisle directly from layout JSON
        when graph distances aren't available.
        """
        aisle = self._aisle_map.get(aisle_name, {})
        depth = aisle.get("depth", 20.0)
        entry_type = aisle.get("entry_type", "dead-end")

        # Estimate head aisle distance as half the warehouse width
        wh = self.layout.get("warehouse", {})
        wh_width = wh.get("width", 40.0)

        # Typical position is mid-aisle (half depth)
        d_aisle = depth / 2.0

        # Head aisle distance: half warehouse width (from dock to aisle entry)
        d_head = wh_width / 4.0

        # Count turns: 2 (one in, one out of storage aisle)
        turns = 2

        return d_head, d_aisle, turns

    def _get_primary_dock_id(self, dock_type: str) -> str:
        key = "inbound_docks" if dock_type == "inbound" else "outbound_docks"
        docks = self.layout.get(key, [])
        if docks:
            return f"dock_{docks[0]['name']}"
        return f"dock_{dock_type.upper()}1"

    def _build_task_mix(
        self, agv_type: str, task_mix: Optional[Dict[str, float]]
    ) -> Dict[str, float]:
        """
        Build a normalized task-type→aisle mapping based on available aisles
        and AGV compatibility. Returns {aisle_name: fraction}.
        """
        spec = AGV_SPECS[agv_type]
        compatible_aisles = []
        for aisle in self.layout.get("storage_aisles", []):
            st = aisle.get("storage_type", "rack")
            w = aisle.get("width", 0.0)
            if st in spec["storage_types"] and w >= spec["aisle_width"]:
                compatible_aisles.append(aisle["name"])

        if not compatible_aisles:
            # Fallback – use all aisles regardless
            compatible_aisles = [a["name"] for a in self.layout.get("storage_aisles", [])]

        n = len(compatible_aisles)
        return {name: 1.0 / n for name in compatible_aisles} if n > 0 else {}

    def _sample_task(
        self, agv_type: str, task_mix: Dict[str, float]
    ) -> Tuple[str, Optional[str]]:
        """
        Sample an aisle (and its storage type) from the task mix distribution.
        Returns (storage_type, aisle_name).
        """
        if not task_mix:
            return "rack", None

        aisles = list(task_mix.keys())
        weights = list(task_mix.values())
        total = sum(weights)
        weights = [w / total for w in weights]

        r = random.random()
        cumulative = 0.0
        for aisle_name, w in zip(aisles, weights):
            cumulative += w
            if r <= cumulative:
                aisle_data = self._aisle_map.get(aisle_name, {})
                st = aisle_data.get("storage_type", "rack")
                return st, aisle_name

        aisle_name = aisles[-1]
        st = self._aisle_map.get(aisle_name, {}).get("storage_type", "rack")
        return st, aisle_name

    def _sample_lift_height(self, aisle_data: dict) -> float:
        """Return an average lift height for a rack aisle."""
        racks = aisle_data.get("racks", [])
        if not racks:
            return 0.0
        max_h = max(r.get("height", 0.0) for r in racks)
        levels = max(r.get("levels", 1) for r in racks)
        # Average lift height = half of max rack height
        return max_h / 2.0 if max_h > 0 else 0.0
