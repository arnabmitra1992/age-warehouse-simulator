# Warehouse AGV Fleet Sizing Simulator – Academic Edition

## For Master's Thesis & Research

This simulator provides a production-ready platform for:

- ✅ AI-driven warehouse layout understanding
- ✅ Physics-accurate AGV movement modeling
- ✅ Fleet sizing optimization
- ✅ Publication-ready visualizations

---

## Quick Start for Research

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Parse Your Warehouse (AI-Driven)

```bash
python main.py parse --text "Your warehouse description here"
```

### 3. Run Case Studies

```bash
python main.py simulate --layout config/case_study_small.json  --throughput 30  --output output/case_study_1
python main.py simulate --layout config/case_study_medium.json --throughput 60  --output output/case_study_2
python main.py simulate --layout config/case_study_large.json  --throughput 150 --output output/case_study_3
```

Or run all at once:

```bash
bash run_case_studies.sh
```

### 4. Generate Reports

All outputs are written to the directory specified by `--output`:

| File                         | Description                                |
|------------------------------|--------------------------------------------|
| `warehouse_graph.png`        | Publication-ready layout graph (300 DPI)   |
| `fleet_comparison.png`       | Fleet size & utilization comparison        |
| `throughput_sensitivity.png` | Sensitivity analysis plot                  |
| `aisle_heatmap.png`          | Aisle usage heatmap (simulation mode)      |
| `fleet_sizing_report.pdf`    | Complete multi-page PDF for thesis figures |
| `fleet_sizing_results.json`  | Machine-readable JSON results              |

---

## Research Contributions

This work demonstrates:

1. **AI-powered warehouse automation** – Ollama integration with few-shot prompting
2. **Accurate AGV physics modeling** – backward-fork kinematics, turn times, lift profiles
3. **Workflow-specific cycle time calculations** – handover, rack storage, ground stacking
4. **Data-driven fleet sizing methodology** – utilization-based sizing with sensitivity analysis

---

## Simulator Architecture

```
Warehouse Layout (JSON / text / image)
        │
        ▼
 LayoutParser (Ollama AI)
        │
        ▼
 WarehouseGraph (NetworkX)
        │
        ├──▶ AGVPhysics (cycle time per workflow)
        │
        ├──▶ FleetSizingCalculator (utilization-based sizing)
        │
        ├──▶ SimulationEngine (discrete-time simulation)
        │
        └──▶ WarehouseVisualizer (300 DPI charts + PDF)
```

---

## AGV Model Reference

| Model    | Storage Types              | Min Aisle | Max Lift | Notes                                |
|----------|----------------------------|-----------|----------|--------------------------------------|
| XQE_122  | Rack, Ground Stacking      | 2.84 m    | 4.5 m    | Standard workhorse                   |
| XPL_201  | Ground Storage, Handover   | 2.84 m    | 0.20 m   | High-speed transport                 |
| XNA_121  | Narrow-aisle Rack          | 1.77 m    | 8.5 m    | Only for aisles < 2.5 m              |
| XNA_151  | Narrow-aisle Rack (heavy)  | 1.77 m    | 8.5 m    | Only for aisles < 2.5 m              |

---

## Citation

If you use this simulator in your thesis:

```bibtex
@mastersthesis{YourName2025,
  title  = {Intelligent Warehouse AGV Fleet Sizing Using AI Layout Understanding},
  author = {Your Name},
  school = {Your University},
  year   = {2025}
}
```

---

## See Also

- [`docs/THESIS_GUIDE.md`](THESIS_GUIDE.md) – Chapter-by-chapter thesis structure
- [`docs/THESIS_OUTLINE.md`](THESIS_OUTLINE.md) – Detailed outline with page estimates
- [`docs/COMPARISON_OLLAMA_VS_MANUAL.md`](COMPARISON_OLLAMA_VS_MANUAL.md) – AI vs manual configuration analysis
