#!/usr/bin/env bash
# start_backend_dev.sh
# Starts Redis (docker-compose or local) and the backend (uvicorn).
# Usage: ./scripts/start_backend_dev.sh [--run-tests] [--port PORT] [--redis docker|local]

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# The script lives in <repo>/backend/scripts. We want REPO_ROOT to be the
# repository root (project root), not the 'backend' package directory. Move
# two levels up from the scripts dir to reach the repo root.
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)

# Defaults
PORT=8000
RUN_TESTS=false
REDIS_MODE="local"
FORCE_RESTART=false
# Run in background and return control by default (use --foreground to block)
DETACH=true

# PID files directory
PIDS_DIR="$REPO_ROOT/backend/run"
LOG_DIR="$REPO_ROOT/backend/logs"
mkdir -p "$PIDS_DIR" "$LOG_DIR"

# Rotation: keep previous logs timestamped. Simple rotation: move existing to .TIMESTAMP
rotate_log() {
  local f="$1"
  if [ -f "$f" ] && [ -s "$f" ]; then
    local ts
    ts=$(date -u +%Y%m%d_%H%M%SZ)
    mv "$f" "${f}.${ts}"
  fi
}

function usage() {
  cat <<EOF
Usage: $0 [--run-tests] [--port PORT] [--redis docker|local]

Options:
  --run-tests        Run pytest after the server is ready (default: disabled)
  --port PORT        Port for the backend HTTP server (default: 8000)
  --redis MODE       How to start Redis: 'docker' (default) or 'local'
  -h, --help         Show this help
EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-tests)
      RUN_TESTS=true; shift;;
    --port)
      PORT="$2"; shift 2;;
    --redis)
      REDIS_MODE="$2"; shift 2;;
    --foreground|--no-detach)
      DETACH=false; shift;;
      --force-restart)
        FORCE_RESTART=true; shift;;
    -h|--help)
      usage;;
    *)
      echo "Unknown argument: $1"; usage;;
  esac
done

echo "Starting backend dev stack..."
echo "Repository: $REPO_ROOT"
echo "Backend port: $PORT"
echo "Redis mode: $REDIS_MODE"
echo "Run tests after ready: $RUN_TESTS"

DOCKER_REDIS_STARTED=false
LOCAL_REDIS_PID=
UVICORN_PID=

function start_redis_docker() {
  echo "Starting Redis via docker-compose..."
  (cd "$REPO_ROOT" && docker compose -f docker-compose.perf.yml up -d redis)
  DOCKER_REDIS_STARTED=true
}

function stop_redis_docker() {
  if [ "$DOCKER_REDIS_STARTED" = true ]; then
    echo "Stopping docker redis..."
    (cd "$REPO_ROOT" && docker compose -f docker-compose.perf.yml down --remove-orphans)
  fi
}

function start_redis_local() {
  if command -v redis-server >/dev/null 2>&1; then
    # check if port 6379 already in use
    if lsof -iTCP:6379 -sTCP:LISTEN -t >/dev/null 2>&1; then
      EXISTING_PID=$(lsof -iTCP:6379 -sTCP:LISTEN -t)
      echo "Redis already running on port 6379 (pid: $EXISTING_PID). Skipping start."
      echo "$EXISTING_PID" > "$PIDS_DIR/redis.pid"
      return 0
    fi
    echo "Starting local redis-server on 6379..."
    # Use a temporary config to avoid persistence; run under nohup so it survives the terminal
  rotate_log "$LOG_DIR/redis_dev.log"
  nohup redis-server --port 6379 --save "" --appendonly no >"$LOG_DIR/redis_dev.log" 2>&1 &
    LOCAL_REDIS_PID=$!
    # Give the server a moment to either start or fail binding
    sleep 0.2
    # If the started process died (exit) or port is already bound by another process,
    # prefer the existing listener PID so we don't leave a defunct pid reference.
    if ! kill -0 "$LOCAL_REDIS_PID" 2>/dev/null; then
      # find existing pid listening on 6379 (if any)
      EXISTING_PID=$(lsof -iTCP:6379 -sTCP:LISTEN -t 2>/dev/null || true)
      if [ -n "$EXISTING_PID" ]; then
        LOCAL_REDIS_PID=$EXISTING_PID
      else
        echo "Failed to start local redis-server (pid $LOCAL_REDIS_PID exited). Check $PIDS_DIR/redis_dev.log for details." >&2
      fi
    fi
  echo "$LOCAL_REDIS_PID" > "$PIDS_DIR/redis.pid"
    echo "Local redis pid: $LOCAL_REDIS_PID"
  else
    echo "redis-server not found. Please install Redis or use --redis docker." >&2
    exit 1
  fi
}

