"""
AGV Specifications for XQE_122, XPL_201, and XNA vehicles.
"""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class XQE122Specs:
    """XQE_122 Racking Robot specifications."""
    forward_speed_ms: float = 1.0       # m/s
    reverse_speed_ms: float = 0.3       # m/s
    lift_speed_ms: float = 0.2          # m/s
    max_lift_height_mm: float = 4500    # mm
    pickup_time_s: float = 30           # seconds
    dropoff_time_s: float = 30          # seconds
    fork_type: str = "backward"         # reverse entry
    name: str = "XQE_122"

    @property
    def max_lift_height_m(self) -> float:
        return self.max_lift_height_mm / 1000.0


@dataclass
class XPL201Specs:
    """XPL_201 Handover Robot specifications."""
    forward_speed_ms: float = 1.5       # m/s
    reverse_speed_ms: float = 0.5       # m/s
    pickup_time_s: float = 30           # seconds
    dropoff_time_s: float = 30          # seconds
    name: str = "XPL_201"


@dataclass
class XNASpecs:
    """XNA Narrow-Aisle Robot specifications (XNA_121, XNA_151)."""
    forward_speed_ms: float = 1.0       # m/s
    reverse_speed_ms: float = 1.0       # m/s (same both directions)
    lift_speed_ms: float = 0.2          # m/s
    max_lift_height_mm: float = 8500    # mm (XNA_121 = 8.5m, XNA_151 = 13m)
    pickup_time_s: float = 30           # seconds
    dropoff_time_s: float = 30          # seconds
    min_aisle_width_mm: float = 1717    # mm (1.717m minimum)
    max_aisle_width_mm: float = 2500    # mm (2.5m maximum)
    fork_type: str = "backward"         # reverse entry
    name: str = "XNA"

    @property
    def max_lift_height_m(self) -> float:
        return self.max_lift_height_mm / 1000.0


@dataclass
class TurnSpecs:
    """Shared turn operation specifications."""
    turn_90_degrees_s: float = 10       # seconds per 90° turn


# Default instances
DEFAULT_XQE122 = XQE122Specs()
DEFAULT_XPL201 = XPL201Specs()
DEFAULT_XNA = XNASpecs()
DEFAULT_TURNS = TurnSpecs()


# AGV_SPECS dictionary for compatibility with fleet sizing logic
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
        "reverse_speed": 0.5,       # m/s - loaded travel (fork engaged)
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


def xqe122_from_dict(d: dict) -> XQE122Specs:
    """Create XQE122Specs from a configuration dictionary."""
    return XQE122Specs(
        forward_speed_ms=d.get("forward_speed_ms", 1.0),
        reverse_speed_ms=d.get("reverse_speed_ms", 0.3),
        lift_speed_ms=d.get("lift_speed_ms", 0.2),
        max_lift_height_mm=d.get("max_lift_height_mm", 4500),
        pickup_time_s=d.get("pickup_time_s", 30),
        dropoff_time_s=d.get("dropoff_time_s", 30),
    )


def xpl201_from_dict(d: dict) -> XPL201Specs:
    """Create XPL201Specs from a configuration dictionary."""
    return XPL201Specs(
        forward_speed_ms=d.get("forward_speed_ms", 1.5),
        reverse_speed_ms=d.get("reverse_speed_ms", 0.5),
        pickup_time_s=d.get("pickup_time_s", 30),
        dropoff_time_s=d.get("dropoff_time_s", 30),
    )


def xna_from_dict(d: dict) -> XNASpecs:
    """Create XNASpecs from a configuration dictionary."""
    return XNASpecs(
        forward_speed_ms=d.get("forward_speed_ms", 1.0),
        reverse_speed_ms=d.get("reverse_speed_ms", 1.0),
        lift_speed_ms=d.get("lift_speed_ms", 0.2),
        max_lift_height_mm=d.get("max_lift_height_mm", 8500),
        min_aisle_width_mm=d.get("min_aisle_width_mm", 1717),
        max_aisle_width_mm=d.get("max_aisle_width_mm", 2500),
        pickup_time_s=d.get("pickup_time_s", 30),
        dropoff_time_s=d.get("dropoff_time_s", 30),
    )


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


def get_compatible_agvs_for_aisle(
    aisle_width: float,
    storage_type: str,
    required_lift_height: Optional[float] = None,
) -> List[str]:
    """
    Return sorted list of AGV types compatible with an aisle's constraints.

    Parameters
    ----------
    aisle_width : float
        Available aisle width in metres.
    storage_type : str
        One of 'rack', 'ground_storage', 'ground_stacking'.
    required_lift_height : float, optional
        Required lift height in metres (for rack storage).
    """
    compatible = []
    for name, spec in AGV_SPECS.items():
        if storage_type not in spec["storage_types"]:
            continue
        if aisle_width < spec["aisle_width"]:
            continue
        if required_lift_height is not None:
            if spec["max_lift_height"] < required_lift_height:
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