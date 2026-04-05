"""
Warehouse layout: distance and dimension management.
All distances stored in millimetres, converted to metres for calculations.
"""
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class WarehouseDistances:
    """All key distances in the warehouse (mm)."""
    rest_to_inbound_mm: float = 5000
    rest_to_head_aisle_mm: float = 3000
    head_aisle_to_handover_mm: float = 8000
    head_aisle_to_rack_aisle_mm: float = 6000
    rack_aisle_length_mm: float = 20000
    head_aisle_to_stacking_mm: float = 10000
    inbound_depth_mm: float = 2000        # depth of inbound buffer position

    # Derived / convenience
    @property
    def rest_to_inbound_m(self) -> float:
        return self.rest_to_inbound_mm / 1000.0

    @property
    def rest_to_head_aisle_m(self) -> float:
        return self.rest_to_head_aisle_mm / 1000.0

    @property
    def head_aisle_to_handover_m(self) -> float:
        return self.head_aisle_to_handover_mm / 1000.0

    @property
    def head_aisle_to_rack_aisle_m(self) -> float:
        return self.head_aisle_to_rack_aisle_mm / 1000.0

    @property
    def rack_aisle_length_m(self) -> float:
        return self.rack_aisle_length_mm / 1000.0

    @property
    def head_aisle_to_stacking_m(self) -> float:
        return self.head_aisle_to_stacking_mm / 1000.0

    @property
    def inbound_depth_m(self) -> float:
        return self.inbound_depth_mm / 1000.0


def distances_from_dict(d: dict) -> WarehouseDistances:
    """Create WarehouseDistances from a configuration dictionary (values in mm)."""
    return WarehouseDistances(
        rest_to_inbound_mm=d.get("Rest_to_Inbound", 5000),
        rest_to_head_aisle_mm=d.get("Rest_to_Head_Aisle", 3000),
        head_aisle_to_handover_mm=d.get("Head_Aisle_to_Handover", 8000),
        head_aisle_to_rack_aisle_mm=d.get("Head_Aisle_to_Rack_Aisle", 6000),
        rack_aisle_length_mm=d.get("Rack_Aisle_Length", 20000),
        head_aisle_to_stacking_mm=d.get("Head_Aisle_to_Stacking", 10000),
        inbound_depth_mm=d.get("Inbound_Depth_mm", 2000),
    )
