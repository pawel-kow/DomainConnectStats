#!/bin/bash

# --- Determine PID_TO_MONITOR ---
# Check if a command-line argument is provided
if [ -n "$1" ]; then
    PID_TO_MONITOR="$1"
    echo "Using PID from command-line argument: $PID_TO_MONITOR" >&2
else
    # No command-line argument, check environment variable
    if [ -z "$PID_TO_MONITOR" ]; then
        # Environment variable is also not set or is empty
        echo "Error: PID_TO_MONITOR is not defined." >&2
        echo "Usage: $0 <pid>" >&2
        echo "Alternatively, set the PID_TO_MONITOR environment variable before running the script." >&2
        exit 1
    else
        # Environment variable is set, use it
        echo "Using PID_TO_MONITOR from environment variable: $PID_TO_MONITOR" >&2
    fi
fi

# --- Configuration ---
SLEEP_INTERVAL=1      # How often to check (in seconds)

# --- Initialization ---
max_fds=0 # Initialize the maximum count to 0

# --- Input Validation ---
# Check if the process directory exists
if [ ! -d "/proc/$PID_TO_MONITOR" ]; then
  echo "Error: Process with PID $PID_TO_MONITOR not found."
  exit 1
fi

# --- Main Loop ---
echo "Monitoring file descriptors for PID: $PID_TO_MONITOR"
echo "Press Ctrl+C to stop."

# Use 'trap' to ensure the cursor is shown again if the script is interrupted
trap 'tput cnorm; exit' INT TERM EXIT # Show cursor on exit/interrupt
tput civis # Hide cursor

while true; do
  # Get the current number of file descriptors
  # Use find instead of ls for potentially better handling of large numbers of files
  # and ensure we only count entries (handles potential errors if dir disappears)
  current_fds=$(find "/proc/$PID_TO_MONITOR/fd" -maxdepth 0 -type d -exec sh -c 'ls -1 "{}" | wc -l' \; 2>/dev/null || echo 0)

  # Check if the current count is greater than the max count
  if [[ "$current_fds" -gt "$max_fds" ]]; then
    max_fds=$current_fds # Update max_fds if current is greater
  fi

  # Clear the screen and move cursor to top-left
  clear
  # Alternatively, use tput cup 0 0 to move cursor without full clear
  # tput cup 0 0
  # tput ed # Clear from cursor to end of screen

  # Print the current and maximum counts
  echo "Monitoring PID: $PID_TO_MONITOR"
  echo "--------------------------"
  echo "Current Open FDs: $current_fds"
  echo "Maximum Open FDs: $max_fds"
  echo "--------------------------"
  echo "(Press Ctrl+C to stop)"


  # Wait for the specified interval
  sleep $SLEEP_INTERVAL
done

# This part is reached if the loop somehow exits, ensure cursor is visible
tput cnorm
