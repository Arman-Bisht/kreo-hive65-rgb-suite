Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = scriptDir

' Launch pythonw in background with accurate color settings
WshShell.Run "pythonw.exe """ & scriptDir & "\keyboardrgb.py"" screen --fps 30 --saturation 1.0 --gain 1.0 --gamma 0.65 --blur 0.5", 0, False

' Give a quick confirmation popup that disappears after 2 seconds
WshShell.Popup "Kreo Hive 65 Screen Sync is now running in the background with Accurate Color Mode!" & vbCrLf & vbCrLf & "To stop it, double-click stop_screen_sync.bat", 2, "Kreo Hive 65 Screen Sync", 64
