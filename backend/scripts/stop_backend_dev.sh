#!/usr/bin/env bash
# stop_backend_dev.sh
# Stops PID-file-managed services started by start_backend_dev.sh
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
PIDS_DIR="$REPO_ROOT/run"
LOG_DIR="$REPO_ROOT/logs"

if [ ! -d "$PIDS_DIR" ]; then
  echo "No run dir found at $PIDS_DIR. Nothing to stop.";
  exit 0
fi

stopped=""
for f in uvicorn.pid redis.pid; do
  pf="$PIDS_DIR/$f"
  if [ -f "$pf" ]; then
    pid=$(cat "$pf" 2>/dev/null || true)
    if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
      echo "Stopping $f (pid $pid)..."
      kill "$pid" || true
      sleep 1
      if ps -p "$pid" > /dev/null 2>&1; then
        echo "$pid still alive; sending SIGKILL..."
        kill -9 "$pid" || true
        sleep 0.5
      fi
      if ps -p "$pid" > /dev/null 2>&1; then
        echo "Failed to stop pid $pid for $f"
      else
        echo "$f (pid $pid) stopped"
        stopped="$stopped $f"
      fi
    else
      echo "No running process for $f (pid: ${pid:-none})"
    fi
    rm -f "$pf"
  else
    echo "PID file $pf not found"
  fi
done

# show remaining listeners
echo "\nRemaining listeners on 6379 and 8000:"
(lsof -iTCP:6379 -sTCP:LISTEN -Pn || true)
(lsof -iTCP:8000 -sTCP:LISTEN -Pn || true)

exit 0
