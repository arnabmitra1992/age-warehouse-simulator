#!/usr/bin/env bash
# Run all case studies
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

echo "=== Running Case Study: Small ==="
python main.py run config/case_study_small.json

echo "=== Running Case Study: Medium ==="
python main.py run config/case_study_medium.json

echo "=== Running Case Study: Large ==="
python main.py run config/case_study_large.json

echo "=== All case studies complete ==="
