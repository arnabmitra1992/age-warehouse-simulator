# Warehouse AGV Fleet Sizing Simulator

A comprehensive Python simulation system for EP Equipment AGV fleet sizing, warehouse layout understanding (via Ollama AI), and realistic physics-based task time calculation.

Built for **master thesis research** – produces publication-quality charts, PDF reports, and detailed fleet sizing recommendations.

---

## ✨ Features

| Component | Description |
|-----------|-------------|
| **AI Layout Parser** | Ollama integration with 3-example Few-Shot prompting. Extracts structured JSON from text descriptions or images. |
| **AGV Physics** | Accurate backward-fork travel model: loaded = reverse speed, empty = forward speed. Counts 90° turns (10 s each). |
| **Graph Generator** | NetworkX directed graph with node types (dock, aisle entry, storage position) and edge attributes (distance, direction, turns). |
| **Simulation Engine** | Discrete-time concurrent task simulation with congestion modelling and aisle blocking. |
| **Fleet Sizing** | Analytical formula + simulation validation. Compares all AGV types, identifies bottlenecks, recommends optimal mix. |
| **Visualizations** | Warehouse layout graph, fleet comparison charts, cycle time breakdowns, aisle heatmaps, throughput sensitivity. |
| **PDF Reports** | Multi-page thesis-ready PDF with all charts. |

---

## 🤖 AGV Specifications

| Model | Fwd (m/s) | Rev (m/s) | Lift (m/s) | Capacity (kg) | Aisle (m) | Max Height (m) | Turn Radius |
|-------|-----------|-----------|------------|---------------|-----------|----------------|-------------|
| XQE_122 | 1.0 | 0.3 | 0.2 | 1200 | 2.84 | 4.5 | — |
| XPL_201 | 1.5 | 0.3 | — | 2000 | 2.60 | 0.20 | — |
| XNA_121 | 1.0 | 1.0 | 0.2 | 1200 | 1.77 | 8.5 | 4.0 m |
| XNA_151 | 1.0 | 1.0 | 0.2 | 1500 | 1.77 | 13.0 | 4.0 m |

---

## 📐 Physics Model

### Key Rule: Fork is Backward-Facing
All AGV models carry pallets with the fork at the **rear**. This means:
- **Empty travel** → forward speed (faster)
- **Loaded travel** → reverse speed (slower, fork engaged)
- XNA models are special: forward = reverse = 1.0 m/s

### Travel Time Formula

**Rack Storage:**
```
cycle_time = d_head_aisle / forward_speed
           + 2 × d_aisle / reverse_speed      ← into aisle (empty) + out (loaded)
           + 2 × lift_height / 0.2            ← lift up + lower down
           + pickup_time (30s) + dropoff_time (30s)
           + num_turns × 10s
```

**Ground Storage:**
```
cycle_time = d_head_aisle / forward_speed
           + 2 × d_aisle / reverse_speed      ← both legs reverse (fork first)
           + pickup_time (30s) + dropoff_time (30s)
           + dock_positioning_time (10s)
           + num_turns × 10s
```

### Fleet Sizing Formula
```
tasks_per_agv_hr = 3600 / cycle_time_s
fleet_size       = ceil(tasks_per_hour / (tasks_per_agv_hr × utilization_target))
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Demo (No Setup Required)

```bash
# Medium warehouse demo (4 aisles, mixed storage types)
python main.py demo

# Simple warehouse, restrict to one AGV type
python main.py demo --example simple --agv XQE_122 --throughput 20

# Complex warehouse at higher throughput
python main.py demo --example complex --throughput 50
```

### 3. Parse Your Warehouse Layout (with Ollama)

```bash
# Install and start Ollama first:
# 1. Download from https://ollama.ai
# 2. Run: ollama serve
# 3. Pull model: ollama pull llama3.2

# Parse from text description
python main.py parse --text "My warehouse is 60m wide and 80m long with one head aisle and 3 storage aisles."

# Parse from image (requires vision-capable model like llava)
python main.py parse --image /path/to/warehouse_sketch.png --model llava

