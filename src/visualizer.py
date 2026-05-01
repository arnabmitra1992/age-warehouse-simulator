"""
Text-based visualiser: workflow diagrams and results reporting.
"""
from typing import Optional

from .cycle_calculator import CycleResult
from .fleet_sizer import FleetSizeResult
from .rack_storage import RackConfig
from .ground_stacking import GroundStackingConfig


SEPARATOR = "=" * 70
SUB_SEP = "-" * 70


def _center(text: str, width: int = 70) -> str:
    return text.center(width)


# ---------------------------------------------------------------------------
# Workflow diagrams
# ---------------------------------------------------------------------------

def xpl201_workflow_diagram() -> str:
    return f"""
{SEPARATOR}
{_center('XPL_201 HANDOVER WORKFLOW')}
{SEPARATOR}

  Rest Area
    │ FORWARD, EMPTY
    ▼
  Head Aisle
    │ FORWARD, EMPTY
    ▼
  Inbound Buffer ◄── REVERSE, EMPTY (back in)
    │ PICKUP (30s)
    │ FORWARD, LOADED (drive out)
    ▼
  Head Aisle
    │ FORWARD, LOADED
    ▼
  TURN 90° ──► Handover Zone ◄── REVERSE, LOADED (back in)
    │ DROPOFF (30s)
    │ FORWARD, EMPTY (drive out)
    │ TURN 90°
    ▼
  Head Aisle
    │ FORWARD, EMPTY
    ▼
  Rest Area ◄── REVERSE, EMPTY (back in to park)

{SEPARATOR}
"""


def xqe122_rack_workflow_diagram() -> str:
    return f"""
{SEPARATOR}
{_center('XQE_122 RACK STORAGE WORKFLOW')}
{SEPARATOR}

  Rest Area
    │ FORWARD, EMPTY
    ▼
  Head Aisle
    │ FORWARD, EMPTY
    ▼
  Inbound Buffer ◄── REVERSE, EMPTY (back in)
    │ PICKUP (30s)
    │ FORWARD, LOADED (drive out)
    ▼
  Head Aisle
    │ FORWARD, LOADED
    ▼
  Rack Aisle Entry
    │ FORWARD, LOADED (travel to position N)
    ▼
  Position N Centre
    │ TURN 90° (toward rack)
    │ REVERSE 1.5m (back up to shelf)
    │ LIFT to shelf height
    │ DROPOFF (30s)
    │ LOWER forks
    │ FORWARD 1.5m (drive away)
    │ TURN 90° (back to aisle)
    ▼
  Rack Aisle Exit
    │ FORWARD, EMPTY
    ▼
  Head Aisle
    │ FORWARD, EMPTY
    ▼
  Rest Area ◄── REVERSE, EMPTY (back in)

{SEPARATOR}
"""


def xqe122_stacking_workflow_diagram() -> str:
    return f"""
{SEPARATOR}
{_center('XQE_122 GROUND STACKING WORKFLOW')}
{SEPARATOR}

  Rest Area
    │ FORWARD, EMPTY
    ▼
  Head Aisle
    │ FORWARD, EMPTY
    ▼
  Inbound Buffer ◄── REVERSE, EMPTY (back in)
    │ PICKUP (30s)
    │ FORWARD, LOADED (drive out)
    ▼
  Head Aisle
    │ FORWARD, LOADED
    ▼
  Stacking Area Entry
    │ FORWARD to Column C (lateral)
    │ FORWARD to Row R (depth)
    ▼
  Position (R, C, L)
    │ REVERSE (back into position)
    │ LIFT to Level L height
    │ DROPOFF (30s)
    │ LOWER forks
    │ FORWARD (drive away)
    ▼
  Stacking Area Exit
    │ FORWARD, EMPTY
    ▼
  Head Aisle
    │ FORWARD, EMPTY
    ▼
  Rest Area ◄── REVERSE, EMPTY (back in)

{SEPARATOR}
"""


def xqe122_inbound_workflow_diagram() -> str:
    return f"""
{SEPARATOR}
{_center('XQE_122 INBOUND WORKFLOW (Production → Ground Storage)')}
{SEPARATOR}

  Rest Area
    │ FORWARD, EMPTY  (Rest_to_Production)
    ▼
  Production Conveyor
    │ PICKUP (30s)
    │ TURN 90°
    │ FORWARD, LOADED  (Production_to_Storage_Entry)
    ▼
  Storage Entry
    │ FORWARD to Column C  (col_dist)
    │ REVERSE to Row R  (row_dist – loaded, into storage)
    │ LIFT to Level L
    │ DROPOFF (30s)
    │ LOWER forks
    ▼
  Return to Rest  (FORWARD, EMPTY – full reverse path)

{SEPARATOR}
"""


