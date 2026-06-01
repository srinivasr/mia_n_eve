#!/usr/bin/env bash
set -e

# Setup trap to kill background jobs when script exits
trap 'kill $(jobs -p) 2>/dev/null || true' SIGINT SIGTERM EXIT

echo "Starting mia_n_eve runtime..."

# Kill lingering processes that might bind to our ports
echo "Cleaning up old processes..."
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 8765/tcp 2>/dev/null || true
fuser -k 8766/tcp 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || true

# 1. Setup Python Environment
echo "Checking Python environment..."
cd eve/eve_brain
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "Installing/Updating Python dependencies..."
pip install --upgrade pip
BLIS_ARCH=generic pip install blis
pip install "spacy<4.0.0" -e '.[stt,tts,llm,vision]'
cd ../..

# 2. Setup Node Environment
echo "Checking Node environment..."
cd eve/UI_eve
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi
# Ensure dist directory exists for Tauri macro
mkdir -p dist
cd ../..

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
