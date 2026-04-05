"""
Warehouse Layout Module
========================
Loads and validates warehouse configuration from JSON files.

All distances in the JSON are stored in **millimetres (mm)** and are
converted to **metres (m)** internally for physics calculations.

Expected JSON structure (config/config_template.json shows the full schema):
  {
    "warehouse": { "name": ..., "width_mm": ..., "length_mm": ... },
    "inbound": {
      "position": "west|east|north|south",
      "distance_to_handover_mm": ...,
      "distance_to_rack_handover_mm": ...,
      "distance_to_stacking_handover_mm": ...
    },
    "outbound": { ... },
    "rack_storage": {
      "aisle_width_mm": ...,
      "aisle_depth_mm": ...,
      "shelves": [...],
      "pallet_spacing_mm": 950
    },
    "ground_stacking": {
      "rows": ..., "cols": ..., "levels": ...,
      "level_height_mm": ..., "area_length_mm": ..., "area_width_mm": ...
    },
    "throughput": {
      "inbound": { "daily_tasks": ..., "operating_hours": ..., "utilization": ... },
      "outbound": { "daily_tasks": ..., "operating_hours": ..., "utilization": ... }
    }
  }
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Aisle-width thresholds (metres)
# ---------------------------------------------------------------------------

#: XNA narrow-aisle minimum working width (m)
XNA_MIN_AISLE_WIDTH_M: float = 1.717
#: XNA narrow-aisle maximum working width / XSC lower bound (m)
XNA_MAX_AISLE_WIDTH_M: float = 2.0
#: XSC medium-aisle upper bound / XQE lower bound (m)
XSC_MAX_AISLE_WIDTH_M: float = 2.84   # also == XQE minimum
#: XQE standard-aisle minimum working width (m)
XQE_MIN_AISLE_WIDTH_M: float = 2.84

#: Distance threshold (m) above which XPL_201 is used for horizontal legs
HANDOVER_DISTANCE_THRESHOLD_M: float = 50.0


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ThroughputConfig:
    """Per-direction throughput configuration."""
    daily_tasks: int
    operating_hours: float
    utilization: float  # 0–1


@dataclass
class RackConfig:
    """Rack storage configuration."""
    aisle_width_m: float
    aisle_depth_m: float
    pallet_spacing_m: float = 0.95   # 950 mm euro-pallet pitch
    shelves: List[dict] = field(default_factory=list)

    @property
    def num_shelves(self) -> int:
        return len(self.shelves)

    @property
    def max_shelf_height_m(self) -> float:
        if not self.shelves:
            return 0.0
        return max(s.get("height_mm", 0) / 1000.0 for s in self.shelves)


@dataclass
class GroundStackingConfig:
    """Ground stacking with multiple levels configuration."""
    rows: int
    cols: int
    levels: int
    level_height_m: float
    area_length_m: float
    area_width_m: float

    @property
    def total_positions(self) -> int:
        return self.rows * self.cols * self.levels

    @property
    def max_stack_height_m(self) -> float:
        return self.levels * self.level_height_m


@dataclass
class WarehouseConfig:
    """Complete parsed warehouse configuration."""

    name: str
    width_m: float
    length_m: float

    # Distances from inbound dock to handover points (m)
    inbound_to_handover_m: float
    inbound_to_rack_handover_m: float
    inbound_to_stacking_handover_m: float

    # Distances from handover to storage areas (m)
    handover_to_rack_m: float
    handover_to_stacking_m: float

    # Distances from handover points to outbound dock (m)
    rack_handover_to_outbound_m: float
    stacking_handover_to_outbound_m: float

    rack: Optional[RackConfig] = None
    stacking: Optional[GroundStackingConfig] = None

    inbound_throughput: Optional[ThroughputConfig] = None
    outbound_throughput: Optional[ThroughputConfig] = None

    # Workflow split (fraction of tasks going to rack vs stacking)
    rack_fraction: float = 0.6
    stacking_fraction: float = 0.4

    def distance_inbound_to_handover(self, storage_type: str) -> float:
        """Return inbound → handover distance for a given storage type."""
        if storage_type == "rack":
            return self.inbound_to_rack_handover_m
        return self.inbound_to_stacking_handover_m

    def distance_handover_to_storage(self, storage_type: str) -> float:
        """Return handover → storage distance for a given storage type."""
        if storage_type == "rack":
            return self.handover_to_rack_m
        return self.handover_to_stacking_m

    def distance_handover_to_outbound(self, storage_type: str) -> float:
        """Return handover → outbound distance for a given storage type."""
        if storage_type == "rack":
            return self.rack_handover_to_outbound_m
        return self.stacking_handover_to_outbound_m

    def aisle_width_m(self) -> float:
        """Return rack aisle width or 0 if no rack configured."""
        return self.rack.aisle_width_m if self.rack else 0.0


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

class WarehouseLayoutLoader:
    """Loads and validates a warehouse configuration JSON file."""

    def load(self, path: str) -> WarehouseConfig:
        """Load configuration from *path* and return a :class:`WarehouseConfig`."""
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "r") as fh:
            raw = json.load(fh)
        return self._parse(raw)

    def load_dict(self, raw: dict) -> WarehouseConfig:
        """Parse a pre-loaded configuration dictionary."""
        return self._parse(raw)

    # ------------------------------------------------------------------

    def _parse(self, d: dict) -> WarehouseConfig:
        wh = d.get("warehouse", {})
        name = wh.get("name", "Warehouse")
        width_m = wh.get("width_mm", 0) / 1000.0
        length_m = wh.get("length_mm", 0) / 1000.0

        ib = d.get("inbound", {})
        ob = d.get("outbound", {})

        inbound_to_handover_m = ib.get("distance_to_handover_mm", 0) / 1000.0
        inbound_to_rack_handover_m = ib.get(
            "distance_to_rack_handover_mm",
            ib.get("distance_to_handover_mm", 0),
        ) / 1000.0
        inbound_to_stacking_handover_m = ib.get(
            "distance_to_stacking_handover_mm",
            ib.get("distance_to_handover_mm", 0),
        ) / 1000.0

        handover_to_rack_m = d.get("distances", {}).get(
            "handover_to_rack_mm", 0
        ) / 1000.0
        handover_to_stacking_m = d.get("distances", {}).get(
            "handover_to_stacking_mm", 0
        ) / 1000.0

        rack_handover_to_outbound_m = ob.get(
            "rack_handover_to_outbound_mm",
            ob.get("distance_from_handover_mm", 0),
        ) / 1000.0
        stacking_handover_to_outbound_m = ob.get(
            "stacking_handover_to_outbound_mm",
            ob.get("distance_from_handover_mm", 0),
        ) / 1000.0

        # Rack config
        rack_cfg: Optional[RackConfig] = None
        if "rack_storage" in d:
            r = d["rack_storage"]
            rack_cfg = RackConfig(
                aisle_width_m=r.get("aisle_width_mm", 2840) / 1000.0,
                aisle_depth_m=r.get("aisle_depth_mm", 20000) / 1000.0,
                pallet_spacing_m=r.get("pallet_spacing_mm", 950) / 1000.0,
                shelves=r.get("shelves", []),
            )

        # Ground stacking config
        stacking_cfg: Optional[GroundStackingConfig] = None
        if "ground_stacking" in d:
            s = d["ground_stacking"]
            stacking_cfg = GroundStackingConfig(
                rows=s.get("rows", 5),
                cols=s.get("cols", 5),
                levels=s.get("levels", 3),
                level_height_m=s.get("level_height_mm", 1200) / 1000.0,
                area_length_m=s.get("area_length_mm", 10000) / 1000.0,
                area_width_m=s.get("area_width_mm", 10000) / 1000.0,
            )

        # Throughput configs
        tp = d.get("throughput", {})
        ib_tp_raw = tp.get("inbound", {})
        ob_tp_raw = tp.get("outbound", {})

        ib_tp: Optional[ThroughputConfig] = None
        if ib_tp_raw:
            ib_tp = ThroughputConfig(
                daily_tasks=ib_tp_raw.get("daily_tasks", 0),
                operating_hours=ib_tp_raw.get("operating_hours", 8.0),
                utilization=ib_tp_raw.get("utilization", 0.75),
            )
        ob_tp: Optional[ThroughputConfig] = None
        if ob_tp_raw:
            ob_tp = ThroughputConfig(
                daily_tasks=ob_tp_raw.get("daily_tasks", 0),
                operating_hours=ob_tp_raw.get("operating_hours", 8.0),
                utilization=ob_tp_raw.get("utilization", 0.75),
            )

        # Workflow split
        wf = d.get("workflow", {})
        rack_frac = wf.get("rack_fraction", 0.6)
        stacking_frac = wf.get("stacking_fraction", 0.4)

        return WarehouseConfig(
            name=name,
            width_m=width_m,
            length_m=length_m,
            inbound_to_handover_m=inbound_to_handover_m,
            inbound_to_rack_handover_m=inbound_to_rack_handover_m,
            inbound_to_stacking_handover_m=inbound_to_stacking_handover_m,
            handover_to_rack_m=handover_to_rack_m,
            handover_to_stacking_m=handover_to_stacking_m,
            rack_handover_to_outbound_m=rack_handover_to_outbound_m,
            stacking_handover_to_outbound_m=stacking_handover_to_outbound_m,
            rack=rack_cfg,
            stacking=stacking_cfg,
            inbound_throughput=ib_tp,
            outbound_throughput=ob_tp,
            rack_fraction=rack_frac,
            stacking_fraction=stacking_frac,
        )


# ---------------------------------------------------------------------------
# AGV selection helpers
# ---------------------------------------------------------------------------

class AisleCompatibilityResult:
    """Result of an aisle-width compatibility check."""

    def __init__(
        self,
        agv_type: Optional[str],
        status: str,
        note: str,
        use_handover: bool = False,
        compatible_agvs: Optional[List[str]] = None,
    ) -> None:
        self.agv_type = agv_type
        self.status = status          # 'ok', 'xsc_pending', 'too_narrow'
        self.note = note
        self.use_handover = use_handover
        self.compatible_agvs: List[str] = compatible_agvs or (
            [agv_type] if agv_type else []
        )

    @property
    def is_ok(self) -> bool:
        return self.status == "ok"

    @property
    def is_blocked(self) -> bool:
        return self.status in ("xsc_pending", "too_narrow")


def select_agv_for_rack_aisle(aisle_width_m: float) -> AisleCompatibilityResult:
    """
    Select the appropriate AGV for a **rack storage** aisle given its width.

    Decision tree:
      ≥ 2.84 m          → XQE_122  (standard aisle)
      2.0 m – 2.84 m    → XSC_PENDING (medium aisle, no data yet)
      1.717 m – 2.0 m   → XNA (narrow aisle, always handover)
      < 1.717 m          → too narrow, no compatible AGV
    """
    if aisle_width_m >= XQE_MIN_AISLE_WIDTH_M:
        return AisleCompatibilityResult(
            agv_type="XQE_122",
            status="ok",
            note=f"Standard aisle ({aisle_width_m:.3f} m ≥ {XQE_MIN_AISLE_WIDTH_M} m) – XQE_122",
            use_handover=False,
            compatible_agvs=["XQE_122"],
        )
    if XNA_MAX_AISLE_WIDTH_M < aisle_width_m < XSC_MAX_AISLE_WIDTH_M:
        return AisleCompatibilityResult(
            agv_type=None,
            status="xsc_pending",
            note=(
                f"⚠️  Medium aisle ({aisle_width_m:.3f} m) requires XSC data. "
                "Waiting for manufacturer specifications – cannot calculate throughput."
            ),
            compatible_agvs=[],
        )
    if XNA_MIN_AISLE_WIDTH_M <= aisle_width_m <= XNA_MAX_AISLE_WIDTH_M:
        return AisleCompatibilityResult(
            agv_type="XNA",
            status="ok",
            note=f"Narrow aisle ({aisle_width_m:.3f} m) – XNA (always handover)",
            use_handover=True,
            compatible_agvs=["XNA_121", "XNA_151"],
        )
    return AisleCompatibilityResult(
        agv_type=None,
        status="too_narrow",
        note=(
            f"❌ Aisle too narrow ({aisle_width_m:.3f} m). "
            f"Minimum is {XNA_MIN_AISLE_WIDTH_M} m for XNA."
        ),
        compatible_agvs=[],
    )


def select_agv_for_ground_stacking() -> AisleCompatibilityResult:
    """
    For **ground stacking with multiple levels**, XQE_122 is the ONLY option.
    XSC cannot perform floor stacking.  Aisle width is irrelevant here.
    """
    return AisleCompatibilityResult(
        agv_type="XQE_122",
        status="ok",
        note="Ground stacking – XQE_122 ONLY (XSC cannot floor-stack)",
        use_handover=False,
        compatible_agvs=["XQE_122"],
    )


def needs_handover_xqe(distance_m: float) -> bool:
    """Return True if a distance leg requires a handover (XPL_201) for XQE routes."""
    return distance_m >= HANDOVER_DISTANCE_THRESHOLD_M
