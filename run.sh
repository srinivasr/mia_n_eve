#!/usr/bin/env bash
set -e

# Setup trap to kill background jobs when script exits
trap 'kill $(jobs -p) 2>/dev/null || true' SIGINT SIGTERM EXIT

echo "Starting mia_n_eve runtime..."

# Start python brain orchestrator (websocket server)
echo "Starting Brain Server..."
cd eve/eve_brain
source venv/bin/activate
python -m brain.server &
cd ../..

# Start python system info (http server)
echo "Starting System Info Server..."
cd eve/eve_brain
source venv/bin/activate
python system_info.py &
cd ../..

# Wait a second for servers to start
sleep 2

# Start Rust Backend / Tauri (which also starts Svelte frontend)
echo "Starting Tauri runtime and Svelte frontend..."
cd eve/backend_eve
cargo tauri dev
