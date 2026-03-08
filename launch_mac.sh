#!/usr/bin/env bash
# Launch Stockflow backend (API) and frontend (dashboard) on macOS.
# Run from repo root: ./launch_mac.sh

set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT/backend"
DASHBOARD_DIR="$ROOT/dashboard"
UNR_SETUP_DIR="$ROOT/unr_setup"
LOG_PATH="$ROOT/debug-d56396.log"

if [[ ! -d "$BACKEND_DIR" ]]; then
  echo "Backend folder not found: $BACKEND_DIR"
  exit 1
fi
if [[ ! -d "$DASHBOARD_DIR" ]]; then
  echo "Dashboard folder not found: $DASHBOARD_DIR"
  exit 1
fi

# Kill backend when this script exits (including Ctrl+C)
BACKEND_PID=""
cleanup() {
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "Stopping backend (PID $BACKEND_PID)..."
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# Start backend in background
echo "Installing unr_setup and backend deps..."
export PYTHONPATH="$BACKEND_DIR:$UNR_SETUP_DIR"
export DEBUG_LOG="$LOG_PATH"
(
  cd "$BACKEND_DIR"
  python3 -m pip install -e "$UNR_SETUP_DIR" -q
  python3 -m pip install -e . -q
  echo "Starting UnR API on http://localhost:8000"
  exec python3 -m uvicorn server.app:app --reload --port 8000
) &
BACKEND_PID=$!

# Wait for backend to be reachable (up to 30 seconds)
echo "Waiting for backend..."
API_READY=false
for i in $(seq 1 15); do
  sleep 2
  if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/api/dates" 2>/dev/null | grep -q "200"; then
    API_READY=true
    echo "Backend is up."
    break
  fi
  echo "Waiting for backend... ($i/15)"
done

if [[ "$API_READY" != "true" ]]; then
  echo "Backend did not respond in time. Check errors above. Starting frontend anyway."
fi

# Start frontend in foreground (script stays in this process)
echo "Starting dashboard on http://localhost:5173"
cd "$DASHBOARD_DIR"
npm run dev
