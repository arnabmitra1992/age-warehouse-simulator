"""
Warehouse Layout Module
========================
Loads, validates, and exposes the new mm-unit JSON configuration format used by
the PR-2 workflow engine.

New config format (all positions in millimetres):
  {
    "warehouse": {
      "name": "My Warehouse",
      "length_mm": 60000,
      "width_mm": 40000,
      "head_aisle_width_mm": 4000
    },
    "docks": {
      "inbound":  {"x_mm": 0,     "y_mm": 20000},
      "outbound": {"x_mm": 60000, "y_mm": 20000}
    },
    "rest_area":    {"x_mm": 30000, "y_mm": 0},
    "handover_zone":{"x_mm": 30000, "y_mm": 40000},
    "storage_aisles": [...],
    "throughput": {
      "daily_pallets": 1000,
      "operating_hours": 16,
      "xpl_percentage": 30,
      "xqe_rack_percentage": 50,
      "xqe_stacking_percentage": 20,
      "utilization_target": 0.75
    }
  }
"""

import json
import math
import os
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MM_TO_M: float = 1.0 / 1000.0

REQUIRED_TOP_LEVEL_KEYS = {
    "warehouse",
    "docks",
    "storage_aisles",
}


# ---------------------------------------------------------------------------
# Distance helpers
# ---------------------------------------------------------------------------

def _euclidean_mm(a: dict, b: dict) -> float:
    """Return Euclidean distance in millimetres between two x_mm/y_mm dicts."""
    dx = b["x_mm"] - a["x_mm"]
    dy = b["y_mm"] - a["y_mm"]
    return math.sqrt(dx * dx + dy * dy)


def _euclidean_m(a: dict, b: dict) -> float:
    """Return Euclidean distance in metres between two x_mm/y_mm dicts."""
    return _euclidean_mm(a, b) * MM_TO_M


# ---------------------------------------------------------------------------
# WarehouseLayout class
# ---------------------------------------------------------------------------

class WarehouseLayout:
    """
    Loads a new-format warehouse config JSON and exposes distances required
    by the PR-2 workflow calculations.

    All public distance attributes are in **metres**.
    """

    def __init__(self, config: dict) -> None:
        self._config = config
        self._validate()

    # ------------------------------------------------------------------
    # Public construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls, path: str) -> "WarehouseLayout":
        """Load layout from a JSON file."""
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls(data)

    @classmethod
    def from_dict(cls, data: dict) -> "WarehouseLayout":
        """Load layout from a plain dict (e.g. from Ollama output)."""
        return cls(data)

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return self._config["warehouse"].get("name", "Warehouse")

    @property
    def length_m(self) -> float:
        return self._config["warehouse"]["length_mm"] * MM_TO_M

    @property
    def width_m(self) -> float:
        return self._config["warehouse"]["width_mm"] * MM_TO_M

    @property
    def head_aisle_width_m(self) -> float:
        return self._config["warehouse"].get("head_aisle_width_mm", 4000) * MM_TO_M

    @property
    def rest_area(self) -> dict:
        return self._config.get("rest_area", {"x_mm": 0, "y_mm": 0})

    @property
    def handover_zone(self) -> dict:
        return self._config.get("handover_zone", {"x_mm": 0, "y_mm": 0})

    @property
    def inbound_dock(self) -> dict:
        return self._config["docks"]["inbound"]

    @property
    def outbound_dock(self) -> dict:
        return self._config["docks"]["outbound"]

    @property
    def storage_aisles(self) -> List[dict]:
        return self._config.get("storage_aisles", [])

    @property
    def throughput_config(self) -> dict:
        return self._config.get("throughput", {})

    # Core distances used by all three workflows
    @property
    def d_rest_to_inbound_m(self) -> float:
        """Distance from rest area to inbound dock (metres)."""
        return _euclidean_m(self.rest_area, self.inbound_dock)

    @property
    def d_inbound_to_handover_m(self) -> float:
        """Distance from inbound dock to handover zone (metres, via head aisle)."""
        return _euclidean_m(self.inbound_dock, self.handover_zone)

    @property
    def d_handover_to_rest_m(self) -> float:
        """Distance from handover zone back to rest area (metres)."""
        return _euclidean_m(self.handover_zone, self.rest_area)

    def aisle_by_name(self, name: str) -> Optional[dict]:
        """Return the storage aisle config dict with the given name."""
        for aisle in self.storage_aisles:
            if aisle.get("name") == name:
                return aisle
        return None

    def rack_aisles(self) -> List[dict]:
        """Return all rack-type storage aisles."""
        return [a for a in self.storage_aisles if a.get("type") == "rack"]

    def ground_stacking_aisles(self) -> List[dict]:
        """Return all ground-stacking-type storage aisles."""
        return [a for a in self.storage_aisles if a.get("type") == "ground_stacking"]

    def aisle_entry_m(self, aisle: dict) -> dict:
        """Return the aisle entry position in metres."""
        return {
            "x": aisle["entry_x_mm"] * MM_TO_M,
            "y": aisle["entry_y_mm"] * MM_TO_M,
        }

    def d_inbound_to_aisle_m(self, aisle: dict) -> float:
        """
        Approximate distance from inbound dock to a storage aisle entry (metres).
        Routes through the head aisle (Manhattan-style: x then y component).
        """
        inb = self.inbound_dock
        entry_mm = {"x_mm": aisle["entry_x_mm"], "y_mm": aisle["entry_y_mm"]}
        return _euclidean_m(inb, entry_mm)

    def validate(self) -> List[str]:
        """Return a list of validation error strings (empty if OK)."""
        errors: List[str] = []
        missing = REQUIRED_TOP_LEVEL_KEYS - set(self._config.keys())
        if missing:
            errors.append(f"Missing top-level keys: {sorted(missing)}")

        wh = self._config.get("warehouse", {})
        for field in ("length_mm", "width_mm"):
            if field not in wh:
                errors.append(f"warehouse.{field} is required")
            elif not isinstance(wh[field], (int, float)) or wh[field] <= 0:
                errors.append(f"warehouse.{field} must be a positive number")

        docks = self._config.get("docks", {})
        for side in ("inbound", "outbound"):
            if side not in docks:
                errors.append(f"docks.{side} is required")

        for aisle in self._config.get("storage_aisles", []):
            name = aisle.get("name", "?")
            for field in ("width_mm", "entry_x_mm", "entry_y_mm"):
                if field not in aisle:
                    errors.append(f"storage_aisle '{name}' missing '{field}'")

        return errors

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        errors = self.validate()
        if errors:
            raise ValueError(
                "Invalid warehouse layout config:\n" + "\n".join(f"  • {e}" for e in errors)
            )


# ---------------------------------------------------------------------------
# Module-level loader
# ---------------------------------------------------------------------------

def load_layout(path: str) -> WarehouseLayout:
    """Load and validate a warehouse layout from a JSON config file."""
    return WarehouseLayout.from_file(path)


def validate_config(config: dict) -> List[str]:
    """Return validation errors for a raw config dict without raising."""
    try:
        layout = WarehouseLayout.from_dict(config)
        return layout.validate()
    except (ValueError, KeyError) as exc:
        return [str(exc)]
