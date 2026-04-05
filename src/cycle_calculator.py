"""
Physics-based cycle time calculator.

All distance inputs are in metres; all time outputs are in seconds.
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

from .agv_specs import XQE122Specs, XPL201Specs, TurnSpecs
from .warehouse_layout import WarehouseDistances
from .rack_storage import RackConfig
from .ground_stacking import GroundStackingConfig

REVERSE_ENTRY_DIST_M = 1.5   # standard reverse-in distance (m) for pickups, dropoffs, parking


@dataclass
class CyclePhase:
    """One step of a cycle timeline."""
    name: str
    duration_s: float
    description: str = ""


@dataclass
class CycleResult:
    """Complete cycle time result with phase breakdown."""
    total_time_s: float
    phases: List[CyclePhase] = field(default_factory=list)

    @property
    def total_time_min(self) -> float:
        return self.total_time_s / 60.0

    def summary(self) -> str:
        lines = [f"Total cycle time: {self.total_time_s:.1f}s ({self.total_time_min:.2f} min)"]
        for p in self.phases:
            lines.append(f"  {p.name:<40} {p.duration_s:>8.1f}s  {p.description}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Workflow 1: XPL_201 Handover
# ---------------------------------------------------------------------------

def xpl201_handover_cycle(
    agv: XPL201Specs,
    turns: TurnSpecs,
    dist: WarehouseDistances,
) -> CycleResult:
    """
    Calculate XPL_201 handover cycle time.

    Movement:
      Rest → Head Aisle (FORWARD, EMPTY)
      → Inbound Buffer (REVERSE, EMPTY – back in)
      → PICKUP (30s)
      → Inbound Buffer (FORWARD, LOADED – drive out)
      → Head Aisle (FORWARD, LOADED)
      → Handover Zone (REVERSE, LOADED – back in) + TURN
      → DROPOFF (30s)
      → Head Aisle (FORWARD, EMPTY) + TURN
      → Rest Area (REVERSE, EMPTY – back in to park)
    """
    fwd = agv.forward_speed_ms
    rev = agv.reverse_speed_ms
    phases: List[CyclePhase] = []

    def _add(name: str, dist_m: float, speed: float, desc: str = ""):
        t = dist_m / speed
        phases.append(CyclePhase(name, t, desc))
        return t

    def _add_fixed(name: str, t: float, desc: str = ""):
        phases.append(CyclePhase(name, t, desc))
        return t

    total = 0.0

    # Rest → Head Aisle (forward, empty)
    total += _add("Rest → Head Aisle (fwd, empty)", dist.rest_to_head_aisle_m, fwd, "forward / empty")
    # Head Aisle → Inbound Buffer (forward, empty)
    inbound_fwd_dist = dist.rest_to_inbound_m - dist.rest_to_head_aisle_m
    total += _add("Head Aisle → Inbound (fwd, empty)", inbound_fwd_dist, fwd, "forward / empty")
    # Reverse into inbound buffer (1.5 m)
    total += _add("Reverse into Inbound (rev, empty)", REVERSE_ENTRY_DIST_M, rev, "reverse 1.5 m / empty")
    # Pickup
    total += _add_fixed("PICKUP", agv.pickup_time_s, "pickup operation")
    # Drive out of inbound buffer forward (1.5 m)
    total += _add("Drive out Inbound (fwd, loaded)", REVERSE_ENTRY_DIST_M, fwd, "forward 1.5 m / loaded")
    # Head Aisle → Handover (forward, loaded)
    total += _add("Inbound → Head Aisle (fwd, loaded)", inbound_fwd_dist, fwd, "forward / loaded")
    total += _add("Head Aisle → Handover (fwd, loaded)", dist.head_aisle_to_handover_m, fwd, "forward / loaded")
    # Turn 90° toward handover zone
    total += _add_fixed("Turn 90° (toward handover)", turns.turn_90_degrees_s, "turn 90°")
    # Reverse into handover zone (1.5 m)
    total += _add("Reverse into Handover (rev, loaded)", REVERSE_ENTRY_DIST_M, rev, "reverse 1.5 m / loaded")
    # Dropoff
    total += _add_fixed("DROPOFF", agv.dropoff_time_s, "dropoff operation")
    # Drive out forward (1.5 m)
    total += _add("Drive out Handover (fwd, empty)", REVERSE_ENTRY_DIST_M, fwd, "forward 1.5 m / empty")
    # Turn 90° back toward head aisle
    total += _add_fixed("Turn 90° (back to aisle)", turns.turn_90_degrees_s, "turn 90°")
    # Handover → Head Aisle (forward, empty)
    total += _add("Handover → Head Aisle (fwd, empty)", dist.head_aisle_to_handover_m, fwd, "forward / empty")
    # Head Aisle → Rest (forward, empty)
    total += _add("Head Aisle → Rest fwd portion", inbound_fwd_dist, fwd, "forward / empty")
    # Reverse into rest area parking spot
    total += _add("Reverse into Rest (rev, empty)", REVERSE_ENTRY_DIST_M, rev, "reverse 1.5 m / empty")

    return CycleResult(total_time_s=total, phases=phases)


# ---------------------------------------------------------------------------
# Workflow 2: XQE_122 Rack Storage
# ---------------------------------------------------------------------------

def xqe122_rack_cycle(
    agv: XQE122Specs,
    turns: TurnSpecs,
    dist: WarehouseDistances,
    rack: RackConfig,
    position_n: int,
    shelf_level: int,
) -> CycleResult:
    """
    Calculate XQE_122 rack storage cycle time for a specific position.

    position_n  : 1-based pallet position along the rack
    shelf_level : 1-based shelf level (1 = lowest shelf)
    """
    fwd = agv.forward_speed_ms
    rev = agv.reverse_speed_ms
    lift = agv.lift_speed_ms
    phases: List[CyclePhase] = []

    def _add(name: str, dist_m: float, speed: float, desc: str = ""):
        t = dist_m / speed
        phases.append(CyclePhase(name, t, desc))
        return t

    def _add_fixed(name: str, t: float, desc: str = ""):
        phases.append(CyclePhase(name, t, desc))
        return t

    total = 0.0

    # Distances
    head_aisle_to_inbound_m = dist.rest_to_inbound_m - dist.rest_to_head_aisle_m

    # Rest → Head Aisle (forward, empty)
    total += _add("Rest → Head Aisle (fwd, empty)", dist.rest_to_head_aisle_m, fwd, "forward / empty")
    # Head Aisle → Inbound Buffer (forward, empty)
    total += _add("Head Aisle → Inbound (fwd, empty)", head_aisle_to_inbound_m, fwd, "forward / empty")
    # Reverse into inbound (1.5 m)
    total += _add("Reverse into Inbound (rev, empty)", REVERSE_ENTRY_DIST_M, rev, "reverse 1.5 m / empty")
    # Pickup
    total += _add_fixed("PICKUP", agv.pickup_time_s, "pickup operation")
    # Drive out of inbound forward (1.5 m)
    total += _add("Drive out Inbound (fwd, loaded)", REVERSE_ENTRY_DIST_M, fwd, "forward 1.5 m / loaded")
    # Inbound → Head Aisle (forward, loaded)
    total += _add("Inbound → Head Aisle (fwd, loaded)", head_aisle_to_inbound_m, fwd, "forward / loaded")
    # Head Aisle → Rack Aisle Entry (forward, loaded)
    total += _add("Head Aisle → Rack Aisle (fwd, loaded)", dist.head_aisle_to_rack_aisle_m, fwd, "forward / loaded")
    # Travel to position N centre within aisle (forward, loaded)
    pos_dist_m = rack.distance_to_position_m(position_n)
    total += _add(f"Rack Aisle → Position {position_n} (fwd, loaded)", pos_dist_m, fwd, "forward / loaded")
    # Turn 90° toward shelf
    total += _add_fixed("Turn 90° (toward rack shelf)", turns.turn_90_degrees_s, "turn 90°")
    # Reverse 1.5 m into shelf position
    total += _add("Reverse into shelf (rev, loaded)", REVERSE_ENTRY_DIST_M, rev, "reverse 1.5 m / loaded")
    # Lift to shelf height
    shelf_height_m = rack.shelf_height_m(shelf_level)
    lift_time = shelf_height_m / lift
    total += _add_fixed(f"LIFT to level {shelf_level} ({shelf_height_m:.2f}m)", lift_time,
                        f"lift {shelf_height_m:.2f} m @ {lift} m/s")
    # Dropoff
    total += _add_fixed("DROPOFF", agv.dropoff_time_s, "dropoff operation")
    # Lower forks (assumed same time as lift)
    total += _add_fixed(f"LOWER forks from level {shelf_level}", lift_time, "lower forks")
    # Forward 1.5 m away from shelf
    total += _add("Drive away from shelf (fwd, empty)", REVERSE_ENTRY_DIST_M, fwd, "forward 1.5 m / empty")
    # Turn 90° back to aisle direction
    total += _add_fixed("Turn 90° (back to aisle)", turns.turn_90_degrees_s, "turn 90°")
    # Travel from position N to aisle exit (forward, empty)
    exit_dist_m = rack.distance_from_position_to_exit_m(position_n)
    total += _add(f"Position {position_n} → Aisle Exit (fwd, empty)", exit_dist_m, fwd, "forward / empty")
    # Rack Aisle Exit → Head Aisle (forward, empty)
    total += _add("Rack Aisle → Head Aisle (fwd, empty)", dist.head_aisle_to_rack_aisle_m, fwd, "forward / empty")
    # Head Aisle → Rest approach (forward, empty)
    total += _add("Head Aisle → Rest (fwd, empty)", dist.rest_to_head_aisle_m, fwd, "forward / empty")
    # Reverse into rest area
    total += _add("Reverse into Rest (rev, empty)", REVERSE_ENTRY_DIST_M, rev, "reverse 1.5 m / empty")

    return CycleResult(total_time_s=total, phases=phases)


def xqe122_rack_average_cycle(
    agv: XQE122Specs,
    turns: TurnSpecs,
    dist: WarehouseDistances,
    rack: RackConfig,
) -> CycleResult:
    """Return the average cycle time across all rack positions and shelf levels."""
    total_time = 0.0
    count = 0
    for (level, pos) in rack.all_positions():
        result = xqe122_rack_cycle(agv, turns, dist, rack, pos, level)
        total_time += result.total_time_s
        count += 1
    if count == 0:
        return CycleResult(0.0)
    avg = total_time / count
    # Return a representative cycle (middle position, middle level)
    mid_pos = max(1, rack.positions_per_shelf // 2)
    mid_level = max(1, rack.num_levels // 2)
    result = xqe122_rack_cycle(agv, turns, dist, rack, mid_pos, mid_level)
    # Override total with the computed average
    result.total_time_s = avg
    return result


# ---------------------------------------------------------------------------
# Workflow 3: XQE_122 Ground Stacking
# ---------------------------------------------------------------------------

def xqe122_stacking_cycle(
    agv: XQE122Specs,
    turns: TurnSpecs,
    dist: WarehouseDistances,
    stacking: GroundStackingConfig,
    row: int,
    col: int,
    level: int,
) -> CycleResult:
    """
    Calculate XQE_122 ground stacking cycle time for position (row, col, level).
    """
    fwd = agv.forward_speed_ms
    rev = agv.reverse_speed_ms
    lift = agv.lift_speed_ms
    phases: List[CyclePhase] = []

    def _add(name: str, dist_m: float, speed: float, desc: str = ""):
        t = dist_m / speed
        phases.append(CyclePhase(name, t, desc))
        return t

    def _add_fixed(name: str, t: float, desc: str = ""):
        phases.append(CyclePhase(name, t, desc))
        return t

    total = 0.0
    head_aisle_to_inbound_m = dist.rest_to_inbound_m - dist.rest_to_head_aisle_m

    # Rest → Head Aisle (forward, empty)
    total += _add("Rest → Head Aisle (fwd, empty)", dist.rest_to_head_aisle_m, fwd, "forward / empty")
    # Head Aisle → Inbound Buffer (forward, empty)
    total += _add("Head Aisle → Inbound (fwd, empty)", head_aisle_to_inbound_m, fwd, "forward / empty")
    # Reverse into inbound buffer (1.5 m)
    total += _add("Reverse into Inbound (rev, empty)", REVERSE_ENTRY_DIST_M, rev, "reverse 1.5 m / empty")
    # Pickup
    total += _add_fixed("PICKUP", agv.pickup_time_s, "pickup operation")
    # Drive out forward (1.5 m)
    total += _add("Drive out Inbound (fwd, loaded)", REVERSE_ENTRY_DIST_M, fwd, "forward 1.5 m / loaded")
    # Inbound → Head Aisle (forward, loaded)
    total += _add("Inbound → Head Aisle (fwd, loaded)", head_aisle_to_inbound_m, fwd, "forward / loaded")
    # Head Aisle → Stacking Area Entry (forward, loaded)
    total += _add("Head Aisle → Stacking Area (fwd, loaded)", dist.head_aisle_to_stacking_m, fwd, "forward / loaded")
    # Navigate to column C (lateral travel, forward, loaded)
    col_dist_m = stacking.column_distance_m(col)
    total += _add(f"Navigate to column {col} (fwd, loaded)", col_dist_m, fwd, "forward / loaded")
    # Navigate to row R (depth travel, forward, loaded)
    row_dist_m = stacking.row_distance_m(row)
    total += _add(f"Navigate to row {row} (fwd, loaded)", row_dist_m, fwd, "forward / loaded")
    # Reverse into stacking position
    rev_dist_m = stacking.effective_box_depth_mm / 2 / 1000.0
    total += _add(f"Reverse to position R{row}C{col} (rev, loaded)", rev_dist_m, rev,
                  "reverse into position / loaded")
    # Lift to level height
    height_m = stacking.level_height_m(level)
    lift_time = height_m / lift if height_m > 0 else 0.0
    if lift_time > 0:
        total += _add_fixed(f"LIFT to level {level} ({height_m:.2f}m)", lift_time,
                            f"lift {height_m:.2f} m @ {lift} m/s")
    # Dropoff
    total += _add_fixed("DROPOFF", agv.dropoff_time_s, "dropoff operation")
    # Lower forks
    if lift_time > 0:
        total += _add_fixed(f"LOWER forks from level {level}", lift_time, "lower forks")
    # Drive forward away from position
    total += _add(f"Drive away from position (fwd, empty)", rev_dist_m, fwd, "forward / empty")
    # Stacking area exit → Head Aisle (forward, empty): reverse path
    total += _add("Stacking Area → Head Aisle (fwd, empty)", dist.head_aisle_to_stacking_m, fwd, "forward / empty")
    # Head Aisle → Rest approach (forward, empty)
    total += _add("Head Aisle → Rest (fwd, empty)", dist.rest_to_head_aisle_m, fwd, "forward / empty")
    # Reverse into rest area
    total += _add("Reverse into Rest (rev, empty)", REVERSE_ENTRY_DIST_M, rev, "reverse 1.5 m / empty")

    return CycleResult(total_time_s=total, phases=phases)


def xqe122_stacking_average_cycle(
    agv: XQE122Specs,
    turns: TurnSpecs,
    dist: WarehouseDistances,
    stacking: GroundStackingConfig,
) -> CycleResult:
    """Return the average cycle time across all stacking positions."""
    total_time = 0.0
    count = 0
    for (row, col, level) in stacking.all_positions():
        result = xqe122_stacking_cycle(agv, turns, dist, stacking, row, col, level)
        total_time += result.total_time_s
        count += 1
    if count == 0:
        return CycleResult(0.0)
    avg = total_time / count
    # Use a representative position for phase detail
    mid_row = max(1, stacking.num_rows // 2)
    mid_col = max(1, stacking.num_columns // 2)
    mid_level = max(1, stacking.num_levels // 2)
    result = xqe122_stacking_cycle(agv, turns, dist, stacking, mid_row, mid_col, mid_level)
    result.total_time_s = avg
    return result
