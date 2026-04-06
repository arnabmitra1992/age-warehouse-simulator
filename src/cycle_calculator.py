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


# ---------------------------------------------------------------------------
# Workflow 4: XQE_122 Inbound (Production → Ground Stacking)
# ---------------------------------------------------------------------------

def xqe122_inbound_cycle(
    agv: XQE122Specs,
    turns: TurnSpecs,
    dist: WarehouseDistances,
    stacking: GroundStackingConfig,
    row: int,
    col: int,
    level: int,
) -> CycleResult:
    """
    Calculate XQE_122 inbound cycle time for a specific storage position.

    Movement:
      Rest → Production Conveyor (FORWARD, EMPTY, Rest_to_Production)
        ↓ PICKUP (30s)
        ↓ Turn 90° (10s)
      Production → Storage Entry (FORWARD, LOADED, Production_to_Storage_Entry)
        ↓
      Storage Entry → Target Column (FORWARD, LOADED, col_dist)
        ↓
      Target Column → Target Row (REVERSE, LOADED, row_dist)
        ↓ DROPOFF (30s)
      Return to Rest (FORWARD, EMPTY – full reverse path as forward motion)
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

    # --- Inbound leg (to storage) ---
    total += _add("Rest → Production (fwd, empty)",
                  dist.rest_to_production_m, fwd, "forward / empty")
    total += _add_fixed("PICKUP", agv.pickup_time_s, "pickup from production conveyor")
    total += _add_fixed("Turn 90°", turns.turn_90_degrees_s, "turn to face storage")
    total += _add("Production → Storage Entry (fwd, loaded)",
                  dist.production_to_storage_entry_m, fwd, "forward / loaded")

    col_dist_m = stacking.column_distance_m(col)
    total += _add(f"Storage Entry → Column {col} (fwd, loaded)",
                  col_dist_m, fwd, "forward / loaded")

    row_dist_m = stacking.row_distance_m(row)
    total += _add(f"Column → Row {row} (rev, loaded)",
                  row_dist_m, rev, "reverse into row / loaded")

    # Lift and dropoff
    height_m = stacking.level_height_m(level)
    lift_time = height_m / lift if height_m > 0 else 0.0
    if lift_time > 0:
        total += _add_fixed(f"LIFT to level {level} ({height_m:.2f}m)", lift_time,
                            f"lift {height_m:.2f} m @ {lift} m/s")
    total += _add_fixed("DROPOFF", agv.dropoff_time_s, "dropoff in storage")
    if lift_time > 0:
        total += _add_fixed(f"LOWER forks from level {level}", lift_time, "lower forks")

    # --- Return leg (all FORWARD, EMPTY) ---
    total += _add(f"Row {row} → Column (fwd, empty)", row_dist_m, fwd, "forward / empty")
    total += _add(f"Column → Storage Entry (fwd, empty)", col_dist_m, fwd, "forward / empty")
    total += _add("Storage Entry → Production (fwd, empty)",
                  dist.production_to_storage_entry_m, fwd, "forward / empty")
    total += _add("Production → Rest (fwd, empty)",
                  dist.rest_to_production_m, fwd, "forward / empty")

    return CycleResult(total_time_s=total, phases=phases)


def xqe122_inbound_average_cycle(
    agv: XQE122Specs,
    turns: TurnSpecs,
    dist: WarehouseDistances,
    stacking: GroundStackingConfig,
) -> CycleResult:
    """Return the average inbound cycle time across all storage positions."""
    total_time = 0.0
    count = 0
    for (row, col, level) in stacking.all_positions():
        result = xqe122_inbound_cycle(agv, turns, dist, stacking, row, col, level)
        total_time += result.total_time_s
        count += 1
    if count == 0:
        return CycleResult(0.0)
    avg = total_time / count
    mid_row = max(1, stacking.num_rows // 2)
    mid_col = max(1, stacking.num_columns // 2)
    mid_level = max(1, stacking.num_levels // 2)
    result = xqe122_inbound_cycle(agv, turns, dist, stacking, mid_row, mid_col, mid_level)
    result.total_time_s = avg
    return result


# ---------------------------------------------------------------------------
# Workflow 5: XQE_122 Outbound (Ground Stacking → Outbound Dock)
# ---------------------------------------------------------------------------

def xqe122_outbound_cycle(
    agv: XQE122Specs,
    turns: TurnSpecs,
    dist: WarehouseDistances,
    stacking: GroundStackingConfig,
    src_row: int,
    src_col: int,
    src_level: int,
    dst_row: int,
    dst_col: int,
    dst_level: int,
) -> CycleResult:
    """
    Calculate XQE_122 outbound cycle time.

    The AGV retrieves a pallet from the INBOUND storage (src position) and
    delivers it to the OUTBOUND stacking area (dst position).

    Movement:
      Rest → Storage Entry (FORWARD, EMPTY, rest_to_storage_entry)
        ↓
      Storage Entry → Source Column (FORWARD, EMPTY, src_col_dist)
        ↓
      Source Column → Source Row (REVERSE, EMPTY, src_row_dist – back rows)
        ↓ PICKUP (30s)
      Source Row → Source Column (FORWARD, LOADED, src_row_dist)
        ↓
      Source Column → Outbound Entry (FORWARD, LOADED, storage_exit_to_outbound_entry)
        ↓
      Outbound Entry → Dest Column (FORWARD, LOADED, dst_col_dist – similar to inbound)
        ↓
      Dest Column → Dest Row (REVERSE, LOADED, dst_row_dist – similar to inbound)
        ↓ DROPOFF (30s)
      Return to Rest (FORWARD, EMPTY – full reverse path as forward motion)
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

    # --- Empty travel to inbound storage for pickup ---
    total += _add("Rest → Storage Entry (fwd, empty)",
                  dist.rest_to_storage_entry_m, fwd, "forward / empty")

    src_col_dist_m = stacking.column_distance_m(src_col)
    total += _add(f"Storage Entry → Column {src_col} (fwd, empty)",
                  src_col_dist_m, fwd, "forward / empty")

    src_row_dist_m = stacking.row_distance_m(src_row)
    total += _add(f"Column → Row {src_row} (rev, empty – back rows)",
                  src_row_dist_m, rev, "reverse to back row / empty")

    # Lift for pickup (if upper level)
    src_height_m = stacking.level_height_m(src_level)
    src_lift_time = src_height_m / lift if src_height_m > 0 else 0.0
    if src_lift_time > 0:
        total += _add_fixed(f"LIFT to level {src_level} ({src_height_m:.2f}m)",
                            src_lift_time, f"lift {src_height_m:.2f} m @ {lift} m/s")
    total += _add_fixed("PICKUP", agv.pickup_time_s, "pickup from inbound storage")
    if src_lift_time > 0:
        total += _add_fixed(f"LOWER forks from level {src_level}", src_lift_time,
                            "lower forks after pickup")

    # --- Loaded travel: storage exit → outbound entry ---
    total += _add(f"Row {src_row} → Column (fwd, loaded)",
                  src_row_dist_m, fwd, "forward / loaded")
    total += _add(f"Column → Storage Exit (fwd, loaded)",
                  src_col_dist_m, fwd, "forward / loaded")
    total += _add("Storage Exit → Outbound Entry (fwd, loaded)",
                  dist.storage_exit_to_outbound_entry_m, fwd, "forward / loaded")

    # --- Outbound dropoff (similar to inbound storage) ---
    dst_col_dist_m = stacking.column_distance_m(dst_col)
    total += _add(f"Outbound Entry → Column {dst_col} (fwd, loaded)",
                  dst_col_dist_m, fwd, "forward / loaded")

    dst_row_dist_m = stacking.row_distance_m(dst_row)
    total += _add(f"Column → Row {dst_row} (rev, loaded)",
                  dst_row_dist_m, rev, "reverse into row / loaded")

    dst_height_m = stacking.level_height_m(dst_level)
    dst_lift_time = dst_height_m / lift if dst_height_m > 0 else 0.0
    if dst_lift_time > 0:
        total += _add_fixed(f"LIFT to level {dst_level} ({dst_height_m:.2f}m)",
                            dst_lift_time, f"lift {dst_height_m:.2f} m @ {lift} m/s")
    total += _add_fixed("DROPOFF", agv.dropoff_time_s, "dropoff at outbound stacking")
    if dst_lift_time > 0:
        total += _add_fixed(f"LOWER forks from level {dst_level}", dst_lift_time,
                            "lower forks after dropoff")

    # --- Return to Rest (FORWARD, EMPTY) ---
    total += _add(f"Row {dst_row} → Column (fwd, empty)", dst_row_dist_m, fwd,
                  "forward / empty")
    total += _add(f"Column → Outbound Entry (fwd, empty)", dst_col_dist_m, fwd,
                  "forward / empty")
    total += _add("Outbound Entry → Rest (fwd, empty)",
                  dist.outbound_exit_to_rest_m, fwd, "forward / empty")

    return CycleResult(total_time_s=total, phases=phases)


