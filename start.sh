#!/usr/bin/env bash
set -e
echo "======================================================"
echo "  VisionTrack — Object Movement Detection & Tracking"
echo "======================================================"

# Create venv if missing
if [ ! -d "venv" ]; then
    echo "[1/4] Creating virtual environment..."
    python3 -m venv venv
fi

# Activate
echo "[2/4] Activating virtual environment..."
source venv/bin/activate

# Install
echo "[3/4] Installing dependencies..."
pip install -r requirements.txt --quiet

# Launch
echo "[4/4] Starting Flask server..."
echo ""
echo "  Open your browser at:  http://localhost:5000"
echo "  Press Ctrl+C to stop."
echo ""
cd backend
python app.py