def xqe122_outbound_workflow_diagram() -> str:
    return f"""
{SEPARATOR}
{_center('XQE_122 OUTBOUND WORKFLOW (Ground Storage → Outbound Dock)')}
{SEPARATOR}

  Rest Area
    │ FORWARD, EMPTY  (rest_to_storage_entry)
    ▼
  Storage Entry
    │ FORWARD to Column C  (col_dist)
    │ REVERSE to Row R  (row_dist – FIFO back rows, empty)
    │ LIFT to Level L
    │ PICKUP (30s)
    │ LOWER forks
    ▼
  Storage Exit  (FORWARD, LOADED)
    │ storage_exit_to_outbound_entry
    ▼
  Outbound Dock Entry
    │ FORWARD to Column C  (col_dist – similar to inbound)
    │ REVERSE to Row R  (row_dist – loaded)
    │ LIFT to Level L
    │ DROPOFF (30s)
    │ LOWER forks
    ▼
  Return to Rest  (FORWARD, EMPTY – outbound_exit_to_rest)

{SEPARATOR}
"""


def xqe122_shuffling_workflow_diagram() -> str:
    return f"""
{SEPARATOR}
{_center('XQE_122 SHUFFLING / REHANDLING WORKFLOW')}
{SEPARATOR}

  [Outbound AGV detects blocking pallets in target column/row]
    │
    ▼
  Storage Entry
    │ FORWARD to Column C  (col_dist)
    │ REVERSE to Blocking Row  (blocking_row_dist – empty)
    │ PICKUP (30s)
    ▼
  Move FORWARD one slot to empty position  (LOADED)
    │ DROPOFF (30s)
    ▼
  Return to Storage Entry  (FORWARD, EMPTY)
    │
    ▼
  [Resume original outbound retrieval task]

{SEPARATOR}
"""


# ---------------------------------------------------------------------------
# Results reporting
# ---------------------------------------------------------------------------

def rack_capacity_report(rack: RackConfig) -> str:
    lines = [
        SEPARATOR,
        _center("RACK STORAGE CAPACITY"),
        SUB_SEP,
        f"  Rack length            : {rack.rack_length_mm:,.0f} mm",
        f"  Position spacing       : {rack.position_spacing_mm:,.0f} mm",
        f"  Positions per shelf    : {rack.positions_per_shelf}",
        f"  Shelf levels           : {rack.num_levels}",
        f"  Total rack positions   : {rack.total_positions}",
        SEPARATOR,
    ]
    return "\n".join(lines)


def stacking_capacity_report(cfg: GroundStackingConfig) -> str:
    lines = [
        SEPARATOR,
        _center("GROUND STACKING CAPACITY"),
        SUB_SEP,
        f"  Box dimensions         : {cfg.box.length_mm:.0f} × {cfg.box.width_mm:.0f} × {cfg.box.height_mm:.0f} mm",
        f"  Fork entry side        : {cfg.fork_entry_side}",
        f"  Effective slot width   : {cfg.effective_box_width_mm:.0f} mm",
        f"  Effective slot depth   : {cfg.effective_box_depth_mm:.0f} mm",
        f"  Storage area           : {cfg.area.length_mm:.0f} × {cfg.area.width_mm:.0f} mm",
        f"  Rows                   : {cfg.num_rows}",
        f"  Columns                : {cfg.num_columns}",
        f"  Levels                 : {cfg.num_levels}",
        f"  Total stacking positions: {cfg.total_positions}",
        SEPARATOR,
    ]
    return "\n".join(lines)


def cycle_time_report(title: str, result: CycleResult) -> str:
    lines = [
        SEPARATOR,
        _center(title),
        SUB_SEP,
        result.summary(),
        SEPARATOR,
    ]
    return "\n".join(lines)


def fleet_report(results: list) -> str:
    lines = [
        SEPARATOR,
        _center("FLEET SIZING RESULTS"),
        SUB_SEP,
    ]
    total_fleet = 0
    for r in results:
        lines.append(f"  {r.summary()}")
        total_fleet += r.fleet_size
    lines += [
        SUB_SEP,
        f"  TOTAL FLEET SIZE: {total_fleet} vehicles",
        SEPARATOR,
    ]
    return "\n".join(lines)


