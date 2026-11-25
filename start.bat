@echo off
echo ============================================================
echo   VisionTrack — Object Movement Detection & Tracking
echo ============================================================
echo.

REM ── Check Python ──────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.9+ and try again.
    pause & exit /b 1
)

REM ── Create venv if missing ─────────────────────────────────────
if not exist "venv\" (
    echo [1/4] Creating virtual environment...
    python -m venv venv
)

REM ── Activate venv ─────────────────────────────────────────────
echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

REM ── Install dependencies ───────────────────────────────────────
echo [3/4] Installing dependencies (first run may take a while)...
pip install -r requirements.txt --quiet

REM ── Set env vars for cache dirs ────────────────────────────────
set MPLCONFIGDIR=%TEMP%\matplotlib_cfg
set YOLO_CONFIG_DIR=%TEMP%\ultralytics_cfg

REM ── Launch Flask ──────────────────────────────────────────────
echo [4/4] Starting Flask server...
echo.
echo  Open your browser at:  http://localhost:5000
echo  Press Ctrl+C to stop.
echo.
cd backend
python app.py
