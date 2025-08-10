#!/bin/bash

# A script to open three wezterm windows in a specific i3 layout.
# Layout: One terminal on the left, two stacked vertically on the right.

# --- 1. Argument Handling ---

# Check if a workspace name was provided.
if [ -z "$1" ]; then
  echo "Error: No workspace name provided."
  echo "Usage: $0 <workspace_name> <directory_path>"
  exit 1
fi

# Check if a directory path was provided.
if [ -z "$2" ]; then
  echo "Error: No directory path provided."
  echo "Usage: $0 <workspace_name> <directory_path>"
  exit 1
fi

SLEEP_TIME="0.25"

# The target i3 workspace.
WORKSPACE_NAME="$1"

# The directory where the terminals should start.
# Use realpath to resolve relative paths like "." or ".."
DIR_PATH=$(realpath "$2")

# The window class for wezterm.
WEZTERM_CLASS="org.wezfurlong.wezterm"

# --- 2. Main Logic ---

echo "Setting up layout on workspace '$WORKSPACE_NAME' in directory '$DIR_PATH'..."

# Switch to the target workspace. This will create it if it doesn't exist.
i3-msg "workspace $WORKSPACE_NAME" >/dev/null

# Open the first terminal (left pane).
wezterm start --cwd "$DIR_PATH" >/dev/null 2>&1 &
# Wait for the terminal to open and get focus.
sleep "$SLEEP_TIME"

WEZTERM_PANE=$(wezterm cli list-clients --format=json | jq -r '.[0].focused_pane_id')
wezterm cli send-text --no-paste --pane-id $WEZTERM_PANE "$(printf "nvim .\r")"

# Set the split direction to horizontal for the next window.
i3-msg "split h" >/dev/null

# Open the second terminal (top-right pane).
wezterm start --cwd "$DIR_PATH" >/dev/null 2>&1 &
# Wait for this terminal to open and get focus.
sleep "$SLEEP_TIME"

# Set the split direction to vertical for the next window.
i3-msg "split v" >/dev/null

# Open the third terminal (bottom-right pane).
wezterm start --cwd "$DIR_PATH" >/dev/null 2>&1 &
# Wait for this terminal to open and get focus.
sleep "$SLEEP_TIME"

echo "Layout complete."
