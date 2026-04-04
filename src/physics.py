"""
AGV Physics Module
==================
Calculates realistic travel times for all AGV types based on warehouse geometry,
load state, fork direction, turn counts, and lifting operations.

Key Physics Rules:
  - Fork is BACKWARD-FACING on all AGV models.
  - When moving to a storage position (fork first), direction = REVERSE.
  - Empty travel along head aisles and open areas uses FORWARD speed.
  - All travel with load engaged uses REVERSE speed.
  - Exception: XNA models have equal forward and reverse speeds (1.0 m/s each).

Turn Mechanics:
  - Every 90° direction change = 10 seconds (fixed, independent of AGV type).
  - Turns are counted along the path and added to the total cycle time.

Lifting:
  - XQE_122 and XNA models: lift_time = height / lifting_speed (0.2 m/s)
  - XPL_201: no significant lifting (≤20 cm); lifting_time ≈ 0
  - Lifting AND lowering are both counted (2× height unless specified).
"""

import math
from dataclasses import dataclass, field
from typing import Optional

from .agv_specs import AGV_SPECS, TASK_PARAMETERS


@dataclass
class TravelSegment:
    """Represents one leg of an AGV's path."""

    description: str
    distance: float          # metres
    is_forward: bool         # True = forward speed, False = reverse speed
    agv_type: str
    is_loaded: bool = False

    @property
    def speed(self) -> float:
        spec = AGV_SPECS[self.agv_type]
        if self.is_forward:
            return spec["forward_speed"]
        return spec["reverse_speed"]

    @property
    def travel_time(self) -> float:
        """Travel time in seconds."""
        if self.distance <= 0:
            return 0.0
        return self.distance / self.speed


@dataclass
class TaskCycleResult:
    """Detailed breakdown of a single AGV task cycle."""

    agv_type: str
    storage_type: str
    aisle_name: str

    # Distance components (metres)
    d_forward_empty: float = 0.0
    d_reverse_empty: float = 0.0
    d_forward_loaded: float = 0.0
    d_reverse_loaded: float = 0.0

    # Time components (seconds)
    forward_travel_time: float = 0.0
    reverse_travel_time: float = 0.0
    pickup_time: float = TASK_PARAMETERS["pickup_time"]
    dropoff_time: float = TASK_PARAMETERS["dropoff_time"]
    lift_time_up: float = 0.0
    lift_time_down: float = 0.0
    turn_time: float = 0.0
    dock_positioning_time: float = 0.0

    num_turns: int = 0
    lift_height: float = 0.0
    segments: list = field(default_factory=list)

    @property
    def total_cycle_time(self) -> float:
        """Total task cycle time in seconds."""
        return (
            self.forward_travel_time
            + self.reverse_travel_time
            + self.pickup_time
            + self.dropoff_time
            + self.lift_time_up
            + self.lift_time_down
            + self.turn_time
            + self.dock_positioning_time
        )

    @property
    def total_distance(self) -> float:
        return (
            self.d_forward_empty
            + self.d_reverse_empty
            + self.d_forward_loaded
            + self.d_reverse_loaded
        )

    def to_dict(self) -> dict:
        return {
            "agv_type": self.agv_type,
            "storage_type": self.storage_type,
            "aisle": self.aisle_name,
            "total_cycle_time_s": round(self.total_cycle_time, 2),
            "total_distance_m": round(self.total_distance, 2),
            "components": {
                "forward_travel_s": round(self.forward_travel_time, 2),
                "reverse_travel_s": round(self.reverse_travel_time, 2),
                "pickup_s": round(self.pickup_time, 2),
                "dropoff_s": round(self.dropoff_time, 2),
                "lift_up_s": round(self.lift_time_up, 2),
                "lift_down_s": round(self.lift_time_down, 2),
                "turns_s": round(self.turn_time, 2),
                "dock_positioning_s": round(self.dock_positioning_time, 2),
                "num_turns": self.num_turns,
                "lift_height_m": round(self.lift_height, 2),
            },
            "distances_m": {
                "forward_empty": round(self.d_forward_empty, 2),
                "reverse_empty": round(self.d_reverse_empty, 2),
                "forward_loaded": round(self.d_forward_loaded, 2),
                "reverse_loaded": round(self.d_reverse_loaded, 2),
            },
        }

    def print_breakdown(self) -> None:
        """Print a human-readable breakdown of the cycle time."""
        print(f"\n{'─' * 56}")
        print(f"  Cycle Time Breakdown – {self.agv_type}  [{self.storage_type}]")
        print(f"{'─' * 56}")
        spec = AGV_SPECS[self.agv_type]
        print(f"  AGV speeds  : fwd={spec['forward_speed']} m/s  "
              f"rev={spec['reverse_speed']} m/s")
        print(f"  Aisle       : {self.aisle_name}")
        print(f"  Lift height : {self.lift_height:.2f} m")
        print()
        print(f"  Forward travel    : {self.d_forward_empty + self.d_forward_loaded:.1f} m "
              f"→ {self.forward_travel_time:.1f} s")
        print(f"  Reverse travel    : {self.d_reverse_empty + self.d_reverse_loaded:.1f} m "
              f"→ {self.reverse_travel_time:.1f} s")
        print(f"  Pickup            : {self.pickup_time:.0f} s")
        print(f"  Dropoff           : {self.dropoff_time:.0f} s")
        if self.lift_time_up > 0 or self.lift_time_down > 0:
            print(f"  Lift (up)         : {self.lift_time_up:.1f} s")
            print(f"  Lift (down)       : {self.lift_time_down:.1f} s")
        print(f"  Turns ({self.num_turns}×10s)   : {self.turn_time:.0f} s")
        if self.dock_positioning_time > 0:
            print(f"  Dock positioning  : {self.dock_positioning_time:.0f} s")
        print(f"{'─' * 56}")
        print(f"  TOTAL CYCLE TIME  : {self.total_cycle_time:.1f} s  "
              f"({self.total_cycle_time / 60:.1f} min)")
        print(f"{'─' * 56}\n")


