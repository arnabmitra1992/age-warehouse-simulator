# Workflow Documentation

## Workflow 1: XPL_201 Handover Operation

XPL_201 brings pallets from the Inbound Buffer to the Handover Zone.

### Movement Pattern
```
Rest Area
  → (FORWARD, EMPTY)
    → Head Aisle (FORWARD, EMPTY)
      → Inbound Buffer (REVERSE, EMPTY – back in)
      → PICKUP (30s)
      → Inbound Buffer (FORWARD, LOADED – drive out)
      → Head Aisle (FORWARD, LOADED)
      → TURN 90°
      → Handover Zone (REVERSE, LOADED – back in)
      → DROPOFF (30s)
      → Head Aisle (FORWARD, EMPTY)
      → TURN 90°
      → Rest Area (REVERSE, EMPTY – back in to park)
```

### Cycle Time Formula
```
Time =
  dist(Rest → Head Aisle) / 1.5  [forward, empty]
  + dist(Head Aisle → Inbound) / 1.5  [forward, empty]
  + 1.5m / 0.5  [reverse into inbound]
  + 30s  [PICKUP]
  + 1.5m / 1.5  [forward out of inbound]
  + dist(Inbound → Head Aisle) / 1.5  [forward, loaded]
  + dist(Head Aisle → Handover) / 1.5  [forward, loaded]
  + 10s  [TURN 90°]
  + 1.5m / 0.5  [reverse into handover]
  + 30s  [DROPOFF]
  + 1.5m / 1.5  [forward out of handover]
  + 10s  [TURN 90°]
  + dist(Handover → Head Aisle) / 1.5  [forward, empty]
  + dist(Head Aisle → Rest) / 1.5  [forward, empty]
  + 1.5m / 0.5  [reverse into rest]
```

---

## Workflow 2: XQE_122 Rack Storage

XQE_122 picks from the Inbound Buffer and deposits at a random shelf position.

### Movement Pattern
```
Rest Area
  → (FORWARD, EMPTY)
    → Head Aisle (FORWARD, EMPTY)
      → Inbound Buffer (REVERSE, EMPTY – back in)
      → PICKUP (30s)
      → Inbound Buffer (FORWARD, LOADED – drive out)
      → Head Aisle (FORWARD, LOADED)
      → Rack Aisle Entry (FORWARD, LOADED)
      → Position N Centre (FORWARD, LOADED)
          → TURN 90° (toward rack)
          → REVERSE 1.5m (back up to shelf)
          → LIFT to shelf height
          → DROPOFF (30s)
          → LOWER forks
          → FORWARD 1.5m (drive away)
          → TURN 90° (back to aisle)
      → Rack Aisle Exit (FORWARD, EMPTY)
      → Head Aisle (FORWARD, EMPTY)
      → Rest Area (REVERSE, EMPTY – back in)
```

### Rack Position Formula
```
Positions per shelf = floor(Rack_Length / 950mm)
Distance to position N = N × 950mm/1000 − 475mm/1000  [m]
Distance from position N to exit = Rack_Length/1000 − distance_to_N  [m]

Note: total aisle traversal (entry→exit) = Rack_Length regardless of position
```

### Shelf Height Formula
```
Height at level L = L × Shelf_Height_Spacing_mm / 1000  [m]
Lift time = height_m / 0.2  [seconds]
```

---

## Workflow 3: XQE_122 Ground Stacking

XQE_122 picks from the Inbound Buffer and deposits at a row/column/level position.

### Movement Pattern
```
Rest Area
  → (FORWARD, EMPTY)
    → Head Aisle (FORWARD, EMPTY)
      → Inbound Buffer (REVERSE, EMPTY – back in)
      → PICKUP (30s)
      → Inbound Buffer (FORWARD, LOADED – drive out)
      → Head Aisle (FORWARD, LOADED)
      → Stacking Area Entry (FORWARD, LOADED)
      → Column C (FORWARD, lateral)
      → Row R (FORWARD, depth)
          → REVERSE (back into position)
          → LIFT to Level L
          → DROPOFF (30s)
          → LOWER forks
          → FORWARD (drive away)
      → Stacking Area Exit (FORWARD, EMPTY)
      → Head Aisle (FORWARD, EMPTY)
      → Rest Area (REVERSE, EMPTY – back in)
```

### Storage Layout Formulas
```
Effective slot width (mm):
  Fork_Entry = "Length": effective_width = Box_Width + 2 × clearance
  Fork_Entry = "Width":  effective_width = Box_Length + 2 × clearance

Effective slot depth (mm):
  Fork_Entry = "Length": effective_depth = Box_Length + 2 × clearance
  Fork_Entry = "Width":  effective_depth = Box_Width + 2 × clearance

Columns = floor((Area_Width − 2×clearance) / effective_width)
Rows    = floor((Area_Length − 2×clearance) / effective_depth)
Levels  = floor(4500 / Box_Height)

Column C distance = (C−1) × effective_width + effective_width/2 + clearance  [mm]
Row R distance    = (R−1) × effective_depth + effective_depth/2 + clearance  [mm]
Level L height    = L × Box_Height  [mm]
```

---

## Fleet Sizing Formula

```
Fleet_Size = ceil(
  (Daily_Pallets × Avg_Cycle_Time_s)
  / (Operating_Hours × 3600 × Utilization_Target)
)
```

Applied independently for each workflow / vehicle type.
