@echo off
title Kreo Hive 65 - Web RGB Studio
cd /d "%~dp0"

echo ====================================================
echo   Kreo Hive 65 - Interactive WebGL RGB Studio
echo ====================================================
echo.

echo Starting WebSocket Bridge (port 8787)...
start /b python kbd_ws_server.py

echo Starting Web App...
cd client
start "" http://localhost:5173
npm run dev
