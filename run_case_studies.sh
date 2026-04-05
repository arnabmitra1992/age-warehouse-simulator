#!/bin/bash
# Run all three case studies and generate thesis-ready outputs

set -e

echo "======================================================"
echo "  Warehouse AGV Fleet Sizing – Case Study Runner"
echo "======================================================"
echo ""

echo "Running Case Study 1: Small Warehouse (30 tasks/hour)"
python main.py simulate \
    --layout config/case_study_small.json \
    --throughput 30 \
    --output output/case_study_1
echo ""

echo "Running Case Study 2: Medium Warehouse (60 tasks/hour)"
python main.py simulate \
    --layout config/case_study_medium.json \
    --throughput 60 \
    --output output/case_study_2
echo ""

echo "Running Case Study 3: Large Warehouse (150 tasks/hour)"
python main.py simulate \
    --layout config/case_study_large.json \
    --throughput 150 \
    --output output/case_study_3
echo ""

echo "======================================================"
echo "  All case studies complete!"
echo "======================================================"
echo ""
echo "Outputs:"
echo "  output/case_study_1/  –  Small Warehouse"
echo "  output/case_study_2/  –  Medium Warehouse"
echo "  output/case_study_3/  –  Large Warehouse"
echo ""
echo "Each directory contains:"
echo "  warehouse_graph.png        – Publication-ready layout graph"
echo "  fleet_comparison.png       – Fleet size & utilization charts"
echo "  throughput_sensitivity.png – Sensitivity analysis"
echo "  fleet_sizing_report.pdf    – Complete multi-page PDF report"
echo "  fleet_sizing_results.json  – Machine-readable results"
