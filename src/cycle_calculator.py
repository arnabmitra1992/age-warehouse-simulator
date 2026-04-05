"""
Cycle Time Calculator Module
==============================
Physics-based cycle time calculations for all workflow phases.

AGV Specifications used in this module:
  XPL_201  – Forward: 1.5 m/s, Reverse: 0.5 m/s, NO lift, pickup/dropoff: 30 s
  XQE_122  – Forward: 1.0 m/s, Reverse: 0.3 m/s, Lift: 0.2 m/s (max 4.5 m)
  XNA_121/151 – Forward/Reverse: 1.0 m/s, Lift: 0.2 m/s (backward fork)

Turn time: 10 s per 90° turn.
Pickup / dropoff: 30 s each.

Workflow phases:
  Horizontal travel leg   →  distance / speed
  Lifting/lowering        →  height / 0.2 m/s (each way)
  Turns                   →  count × 10 s
  Pickup                  →  30 s
  Dropoff                 →  30 s
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# AGV speed constants (metres/second)
# ---------------------------------------------------------------------------

_SPECS: Dict[str, Dict[str, float]] = {
    "XPL_201": {
        "forward_speed": 1.5,
        "reverse_speed": 0.5,   # loaded / fork-engaged
        "lifting_speed": 0.0,   # no significant lifting
    },
    "XQE_122": {
        "forward_speed": 1.0,
        "reverse_speed": 0.3,
        "lifting_speed": 0.2,
        "max_lift_height": 4.5,
    },
    "XNA_121": {
        "forward_speed": 1.0,
        "reverse_speed": 1.0,   # equal in both directions
        "lifting_speed": 0.2,
        "max_lift_height": 8.5,
    },
    "XNA_151": {
        "forward_speed": 1.0,
        "reverse_speed": 1.0,
        "lifting_speed": 0.2,
        "max_lift_height": 13.0,
    },
    # Generic "XNA" alias (uses XNA_151 characteristics for conservative sizing)
    "XNA": {
        "forward_speed": 1.0,
        "reverse_speed": 1.0,
        "lifting_speed": 0.2,
        "max_lift_height": 13.0,
    },
}

PICKUP_TIME_S: float = 30.0
DROPOFF_TIME_S: float = 30.0
TURN_TIME_S: float = 10.0    # per 90° turn
LIFTING_SPEED_M_S: float = 0.2


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class CycleTimeResult:
    """Detailed breakdown of a single workflow phase or full cycle."""

    agv_type: str
    phase: str = ""          # e.g. 'inbound_to_handover', 'handover_to_rack', 'full'

    # Travel time components (seconds)
    forward_travel_s: float = 0.0
    reverse_travel_s: float = 0.0

    # Other components (seconds)
    lift_up_s: float = 0.0
    lift_down_s: float = 0.0
    pickup_s: float = 0.0
    dropoff_s: float = 0.0
    turn_s: float = 0.0

    # Distance components (metres)
    distance_m: float = 0.0
    lift_height_m: float = 0.0
    num_turns: int = 0

    # Sub-phases (for multi-leg workflows)
    sub_results: list = field(default_factory=list)

    @property
    def total_s(self) -> float:
        """Total cycle time in seconds."""
        return (
            self.forward_travel_s
            + self.reverse_travel_s
            + self.lift_up_s
            + self.lift_down_s
            + self.pickup_s
            + self.dropoff_s
            + self.turn_s
        )

    @property
    def total_min(self) -> float:
        return self.total_s / 60.0

    def to_dict(self) -> dict:
        return {
            "agv_type": self.agv_type,
            "phase": self.phase,
            "total_s": round(self.total_s, 2),
            "total_min": round(self.total_min, 2),
            "components": {
                "forward_travel_s": round(self.forward_travel_s, 2),
                "reverse_travel_s": round(self.reverse_travel_s, 2),
                "lift_up_s": round(self.lift_up_s, 2),
                "lift_down_s": round(self.lift_down_s, 2),
                "pickup_s": round(self.pickup_s, 2),
                "dropoff_s": round(self.dropoff_s, 2),
                "turn_s": round(self.turn_s, 2),
            },
            "inputs": {
                "distance_m": round(self.distance_m, 3),
                "lift_height_m": round(self.lift_height_m, 3),
                "num_turns": self.num_turns,
            },
        }


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------

class CycleCalculator:
    """
    Physics-based cycle time calculator for AGV workflow phases.

    All distances in metres (m).
    """

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    @staticmethod
    def travel_time(distance_m: float, speed_m_s: float) -> float:
        """Return travel time in seconds."""
        if distance_m <= 0 or speed_m_s <= 0:
            return 0.0
        return distance_m / speed_m_s

    @staticmethod
    def lift_time(height_m: float, speed_m_s: float = LIFTING_SPEED_M_S) -> float:
        """Return lift (or lower) time in seconds for a given height."""
        if height_m <= 0 or speed_m_s <= 0:
            return 0.0
        return height_m / speed_m_s

    @staticmethod
    def turn_time(num_turns: int) -> float:
        return num_turns * TURN_TIME_S

    # ------------------------------------------------------------------
    # Single-leg phase calculations
    # ------------------------------------------------------------------

    def horizontal_leg(
        self,
        agv_type: str,
        distance_m: float,
        is_loaded: bool = False,
        num_turns: int = 0,
        phase: str = "horizontal",
    ) -> CycleTimeResult:
        """
        Calculate time for one horizontal travel leg.

        Empty travel → forward speed.
        Loaded travel (fork engaged) → reverse speed.
        """
        spec = _SPECS[agv_type]
        if is_loaded:
            speed = spec["reverse_speed"]
            fwd_t = 0.0
            rev_t = self.travel_time(distance_m, speed)
        else:
            speed = spec["forward_speed"]
            fwd_t = self.travel_time(distance_m, speed)
            rev_t = 0.0

        return CycleTimeResult(
            agv_type=agv_type,
            phase=phase,
            forward_travel_s=fwd_t,
            reverse_travel_s=rev_t,
            turn_s=self.turn_time(num_turns),
            distance_m=distance_m,
            num_turns=num_turns,
        )

    def rack_storage_leg(
        self,
        agv_type: str,
        depth_m: float,
        lift_height_m: float,
        is_inbound: bool = True,
        num_entry_turns: int = 2,
    ) -> CycleTimeResult:
        """
        Calculate time for the in-aisle rack storage/retrieval leg.

        For XNA models, the AGV enters and exits the rack aisle at the handover hub.
        For XQE, the AGV performs the full operation autonomously if no handover.

        The AGV travels *depth_m* into the aisle (fork-first = reverse, empty)
        performs the pickup/dropoff, lifts/lowers, then exits (*depth_m*, loaded,
        reverse).  Two entry/exit turns are included by default.

        Parameters
        ----------
        depth_m : float
            Distance from aisle entry to storage position.
        lift_height_m : float
            Height to lift (or lower) the pallet.
        is_inbound : bool
            True → pickup at dock, dropoff at rack (lift up, then lower on return).
            False → pickup at rack (lift to height), dropoff at dock.
        num_entry_turns : int
            Turns entering + exiting the aisle (default 2).
        """
        spec = _SPECS[agv_type]

        # Into aisle: empty, fork-first → reverse
        rev_in_t = self.travel_time(depth_m, spec["reverse_speed"])
        # Out of aisle: loaded, fork-first → reverse
        rev_out_t = self.travel_time(depth_m, spec["reverse_speed"])

        lift_s = self.lift_time(lift_height_m, spec.get("lifting_speed", 0.0))

        result = CycleTimeResult(
            agv_type=agv_type,
            phase="rack_storage" if is_inbound else "rack_retrieval",
            reverse_travel_s=rev_in_t + rev_out_t,
            lift_up_s=lift_s,
            lift_down_s=lift_s,
            pickup_s=PICKUP_TIME_S,
            dropoff_s=DROPOFF_TIME_S,
            turn_s=self.turn_time(num_entry_turns),
            distance_m=depth_m * 2,
            lift_height_m=lift_height_m,
            num_turns=num_entry_turns,
        )
        return result

    def stacking_leg(
        self,
        agv_type: str,
        depth_m: float,
        lift_height_m: float,
        is_inbound: bool = True,
        num_entry_turns: int = 2,
    ) -> CycleTimeResult:
        """
        Calculate time for the ground stacking / retrieval leg (XQE_122 only).

        Mirrors rack_storage_leg but only valid for XQE_122.
        """
        result = self.rack_storage_leg(
            agv_type=agv_type,
            depth_m=depth_m,
            lift_height_m=lift_height_m,
            is_inbound=is_inbound,
            num_entry_turns=num_entry_turns,
        )
        result.phase = "stacking_store" if is_inbound else "stacking_retrieve"
        return result

    # ------------------------------------------------------------------
    # Full workflow cycle times
    # ------------------------------------------------------------------

    def inbound_xna_cycle(
        self,
        d_inbound_to_handover_m: float,
        d_handover_to_rack_m: float,
        avg_rack_depth_m: float,
        avg_lift_height_m: float,
        num_turns_xpl: int = 2,
        num_turns_xna: int = 2,
    ) -> Dict[str, CycleTimeResult]:
        """
        INBOUND – XNA (Narrow Aisle, ALWAYS HANDOVER):
          Inbound → [XPL_201] → Handover → [XNA] → Rack Storage

        Returns dict of phase → CycleTimeResult.
        """
        # XPL leg: Inbound → Handover (empty forward, loaded reverse)
        xpl_empty = self.horizontal_leg(
            "XPL_201", d_inbound_to_handover_m, is_loaded=False,
            num_turns=0, phase="inbound_empty",
        )
        xpl_loaded = self.horizontal_leg(
            "XPL_201", d_inbound_to_handover_m, is_loaded=True,
            num_turns=num_turns_xpl, phase="inbound_to_handover_loaded",
        )
        xpl_pickup = CycleTimeResult("XPL_201", phase="xpl_pickup",
                                     pickup_s=PICKUP_TIME_S, dropoff_s=DROPOFF_TIME_S)

        # XNA leg: Handover → Rack
        xna_approach = self.horizontal_leg(
            "XNA", d_handover_to_rack_m, is_loaded=False,
            num_turns=0, phase="handover_to_rack_empty",
        )
        xna_storage = self.rack_storage_leg(
            "XNA", avg_rack_depth_m, avg_lift_height_m,
            is_inbound=True, num_entry_turns=num_turns_xna,
        )

        return {
            "xpl_inbound_to_handover": _combine(
                "XPL_201", "xpl_inbound_to_handover",
                xpl_empty, xpl_loaded, xpl_pickup,
            ),
            "xna_handover_to_rack": _combine(
                "XNA", "xna_handover_to_rack",
                xna_approach, xna_storage,
            ),
        }

    def inbound_xqe_no_handover_cycle(
        self,
        d_inbound_to_rack_m: float,
        avg_rack_depth_m: float,
        avg_lift_height_m: float,
        num_turns: int = 4,
    ) -> CycleTimeResult:
        """
        INBOUND – XQE (Standard Aisle, NO HANDOVER, distance < 50 m):
          Inbound → [XQE_122] → Storage → [XQE_122] → Rest

        Single XQE cycle from inbound dock to rack and back to rest.
        """
        # Forward to inbound dock area
        approach = self.horizontal_leg(
            "XQE_122", d_inbound_to_rack_m, is_loaded=False,
            num_turns=0, phase="approach_inbound",
        )
        # Into rack + store
        storage = self.rack_storage_leg(
            "XQE_122", avg_rack_depth_m, avg_lift_height_m,
            is_inbound=True, num_entry_turns=num_turns,
        )
        # Return from rack to rest
        return_leg = self.horizontal_leg(
            "XQE_122", d_inbound_to_rack_m, is_loaded=False,
            num_turns=0, phase="return_to_rest",
        )
        return _combine("XQE_122", "inbound_xqe_no_handover",
                        approach, storage, return_leg)

    def inbound_xqe_with_handover_cycle(
        self,
        d_inbound_to_handover_m: float,
        d_handover_to_rack_m: float,
        avg_rack_depth_m: float,
        avg_lift_height_m: float,
        num_turns_xpl: int = 2,
        num_turns_xqe: int = 4,
    ) -> Dict[str, CycleTimeResult]:
        """
        INBOUND – XQE (Standard Aisle, WITH HANDOVER, distance ≥ 50 m):
          Inbound → [XPL_201] → Handover → [XQE_122] → Storage

        Returns dict of phase → CycleTimeResult.
        """
        # XPL leg: Inbound → Handover
        xpl_leg = self.horizontal_leg(
            "XPL_201", d_inbound_to_handover_m, is_loaded=True,
            num_turns=num_turns_xpl, phase="inbound_to_handover",
        )
        xpl_overhead = CycleTimeResult("XPL_201", phase="xpl_pickup_dropoff",
                                       pickup_s=PICKUP_TIME_S, dropoff_s=DROPOFF_TIME_S)

        # XQE leg: Handover → Rack
        xqe_approach = self.horizontal_leg(
            "XQE_122", d_handover_to_rack_m, is_loaded=False,
            num_turns=0, phase="handover_to_rack_empty",
        )
        xqe_storage = self.rack_storage_leg(
            "XQE_122", avg_rack_depth_m, avg_lift_height_m,
            is_inbound=True, num_entry_turns=num_turns_xqe,
        )

        return {
            "xpl_inbound_to_handover": _combine(
                "XPL_201", "xpl_inbound_to_handover", xpl_leg, xpl_overhead
            ),
            "xqe_handover_to_rack": _combine(
                "XQE_122", "xqe_handover_to_rack", xqe_approach, xqe_storage
            ),
        }

    def inbound_xqe_stacking_no_handover_cycle(
        self,
        d_inbound_to_stacking_m: float,
        avg_stacking_depth_m: float,
        avg_lift_height_m: float,
        num_turns: int = 4,
    ) -> CycleTimeResult:
        """
        INBOUND – XQE Ground Stacking (NO HANDOVER):
          Inbound → [XQE_122] → Stacking Area → Rest
        """
        approach = self.horizontal_leg(
            "XQE_122", d_inbound_to_stacking_m, is_loaded=False,
            num_turns=0, phase="approach_stacking",
        )
        stack_leg = self.stacking_leg(
            "XQE_122", avg_stacking_depth_m, avg_lift_height_m,
            is_inbound=True, num_entry_turns=num_turns,
        )
        return_leg = self.horizontal_leg(
            "XQE_122", d_inbound_to_stacking_m, is_loaded=False,
            num_turns=0, phase="return_to_rest",
        )
        return _combine("XQE_122", "inbound_xqe_stacking_no_handover",
                        approach, stack_leg, return_leg)

    def inbound_xqe_stacking_with_handover_cycle(
        self,
        d_inbound_to_handover_m: float,
        d_handover_to_stacking_m: float,
        avg_stacking_depth_m: float,
        avg_lift_height_m: float,
        num_turns_xpl: int = 2,
        num_turns_xqe: int = 4,
    ) -> Dict[str, CycleTimeResult]:
        """
        INBOUND – XQE Ground Stacking WITH HANDOVER (distance ≥ 50 m):
          Inbound → [XPL_201] → Handover → [XQE_122] → Stacking Area
        """
        xpl_leg = self.horizontal_leg(
            "XPL_201", d_inbound_to_handover_m, is_loaded=True,
            num_turns=num_turns_xpl, phase="inbound_to_handover",
        )
        xpl_overhead = CycleTimeResult("XPL_201", phase="xpl_ops",
                                       pickup_s=PICKUP_TIME_S, dropoff_s=DROPOFF_TIME_S)

        xqe_approach = self.horizontal_leg(
            "XQE_122", d_handover_to_stacking_m, is_loaded=False,
            num_turns=0, phase="handover_to_stacking_empty",
        )
        xqe_stack = self.stacking_leg(
            "XQE_122", avg_stacking_depth_m, avg_lift_height_m,
            is_inbound=True, num_entry_turns=num_turns_xqe,
        )

        return {
            "xpl_inbound_to_handover": _combine(
                "XPL_201", "xpl_inbound_to_handover", xpl_leg, xpl_overhead
            ),
            "xqe_handover_to_stacking": _combine(
                "XQE_122", "xqe_handover_to_stacking", xqe_approach, xqe_stack
            ),
        }

    # ------------------------------------------------------------------
    # Outbound cycles
    # ------------------------------------------------------------------

    def outbound_xna_cycle(
        self,
        d_handover_to_outbound_m: float,
        d_handover_to_rack_m: float,
        avg_rack_depth_m: float,
        avg_lift_height_m: float,
        num_turns_xna: int = 2,
        num_turns_xpl: int = 2,
    ) -> Dict[str, CycleTimeResult]:
        """
        OUTBOUND – XNA (Narrow Aisle, ALWAYS HANDOVER):
          Rest → [XNA] → Rack → [XNA] → Handover → [XPL_201] → Outbound

        Returns dict of phase → CycleTimeResult.
        """
        # XNA: approach rack from rest (via handover)
        xna_approach = self.horizontal_leg(
            "XNA", d_handover_to_rack_m, is_loaded=False,
            num_turns=0, phase="rest_to_rack_empty",
        )
        xna_retrieve = self.rack_storage_leg(
            "XNA", avg_rack_depth_m, avg_lift_height_m,
            is_inbound=False, num_entry_turns=num_turns_xna,
        )
        # XNA: rack to handover (loaded)
        xna_to_handover = self.horizontal_leg(
            "XNA", d_handover_to_rack_m, is_loaded=True,
            num_turns=0, phase="rack_to_handover_loaded",
        )
        # XPL: handover to outbound
        xpl_leg = self.horizontal_leg(
            "XPL_201", d_handover_to_outbound_m, is_loaded=True,
            num_turns=num_turns_xpl, phase="handover_to_outbound",
        )
        xpl_overhead = CycleTimeResult("XPL_201", phase="xpl_ops",
                                       pickup_s=PICKUP_TIME_S, dropoff_s=DROPOFF_TIME_S)

        return {
            "xna_rack_to_handover": _combine(
                "XNA", "xna_rack_to_handover",
                xna_approach, xna_retrieve, xna_to_handover,
            ),
            "xpl_handover_to_outbound": _combine(
                "XPL_201", "xpl_handover_to_outbound", xpl_leg, xpl_overhead
            ),
        }

    def outbound_xqe_no_handover_cycle(
        self,
        d_rack_to_outbound_m: float,
        avg_rack_depth_m: float,
        avg_lift_height_m: float,
        num_turns: int = 4,
    ) -> CycleTimeResult:
        """
        OUTBOUND – XQE (Standard Aisle, NO HANDOVER, distance < 50 m):
          Rest → [XQE_122] → Rack → [XQE_122] → Outbound → Rest
        """
        approach = self.horizontal_leg(
            "XQE_122", d_rack_to_outbound_m, is_loaded=False,
            num_turns=0, phase="rest_to_rack_empty",
        )
        retrieve = self.rack_storage_leg(
            "XQE_122", avg_rack_depth_m, avg_lift_height_m,
            is_inbound=False, num_entry_turns=num_turns,
        )
        delivery = self.horizontal_leg(
            "XQE_122", d_rack_to_outbound_m, is_loaded=True,
            num_turns=0, phase="rack_to_outbound_loaded",
        )
        return _combine("XQE_122", "outbound_xqe_no_handover",
                        approach, retrieve, delivery)

    def outbound_xqe_with_handover_cycle(
        self,
        d_rack_to_handover_m: float,
        d_handover_to_outbound_m: float,
        avg_rack_depth_m: float,
        avg_lift_height_m: float,
        num_turns_xqe: int = 4,
        num_turns_xpl: int = 2,
    ) -> Dict[str, CycleTimeResult]:
        """
        OUTBOUND – XQE (Standard Aisle, WITH HANDOVER, distance ≥ 50 m):
          Rest → [XQE_122] → Rack → [XQE_122] → Handover → [XPL_201] → Outbound

        Returns dict of phase → CycleTimeResult.
        """
        # XQE: rest → rack → handover
        xqe_approach = self.horizontal_leg(
            "XQE_122", d_rack_to_handover_m, is_loaded=False,
            num_turns=0, phase="rest_to_rack_empty",
        )
        xqe_retrieve = self.rack_storage_leg(
            "XQE_122", avg_rack_depth_m, avg_lift_height_m,
            is_inbound=False, num_entry_turns=num_turns_xqe,
        )
        xqe_to_handover = self.horizontal_leg(
            "XQE_122", d_rack_to_handover_m, is_loaded=True,
            num_turns=0, phase="rack_to_handover_loaded",
        )
        xqe_dropoff = CycleTimeResult("XQE_122", phase="xqe_dropoff",
                                      dropoff_s=DROPOFF_TIME_S)

        # XPL: handover → outbound
        xpl_leg = self.horizontal_leg(
            "XPL_201", d_handover_to_outbound_m, is_loaded=True,
            num_turns=num_turns_xpl, phase="handover_to_outbound",
        )
        xpl_overhead = CycleTimeResult("XPL_201", phase="xpl_pickup",
                                       pickup_s=PICKUP_TIME_S, dropoff_s=DROPOFF_TIME_S)

        return {
            "xqe_rack_to_handover": _combine(
                "XQE_122", "xqe_rack_to_handover",
                xqe_approach, xqe_retrieve, xqe_to_handover, xqe_dropoff,
            ),
            "xpl_handover_to_outbound": _combine(
                "XPL_201", "xpl_handover_to_outbound", xpl_leg, xpl_overhead
            ),
        }

    def outbound_xqe_stacking_no_handover_cycle(
        self,
        d_stacking_to_outbound_m: float,
        avg_stacking_depth_m: float,
        avg_lift_height_m: float,
        num_turns: int = 4,
    ) -> CycleTimeResult:
        """
        OUTBOUND – XQE Ground Stacking (NO HANDOVER):
          Rest → [XQE_122] → Stacking Area → [XQE_122] → Outbound → Rest
        """
        approach = self.horizontal_leg(
            "XQE_122", d_stacking_to_outbound_m, is_loaded=False,
            num_turns=0, phase="rest_to_stacking_empty",
        )
        retrieve = self.stacking_leg(
            "XQE_122", avg_stacking_depth_m, avg_lift_height_m,
            is_inbound=False, num_entry_turns=num_turns,
        )
        delivery = self.horizontal_leg(
            "XQE_122", d_stacking_to_outbound_m, is_loaded=True,
            num_turns=0, phase="stacking_to_outbound_loaded",
        )
        return _combine("XQE_122", "outbound_xqe_stacking_no_handover",
                        approach, retrieve, delivery)

    def outbound_xqe_stacking_with_handover_cycle(
        self,
        d_stacking_to_handover_m: float,
        d_handover_to_outbound_m: float,
        avg_stacking_depth_m: float,
        avg_lift_height_m: float,
        num_turns_xqe: int = 4,
        num_turns_xpl: int = 2,
    ) -> Dict[str, CycleTimeResult]:
        """
        OUTBOUND – XQE Ground Stacking WITH HANDOVER:
          Rest → [XQE_122] → Stacking → [XQE_122] → Handover → [XPL_201] → Outbound
        """
        xqe_approach = self.horizontal_leg(
            "XQE_122", d_stacking_to_handover_m, is_loaded=False,
            num_turns=0, phase="rest_to_stacking_empty",
        )
        xqe_retrieve = self.stacking_leg(
            "XQE_122", avg_stacking_depth_m, avg_lift_height_m,
            is_inbound=False, num_entry_turns=num_turns_xqe,
        )
        xqe_to_handover = self.horizontal_leg(
            "XQE_122", d_stacking_to_handover_m, is_loaded=True,
            num_turns=0, phase="stacking_to_handover_loaded",
        )
        xqe_dropoff = CycleTimeResult("XQE_122", phase="xqe_dropoff",
                                      dropoff_s=DROPOFF_TIME_S)

        xpl_leg = self.horizontal_leg(
            "XPL_201", d_handover_to_outbound_m, is_loaded=True,
            num_turns=num_turns_xpl, phase="handover_to_outbound",
        )
        xpl_overhead = CycleTimeResult("XPL_201", phase="xpl_pickup",
                                       pickup_s=PICKUP_TIME_S, dropoff_s=DROPOFF_TIME_S)

        return {
            "xqe_stacking_to_handover": _combine(
                "XQE_122", "xqe_stacking_to_handover",
                xqe_approach, xqe_retrieve, xqe_to_handover, xqe_dropoff,
            ),
            "xpl_handover_to_outbound": _combine(
                "XPL_201", "xpl_handover_to_outbound", xpl_leg, xpl_overhead
            ),
        }


# ---------------------------------------------------------------------------
# Utility: combine multiple CycleTimeResult instances into one
# ---------------------------------------------------------------------------

def _combine(agv_type: str, phase: str, *results: CycleTimeResult) -> CycleTimeResult:
    combined = CycleTimeResult(agv_type=agv_type, phase=phase)
    for r in results:
        combined.forward_travel_s += r.forward_travel_s
        combined.reverse_travel_s += r.reverse_travel_s
        combined.lift_up_s += r.lift_up_s
        combined.lift_down_s += r.lift_down_s
        combined.pickup_s += r.pickup_s
        combined.dropoff_s += r.dropoff_s
        combined.turn_s += r.turn_s
        combined.distance_m += r.distance_m
        combined.lift_height_m = max(combined.lift_height_m, r.lift_height_m)
        combined.num_turns += r.num_turns
    return combined
