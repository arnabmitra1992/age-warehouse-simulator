"""
Cycle Calculator Module
========================
Unified physics engine that orchestrates XPL_201 handover, XQE_122 rack
storage, and XQE_122 ground stacking cycle time calculations from a
WarehouseLayout configuration.

Public API:
  CycleCalculator(layout: WarehouseLayout)
    .handover_cycle()            → HandoverCycleResult
    .rack_storage_cycle(aisle)   → RackStorageCycleResult
    .ground_stacking_cycle(aisle)→ GroundStackingCycleResult
    .all_cycle_times()           → dict[workflow → cycle_time_s]
"""

from typing import Dict, List, Optional

from .warehouse_layout import WarehouseLayout
from .handover_workflow import HandoverCycleResult, xpl_handover_cycle
from .rack_storage import (
    RackStorageCycleResult,
    xqe_rack_storage_cycle,
    xqe_rack_storage_cycle_avg,
)
from .ground_stacking import (
    GroundStackingCycleResult,
    xqe_ground_stacking_cycle,
    xqe_ground_stacking_cycle_avg,
)


# ---------------------------------------------------------------------------
# CycleCalculator
# ---------------------------------------------------------------------------

class CycleCalculator:
    """
    Calculates cycle times for all three PR-2 workflows from a WarehouseLayout.

    Parameters
    ----------
    layout : WarehouseLayout
        Loaded and validated warehouse layout.
    """

    def __init__(self, layout: WarehouseLayout) -> None:
        self.layout = layout

    # ------------------------------------------------------------------
    # Workflow 1: XPL_201 Handover
    # ------------------------------------------------------------------

    def handover_cycle(self) -> HandoverCycleResult:
        """Calculate XPL_201 handover cycle for this warehouse."""
        return xpl_handover_cycle(
            d_rest_to_inbound=self.layout.d_rest_to_inbound_m,
            d_inbound_to_handover=self.layout.d_inbound_to_handover_m,
            d_handover_to_rest=self.layout.d_handover_to_rest_m,
        )

    # ------------------------------------------------------------------
    # Workflow 2: XQE_122 Rack Storage
    # ------------------------------------------------------------------

    def rack_storage_cycle(
        self,
        aisle: dict,
        shelf_height: Optional[float] = None,
        position_n: Optional[int] = None,
    ) -> RackStorageCycleResult:
        """
        Calculate XQE_122 rack storage cycle for a specific aisle.

        Parameters
        ----------
        aisle : dict
            Storage aisle config dict from the layout (must have type='rack').
        shelf_height : float, optional
            Target shelf height in metres.  If None, uses the average of all
            configured shelf heights.
        position_n : int, optional
            Specific rack slot (1-based).  If None, uses middle slot.
        """
        if aisle.get("type") != "rack":
            raise ValueError(
                f"Aisle '{aisle.get('name')}' is not a rack aisle (type='{aisle.get('type')}')"
            )

        d_rest_to_inb = self.layout.d_rest_to_inbound_m
        d_inb_to_aisle = self.layout.d_inbound_to_aisle_m(aisle)
        rack_length_mm = float(aisle.get("rack_length_mm", aisle.get("length_mm", 20000)))

        if shelf_height is None:
            heights = [float(h) for h in aisle.get("shelf_heights", [1.3])]
            # Average cycle across all shelf heights
            avg_ct = xqe_rack_storage_cycle_avg(
                d_rest_to_inbound=d_rest_to_inb,
                d_inbound_to_rack_entry=d_inb_to_aisle,
                shelf_heights=heights,
                rack_length_mm=rack_length_mm,
            )
            # Return a representative cycle using the middle shelf
            mid_height = heights[len(heights) // 2]
            return xqe_rack_storage_cycle(
                d_rest_to_inbound=d_rest_to_inb,
                d_inbound_to_rack_entry=d_inb_to_aisle,
                shelf_height=mid_height,
                rack_length_mm=rack_length_mm,
                position_n=position_n,
            )

        return xqe_rack_storage_cycle(
            d_rest_to_inbound=d_rest_to_inb,
            d_inbound_to_rack_entry=d_inb_to_aisle,
            shelf_height=shelf_height,
            rack_length_mm=rack_length_mm,
            position_n=position_n,
        )

    def rack_storage_avg_cycle_time(self, aisle: dict) -> float:
        """Return the average rack storage cycle time (seconds) for an aisle."""
        d_rest_to_inb = self.layout.d_rest_to_inbound_m
        d_inb_to_aisle = self.layout.d_inbound_to_aisle_m(aisle)
        rack_length_mm = float(aisle.get("rack_length_mm", aisle.get("length_mm", 20000)))
        heights = [float(h) for h in aisle.get("shelf_heights", [1.3])]
        return xqe_rack_storage_cycle_avg(
            d_rest_to_inbound=d_rest_to_inb,
            d_inbound_to_rack_entry=d_inb_to_aisle,
            shelf_heights=heights,
            rack_length_mm=rack_length_mm,
        )

    # ------------------------------------------------------------------
    # Workflow 3: XQE_122 Ground Stacking
    # ------------------------------------------------------------------

    def ground_stacking_cycle(
        self,
        aisle: dict,
        col: int = 1,
        row: int = 1,
        level: int = 0,
    ) -> GroundStackingCycleResult:
        """
        Calculate XQE_122 ground stacking cycle for a specific position.

        Parameters
        ----------
        aisle : dict
            Storage aisle config dict (must have type='ground_stacking').
        col, row : int
            Target column/row (1-based).
        level : int
            Stack level (0 = ground).
        """
        if aisle.get("type") != "ground_stacking":
            raise ValueError(
                f"Aisle '{aisle.get('name')}' is not a ground_stacking aisle"
            )

        d_rest_to_inb = self.layout.d_rest_to_inbound_m
        d_inb_to_stacking = self.layout.d_inbound_to_aisle_m(aisle)

        return xqe_ground_stacking_cycle(
            d_rest_to_inbound=d_rest_to_inb,
            d_inbound_to_stacking=d_inb_to_stacking,
            box_width_mm=float(aisle["box_width_mm"]),
            box_length_mm=float(aisle["box_length_mm"]),
            box_height_mm=float(aisle["box_height_mm"]),
            col=col,
            row=row,
            level=level,
        )

    def ground_stacking_avg_cycle_time(self, aisle: dict) -> float:
        """Return average ground stacking cycle time (seconds) for an aisle."""
        d_rest_to_inb = self.layout.d_rest_to_inbound_m
        d_inb_to_stacking = self.layout.d_inbound_to_aisle_m(aisle)
        return xqe_ground_stacking_cycle_avg(
            d_rest_to_inbound=d_rest_to_inb,
            d_inbound_to_stacking=d_inb_to_stacking,
            area_width_mm=float(aisle["width_mm"]),
            area_length_mm=float(aisle.get("length_mm", aisle.get("rack_length_mm", 10000))),
            box_width_mm=float(aisle["box_width_mm"]),
            box_length_mm=float(aisle["box_length_mm"]),
            box_height_mm=float(aisle["box_height_mm"]),
        )

    # ------------------------------------------------------------------
    # Combined summary
    # ------------------------------------------------------------------

    def all_cycle_times(self) -> Dict[str, float]:
        """
        Return average cycle times for all workflows present in the layout.

        Returns
        -------
        dict
          Keys: 'XPL_201_Handover', 'XQE_122_Rack_<aisle_name>',
                'XQE_122_Stacking_<aisle_name>'
          Values: cycle time in seconds.
        """
        result: Dict[str, float] = {}

        # Handover (always present if handover_zone is configured)
        if "handover_zone" in self.layout._config:
            hw = self.handover_cycle()
            result["XPL_201_Handover"] = hw.total_cycle_time

        for aisle in self.layout.storage_aisles:
            name = aisle.get("name", "?")
            aisle_type = aisle.get("type")

            if aisle_type == "rack":
                try:
                    ct = self.rack_storage_avg_cycle_time(aisle)
                    result[f"XQE_122_Rack_{name}"] = ct
                except (ValueError, KeyError):
                    pass

            elif aisle_type == "ground_stacking":
                try:
                    ct = self.ground_stacking_avg_cycle_time(aisle)
                    result[f"XQE_122_Stacking_{name}"] = ct
                except (ValueError, KeyError):
                    pass

        return result