function stop_redis_local() {
  if [ -n "${LOCAL_REDIS_PID:-}" ]; then
    echo "Stopping local redis pid $LOCAL_REDIS_PID..."
    kill "$LOCAL_REDIS_PID" || true
  else
    if [ -f "$PIDS_DIR/redis.pid" ]; then
      pid=$(cat "$PIDS_DIR/redis.pid" 2>/dev/null || true)
      if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
        echo "Stopping redis pid $pid from pid file..."
        kill "$pid" || true
      fi
    fi
  fi
}

function start_uvicorn() {
  echo "Starting uvicorn on port $PORT..."
  # Prefer installed uvicorn command, else use python -m uvicorn
  # choose python executable
  # prefer a project venv if present
  # prefer a project venv if present (.venv or venv)
  if [ -x "$REPO_ROOT/backend/.venv/bin/python" ]; then
    PYTHON_CMD="$REPO_ROOT/backend/.venv/bin/python"
  elif [ -x "$REPO_ROOT/backend/venv/bin/python" ]; then
    PYTHON_CMD="$REPO_ROOT/backend/venv/bin/python"
  else
    PYTHON_CMD="$(command -v python3 || command -v python || true)"
  fi
  if [ -z "$PYTHON_CMD" ]; then
    echo "No python or python3 executable found in PATH" >&2
    exit 1
  fi

  # use nohup to survive terminal disconnect; prefer uvicorn CLI if available
  rotate_log "$LOG_DIR/uvicorn.log"
  if command -v uvicorn >/dev/null 2>&1; then
    nohup uvicorn backend.main:app --reload --host localhost --port "$PORT" >"$LOG_DIR/uvicorn.log" 2>&1 &
  else
    nohup "$PYTHON_CMD" -m uvicorn backend.main:app --reload --host localhost --port "$PORT" >"$LOG_DIR/uvicorn.log" 2>&1 &
  fi
  UVICORN_PID=$!
  echo "$UVICORN_PID" > "$PIDS_DIR/uvicorn.pid"
  echo "Uvicorn pid: $UVICORN_PID"
}

function stop_uvicorn() {
  if [ -n "${UVICORN_PID:-}" ]; then
    echo "Stopping uvicorn pid $UVICORN_PID..."
    kill "$UVICORN_PID" || true
  fi
}

function wait_for_ready() {
  local url="http://127.0.0.1:$PORT/"
  echo "Waiting for backend to be ready at $url"
  for i in {1..60}; do
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -E '200|404' >/dev/null; then
      echo "Backend ready"
      return 0
    fi
    sleep 0.5
  done
  echo "Backend did not become ready in time" >&2
  return 1
}

function run_tests() {
  echo "Running pytest..."
  (cd "$REPO_ROOT" && pytest -q)
}

function cleanup() {
  echo "Cleaning up..."
  stop_uvicorn
  stop_redis_local
  stop_redis_docker
}

# If running in foreground, install trap to cleanup on exit; if detaching, leave processes running
if [ "$DETACH" = false ]; then
  trap cleanup EXIT INT TERM
fi

if [ "$FORCE_RESTART" = true ]; then
  echo "Force restart requested: attempting to stop existing services first..."
  if [ -f "$PIDS_DIR/uvicorn.pid" ]; then
    pid=$(cat "$PIDS_DIR/uvicorn.pid" 2>/dev/null || true)
    if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
      kill "$pid" || true
      sleep 0.5
    fi
    rm -f "$PIDS_DIR/uvicorn.pid" || true
  fi
  if [ -f "$PIDS_DIR/redis.pid" ]; then
    pid=$(cat "$PIDS_DIR/redis.pid" 2>/dev/null || true)
    if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
      kill "$pid" || true
      sleep 0.5
    fi
    rm -f "$PIDS_DIR/redis.pid" || true
  fi
fi

if [ "$REDIS_MODE" = "docker" ]; then
  if command -v docker >/dev/null 2>&1 && command -v docker-compose >/dev/null 2>&1; then
    start_redis_docker
  elif command -v docker >/dev/null 2>&1; then
    # newer docker compose might be `docker compose` instead of docker-compose
    start_redis_docker || true
  else
    echo "Docker not available; falling back to local redis-server (if installed)"
    start_redis_local
  fi
else
  start_redis_local
fi

start_uvicorn

if ! wait_for_ready; then
  echo "Server failed to start; exiting" >&2
  exit 1
fi

if [ "$RUN_TESTS" = true ]; then
  run_tests
fi

if [ "$DETACH" = true ]; then
  echo "Started services in background. PID files in $PIDS_DIR"
  echo "redis pid: $(cat "$PIDS_DIR/redis.pid" 2>/dev/null || echo 'n/a')"
  echo "uvicorn pid: $(cat "$PIDS_DIR/uvicorn.pid" 2>/dev/null || echo 'n/a')"
  echo "To stop these processes run: kill \\$(cat $PIDS_DIR/uvicorn.pid) && kill \\$(cat $PIDS_DIR/redis.pid)"
  exit 0
else
  echo "Backend dev stack is running in foreground. To stop, press Ctrl-C." 
  # Wait indefinitely until signal
  while true; do sleep 3600; done
fi
