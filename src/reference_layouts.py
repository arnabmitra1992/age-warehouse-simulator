"""
Reference Warehouse Layouts Module
====================================
Three reference warehouse layouts used for Few-Shot prompting with Ollama.
Each layout includes a text description and the expected structured JSON output
so that the AI can learn the extraction pattern.

Layouts:
  1. simple_warehouse   – 1 head aisle, 2 rack aisles, 2 docks
  2. medium_warehouse   – 1 head aisle, 4 mixed aisles, 4 docks
  3. complex_warehouse  – 2 head aisles, 6 mixed aisles, 6 docks
"""

import json
from typing import Dict

# ---------------------------------------------------------------------------
# Reference Layout 1 – Simple warehouse
# ---------------------------------------------------------------------------
SIMPLE_WAREHOUSE_DESCRIPTION = """
Simple warehouse layout:
- Rectangular building, 40 m wide × 50 m long
- 1 horizontal head aisle (HA1) running the full 40 m width at y=5m, width=4m
- 2 storage aisles branching north from HA1:
    SA1: starts at x=10m, y=5m, runs north 40m, width=2.84m, dead-end, RACK storage
         Left and right racks, 10 positions per side, 4.5m height, 3 levels
    SA2: starts at x=25m, y=5m, runs north 40m, width=2.84m, dead-end, RACK storage
         Left and right racks, 10 positions per side, 4.5m height, 3 levels
- 1 inbound dock at (0, 5) – west end of head aisle
- 1 outbound dock at (40, 5) – east end of head aisle
"""

SIMPLE_WAREHOUSE_JSON = {
    "warehouse": {"name": "Simple Warehouse", "width": 40.0, "length": 50.0},
    "inbound_docks": [
        {"name": "IB1", "position": {"x": 0.0, "y": 5.0}, "count": 1}
    ],
    "outbound_docks": [
        {"name": "OB1", "position": {"x": 40.0, "y": 5.0}, "count": 1}
    ],
    "head_aisles": [
        {
            "name": "HA1",
            "start": {"x": 0.0, "y": 5.0},
            "end": {"x": 40.0, "y": 5.0},
            "width": 4.0,
            "connections": ["SA1", "SA2"],
        }
    ],
    "storage_aisles": [
        {
            "name": "SA1",
            "start": {"x": 10.0, "y": 5.0},
            "end": {"x": 10.0, "y": 45.0},
            "width": 2.84,
            "depth": 40.0,
            "entry_type": "dead-end",
            "storage_type": "rack",
            "head_aisle": "HA1",
            "racks": [
                {"side": "left", "positions": 10, "height": 4.5, "levels": 3},
                {"side": "right", "positions": 10, "height": 4.5, "levels": 3},
            ],
        },
        {
            "name": "SA2",
            "start": {"x": 25.0, "y": 5.0},
            "end": {"x": 25.0, "y": 45.0},
            "width": 2.84,
            "depth": 40.0,
            "entry_type": "dead-end",
            "storage_type": "rack",
            "head_aisle": "HA1",
            "racks": [
                {"side": "left", "positions": 10, "height": 4.5, "levels": 3},
                {"side": "right", "positions": 10, "height": 4.5, "levels": 3},
            ],
        },
    ],
    "ground_storage_zones": [],
    "ground_stacking_zones": [],
}

# ---------------------------------------------------------------------------
# Reference Layout 2 – Medium warehouse (mixed storage types)
# ---------------------------------------------------------------------------
MEDIUM_WAREHOUSE_DESCRIPTION = """
Medium warehouse layout:
- Building: 60 m wide × 80 m long
- 1 horizontal head aisle (HA1): full 60 m width at y=6m, width=4.5m
- 4 storage aisles branching north from HA1:
    SA1: x=10m, y=6m, north 60m, width=2.84m, dead-end, RACK, 4.5m height, 4 levels
    SA2: x=25m, y=6m, north 60m, width=2.84m, dead-end, RACK, 4.5m height, 4 levels
    SA3: x=40m, y=6m, north 30m, width=3.5m, GROUND STORAGE zone (8 rows × 12 cols)
    SA4: x=52m, y=6m, north 15m, width=5m, GROUND STACKING zone (boxes 1200×800)
- 2 inbound docks at west end (x=0, y=6)
- 2 outbound docks at east end (x=60, y=6)
"""

