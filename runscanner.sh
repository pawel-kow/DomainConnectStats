#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e
# Treat pipe failures as errors
set -o pipefail

# --- Determine SCANFOLDER ---
# Check if a command-line argument is provided
if [ -n "$1" ]; then
    SCANFOLDER="$1"
    echo "Using SCANFOLDER from command-line argument: $SCANFOLDER" >&2
else
    # No command-line argument, check environment variable
    if [ -z "$SCANFOLDER" ]; then
        # Environment variable is also not set or is empty
        echo "Error: SCANFOLDER is not defined." >&2
        echo "Usage: $0 <scan_folder_name>" >&2
        echo "Alternatively, set the SCANFOLDER environment variable before running the script." >&2
        exit 1
    else
        # Environment variable is set, use it
        echo "Using SCANFOLDER from environment variable: $SCANFOLDER" >&2
    fi
fi

# --- Validation (Optional but recommended) ---
# Ensure SCANFOLDER is not empty after determination
if [ -z "$SCANFOLDER" ]; then
    echo "Error: SCANFOLDER resolved to an empty string. Aborting." >&2
    exit 1
fi

# --- Main Script Logic ---
OUTPUT_DIR="output/$SCANFOLDER"
LOGS_DIR="logs"
TIMESTAMP=$(date +%Y%m%d_%H%M)
LOG_FILE="$LOGS_DIR/log_${SCANFOLDER}_${TIMESTAMP}.log"

echo "Creating output directory: $OUTPUT_DIR" >&2
mkdir -p "$OUTPUT_DIR"

echo "Creating logs directory: $LOGS_DIR" >&2
mkdir -p "$LOGS_DIR"

echo "Starting scanner. Logging to: $LOG_FILE" >&2
# Run the python script, pipe stdout and stderr to tee, which writes to log and stdout
# The '-u' flag for python ensures unbuffered output, which is often better for logging pipes.
python -u ./scanner_cmd.py scan_zonefile --zone_file zonefiles/com.txt.gz --folder_prefix "$OUTPUT_DIR" 2>&1 | tee "$LOG_FILE"
# Note: 2>&1 redirects stderr to stdout before piping to tee, so both are captured.

echo "Script finished successfully for SCANFOLDER: $SCANFOLDER" >&2
exit 0
