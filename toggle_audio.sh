#!/bin/bash

PYTHON_SCRIPT="/home/cryo/kbd-re/keyboardrgb.py"
PID_FILE="/tmp/my_script.pid"

if [ -f "$PID_FILE" ]; then
	PID=$(cat "$PID_FILE")

	if kill -0 "$PID" 2>/dev/null; then
		echo "Stopping script (PID $PID)..."
		kill "$PID"
		rm -f "$PID_FILE"
		exit 0
	else
		rm -f "$PID_FILE"
	fi
fi

echo "Starting script..."
# python3 "$PYTHON_SCRIPT" audio --shape bars --direction sides --gain 0.8 --smooth 2 --idle-gap 3 &
python3 "$PYTHON_SCRIPT" audio --shape wave --direction sides --color baff51 --smooth 1.7 --default breathe &
echo $! >"$PID_FILE"