MEDIUM_WAREHOUSE_JSON = {
    "warehouse": {"name": "Medium Warehouse", "width": 60.0, "length": 80.0},
    "inbound_docks": [
        {"name": "IB1", "position": {"x": 0.0, "y": 6.0}, "count": 2}
    ],
    "outbound_docks": [
        {"name": "OB1", "position": {"x": 60.0, "y": 6.0}, "count": 2}
    ],
    "head_aisles": [
        {
            "name": "HA1",
            "start": {"x": 0.0, "y": 6.0},
            "end": {"x": 60.0, "y": 6.0},
            "width": 4.5,
            "connections": ["SA1", "SA2", "SA3", "SA4"],
        }
    ],
    "storage_aisles": [
        {
            "name": "SA1",
            "start": {"x": 10.0, "y": 6.0},
            "end": {"x": 10.0, "y": 66.0},
            "width": 2.84,
            "depth": 60.0,
            "entry_type": "dead-end",
            "storage_type": "rack",
            "head_aisle": "HA1",
            "racks": [
                {"side": "left", "positions": 15, "height": 4.5, "levels": 4},
                {"side": "right", "positions": 15, "height": 4.5, "levels": 4},
            ],
        },
        {
            "name": "SA2",
            "start": {"x": 25.0, "y": 6.0},
            "end": {"x": 25.0, "y": 66.0},
            "width": 2.84,
            "depth": 60.0,
            "entry_type": "dead-end",
            "storage_type": "rack",
            "head_aisle": "HA1",
            "racks": [
                {"side": "left", "positions": 15, "height": 4.5, "levels": 4},
                {"side": "right", "positions": 15, "height": 4.5, "levels": 4},
            ],
        },
        {
            "name": "SA3",
            "start": {"x": 40.0, "y": 6.0},
            "end": {"x": 40.0, "y": 36.0},
            "width": 3.5,
            "depth": 30.0,
            "entry_type": "dead-end",
            "storage_type": "ground_storage",
            "head_aisle": "HA1",
            "racks": [],
        },
        {
            "name": "SA4",
            "start": {"x": 52.0, "y": 6.0},
            "end": {"x": 52.0, "y": 21.0},
            "width": 5.0,
            "depth": 15.0,
            "entry_type": "dead-end",
            "storage_type": "ground_stacking",
            "head_aisle": "HA1",
            "racks": [],
        },
    ],
    "ground_storage_zones": [
        {
            "name": "GS1",
            "aisle": "SA3",
            "position": {"x": 40.0, "y": 6.0},
            "width": 3.5,
            "depth": 30.0,
            "rows": 8,
            "columns": 12,
        }
    ],
    "ground_stacking_zones": [
        {
            "name": "GST1",
            "aisle": "SA4",
            "position": {"x": 52.0, "y": 6.0},
            "width": 5.0,
            "depth": 15.0,
            "box_types": ["1200x800", "800x600"],
            "max_stack_height": 2.0,
        }
    ],
}

# ---------------------------------------------------------------------------
# Reference Layout 3 – Complex warehouse (two head aisles, 6 aisles)
# ---------------------------------------------------------------------------
COMPLEX_WAREHOUSE_DESCRIPTION = """
Complex warehouse layout:
- Building: 80 m wide × 120 m long
- 2 horizontal head aisles:
    HA1: y=6m, full 80 m width, 5m wide, connects SA1–SA3
    HA2: y=66m, full 80 m width, 5m wide, connects SA4–SA6
    HA1 and HA2 connected by a vertical linking corridor at x=0 and x=80
- 6 storage aisles:
    SA1 (rack, dead-end): x=15m, y=6m, depth=55m, width=1.77m, height=8.5m, 5 levels
    SA2 (rack, dead-end): x=35m, y=6m, depth=55m, width=1.77m, height=8.5m, 5 levels
    SA3 (rack, through):  x=55m, y=6m, depth=55m (connects HA1 and HA2), width=1.77m
    SA4 (rack, dead-end): x=15m, y=66m, depth=50m, width=2.84m, height=4.5m, 3 levels
    SA5 (ground storage): x=40m, y=66m, depth=40m, width=3.5m
    SA6 (ground stacking):x=60m, y=66m, depth=30m, width=5m
- 3 inbound docks at west end of HA1 (x=0, y=6)
- 3 outbound docks at east end of HA1 (x=80, y=6)
"""

