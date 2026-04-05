"""
AGV Specifications Module
==========================
Hardcoded specifications for EP Equipment AGV models used in warehouse operations.

Key physics note:
  - Fork is BACKWARD-FACING on all models.
  - When the fork is engaged (loaded travel), the AGV moves in REVERSE.
  - Empty travel uses FORWARD speed (faster).
  - Loaded travel uses REVERSE speed (slower).
"""

from typing import Optional, List


AGV_SPECS: dict = {
    "XQE_122": {
        "name": "XQE_122",
        "forward_speed": 1.0,       # m/s - empty travel
        "reverse_speed": 0.3,       # m/s - loaded travel (fork engaged)
        "lifting_speed": 0.2,       # m/s - mast lifting/lowering
        "capacity": 1200,           # kg
        "aisle_width": 2.84,        # m - minimum aisle width required
        "turn_space": 3.1,          # m - space required to complete a turn
        "turn_radius": None,        # m - not specified
        "max_lift_height": 4.5,     # m
        "storage_types": ["rack", "ground_storage"],
        "description": "Reach truck – mid-height rack storage and ground level",
    },
    "XPL_201": {
        "name": "XPL_201",
        "forward_speed": 1.5,       # m/s - empty travel
        "reverse_speed": 0.3,       # m/s - loaded travel (fork engaged)
        "lifting_speed": None,      # Not applicable – only 20 cm lift
        "capacity": 2000,           # kg
        "aisle_width": 2.6,         # m
        "turn_space": 3.1,          # m
        "turn_radius": None,        # m
        "max_lift_height": 0.20,    # m (20 cm – ground level only)
        "storage_types": ["ground_storage", "ground_stacking"],
        "description": "Pallet truck – heavy ground-level storage and stacking",
    },
    "XNA_121": {
        "name": "XNA_121",
        "forward_speed": 1.0,       # m/s
        "reverse_speed": 1.0,       # m/s (same speed in both directions)
        "lifting_speed": 0.2,       # m/s
        "capacity": 1200,           # kg
        "aisle_width": 1.77,        # m – very narrow aisle
        "turn_space": 1.9,          # m
        "turn_radius": 4.0,         # m – minimum turning radius
        "max_lift_height": 8.5,     # m
        "storage_types": ["rack"],
        "description": "Narrow-aisle reach truck – high rack storage up to 8.5 m",
    },
    "XNA_151": {
        "name": "XNA_151",
        "forward_speed": 1.0,       # m/s
        "reverse_speed": 1.0,       # m/s
        "lifting_speed": 0.2,       # m/s
        "capacity": 1500,           # kg
        "aisle_width": 1.77,        # m
        "turn_space": 1.9,          # m
        "turn_radius": 4.0,         # m
        "max_lift_height": 13.0,    # m
        "storage_types": ["rack"],
        "description": "Narrow-aisle reach truck – very high rack storage up to 13 m (1500 kg)",
    },
}

TASK_PARAMETERS: dict = {
    "pickup_time": 30,              # seconds – time to engage fork / pick pallet
    "dropoff_time": 30,             # seconds – time to disengage fork / place pallet
    "turn_time_per_90deg": 10,      # seconds – time to execute one 90° turn
    "dock_positioning_time": 10,    # seconds – reversing into dock position
    "target_utilization": 0.80,     # 80% – target AGV utilization for fleet sizing
}


def get_agv_spec(agv_type: str) -> dict:
    """Return specification dict for a given AGV type name."""
    if agv_type not in AGV_SPECS:
        raise ValueError(
            f"Unknown AGV type '{agv_type}'. "
            f"Available types: {list(AGV_SPECS.keys())}"
        )
    return AGV_SPECS[agv_type]


def get_compatible_agv_types(storage_type: str) -> List[str]:
    """Return list of AGV types that can handle the given storage type."""
    return [
        name
        for name, spec in AGV_SPECS.items()
        if storage_type in spec["storage_types"]
    ]


def validate_aisle_width(agv_type: str, aisle_width: float) -> bool:
    """Return True if the AGV fits in the given aisle width."""
    spec = get_agv_spec(agv_type)
    return aisle_width >= spec["aisle_width"]


def validate_lift_height(agv_type: str, required_height: float) -> bool:
    """Return True if the AGV can reach the required lift height."""
    spec = get_agv_spec(agv_type)
    return spec["max_lift_height"] >= required_height


# Aisle width threshold below which narrow-aisle (XNA) models are used exclusively.
NARROW_AISLE_THRESHOLD_M: float = 2.5


def get_compatible_agvs_for_aisle(
    aisle_width: float,
    storage_type: str,
    required_lift_height: Optional[float] = None,
) -> List[str]:
    """
    Return sorted list of AGV types compatible with an aisle's constraints.

    XNA models (XNA_121, XNA_151) are ONLY recommended for narrow aisles
    where aisle_width < 2.5 m.  Standard aisles (>= 2.5 m) use XQE_122
    and XPL_201 only.

    Parameters
    ----------
    aisle_width : float
        Available aisle width in metres.
    storage_type : str
        One of 'rack', 'ground_storage', 'ground_stacking'.
    required_lift_height : float, optional
        Required lift height in metres (for rack storage).
    """
    is_narrow = aisle_width < NARROW_AISLE_THRESHOLD_M
    compatible = []
    for name, spec in AGV_SPECS.items():
        if storage_type not in spec["storage_types"]:
            continue
        if aisle_width < spec["aisle_width"]:
            continue
        if required_lift_height is not None:
            if spec["max_lift_height"] < required_lift_height:
                continue
        # XNA models are only appropriate for narrow aisles (< 2.5 m).
        is_xna = name.startswith("XNA")
        if is_xna and not is_narrow:
            continue
        # Standard AGVs (XQE, XPL) are not recommended for narrow aisles.
        if not is_xna and is_narrow:
            continue
        compatible.append(name)
    return compatible


def print_agv_summary() -> None:
    """Print a formatted summary table of all AGV specifications."""
    print("\n" + "=" * 78)
    print(f"{'AGV MODEL':<12} {'FWD':>6} {'REV':>6} {'LIFT':>6} {'CAP':>7} "
          f"{'AISLE':>7} {'MAX H':>7} {'STORAGE TYPES'}")
    print(f"{'':12} {'(m/s)':>6} {'(m/s)':>6} {'(m/s)':>6} {'(kg)':>7} "
          f"{'(m)':>7} {'(m)':>7}")
    print("-" * 78)
    for name, s in AGV_SPECS.items():
        fwd = f"{s['forward_speed']:.1f}"
        rev = f"{s['reverse_speed']:.1f}"
        lst = f"{s['lifting_speed']:.1f}" if s["lifting_speed"] else "N/A"
        cap = str(s["capacity"])
        aw = f"{s['aisle_width']:.2f}"
        mh = f"{s['max_lift_height']:.1f}"
        st = ", ".join(s["storage_types"])
        print(f"{name:<12} {fwd:>6} {rev:>6} {lst:>6} {cap:>7} {aw:>7} {mh:>7}  {st}")
    print("=" * 78 + "\n")
