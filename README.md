# Age Warehouse AGV Simulator

A comprehensive, physics-based AGV (Automated Guided Vehicle) simulator for warehouse operations supporting **XQE_122** (Racking Robot) and **XPL_201** (Handover Robot).

## Quick Start

```bash
pip install -r requirements.txt
python main.py demo --example medium
✨ Features

✅ XPL_201 handover workflow (Inbound → Handover Zone)
✅ XQE_122 rack storage workflow (Inbound → Rack shelves with lifting)
✅ XQE_122 ground stacking workflow (Inbound → Floor stacking with level-based lifting)
✅ Physics-based cycle time calculations (speeds, directions, lifting)
✅ Fleet sizing with utilisation analysis for both vehicle types
✅ Detailed time breakdowns per workflow phase
✅ Storage capacity calculations (racks + ground stacking)
✅ JSON/CSV result export
✅ Example configurations: small, medium, large warehouse
✅ Warehouse layout understanding via JSON config
✅ Publication-quality visualizations
✅ PDF thesis-ready reports
🤖 AGV Specifications

Model	Forward (m/s)	Reverse (m/s)	Lift (m/s)	Capacity (kg)	Aisle Width (m)	Max Height (m)
XQE_122	1.0	0.3	0.2	1200	2.84	4.5
XPL_201	1.5	0.5	—	2000	2.60	0.20
XNA_121	1.0	1.0	0.2	1200	1.77	8.5
XNA_151	1.0	1.0	0.2	1500	1.77	13.0
📐 Physics Model

AGV Travel Logic

All AGV models carry pallets with the fork at the rear:

Empty travel → forward speed (faster)
Loaded travel → reverse speed (slower, fork engaged)
Fleet Sizing Formula
tasks_per_agv_hr = 3600 / cycle_time_s
fleet_size       = ceil(tasks_per_hour / (tasks_per_agv_hr × utilization_target))
🚀 Usage
# Run demo
python main.py demo --example medium

# Run with custom config
python main.py run --config config/my_warehouse.json

# Export results
python main.py run --config config/medium.json --output results/
📁 Project Structure
├── main.py                        # CLI entry point
├── requirements.txt               # Dependencies
├── src/
│   ├── agv_specs.py               # AGV specifications
│   ├── warehouse_layout.py         # JSON config loader
│   ├── rack_storage.py             # Rack storage cycles
│   ├── ground_stacking.py          # Ground stacking cycles
│   ├── cycle_calculator.py         # Physics engine
│   ├── fleet_sizer.py              # Fleet sizing
│   ├── simulator.py                # Main orchestrator
│   └── visualizer.py               # Visualizations & reports
├── config/
│   ├── config_template.json
│   ├── config_small.json
│   ├── config_medium.json
│   └── config_large.json
├── docs/
│   ├── WORKFLOWS.md
│   ├── USER_GUIDE.md
│   └── EXAMPLES.md
└── tests/
    ├── test_calculations.py
    ├── test_workflows.py
    ├── test_fleet_sizing.py
    └── test_integration.py
 Tests
 python -m pytest tests/ -v
 📝 Warehouse Layout JSON Format

See config/config_template.json for complete schema.
Documentation

See docs/USER_GUIDE.md for full documentation.

Built for EP Equipment AGV fleet optimization – Master Thesis Project