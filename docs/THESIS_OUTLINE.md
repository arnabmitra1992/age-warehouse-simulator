# Complete Thesis Outline with Simulator Integration

## 1. Introduction (2–3 pages)

- **Problem statement**: Manual warehouse layout understanding is time-consuming and error-prone
- **Solution**: AI-driven automated layout parsing using Ollama
- **Contributions**:
  - Novel Ollama integration with few-shot prompting for warehouse layout extraction
  - Accurate AGV physics modeling (backward-fork kinematics)
  - Validated fleet sizing methodology with sensitivity analysis

## 2. Literature Review (5–7 pages)

- AGV systems and classifications (pallet movers, narrow-aisle, forklift)
- Traditional fleet sizing methods (analytical, simulation-based)
- AI/ML in warehouse automation – recent advances
- Use `config/case_study_*` comparisons to benchmark against industry standards
- Reference simulator results in tables

## 3. Methodology (4–5 pages)

### 3.1 AI Layout Parsing

- How Ollama parses warehouse descriptions via few-shot prompting
- JSON schema extraction and validation
- Error handling and fallback strategies

### 3.2 Graph-Based Warehouse Model

- Node types: dock, head aisle point, aisle entry/exit, storage position
- Edge weights: travel distances and AGV compatibility constraints

### 3.3 AGV Physics Modeling

- Backward-fork kinematics: empty (forward) vs. loaded (reverse) travel
- Lift time model: `height / 0.2 m/s`
- Turn time: 10 s per 90° turn
- XNA narrow-aisle condition: only applicable when aisle width < 2.5 m

### 3.4 Fleet Sizing Algorithm

- Cycle time per workflow type
- Fleet size formula: `ceil(tasks/hr × cycle_s / 3600 / utilization)`
- Utilization targets and sensitivity analysis

## 4. Case Studies (8–10 pages)

### 4.1 Case Study 1: Small Warehouse

- Configuration: `config/case_study_small.json`
- Throughput target: 30 tasks/hour
- Output: `output/case_study_1/`
- Analysis: basic fleet sizing with limited complexity

### 4.2 Case Study 2: Medium Warehouse

- Configuration: `config/case_study_medium.json`
- Throughput target: 60 tasks/hour
- Output: `output/case_study_2/`
- Analysis: multi-aisle coordination and mixed AGV types

### 4.3 Case Study 3: Large Warehouse

- Configuration: `config/case_study_large.json`
- Throughput target: 150 tasks/hour
- Output: `output/case_study_3/`
- Analysis: bottleneck detection and aisle congestion modeling

### 4.4 Comparative Analysis

- Fleet compositions across scenarios (use `fleet_comparison.png`)
- Throughput sensitivity (use `throughput_sensitivity.png`)
- Cost-benefit discussion

## 5. Results (5–7 pages)

- Fleet composition tables (from `fleet_sizing_results.json`)
- Cycle time breakdowns (from PDF reports)
- Sensitivity analysis plots (`throughput_sensitivity.png`)
- Aisle usage heatmaps (`aisle_heatmap.png`)
- Recommendation rationale

## 6. Discussion (3–5 pages)

- Implications for warehouse design and automation investment
- Accuracy of AI parsing vs. manual JSON configuration (see `COMPARISON_OLLAMA_VS_MANUAL.md`)
- Limitations: Ollama availability, 2D model vs. 3D reality, single-AGV-type-per-aisle assumption
- Threats to validity

## 7. Conclusion (1–2 pages)

- Summary of contributions
- Practical recommendations
- Future work: real-time re-routing, multi-AGV collision avoidance, 3D layouts

## Appendices

- **A**: Simulator User Guide (see `README.md`)
- **B**: JSON Configuration Schema
- **C**: AGV Specification Details (see `src/agv_specs.py`)
- **D**: Sample Output Reports (include PDF from one case study)
