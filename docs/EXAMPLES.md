# Example Scenarios

## Small Warehouse (200 pallets/day)

**Config:** `config/config_small.json`

| Parameter | Value |
|-----------|-------|
| Daily pallets | 200 |
| Operating hours | 8h |
| Distances (Rest→Inbound) | 3,000 mm |
| Rack length | 10,000 mm |
| Stacking area | 8,000 × 5,000 mm |

**Run:**
```bash
python main.py demo --example small
```

---

## Medium Warehouse (1000 pallets/day)

**Config:** `config/config_medium.json`

| Parameter | Value |
|-----------|-------|
| Daily pallets | 1,000 |
| Operating hours | 16h |
| Distances (Rest→Inbound) | 5,000 mm |
| Rack length | 20,000 mm |
| Stacking area | 15,000 × 10,000 mm |

**Run:**
```bash
python main.py demo --example medium
```

**Expected results (approximate):**
- Rack positions: 21 per shelf × 3 levels = 63 total
- Stacking positions: 9 rows × 8 cols × 4 levels = 288 total
- XPL_201 fleet: 1 vehicle
- XQE_122 fleet: 2 rack + 1 stacking = 3 vehicles
- Total fleet: 4 vehicles

---

## Large Warehouse (3000 pallets/day)

**Config:** `config/config_large.json`

| Parameter | Value |
|-----------|-------|
| Daily pallets | 3,000 |
| Operating hours | 20h |
| Distances (Rest→Inbound) | 8,000 mm |
| Rack length | 40,000 mm |
| Stacking area | 30,000 × 20,000 mm |

**Run:**
```bash
python main.py demo --example large
```

---

## What-If Analysis

Override throughput without editing config files:

```bash
# How many vehicles for 500 pallets/day?
python main.py demo --example medium --throughput 500

# How many vehicles for 5000 pallets/day?
python main.py demo --example large --throughput 5000
```

---

## Custom Configuration

Copy the template and modify:

```bash
cp config/config_template.json config/my_warehouse.json
# Edit my_warehouse.json with your warehouse parameters
python main.py run --config config/my_warehouse.json --output my_results.json
```
