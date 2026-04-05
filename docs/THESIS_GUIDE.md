# Master's Thesis Guide: AGV Fleet Sizing Simulator

## Structure for Your Thesis

### Chapter 1: Introduction

- Warehouse AGV fleet sizing problem
- Research questions
- Contributions of this work

### Chapter 2: Literature Review

- AGV systems and classifications
- Fleet sizing methodologies
- AI in warehouse automation

### Chapter 3: AI-Driven Layout Understanding (NOVEL CONTRIBUTION)

- Traditional manual input methods vs. AI parsing
- Ollama integration architecture
- Few-shot prompting approach
- Validation against AGV constraints
- Limitations and future improvements

### Chapter 4: AGV Physics & Movement Models

- Backward-fork kinematics (critical for accurate modeling)
- XPL_201 handover workflow (ground-level fast movement)
- XQE_122 rack storage workflow (with lifting)
- XQE_122 ground stacking workflow (with level-based lifting)
- Turn calculations and maneuvering time
- Speed optimization (forward vs. reverse travel)

### Chapter 5: Fleet Sizing Algorithm

- Cycle time calculations per workflow
- Utilization metrics and target rates
- Bottleneck detection in aisles
- AGV type recommendation logic
- XNA narrow-aisle condition (< 2.5 m width)

### Chapter 6: Case Studies (3 Real-World Scenarios)

- Small warehouse (text-based parsing)
- Medium warehouse (hybrid approach)
- Large warehouse (real operational data)

### Chapter 7: Results & Analysis

- Fleet compositions per scenario
- Cost-benefit analysis
- Sensitivity analysis (throughput vs. fleet size)
- Performance forecasting

### Chapter 8: Conclusions & Future Work

---

## Key AGV Models

| Model    | Use Case                     | Aisle Width | Max Lift Height | Notes                         |
|----------|------------------------------|-------------|-----------------|-------------------------------|
| XQE_122  | Rack & ground stacking       | ≥ 2.84 m    | 4.5 m           | Backward-fork, reverse loaded |
| XPL_201  | Handover / ground transport  | ≥ 2.84 m    | 0.20 m          | Fast forward travel           |
| XNA_121  | Narrow-aisle rack            | ≥ 1.77 m    | 8.5 m           | Equal fwd/rev speeds          |
| XNA_151  | Narrow-aisle rack (heavy)    | ≥ 1.77 m    | 8.5 m           | Equal fwd/rev speeds          |

> **Important:** XNA models are only applicable when aisle width < 2.5 m. For standard aisles (≥ 2.5 m), use XQE_122 or XPL_201.

---

## Physics Modeling Summary

### Backward-Fork Kinematics

AGVs with a backward-facing fork travel:
- **Empty** → forward direction (faster: 1.0–1.5 m/s)
- **Loaded** → reverse direction (slower: 0.3 m/s for XQE/XPL)

This distinction is critical for accurate cycle time calculations.

### Cycle Time Formula

```
Cycle Time = travel_empty + travel_loaded + lift_up + lift_down + pickup + dropoff + turns
```

### Fleet Sizing Formula

```
Fleet Size = ceil( tasks_per_hour × cycle_time_seconds / 3600 / utilization_target )
```

---

## Running Case Studies

```bash
# Install dependencies
pip install -r requirements.txt

# Run all case studies
bash run_case_studies.sh

# Or run individually
python main.py simulate --layout config/case_study_small.json --throughput 30 --output output/case_study_1
python main.py simulate --layout config/case_study_medium.json --throughput 60 --output output/case_study_2
python main.py simulate --layout config/case_study_large.json --throughput 150 --output output/case_study_3
```

## Output Files

Each case study generates the following in its output directory:

| File                         | Description                                   |
|------------------------------|-----------------------------------------------|
| `warehouse_graph.png`        | Publication-ready layout graph (300 DPI)      |
| `fleet_comparison.png`       | Fleet size & utilization comparison charts    |
| `throughput_sensitivity.png` | Sensitivity analysis (throughput vs fleet)    |
| `aisle_heatmap.png`          | Aisle usage heatmap (when simulation runs)    |
| `fleet_sizing_report.pdf`    | Complete multi-page PDF report                |
| `fleet_sizing_results.json`  | Machine-readable results for further analysis |
