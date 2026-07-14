#!/bin/bash
set -e

echo "===== Smoke Test ====="
python3 scripts/run_benchmark.py --task verticals/smoke_test/task_001.json

echo ""
echo "===== Medical Diagnostic ====="
python3 scripts/run_benchmark.py --task verticals/medical_diagnostic/

echo ""
echo "===== E-commerce Trend Research ====="
python3 scripts/run_benchmark.py --task verticals/ecommerce_trend_research/

echo ""
echo "===== Hallucination Risk Report ====="
python3 scripts/report_hallucination_risk.py

echo ""
echo "===== Medical Safety Report ====="
python3 scripts/report_medical_safety.py

echo ""
echo "===== Framework Suitability Matrix ====="
python3 scripts/generate_suitability_matrix.py

echo ""
echo "Done. See results/framework_suitability_matrix.md"
