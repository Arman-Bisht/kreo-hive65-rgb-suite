@echo off
title Kreo Hive 65 - Screen Sync RGB
cd /d "%~dp0"

echo ====================================================
echo   Kreo Hive 65 - Real-Time Screen Sync RGB (Windows)
echo   [Accurate Color Mode: True Shades and Gradients]
echo ====================================================
echo.

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python from python.org and check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo Starting real-time screen sync with accurate shade matching...
echo  - Saturation: 1.0 (No artificial color blowout)
echo  - Gamma: 0.65 (True LED dynamic range for dark/light shades)
echo  - Blur: 0.5 (Clear color separation between keys)
echo.
echo Keep this window open while playing games or watching videos.
echo (To stop, close this window or press Ctrl+C)
echo.

python keyboardrgb.py screen --fps 30 --saturation 1.0 --gain 1.0 --gamma 0.65 --blur 0.5 %*

if errorlevel 1 (
    echo.
    echo [INFO] Stopped.
    pause
)