# Manual interactive configuration
python main.py parse --manual --output-layout my_warehouse.json
```

### 4. Run Fleet Sizing on Your Layout

```bash
python main.py simulate --layout my_warehouse.json --throughput 40
python main.py simulate --layout examples/medium_warehouse.json --throughput 30 --agv XNA_121
```

### 5. Interactive Mode

```bash
python main.py interactive
```

---

## 📁 Project Structure

```
├── main.py                        # CLI entry point
├── requirements.txt               # Python dependencies
├── src/
│   ├── agv_specs.py               # AGV constants & validation helpers
│   ├── reference_layouts.py       # 3 reference warehouse layouts (few-shot)
│   ├── layout_parser.py           # Ollama AI parser + manual builder
│   ├── graph_generator.py         # NetworkX warehouse graph builder
│   ├── physics.py                 # Realistic AGV cycle time calculations
│   ├── simulation_engine.py       # Concurrent task simulation + congestion
│   ├── fleet_sizing.py            # Fleet sizing calculator & aisle analysis
│   └── visualization.py           # Charts, heatmaps, PDF reports
├── examples/
│   ├── simple_warehouse.json      # 2 rack aisles, 2 docks
│   ├── medium_warehouse.json      # 4 mixed aisles, 4 docks
│   └── complex_warehouse.json     # 6 aisles, 2 head aisles, 6 docks
└── tests/
    └── test_simulation.py         # 62 unit tests
```

---

## 📊 Output Files

All outputs are saved to the `output/` directory (or `--output <dir>`):

| File | Description |
|------|-------------|
| `warehouse_graph.png` | NetworkX graph of warehouse layout |
| `fleet_comparison.png` | Fleet size & utilization bar charts |
| `throughput_sensitivity.png` | Fleet size vs. throughput curves |
| `aisle_heatmap.png` | Aisle usage frequency heatmap |
| `fleet_sizing_report.pdf` | Multi-page thesis-ready PDF |
| `fleet_sizing_results.json` | Machine-readable results |

---

## 🧪 Tests

```bash
python -m pytest tests/test_simulation.py -v
# 62 tests covering AGV specs, physics, graph, fleet sizing, simulation
```

---

## 📝 Warehouse Layout JSON Format

```json
{
  "warehouse": {"name": "My Warehouse", "width": 60.0, "length": 80.0},
  "inbound_docks": [
    {"name": "IB1", "position": {"x": 0.0, "y": 6.0}, "count": 2}
  ],
  "outbound_docks": [
    {"name": "OB1", "position": {"x": 60.0, "y": 6.0}, "count": 2}
  ],
  "head_aisles": [
    {
      "name": "HA1",
      "start": {"x": 0.0, "y": 6.0},
      "end": {"x": 60.0, "y": 6.0},
      "width": 4.5,
      "connections": ["SA1", "SA2"]
    }
  ],
  "storage_aisles": [
    {
      "name": "SA1",
      "start": {"x": 15.0, "y": 6.0},
      "end": {"x": 15.0, "y": 66.0},
      "width": 2.84,
      "depth": 60.0,
      "entry_type": "dead-end",
      "storage_type": "rack",
      "head_aisle": "HA1",
      "racks": [
        {"side": "left",  "positions": 15, "height": 4.5, "levels": 3},
        {"side": "right", "positions": 15, "height": 4.5, "levels": 3}
      ]
    }
  ],
  "ground_storage_zones": [],
  "ground_stacking_zones": []
}
```

`storage_type`: `"rack"` | `"ground_storage"` | `"ground_stacking"`
`entry_type`: `"dead-end"` | `"through"`

---

## 🔧 Technical Stack

- **Python 3.8+**
- **Ollama** – Local LLM for layout parsing (free, offline)
- **NetworkX** – Warehouse graph representation and pathfinding
- **Matplotlib** – All charts and PDF reports
- **NumPy / Pandas** – Numerical operations
- **pytest** – Unit testing

---

## 💡 Tips for Best Results with Ollama

1. Use a capable model: `llama3.2` or `mistral` for text, `llava` for images
2. Be specific in your description: include dimensions, number of aisles, storage types
3. Reference the example layouts in `examples/` for the expected JSON format
4. Use `--manual` mode for precise control over the configuration

---

*Built for EP Equipment AGV fleet optimization – Master Thesis Project*