def xqe122_outbound_average_cycle(
    agv: XQE122Specs,
    turns: TurnSpecs,
    dist: WarehouseDistances,
    stacking: GroundStackingConfig,
) -> CycleResult:
    """
    Return the average outbound cycle time across all position pairs.

    The source position iterates through all storage slots (back rows first for
    FIFO) and the destination iterates through all outbound slots.  To keep the
    computation tractable, the average is computed over representative mid-range
    positions for both source and destination, weighted by the full position set.
    """
    total_time = 0.0
    count = 0
    for (src_row, src_col, src_level) in stacking.all_positions():
        for (dst_row, dst_col, dst_level) in stacking.all_positions():
            result = xqe122_outbound_cycle(
                agv, turns, dist, stacking,
                src_row, src_col, src_level,
                dst_row, dst_col, dst_level,
            )
            total_time += result.total_time_s
            count += 1
    if count == 0:
        return CycleResult(0.0)
    avg = total_time / count
    mid_row = max(1, stacking.num_rows // 2)
    mid_col = max(1, stacking.num_columns // 2)
    mid_level = max(1, stacking.num_levels // 2)
    result = xqe122_outbound_cycle(
        agv, turns, dist, stacking,
        mid_row, mid_col, mid_level,
        mid_row, mid_col, mid_level,
    )
    result.total_time_s = avg
    return result


# ---------------------------------------------------------------------------
# Workflow 6: XQE_122 Shuffling / Rehandling
# ---------------------------------------------------------------------------

def xqe122_shuffling_cycle(
    agv: XQE122Specs,
    dist: WarehouseDistances,
    stacking: GroundStackingConfig,
    blocking_row: int,
    target_row: int,
    col: int,
    level: int,
) -> CycleResult:
    """
    Calculate the cycle time for one shuffling operation.

    When retrieving from ``target_row`` (back), pallets in earlier rows
    (row < target_row) in the same column/level may block access.  This
    function calculates the time to move ONE blocking pallet at ``blocking_row``
    to the nearest empty slot in front of it (a lower-numbered row).

    The AGV is assumed to be at the storage entry when the shuffle starts and
    returns to the storage entry after the shuffle.

    Movement:
      Storage Entry → Blocking Column (FORWARD, EMPTY, col_dist)
        ↓
      Column → Blocking Row (REVERSE, EMPTY, blocking_row_dist)
        ↓ PICKUP (30s)
      Blocking Row → Empty Row (FORWARD, LOADED – one row depth approx.)
        ↓ DROPOFF (30s)
      Return to Storage Entry (FORWARD, EMPTY)
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

    col_dist_m = stacking.column_distance_m(col)
    blocking_row_dist_m = stacking.row_distance_m(blocking_row)
    # Move pallet forward by one slot (effective depth of one row)
    one_slot_m = stacking.effective_box_depth_mm / 1000.0

    height_m = stacking.level_height_m(level)
    lift_time = height_m / lift if height_m > 0 else 0.0

    # Navigate to blocking pallet (empty)
    total += _add(f"Storage Entry → Column {col} (fwd, empty)",
                  col_dist_m, fwd, "forward / empty")
    total += _add(f"Column → Blocking Row {blocking_row} (rev, empty)",
                  blocking_row_dist_m, rev, "reverse to blocking pallet / empty")
    if lift_time > 0:
        total += _add_fixed(f"LIFT to level {level}", lift_time, "lift for pickup")
    total += _add_fixed("PICKUP (blocking pallet)", agv.pickup_time_s, "pickup blocking pallet")
    if lift_time > 0:
        total += _add_fixed(f"LOWER forks from level {level}", lift_time, "lower after pickup")

    # Move forward to empty slot (approx one row depth)
    total += _add("Move to empty slot (fwd, loaded)", one_slot_m, fwd,
                  "forward to empty slot / loaded")
    if lift_time > 0:
        total += _add_fixed(f"LIFT to level {level}", lift_time, "lift for dropoff")
    total += _add_fixed("DROPOFF (to empty slot)", agv.dropoff_time_s, "dropoff at empty slot")
    if lift_time > 0:
        total += _add_fixed(f"LOWER forks from level {level}", lift_time, "lower after dropoff")

    # Return to storage entry (FORWARD, EMPTY)
    # Approx: travel back through blocking row dist + col dist
    empty_row_dist_m = max(0.0, blocking_row_dist_m - one_slot_m)
    total += _add("Return from empty slot to entry (fwd, empty)",
                  empty_row_dist_m + col_dist_m, fwd, "forward / empty")

    return CycleResult(total_time_s=total, phases=phases)


def xqe122_shuffling_average_cycle(
    agv: XQE122Specs,
    dist: WarehouseDistances,
    stacking: GroundStackingConfig,
) -> CycleResult:
    """
    Return the average shuffling cycle time, computed across all possible
    (blocking_row, col, level) combinations, using the mid-row as the target.
    """
    if stacking.num_rows < 2:
        return CycleResult(0.0)
    total_time = 0.0
    count = 0
    target_row = stacking.num_rows  # retrieve from the back (oldest)
    for blocking_row in range(1, target_row):
        for col in range(1, stacking.num_columns + 1):
            for level in range(1, stacking.num_levels + 1):
                result = xqe122_shuffling_cycle(
                    agv, dist, stacking, blocking_row, target_row, col, level
                )
                total_time += result.total_time_s
                count += 1
    if count == 0:
        return CycleResult(0.0)
    avg = total_time / count
    mid_blocking = max(1, stacking.num_rows // 2)
    mid_col = max(1, stacking.num_columns // 2)
    mid_level = max(1, stacking.num_levels // 2)
    result = xqe122_shuffling_cycle(
        agv, dist, stacking, mid_blocking, target_row, mid_col, mid_level
    )
    result.total_time_s = avg
    return result