def outbound_performance_report(
    throughput_config,
    inbound_cycle: CycleResult,
    outbound_cycle: CycleResult,
    shuffling_cycle: Optional[CycleResult],
    inbound_fleet: "FleetSizeResult",
    outbound_fleet: "FleetSizeResult",
    shuffling_fleet: Optional["FleetSizeResult"],
    traffic_report: str = "",
    avg_shuffles_per_cycle: float = 0.0,
    block_storage_policy: str = "fifo",
) -> str:
    policy_label = {
        "lane_sequence": "Lane-Sequence (column drain, top-down, 0 shuffles)",
        "fifo": "FIFO (time-ordered, blocking/shuffling)",
    }.get(block_storage_policy, block_storage_policy)
    lines = [
        SEPARATOR,
        _center("INBOUND / OUTBOUND PERFORMANCE METRICS"),
        SUB_SEP,
        f"  Block storage policy   : {policy_label}",
        f"  Daily inbound pallets  : {throughput_config.effective_inbound_pallets}",
        f"  Daily outbound pallets : {throughput_config.effective_outbound_pallets}",
        f"  Operating hours/day    : {throughput_config.operating_hours}h",
        f"  Utilisation target     : {throughput_config.utilization_target * 100:.0f}%",
        SUB_SEP,
        f"  Inbound avg cycle time : {inbound_cycle.total_time_s:.1f}s "
        f"({inbound_cycle.total_time_min:.2f} min)",
        f"  Inbound throughput/h   : {3600 / inbound_cycle.total_time_s:.2f} pallets/h (per AGV)",
        f"  Inbound fleet required : {inbound_fleet.fleet_size} AGVs",
        SUB_SEP,
        f"  Outbound avg cycle     : {outbound_cycle.total_time_s:.1f}s "
        f"({outbound_cycle.total_time_min:.2f} min)",
        f"  Outbound throughput/h  : {3600 / outbound_cycle.total_time_s:.2f} pallets/h (per AGV)",
        f"  Outbound fleet required: {outbound_fleet.fleet_size} AGVs",
    ]
    if shuffling_cycle and shuffling_fleet:
        lines += [
            SUB_SEP,
            f"  Shuffling avg cycle    : {shuffling_cycle.total_time_s:.1f}s",
            f"  Avg shuffles/outbound  : {avg_shuffles_per_cycle:.2f}",
            f"  Shuffling fleet overhead: {shuffling_fleet.fleet_size} AGVs",
        ]
    total = (
        inbound_fleet.fleet_size
        + outbound_fleet.fleet_size
        + (shuffling_fleet.fleet_size if shuffling_fleet else 0)
    )
    lines += [
        SUB_SEP,
        f"  TOTAL FLEET (inbound + outbound + shuffling): {total} AGVs",
        SEPARATOR,
    ]
    if traffic_report:
        lines += ["", traffic_report]
    return "\n".join(lines)


def performance_report(
    throughput_config,
    xpl_cycle: CycleResult,
    xqe_rack_cycle: CycleResult,
    xqe_stack_cycle: CycleResult,
) -> str:
    lines = [
        SEPARATOR,
        _center("PERFORMANCE METRICS"),
        SUB_SEP,
        f"  Total daily pallets    : {throughput_config.total_daily_pallets}",
        f"  Operating hours/day    : {throughput_config.operating_hours}h",
        f"  Utilisation target     : {throughput_config.utilization_target * 100:.0f}%",
        SUB_SEP,
        f"  XPL_201 pallets/day    : {throughput_config.xpl201_daily_pallets:.0f}",
        f"  XPL_201 avg cycle time : {xpl_cycle.total_time_s:.1f}s",
        f"  XPL_201 throughput/h   : {3600 / xpl_cycle.total_time_s:.2f} pallets/h (per vehicle)",
        SUB_SEP,
        f"  XQE_122 rack pallets/d : {throughput_config.xqe_rack_daily_pallets:.0f}",
        f"  XQE_122 rack cycle     : {xqe_rack_cycle.total_time_s:.1f}s",
        f"  XQE_122 rack tput/h    : {3600 / xqe_rack_cycle.total_time_s:.2f} pallets/h (per vehicle)",
        SUB_SEP,
        f"  XQE_122 stack pallets/d: {throughput_config.xqe_stacking_daily_pallets:.0f}",
        f"  XQE_122 stack cycle    : {xqe_stack_cycle.total_time_s:.1f}s",
        f"  XQE_122 stack tput/h   : {3600 / xqe_stack_cycle.total_time_s:.2f} pallets/h (per vehicle)",
        SEPARATOR,
    ]
    return "\n".join(lines)
