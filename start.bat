@echo off
REM GPU Monitor for AI Workloads — Launcher
cd /d "%~dp0"

REM Check if node_modules exists, install if needed
if not exist "node_modules\electron" (
    echo Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
)

REM Launch Electron
echo Starting GPU Monitor for AI Workloads...
start "" "node_modules\.bin\electron.cmd" . --disable-gpu
