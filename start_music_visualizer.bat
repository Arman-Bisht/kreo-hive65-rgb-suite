@echo off
title Kreo Hive 65 - Music Audio Visualizer
cd /d "%~dp0"

echo ====================================================
echo   Kreo Hive 65 - Real-Time Music Visualizer (Windows)
echo ====================================================
echo.

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    pause
    exit /b 1
)

echo.
echo Pick an audio visualizer effect:
echo   [1] Vortex (Black Hole with Spinning Color Accretion Ring) - DEFAULT
echo   [2] Bars (Classic Equalizer Spectrum)
echo   [3] Flow (Bass Waterfall - Punch travels left to right)
echo   [4] Ripple (Concentric Rings breathing to the beat)
echo   [5] Split (Bass on Left, Treble on Right)
echo.
set /p choice="Enter choice (1-5, press Enter for 1): "

if "%choice%"=="2" (
    set "EFFECT=bars"
) else if "%choice%"=="3" (
    set "EFFECT=flow"
) else if "%choice%"=="4" (
    set "EFFECT=ripple"
) else if "%choice%"=="5" (
    set "EFFECT=split"
) else (
    set "EFFECT=vortex"
)

echo.
echo Starting Music Visualizer (%EFFECT%)...
echo Play music on Spotify, YouTube, or any game!
echo When music is paused, keyboard smoothly crossfades to ambient gradient.
echo Press Ctrl+C in this window at any time to stop.
echo.

python keyboardrgb.py audio --effect %EFFECT% --gain 1.2 --smooth 1.0 %*

if errorlevel 1 (
    echo.
    echo [INFO] Stopped.
    pause
)
