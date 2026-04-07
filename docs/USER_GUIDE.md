# User Guide

## Configuration File Structure

All simulator parameters are controlled via a JSON configuration file.

### AGV_Specifications

```json
"AGV_Specifications": {
  "XQE_122": {
    "forward_speed_ms": 1.0,        // m/s – forward travel speed
    "reverse_speed_ms": 0.3,        // m/s – reverse travel speed
    "lift_speed_ms": 0.2,           // m/s – vertical lift speed
    "max_lift_height_mm": 4500,     // mm  – maximum lift height
    "pickup_time_s": 30,            // s   – time to pickup a pallet
    "dropoff_time_s": 30            // s   – time to deposit a pallet
  },
  "XPL_201": {
    "forward_speed_ms": 1.5,        // m/s – forward travel speed
    "reverse_speed_ms": 0.5,        // m/s – reverse travel speed
    "pickup_time_s": 30,            // s   – time to pickup a pallet
    "dropoff_time_s": 30            // s   – time to deposit a pallet
  },
  "Turn_90_degrees_s": 10           // s   – time for a 90° turn
}
```

### Warehouse_Layout

```json
"Warehouse_Layout": {
  "Distances_mm": {
    "Rest_to_Inbound": 5000,           // mm – rest area to inbound buffer
    "Rest_to_Head_Aisle": 3000,        // mm – rest area to head aisle junction
    "Head_Aisle_to_Handover": 8000,    // mm – head aisle to handover zone
    "Head_Aisle_to_Rack_Aisle": 6000,  // mm – head aisle to rack aisle entry
    "Rack_Aisle_Length": 20000,        // mm – full length of rack aisle
    "Head_Aisle_to_Stacking": 10000,   // mm – head aisle to stacking area
    "Inbound_Depth_mm": 2000           // mm – depth of inbound buffer bay
  }
}
```

### Rack_Configuration

```json
"Rack_Configuration": {
  "Rack_Length_mm": 20000,          // mm – total rack length
  "Pallet_Width_mm": 800,           // mm – pallet width (for reference)
  "Shelf_Height_Spacing_mm": 1300,  // mm – vertical spacing between shelf levels
  "Position_Spacing_mm": 950        // mm – spacing between pallet positions (800mm pallet + 2×75mm gaps)
}
```

### Ground_Stacking_Configuration

```json
"Ground_Stacking_Configuration": {
  "Box_Dimensions": {
    "Length_mm": 1200,   // mm – box/pallet length
    "Width_mm": 800,     // mm – box/pallet width
    "Height_mm": 1000    // mm – box/pallet height
  },
  "Storage_Area_Dimensions": {
    "Length_mm": 15000,  // mm – stacking area total length
    "Width_mm": 10000    // mm – stacking area total width
  },
  "Fork_Entry_Side": "Length",  // "Length" or "Width" – which side the forks enter
  "Clearance_mm": 200           // mm – clearance between box positions (fixed at 200mm)
}
```

### Throughput_Configuration

```json
"Throughput_Configuration": {
  "Total_Daily_Pallets": 1000,      // total pallets handled per day
  "Operating_Hours": 16,            // operating hours per day
  "XPL_201_Percentage": 30,         // % of pallets handled by XPL_201 (handover)
  "XQE_Rack_Percentage": 50,        // % of pallets handled by XQE_122 (racks)
  "XQE_Stacking_Percentage": 20,    // % of pallets handled by XQE_122 (stacking)
  "Utilization_Target": 0.75,       // AGV utilisation target (0.0 – 1.0)
  "Buffer_Capacity_Pallets": 50     // inbound buffer capacity (for reference)
}
```

**Note:** `XPL_201_Percentage + XQE_Rack_Percentage + XQE_Stacking_Percentage` must equal 100.

---

### Shuffle_Configuration — Alternating Buffer Column Strategy

Activate this strategy by setting `strategy` to `"alternating_buffer_column_24h"`.

