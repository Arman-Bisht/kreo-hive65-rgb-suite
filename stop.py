import os
import subprocess
import sys

def main():
    try:
        ps_cmd = "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'keyboardrgb' } | ForEach-Object { $_.ProcessId }"
        out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_cmd], text=True)
        my_pid = os.getpid()
        pids = [int(p.strip()) for p in out.split() if p.strip().isdigit() and int(p.strip()) != my_pid]
        if not pids:
            print("No active Screen Sync process found.")
            return
        for pid in pids:
            print(f"Terminating PID {pid}...")
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        print("Screen sync successfully stopped.")
    except Exception as e:
        print(f"Error stopping process: {e}")

if __name__ == "__main__":
    main()
