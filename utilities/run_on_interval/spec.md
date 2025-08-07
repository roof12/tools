# run-on-interval.py

Specification:

## Purpose

run-on-interval.py is a Python script that conditionally executes a given
command, based on the provided interval and offset. If the current day of
the year (1-366) modulo the interval is equal to the offset, the command
will be executed.

## Command-line arguments

The script must accept arguments using the `argparse` module.

1. `interval`: A required positional argument. Must be a positive integer.
2. `offset`: A required positional argument. Must be a non-negative integer.
3. `command`: A required argument that captures the command to be executed
   and all its subsequent arguments (e.g., using `nargs=argparse.REMAINDER`).
4. `-v, --verbose`: An optional flag that enables verbose output.

## Behavior

1. The script will determine the current day of the year (1-366) using
   `datetime.date.today().timetuple().tm_yday`.

2. It will perform the calculation:
   `(current_day_of_year - offset) % interval`

3. If the result of the modulo operation is `0`, the script will execute the
   provided `command` with its arguments.
   - If `--verbose` is specified, a message indicating that the condition was met
     and the command is being executed will be printed to stdout.
   - The command should be executed using `subprocess.run()`.
   - The script should exit with the return code of the executed command.

4. If the condition is not met, the script should exit with status code `0`
   without executing the command.
   - If `--verbose` is specified, a message indicating that the condition was not
     met will be printed to stdout.

## Error Handling

1. `argparse` should be configured to handle missing arguments.

2. If `interval` is not a positive integer (`< 1`), the script should
   print an error message to stderr and exit with a non-zero status code.
   A custom `type` function for `argparse` can be used for validation.

3. If `offset` is not a non-negative integer (`< 0`), the script should
   print an error message to stderr and exit with a non-zero status code.
   A custom `type` function for `argparse` can be used for validation.

## Example Usage

utilities/run_on_interval/run_on_interval.py 7 0 echo "This runs on a 7-day interval"
utilities/run_on_interval/run_on_interval.py --verbose 7 0 echo "This runs on a 7-day interval"
utilities/run_on_interval/run_on_interval.py 30 5 ls -l /tmp