COMPLEX_WAREHOUSE_JSON = {
    "warehouse": {"name": "Complex Warehouse", "width": 80.0, "length": 120.0},
    "inbound_docks": [
        {"name": "IB1", "position": {"x": 0.0, "y": 6.0}, "count": 3}
    ],
    "outbound_docks": [
        {"name": "OB1", "position": {"x": 80.0, "y": 6.0}, "count": 3}
    ],
    "head_aisles": [
        {
            "name": "HA1",
            "start": {"x": 0.0, "y": 6.0},
            "end": {"x": 80.0, "y": 6.0},
            "width": 5.0,
            "connections": ["SA1", "SA2", "SA3"],
        },
        {
            "name": "HA2",
            "start": {"x": 0.0, "y": 66.0},
            "end": {"x": 80.0, "y": 66.0},
            "width": 5.0,
            "connections": ["SA3", "SA4", "SA5", "SA6"],
        },
    ],
    "storage_aisles": [
        {
            "name": "SA1",
            "start": {"x": 15.0, "y": 6.0},
            "end": {"x": 15.0, "y": 61.0},
            "width": 1.77,
            "depth": 55.0,
            "entry_type": "dead-end",
            "storage_type": "rack",
            "head_aisle": "HA1",
            "racks": [
                {"side": "left", "positions": 20, "height": 8.5, "levels": 5},
                {"side": "right", "positions": 20, "height": 8.5, "levels": 5},
            ],
        },
        {
            "name": "SA2",
            "start": {"x": 35.0, "y": 6.0},
            "end": {"x": 35.0, "y": 61.0},
            "width": 1.77,
            "depth": 55.0,
            "entry_type": "dead-end",
            "storage_type": "rack",
            "head_aisle": "HA1",
            "racks": [
                {"side": "left", "positions": 20, "height": 8.5, "levels": 5},
                {"side": "right", "positions": 20, "height": 8.5, "levels": 5},
            ],
        },
        {
            "name": "SA3",
            "start": {"x": 55.0, "y": 6.0},
            "end": {"x": 55.0, "y": 66.0},
            "width": 1.77,
            "depth": 60.0,
            "entry_type": "through",
            "storage_type": "rack",
            "head_aisle": "HA1",
            "racks": [
                {"side": "left", "positions": 22, "height": 8.5, "levels": 5},
                {"side": "right", "positions": 22, "height": 8.5, "levels": 5},
            ],
        },
        {
            "name": "SA4",
            "start": {"x": 15.0, "y": 66.0},
            "end": {"x": 15.0, "y": 116.0},
            "width": 2.84,
            "depth": 50.0,
            "entry_type": "dead-end",
            "storage_type": "rack",
            "head_aisle": "HA2",
            "racks": [
                {"side": "left", "positions": 18, "height": 4.5, "levels": 3},
                {"side": "right", "positions": 18, "height": 4.5, "levels": 3},
            ],
        },
        {
            "name": "SA5",
            "start": {"x": 40.0, "y": 66.0},
            "end": {"x": 40.0, "y": 106.0},
            "width": 3.5,
            "depth": 40.0,
            "entry_type": "dead-end",
            "storage_type": "ground_storage",
            "head_aisle": "HA2",
            "racks": [],
        },
        {
            "name": "SA6",
            "start": {"x": 60.0, "y": 66.0},
            "end": {"x": 60.0, "y": 96.0},
            "width": 5.0,
            "depth": 30.0,
            "entry_type": "dead-end",
            "storage_type": "ground_stacking",
            "head_aisle": "HA2",
            "racks": [],
        },
    ],
    "ground_storage_zones": [
        {
            "name": "GS1",
            "aisle": "SA5",
            "position": {"x": 40.0, "y": 66.0},
            "width": 3.5,
            "depth": 40.0,
            "rows": 10,
            "columns": 14,
        }
    ],
    "ground_stacking_zones": [
        {
            "name": "GST1",
            "aisle": "SA6",
            "position": {"x": 60.0, "y": 66.0},
            "width": 5.0,
            "depth": 30.0,
            "box_types": ["1200x800", "800x600"],
            "max_stack_height": 2.5,
        }
    ],
}

# ---------------------------------------------------------------------------
# Exported reference set
# ---------------------------------------------------------------------------

REFERENCE_LAYOUTS = [
    {
        "id": 1,
        "label": "Simple Warehouse",
        "description": SIMPLE_WAREHOUSE_DESCRIPTION.strip(),
        "json": SIMPLE_WAREHOUSE_JSON,
    },
    {
        "id": 2,
        "label": "Medium Warehouse",
        "description": MEDIUM_WAREHOUSE_DESCRIPTION.strip(),
        "json": MEDIUM_WAREHOUSE_JSON,
    },
    {
        "id": 3,
        "label": "Complex Warehouse",
        "description": COMPLEX_WAREHOUSE_DESCRIPTION.strip(),
        "json": COMPLEX_WAREHOUSE_JSON,
    },
]


def get_few_shot_prompt_block() -> str:
    """
    Build the few-shot examples block that is injected into the Ollama system prompt.
    Returns a formatted string showing description → JSON pairs.
    """
    lines = []
    for ref in REFERENCE_LAYOUTS:
        lines.append(f"--- EXAMPLE {ref['id']}: {ref['label']} ---")
        lines.append("DESCRIPTION:")
        lines.append(ref["description"])
        lines.append("EXPECTED JSON OUTPUT:")
        lines.append(json.dumps(ref["json"], indent=2))
        lines.append("")
    return "\n".join(lines)
