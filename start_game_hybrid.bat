@echo off
title Kreo Hive 65 - Hybrid Game Mode (Screen + Audio)
cd /d "%~dp0"

echo ====================================================
echo   Kreo Hive 65 - Hybrid Gaming Mode (Windows)
echo   [Visual Screen Mirror + Audio Explosion Shockwaves]
echo ====================================================
echo.

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    pause
    exit /b 1
)

echo Starting Hybrid Game Mode...
echo  - Base Lighting: Mirrors your in-game display colors
echo  - Audio Reactions: Gunshots, explosions, and bass kicks pulse & ripple across keys!
echo.
echo Launch any game (CS2, Valorant, Apex, GTA, Cyberpunk, etc.)!
echo Tip: For best results, set your game to "Borderless Fullscreen".
echo Press Ctrl+C in this window at any time to stop.
echo.

python keyboardrgb.py game --fps 30 --blur 0.5 --saturation 1.0 --gamma 0.65 --bass-punch 1.4 %*

if errorlevel 1 (
    echo.
    echo [INFO] Stopped.
    pause
)
