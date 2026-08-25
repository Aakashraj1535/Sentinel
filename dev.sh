#!/bin/bash
# dev.sh -- starts BOTH the backend (FastAPI/uvicorn) and frontend (Vite)
# with one command, instead of two separate terminals.
#
# Usage (from the project root):
#   ./dev.sh
#
# Ctrl+C stops both cleanly. Backend logs go to backend.log (in the
# project root) rather than mixing into the terminal with the frontend's
# logs -- run `tail -f backend.log` in another terminal if you need to
# watch backend output live (e.g. Ollama call errors, SQL errors).

set -e
cd "$(dirname "$0")"

if [ ! -d "backend/venv" ]; then
    echo "No venv found at backend/venv -- create it first:"
    echo "  cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

echo "Starting backend (uvicorn) in the background..."
(
  cd backend
  source venv/bin/activate
  uvicorn app.main:app --reload --port 8080
) > backend.log 2>&1 &
BACKEND_PID=$!

cleanup() {
    echo ""
    echo "Stopping backend (PID $BACKEND_PID)..."
    kill "$BACKEND_PID" 2>/dev/null
    wait "$BACKEND_PID" 2>/dev/null
}
trap cleanup EXIT INT TERM

# Give uvicorn a moment to either come up or fail fast, and surface an
# early error instead of silently continuing to start the frontend
# against a dead backend.
sleep 2
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "Backend failed to start -- check backend.log:"
    echo "---"
    tail -20 backend.log
    echo "---"
    exit 1
fi

echo "Backend running (PID $BACKEND_PID) on http://localhost:8080 -- logs: backend.log"
echo "Starting frontend (Vite)..."
echo ""

npm run dev