```json
"Shuffle_Configuration": {
  "strategy": "alternating_buffer_column_24h",
  "min_age_hours_for_outbound": 24,
  "outbound_column_mode": "hard",
  "initial_fill_columns": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
  "day_patterns": [
    {
      "inbound_column_order":  [11, 10, 9, 8, 7, 6, 5, 4, 3, 2],
      "outbound_column_order": [10,  9, 8, 7, 6, 5, 4, 3, 2, 1]
    },
    {
      "inbound_column_order":  [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
      "outbound_column_order": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    }
  ]
}
```

#### Key fields

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `strategy` | string | — | Must be `"alternating_buffer_column_24h"` to activate this strategy. |
| `min_age_hours_for_outbound` | number | `24` | A pallet must be at least this many hours old before it is eligible for outbound retrieval. |
| `outbound_column_mode` | string | `"hard"` | Controls fallback behaviour when the preferred outbound columns are exhausted. See below. |
| `initial_fill_columns` | array of int | day-1 outbound order | Columns to fill with pre-aged pallets at simulation start (time 0). |
| `day_patterns` | array of objects | required | Cyclic list of day patterns (see below). |

Each entry in `day_patterns` has:

| Key | Type | Description |
|-----|------|-------------|
| `inbound_column_order` | array of int | Ordered list of columns for inbound placement. The first vacant slot in the first listed column is used. |
| `outbound_column_order` | array of int | Ordered list of columns for outbound retrieval (the "preferred" columns). |

Day patterns cycle: day 1 uses index 0, day 2 uses index 1, day 3 uses index 0 again, etc.

#### `outbound_column_mode`

**`"hard"` (default)**

Outbound retrieval *only* considers columns listed in the day's `outbound_column_order`.
If no eligible pallet (age ≥ `min_age_hours_for_outbound`) exists in those columns,
the outbound move is skipped (counted as a missed retrieval).
This mode models a strict physical routing constraint and is the simplest to reason about.

**`"preference"`**

Outbound first tries the columns in the day's `outbound_column_order`.
If demand cannot be met from those columns, it falls back to the *remaining* columns
(those not listed in `outbound_column_order`), scanned in **the same direction** as the
preferred list:

- If `outbound_column_order` is descending (e.g. `[10, 9, … 1]`), the fallback columns
  are also scanned descending.
- If `outbound_column_order` is ascending (e.g. `[2, 3, … 11]`), the fallback columns
  are scanned ascending.

The 24 h aging gate still applies in fallback mode: only pallets with
`age >= min_age_hours_for_outbound` are eligible.

#### Example configs

| File | Mode |
|------|------|
| `config/config_alternating_buffer_11x12x3_hard.json` | `"hard"` |
| `config/config_alternating_buffer_11x12x3_preference.json` | `"preference"` |

Both configs use an 11 × 12 × 3 ground-stacking layout with 10 operating hours per day
and 36 pallets/hour.

---

## CLI Usage

```bash
# Run with a config file (prints full report to stdout)
python main.py run --config config/config_template.json

# Export results as JSON
python main.py run --config config/config_medium.json --output results.json

# Export results as CSV
python main.py run --config config/config_medium.json --output results.csv

# Run a built-in example
python main.py demo --example small
python main.py demo --example medium
python main.py demo --example large

# Override throughput for quick what-if analysis
python main.py demo --example medium --throughput 2000
```

---

## Output Description

The simulator prints:
1. **Workflow diagrams** – visual movement sequence for each AGV type
2. **Storage capacity** – rack positions and ground stacking positions
3. **Cycle time breakdown** – phase-by-phase timing for each workflow
4. **Fleet sizing results** – minimum vehicles needed per workflow
5. **Performance metrics** – throughput per hour, utilisation percentages

JSON export fields:
```json
{
  "rack_capacity": { "positions_per_shelf", "num_levels", "total_positions" },
  "stacking_capacity": { "rows", "columns", "levels", "total_positions" },
  "cycle_times_s": { "xpl201_handover", "xqe122_rack_avg", "xqe122_stack_avg" },
  "fleet_sizes": { "xpl201", "xqe122_rack", "xqe122_stacking", "total" }
}
```
