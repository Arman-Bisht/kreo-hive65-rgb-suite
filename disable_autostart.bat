@echo off
setlocal
title Disable Kreo Hive 65 Auto-Start

set "SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\KreoHive65ScreenSync.lnk"

if exist "%SHORTCUT%" (
    del /f /q "%SHORTCUT%"
    echo [SUCCESS] Auto-start on boot has been disabled.
) else (
    echo [INFO] Auto-start is not currently enabled.
)

echo.
pause
