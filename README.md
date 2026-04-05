# Age Warehouse AGV Simulator

A comprehensive, physics-based AGV (Automated Guided Vehicle) simulator for warehouse operations supporting **XQE_122** (Racking Robot) and **XPL_201** (Handover Robot).

## Quick Start

```bash
pip install -r requirements.txt
python main.py demo --example medium
```

## Features

- ✅ XPL_201 handover workflow (Inbound → Handover Zone)
- ✅ XQE_122 rack storage workflow (Inbound → Rack shelves with lifting)
- ✅ XQE_122 ground stacking workflow (Inbound → Floor stacking with level-based lifting)
- ✅ Physics-based cycle time calculations (speeds, directions, lifting)
- ✅ Fleet sizing with utilisation analysis for both vehicle types
- ✅ Detailed time breakdowns per workflow phase
- ✅ Storage capacity calculations (racks + ground stacking)
- ✅ JSON/CSV result export
- ✅ Example configurations: small, medium, large warehouse

## Documentation

See [docs/README.md](docs/README.md) for full documentation.
