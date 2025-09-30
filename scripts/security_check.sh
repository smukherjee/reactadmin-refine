#!/usr/bin/env bash
set -euo pipefail

echo "Running bandit..."
bandit -r backend -x backend/tools -lll

echo "Running safety..."
safety check --full-report

echo "Security checks complete."
