#!/usr/bin/env bash
# Run test + type checks and print a concise summary.
# Usage: ./scripts/run_checks.sh

set -u

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR" || exit 1

# Run pytest inside backend
echo "--- pytest ---"
cd backend || exit 1
pytest -q
PYTEST_EXIT=$?
cd "$ROOT_DIR" || exit 1

# Run pyright
echo "--- pyright ---"
pyright backend
PYRIGHT_EXIT=$?

# Run mypy
echo "--- mypy ---"
mypy backend
MYPY_EXIT=$?

# Summary
echo
echo "SUMMARY: pytest=$PYTEST_EXIT, pyright=$PYRIGHT_EXIT, mypy=$MYPY_EXIT"

# Exit non-zero if any failed
if [ "$PYTEST_EXIT" -ne 0 ] || [ "$PYRIGHT_EXIT" -ne 0 ] || [ "$MYPY_EXIT" -ne 0 ]; then
  exit 1
fi

exit 0
