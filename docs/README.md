# Warehouse AGV Simulator

A comprehensive, physics-based AGV (Automated Guided Vehicle) simulator for warehouse operations supporting **XQE_122** (Racking Robot) and **XPL_201** (Handover Robot).

## Features

- ✅ Full parameterisation – all inputs are user-configurable via JSON
- ✅ Physics-based cycle time calculations (speeds, directions, lifting)
- ✅ Three complete workflow types: Handover, Rack Storage, Ground Stacking
- ✅ Fleet sizing with utilisation analysis for both vehicle types
- ✅ Detailed time breakdowns per workflow phase
- ✅ Storage capacity calculations (racks + ground stacking)
- ✅ Export results to JSON or CSV
- ✅ Visual workflow diagrams (text-based)

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run with the medium example config
python main.py demo --example medium

# Run with your own config
python main.py run --config config/config_template.json

# Export results
python main.py run --config config/config_medium.json --output results.json
python main.py run --config config/config_medium.json --output results.csv
```

---

## Project Structure

```
age-warehouse-simulator/
├── main.py                     # CLI entry point
├── requirements.txt
├── src/
│   ├── agv_specs.py            # XQE_122 & XPL_201 specifications
│   ├── warehouse_layout.py     # Distance & dimension management
│   ├── rack_storage.py         # Rack position calculations
│   ├── ground_stacking.py      # Ground stacking calculations
│   ├── cycle_calculator.py     # Physics-based cycle time calculations
│   ├── fleet_sizer.py          # Fleet sizing for both vehicle types
│   ├── simulator.py            # Main orchestrator
│   └── visualizer.py           # Diagrams & text outputs
├── config/
│   ├── config_template.json    # Template with default values
│   ├── config_small.json       # Small warehouse (200 pallets/day)
│   ├── config_medium.json      # Medium warehouse (1000 pallets/day)
│   └── config_large.json       # Large warehouse (3000 pallets/day)
├── tests/
│   ├── test_calculations.py    # Cycle time calculation tests
│   ├── test_workflows.py       # Rack & stacking layout tests
│   └── test_fleet_sizing.py    # Fleet sizing & integration tests
└── docs/
    ├── README.md               # This file
    ├── WORKFLOWS.md            # Detailed workflow documentation
    ├── USER_GUIDE.md           # User configuration guide
    └── EXAMPLES.md             # Example scenarios
```

---

## AGV Specifications

### XQE_122 (Racking Robot)
| Parameter | Value |
|-----------|-------|
| Forward speed | 1.0 m/s |
| Reverse speed | 0.3 m/s |
| Lift speed | 0.2 m/s |
| Max lift height | 4,500 mm |
| Pickup time | 30 s |
| Dropoff time | 30 s |
| Fork type | Backward (reverse entry) |

### XPL_201 (Handover Robot)
| Parameter | Value |
|-----------|-------|
| Forward speed | 1.5 m/s |
| Reverse speed | 0.5 m/s |
| Pickup time | 30 s |
| Dropoff time | 30 s |
| Lift capability | None |

### Shared
- 90° turn time: 10 s (any direction)

---

## Running Tests

```bash
python -m pytest tests/ -v
```

---

## Configuration

See `config/config_template.json` for the full configuration schema.  
See `docs/USER_GUIDE.md` for detailed parameter descriptions.
