"""
Warehouse Layout Module (mm-based configuration)
"""
import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional

MM_PER_METRE = 1000.0

@dataclass
class AisleConfig:
    name: str
    aisle_type: str        # "rack", "ground_stacking", "handover"
    width_mm: float        # aisle width in mm
    depth_mm: float        # aisle depth in mm
    num_positions: int = 0
    shelf_heights_mm: List[float] = field(default_factory=list)  # for rack aisles
    stacking_levels: int = 1  # for ground stacking

    @property
    def width_m(self) -> float:
        return self.width_mm / MM_PER_METRE

    @property
    def depth_m(self) -> float:
        return self.depth_mm / MM_PER_METRE

@dataclass
class WarehouseConfig:
    name: str
    width_mm: float
    length_mm: float
    head_aisle_width_mm: float
    inbound_dock_count: int
    outbound_dock_count: int
    aisles: List[AisleConfig] = field(default_factory=list)
    throughput_pallets_per_day: int = 500
    operating_hours: float = 16.0
    utilization_target: float = 0.80

    @property
    def throughput_per_hour(self) -> float:
        return self.throughput_pallets_per_day / self.operating_hours

    @property
    def head_aisle_width_m(self) -> float:
        return self.head_aisle_width_mm / MM_PER_METRE

    @property
    def width_m(self) -> float:
        return self.width_mm / MM_PER_METRE

    @property
    def length_m(self) -> float:
        return self.length_mm / MM_PER_METRE


def load_config(path: str) -> WarehouseConfig:
    """Load a mm-based warehouse config from JSON."""
    with open(path, 'r') as f:
        data = json.load(f)
    return parse_config(data)


def parse_config(data: dict) -> WarehouseConfig:
    """Parse a warehouse config dict."""
    wh = data.get("warehouse", data)
    aisles_data = data.get("aisles", [])
    aisles = []
    for a in aisles_data:
        if "width_mm" in a:
            width_mm = float(a["width_mm"])
        elif "width" in a:
            width_mm = float(a["width"]) * MM_PER_METRE
        else:
            width_mm = 2840.0

        aisle = AisleConfig(
            name=a["name"],
            aisle_type=a.get("type", a.get("aisle_type", "rack")),
            width_mm=width_mm,
            depth_mm=float(a.get("depth_mm", a.get("depth", 15000))),
            num_positions=int(a.get("num_positions", 0)),
            shelf_heights_mm=list(a.get("shelf_heights_mm", [])),
            stacking_levels=int(a.get("stacking_levels", 1)),
        )
        aisles.append(aisle)

    throughput_data = data.get("throughput", {})

    if isinstance(wh, dict):
        name = wh.get("name", data.get("name", "Warehouse"))
        width_mm = float(wh.get("width_mm", data.get("width_mm", 20000)))
        length_mm = float(wh.get("length_mm", data.get("length_mm", 30000)))
        head_aisle_width_mm = float(wh.get("head_aisle_width_mm", data.get("head_aisle_width_mm", 4000)))
        inbound_dock_count = int(wh.get("inbound_docks", data.get("inbound_docks", 2)))
        outbound_dock_count = int(wh.get("outbound_docks", data.get("outbound_docks", 2)))
    else:
        name = data.get("name", "Warehouse")
        width_mm = float(data.get("width_mm", 20000))
        length_mm = float(data.get("length_mm", 30000))
        head_aisle_width_mm = float(data.get("head_aisle_width_mm", 4000))
        inbound_dock_count = int(data.get("inbound_docks", 2))
        outbound_dock_count = int(data.get("outbound_docks", 2))

    return WarehouseConfig(
        name=name,
        width_mm=width_mm,
        length_mm=length_mm,
        head_aisle_width_mm=head_aisle_width_mm,
        inbound_dock_count=inbound_dock_count,
        outbound_dock_count=outbound_dock_count,
        aisles=aisles,
        throughput_pallets_per_day=int(throughput_data.get("pallets_per_day", data.get("throughput_pallets_per_day", 500))),
        operating_hours=float(throughput_data.get("operating_hours", data.get("operating_hours", 16.0))),
        utilization_target=float(data.get("utilization_target", 0.80)),
    )
