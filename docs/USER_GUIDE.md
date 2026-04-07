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

## Shuffle_Configuration (optional)

Activate a specialised dispatch/shuffle strategy via the optional
`Shuffle_Configuration` block.

### Alternating Buffer Column Strategy (`alternating_buffer_column_24h`)

Models a **24-hour aging constraint** (a pallet produced on a given day
cannot be shipped until at least 24 hours later) combined with an
**alternating buffer-column policy** that ensures one column is always free
to absorb new inbound stock.

**Layout assumption:** 12 rows × 11 columns × 3 levels (396 total slots).
One full production day = 10 columns × 12 × 3 = 360 pallets.
One column (36 slots) is kept empty as a rolling intra-day buffer.

**Day patterns (1-indexed):**

| Day | Buffer column (empty at start) | Outbound scan order | Inbound fill order |
|-----|--------------------------------|---------------------|--------------------|
| Odd  (1, 3, …) | 11 | 10 → 1  | 11 → 2  |
| Even (2, 4, …) | 1  | 2  → 11 | 1  → 10 |

**Outbound selection:** strict column scan – the robot picks the first
occupied slot (row 1 first) in the first eligible column.  A pallet is
eligible only if its age ≥ `min_age_hours_for_outbound`.

**Initial inventory:** at simulation start (hour 0), columns 1–10 are
pre-filled with pallets whose `put_time_hour = -min_age_hours_for_outbound`
so they are immediately eligible for outbound on Day 1.

```json
"Shuffle_Configuration": {
  "strategy": "alternating_buffer_column_24h",
  "min_age_hours_for_outbound": 24,
  "buffer_columns": 1,
  "num_days": 2
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `strategy` | string | – | Set to `"alternating_buffer_column_24h"` to activate |
| `min_age_hours_for_outbound` | float | `24.0` | Minimum pallet age in hours before outbound eligibility |
| `buffer_columns` | int | `1` | Number of buffer columns (informational; code uses 1) |
| `num_days` | int | `2` | Number of simulated days |

**Sample config:** `config/config_alternating_buffer_11x12x3.json`

```bash
python main.py run --config config/config_alternating_buffer_11x12x3.json
```

The console output will include an **ALTERNATING BUFFER COLUMN STRATEGY RESULTS**
section showing per-day inbound/outbound counts, the active column orders, and
any missed outbound retrievals.

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