# ---------------------------------------------------------------------------
# Core physics calculator
# ---------------------------------------------------------------------------

class AGVPhysics:
    """
    Calculates AGV task cycle times using realistic warehouse physics.

    The calculator handles three storage modes:
      - rack          : pallets stored at height, requires lifting
      - ground_storage: pallets on floor, no lifting beyond fork engagement
      - ground_stacking: boxes on floor, stacking/unstacking considered
    """

    def __init__(self, agv_type: str) -> None:
        if agv_type not in AGV_SPECS:
            raise ValueError(f"Unknown AGV type '{agv_type}'")
        self.agv_type = agv_type
        self.spec = AGV_SPECS[agv_type]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_rack_task(
        self,
        d_head_aisle_inbound: float,
        d_aisle: float,
        d_head_aisle_outbound: float,
        lift_height: float,
        num_turns: int,
        aisle_name: str = "unknown",
    ) -> TaskCycleResult:
        """
        Calculate cycle time for a rack storage task (pallets at height).

        Path:
          Inbound dock
            → Head aisle (FORWARD, empty)
            → Storage aisle entry → Rack position (REVERSE, empty – fork first)
            → Pickup (30 s) + Lift (height / 0.2 m/s)
            → Rack position → Aisle exit (REVERSE, loaded)
            → Head aisle → Outbound dock (FORWARD, loaded)

        Parameters
        ----------
        d_head_aisle_inbound : float
            Distance along head aisle from inbound dock to aisle entry (m).
        d_aisle : float
            Distance from aisle entry to rack position (m).
            The AGV travels this distance TWICE (in and out).
        d_head_aisle_outbound : float
            Distance along head aisle from aisle exit to outbound dock (m).
        lift_height : float
            Height to lift the pallet (m). Both up and down are counted.
        num_turns : int
            Total number of 90° turns in the path.
        aisle_name : str
            Label for reporting.
        """
        self._validate_lift_height(lift_height)

        spec = self.spec
        result = TaskCycleResult(
            agv_type=self.agv_type,
            storage_type="rack",
            aisle_name=aisle_name,
            lift_height=lift_height,
            num_turns=num_turns,
        )

        # Distance split
        result.d_forward_empty = d_head_aisle_inbound
        result.d_reverse_empty = d_aisle          # into aisle, fork first (empty)
        result.d_reverse_loaded = d_aisle         # out of aisle with load
        result.d_forward_loaded = d_head_aisle_outbound

        # Travel times
        result.forward_travel_time = (
            result.d_forward_empty + result.d_forward_loaded
        ) / spec["forward_speed"]
        result.reverse_travel_time = (
            result.d_reverse_empty + result.d_reverse_loaded
        ) / spec["reverse_speed"]

        # Lifting
        if spec["lifting_speed"]:
            result.lift_time_up = lift_height / spec["lifting_speed"]
            result.lift_time_down = lift_height / spec["lifting_speed"]
        else:
            result.lift_time_up = 0.0
            result.lift_time_down = 0.0

        # Turns + operations
        result.turn_time = num_turns * TASK_PARAMETERS["turn_time_per_90deg"]
        result.pickup_time = TASK_PARAMETERS["pickup_time"]
        result.dropoff_time = TASK_PARAMETERS["dropoff_time"]

        return result

    def calculate_ground_storage_task(
        self,
        d_head_aisle_inbound: float,
        d_aisle: float,
        d_head_aisle_outbound: float,
        num_turns: int,
        aisle_name: str = "unknown",
    ) -> TaskCycleResult:
        """
        Calculate cycle time for a ground storage task (pallets on floor).

        Path:
          Inbound dock
            → Head aisle (FORWARD, empty)
            → Aisle entry → Storage position (REVERSE, empty – fork first)
            → Pickup / fork engage (30 s)
            → Storage position → Aisle exit (REVERSE, loaded)
            → Head aisle → Dock approach (FORWARD, loaded)
            → Dock positioning (10 s – reversing into dock)
            → Dropoff (30 s)

        Travel time formula:
          d_forward / forward_speed
          + 2 × d_aisle / reverse_speed   (in empty + out loaded, both reverse)
          + turns × 10 s
          + pickup_time + dropoff_time + dock_positioning_time
        """
        spec = self.spec
        result = TaskCycleResult(
            agv_type=self.agv_type,
            storage_type="ground_storage",
            aisle_name=aisle_name,
            lift_height=0.0,
            num_turns=num_turns,
        )

        result.d_forward_empty = d_head_aisle_inbound
        result.d_reverse_empty = d_aisle       # into aisle empty (fork first = reverse)
        result.d_reverse_loaded = d_aisle      # out of aisle loaded (fork first = reverse)
        result.d_forward_loaded = d_head_aisle_outbound

        result.forward_travel_time = (
            result.d_forward_empty + result.d_forward_loaded
        ) / spec["forward_speed"]
        result.reverse_travel_time = (
            result.d_reverse_empty + result.d_reverse_loaded
        ) / spec["reverse_speed"]

        result.lift_time_up = 0.0
        result.lift_time_down = 0.0

        result.turn_time = num_turns * TASK_PARAMETERS["turn_time_per_90deg"]
        result.pickup_time = TASK_PARAMETERS["pickup_time"]
        result.dropoff_time = TASK_PARAMETERS["dropoff_time"]
        result.dock_positioning_time = TASK_PARAMETERS["dock_positioning_time"]

        return result

    def calculate_ground_stacking_task(
        self,
        d_head_aisle_inbound: float,
        d_aisle: float,
        d_head_aisle_outbound: float,
        num_turns: int,
        stack_height: float = 0.0,
        aisle_name: str = "unknown",
    ) -> TaskCycleResult:
        """
        Calculate cycle time for a ground stacking task (boxes).

        Same as ground storage with optional minor lift for stacking.

        Parameters
        ----------
        stack_height : float
            Height of existing stack that pallet must be placed on top of (m).
            Only relevant for AGVs with lifting capability.
        """
        result = self.calculate_ground_storage_task(
            d_head_aisle_inbound,
            d_aisle,
            d_head_aisle_outbound,
            num_turns,
            aisle_name=aisle_name,
        )
        result.storage_type = "ground_stacking"
        result.lift_height = stack_height

        # Add stacking lift time if the AGV supports lifting
        if self.spec["lifting_speed"] and stack_height > 0:
            result.lift_time_up = stack_height / self.spec["lifting_speed"]
            result.lift_time_down = stack_height / self.spec["lifting_speed"]

        return result

    def can_operate_in_aisle(
        self,
        aisle_width: float,
        storage_type: str,
        lift_height: float = 0.0,
    ) -> tuple:
        """
        Check whether this AGV can operate in the given aisle.

        Returns
        -------
        (bool, str)
            (True, '') if compatible, or (False, reason) if not.
        """
        if storage_type not in self.spec["storage_types"]:
            return (
                False,
                f"{self.agv_type} does not support '{storage_type}' storage. "
                f"Supported: {self.spec['storage_types']}",
            )
        if aisle_width < self.spec["aisle_width"]:
            return (
                False,
                f"Aisle width {aisle_width:.2f}m is too narrow for "
                f"{self.agv_type} (requires ≥{self.spec['aisle_width']}m)",
            )
        if lift_height > self.spec["max_lift_height"]:
            return (
                False,
                f"Required lift height {lift_height:.1f}m exceeds "
                f"{self.agv_type} maximum ({self.spec['max_lift_height']}m)",
            )
        return True, ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _validate_lift_height(self, lift_height: float) -> None:
        if lift_height > self.spec["max_lift_height"]:
            raise ValueError(
                f"Lift height {lift_height:.1f}m exceeds {self.agv_type} "
                f"maximum of {self.spec['max_lift_height']}m"
            )

    @staticmethod
    def count_turns_in_path(path_nodes: list, node_positions: dict) -> int:
        """
        Count the number of 90° turns in a path through a set of nodes.

        Parameters
        ----------
        path_nodes : list
            Ordered list of node IDs in the path.
        node_positions : dict
            Mapping of node_id → (x, y) coordinates.

        Returns
        -------
        int
            Number of 90° (or near-90°) directional changes in the path.
        """
        if len(path_nodes) < 3:
            return 0

        turns = 0
        for i in range(1, len(path_nodes) - 1):
            a = node_positions.get(path_nodes[i - 1])
            b = node_positions.get(path_nodes[i])
            c = node_positions.get(path_nodes[i + 1])
            if a is None or b is None or c is None:
                continue

            # Vector AB and BC
            ab = (b[0] - a[0], b[1] - a[1])
            bc = (c[0] - b[0], c[1] - b[1])

            if _vector_len(ab) < 1e-6 or _vector_len(bc) < 1e-6:
                continue

            cos_angle = _dot(ab, bc) / (_vector_len(ab) * _vector_len(bc))
            cos_angle = max(-1.0, min(1.0, cos_angle))  # numerical safety
            angle_deg = math.degrees(math.acos(cos_angle))

            # Count turns that are roughly 90° (±30°)
            if 60 <= angle_deg <= 120:
                turns += 1

        return turns

    @staticmethod
    def estimate_turns_for_layout(
        d_head_aisle: float,
        aisle_entry_type: str,
        has_separate_inbound_outbound: bool = True,
    ) -> int:
        """
        Estimate the number of 90° turns for a typical inbound→storage→outbound
        cycle without a full graph traversal.

        Rules:
          - 1 turn: head aisle → storage aisle entry
          - 1 turn: storage aisle exit → head aisle
          - +1 turn: at outbound dock if docks are at aisle ends (not in-line)
          - +1 turn: at inbound dock if docks are at aisle ends

        Parameters
        ----------
        d_head_aisle : float
            Head aisle length in metres (used to determine dock placement).
        aisle_entry_type : str
            'dead-end' or 'through'.
        has_separate_inbound_outbound : bool
            True if inbound and outbound docks are at opposite ends of head aisle.
        """
        turns = 2  # entering + exiting the storage aisle
        if has_separate_inbound_outbound:
            turns += 0  # Docks are inline with head aisle – no extra turns
        return turns


def _dot(a: tuple, b: tuple) -> float:
    return a[0] * b[0] + a[1] * b[1]


def _vector_len(v: tuple) -> float:
    return math.sqrt(v[0] ** 2 + v[1] ** 2)
