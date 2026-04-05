# User Guide

## Quick Start

```bash
pip install -r requirements.txt
python main.py run config/config_small.json
```

## Configuration Format (mm-based)

All distances use millimetres. See `config/config_template.json` for an example.

### Aisle Types
- `rack`: Rack storage (XQE_122)
- `ground_stacking`: Ground stacking (XQE_122)
- `handover`: Handover/dock operations (XPL_201)

## AGV Selection Rules
- Aisles < 2.5 m: XNA models only
- Rack aisles ≥ 2.84 m: XQE_122
- Handover aisles ≥ 2.6 m: XPL_201
- Ground stacking ≥ 2.84 m: XQE_122, ≥ 2.6 m: XPL_201
