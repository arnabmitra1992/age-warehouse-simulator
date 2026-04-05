# AGV Workflow Documentation

## Overview
This simulator models three AGV workflows for EP Equipment vehicles.

## XPL_201 Handover Workflow
- Forward speed: 1.5 m/s (empty)
- Reverse speed: 0.3 m/s (loaded)
- Typical cycle: 180-200 seconds

## XQE_122 Rack Storage Workflow
- Forward speed: 1.0 m/s (head aisle)
- Reverse speed: 0.3 m/s (aisle, both empty and loaded)
- Lift speed: 0.2 m/s
- Euro pallet spacing: 950 mm
- Typical cycle: 300-350 seconds

## XQE_122 Ground Stacking Workflow
- Same travel speeds as rack storage
- Level-based lifting: level × 1200 mm + 200 mm clearance
- Typical cycle: 280-320 seconds

## XNA Narrow Aisle Constraint
XNA_121 and XNA_151 are ONLY compatible with aisles narrower than 2.5 m.
For wider aisles, use XQE_122 (rack) or XPL_201 (handover/ground).
