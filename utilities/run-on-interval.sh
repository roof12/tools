#!/bin/bash

# Check for a positive integer argument for interval
if [[ ! $1 =~ ^[1-9][0-9]*$ ]]; then
	echo "Error: Please provide a positive integer as the first argument (interval)."
	exit 1
fi

# Get the interval and remaining arguments
interval="$1"
shift

# Get the current day modulo interval
current_day=$(($(date +%-j) % interval))

# Check if current day is a multiple of interval
if [[ $current_day -eq 0 ]]; then
	# Execute remaining arguments as a script
	"$@"
fi
