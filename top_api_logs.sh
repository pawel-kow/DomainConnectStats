#!/bin/bash

# --- Configuration ---
LOG_FILE="$1"
REFRESH_INTERVAL=15 # seconds
TOP_N=20

# --- Input Validation ---
if [[ -z "$LOG_FILE" ]]; then
  echo "Usage: $0 <log_file_path>"
  exit 1
fi

if [[ ! -r "$LOG_FILE" ]]; then
  echo "Error: Log file '$LOG_FILE' not found or not readable."
  exit 1
fi

echo "Monitoring log file: $LOG_FILE"
echo "Refreshing every $REFRESH_INTERVAL seconds. Press Ctrl+C to stop."
sleep 2

# --- Main Loop ---
while true; do
  # Use an associative array to store the latest entry for each URL/key
  # Keys: URL or "None: Reason"
  # Values: "absolute_count (percentage%)"
  declare -A latest_stats

  # Process the log file efficiently to populate the array
  # sed extracts 'key|value', the loop reads it and updates the array
  # This ensures only the *last* occurrence of each key is stored in the array
  while IFS='|' read -r key value; do
      # Basic check to avoid empty keys/values if sed fails unexpectedly
      # Trim leading/trailing whitespace from key just in case
      key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
      if [[ -n "$key" && -n "$value" ]]; then
          #echo $key $value
          latest_stats["$key"]="$value"
      fi
  # Regex Explanation:
  # ^\[.*\]      : Match the timestamp part '[ ... ]' at the start
  # [[:space:]]+ : Match one or more spaces after the timestamp
  # (.*)         : Capture group 1: The URL or "None: Reason" (greedy match up to the last colon)
  # :[[:space:]]+: Match the last colon followed by one or more spaces
  # ([0-9.]+ \(.*%\)) : Capture group 2: The absolute count (digits, maybe dot) followed by space and "(percentage%)"
  # $            : End of line
  # \1|\2        : Output: captured group 1, a pipe delimiter, captured group 2
  done < <(tail -2000 "$LOG_FILE" | sed -E 's/^\[.*\] (.*): ([0-9]+ \([0-9.]+%\))$/\1|\2/')

  # --- Prepare data for sorting ---
  sortable_output=""
  if [[ ${#latest_stats[@]} -gt 0 ]]; then
      # Only proceed if the array is not empty
      temp_file=$(mktemp) # Use a temporary file to build the sortable output
      for key in "${!latest_stats[@]}"; do
          value="${latest_stats[$key]}"
          # Extract the numeric count (first field of the value string)
          numeric_count=$(echo "$value" | awk '{print $1}')
          # Ensure numeric_count is actually a number before proceeding
          if [[ "$numeric_count" =~ ^[0-9.]+$ ]]; then
              # Use printf for cleaner formatting and handling potential special characters
              printf "%s\t%s: %s\n" "$numeric_count" "$key" "$value" >> "$temp_file"
          else
              # Uncomment the next line to debug entries with non-numeric counts
              # echo "DEBUG: Skipped entry due to non-numeric count. Key='${key}', Value='${value}'" >&2
              : # Do nothing, effectively skipping this entry
          fi
      done
      sortable_output=$(cat "$temp_file")
      rm "$temp_file" # Clean up the temporary file
  fi

  # --- Sort, Format, and Display ---
  clear
  echo "--- Top ${TOP_N} API URLs --- (Updated: $(date '+%Y-%m-%d %H:%M:%S')) ---"
  tail -1 $LOG_FILE | sed -E 's/^(\[.*\]) .*: [0-9]+ \([0-9.]+%\)$/\1/'
  echo "------------------------------------------------------------------"

  # Check if there's any output to sort
  if [[ -n "$sortable_output" ]]; then
      echo -e "$sortable_output" | \
          # Sort numerically (n) reverse (r) on the first field (k1,1), tab delimited
          sort -t$'\t' -k1,1nr | \
          # Get the top N lines
          head -n "$TOP_N" | \
          # Cut from the second field onwards (removes the sorting number), tab delimited
          cut -f2-
  else
      echo "No data processed yet or log file format mismatch."
  fi
  echo "------------------------------------------------------------------"
  echo "(Refreshing in $REFRESH_INTERVAL seconds...)"


  # --- Wait for the next interval ---
  sleep "$REFRESH_INTERVAL"
done

exit 0 # Should not be reached in normal operation
