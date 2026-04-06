"""
Warehouse layout: distance and dimension management.
All distances stored in millimetres, converted to metres for calculations.
"""
from dataclasses import dataclass, field
from typing import Dict

# XQE_122 aisle width thresholds (mm)
XQE_MIN_AISLE_WIDTH_MM = 2840       # cannot operate below this width
XQE_BIDIRECTIONAL_WIDTH_MM = 3500   # two XQEs can pass simultaneously at or above this width


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

    # New fields for inbound/outbound workflow
    rest_to_production_mm: float = 5000       # Rest → Production Conveyor
    production_to_storage_entry_mm: float = 3000  # Production Conveyor → Storage Entry
    head_aisle_to_outbound_mm: float = 10000  # Head Aisle → Outbound Stacking Entry

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

    @property
    def rest_to_production_m(self) -> float:
        return self.rest_to_production_mm / 1000.0

    @property
    def production_to_storage_entry_m(self) -> float:
        return self.production_to_storage_entry_mm / 1000.0

    @property
    def head_aisle_to_outbound_m(self) -> float:
        return self.head_aisle_to_outbound_mm / 1000.0

    @property
    def rest_to_storage_entry_m(self) -> float:
        """Total distance from Rest to Storage Entry (via Production path, no stop)."""
        return (self.rest_to_production_mm + self.production_to_storage_entry_mm) / 1000.0

    @property
    def storage_exit_to_outbound_entry_m(self) -> float:
        """Distance from Storage Entry back through production path to head aisle and into outbound."""
        return (
            self.production_to_storage_entry_mm
            + self.rest_to_production_mm
            + self.rest_to_head_aisle_mm
            + self.head_aisle_to_outbound_mm
        ) / 1000.0

    @property
    def outbound_exit_to_rest_m(self) -> float:
        """Distance from Outbound Stacking Entry back to Rest (via Head Aisle)."""
        return (self.head_aisle_to_outbound_mm + self.rest_to_head_aisle_mm) / 1000.0


@dataclass
class AisleWidths:
    """Aisle widths for traffic control calculations (mm)."""
    inbound_access_width_mm: float = 3900
    head_aisle_width_mm: float = 3500
    outbound_access_width_mm: float = 3900

    def bidirectional_capacity(self, width_mm: float,
                                min_width: float = XQE_MIN_AISLE_WIDTH_MM,
                                bidi_width: float = XQE_BIDIRECTIONAL_WIDTH_MM) -> int:
        """Return how many XQEs can pass simultaneously in an aisle of this width."""
        if width_mm < min_width:
            return 0
        if width_mm < bidi_width:
            return 1
        return 2

    @property
    def inbound_capacity(self) -> int:
        return self.bidirectional_capacity(self.inbound_access_width_mm)

    @property
    def head_aisle_capacity(self) -> int:
        return self.bidirectional_capacity(self.head_aisle_width_mm)

    @property
    def outbound_capacity(self) -> int:
        return self.bidirectional_capacity(self.outbound_access_width_mm)


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
        rest_to_production_mm=d.get("Rest_to_Production", 5000),
        production_to_storage_entry_mm=d.get("Production_to_Storage_Entry", 3000),
        head_aisle_to_outbound_mm=d.get("Head_Aisle_to_Outbound", 10000),
    )


def aisle_widths_from_dict(d: dict) -> AisleWidths:
    """Create AisleWidths from a configuration dictionary (values in mm)."""
    return AisleWidths(
        inbound_access_width_mm=d.get("Inbound_Access_Width_mm", 3900),
        head_aisle_width_mm=d.get("Head_Aisle_Width_mm", 3500),
        outbound_access_width_mm=d.get("Outbound_Access_Width_mm", 3900),
    )
