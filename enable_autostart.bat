@echo off
setlocal
cd /d "%~dp0"
title Enable Kreo Hive 65 Auto-Start on Windows Boot

echo Setting up Auto-Start on Windows boot...

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; " ^
  "$shortcutPath = [System.IO.Path]::Combine($env:APPDATA, 'Microsoft\Windows\Start Menu\Programs\Startup\KreoHive65ScreenSync.lnk'); " ^
  "$targetScript = [System.IO.Path]::Combine((Get-Location).Path, 'start_silent.vbs'); " ^
  "$s = $ws.CreateShortcut($shortcutPath); " ^
  "$s.TargetPath = 'wscript.exe'; " ^
  "$s.Arguments = '\"' + $targetScript + '\"'; " ^
  "$s.WorkingDirectory = (Get-Location).Path; " ^
  "$s.Save()"

if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] Auto-start on boot is now ENABLED!
    echo Kreo Hive 65 Screen Sync will start automatically whenever Windows turns on.
    echo.
    echo Starting Screen Sync right now in the background...
    wscript.exe "%~dp0start_silent.vbs"
    echo.
    echo Done! To stop it at any time, run stop_screen_sync.bat.
) else (
    echo [ERROR] Failed to set up auto-start.
)

echo.
pause
