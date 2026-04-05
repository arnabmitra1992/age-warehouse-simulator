# Examples

## Small Warehouse
```python
from src.simulator import WarehouseSimulator
sim = WarehouseSimulator.from_file("config/config_small.json")
result = sim.run()
```

## Custom Configuration
```python
from src.warehouse_layout import parse_config
from src.simulator import WarehouseSimulator

config_data = {
    "name": "My Warehouse",
    "width_mm": 40000,
    "length_mm": 60000,
    "head_aisle_width_mm": 4000,
    "inbound_docks": 2,
    "outbound_docks": 2,
    "aisles": [
        {"name": "SA1", "type": "rack", "width_mm": 2840, "depth_mm": 20000,
         "shelf_heights_mm": [0, 1200, 2400, 3600]}
    ],
    "throughput": {"pallets_per_day": 500, "operating_hours": 16},
    "utilization_target": 0.80
}
sim = WarehouseSimulator.from_dict(config_data)
result = sim.run()
```
