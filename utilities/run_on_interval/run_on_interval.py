#!/usr/bin/env python3

"""
Conditionally executes a given command, based on the provided interval and
offset.
"""

import argparse
import datetime
import subprocess
import sys


def positive_int(value):
    """Argparse type for a positive integer."""
    ivalue = int(value)
    if ivalue < 1:
        raise argparse.ArgumentTypeError(f"{value} is not a positive integer")
    return ivalue


def non_negative_int(value):
    """Argparse type for a non-negative integer."""
    ivalue = int(value)
    if ivalue < 0:
        raise argparse.ArgumentTypeError(f"{value} is not a non-negative integer")
    return ivalue


def get_usage_info():
    """Constructs description and epilog for argparse, including current day."""
    description = "Conditionally execute a command based on the day of the year."
    day_of_year = datetime.date.today().timetuple().tm_yday
    epilog = f"Today is day {day_of_year}."
    return description, epilog


def main(argv=None):
    """Parse arguments and execute command if conditions are met."""
    description, epilog = get_usage_info()
    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output."
    )
    parser.add_argument(
        "interval", type=positive_int, help="The interval in days (positive integer)."
    )
    parser.add_argument(
        "offset",
        type=non_negative_int,
        help="The offset in days (non-negative integer).",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="The command to execute and all its subsequent arguments.",
    )

    args = parser.parse_args(argv)

    if not args.command:
        parser.error("the following arguments are required: command")

    day_of_year = datetime.date.today().timetuple().tm_yday

    if (day_of_year - args.offset) % args.interval == 0:
        if args.verbose:
            print(
                f"Condition met (day {day_of_year}, interval {args.interval}, offset {args.offset})."
                f"Executing command: {' '.join(args.command)}"
            )
        result = subprocess.run(args.command, check=False)
        sys.exit(result.returncode)
    else:
        if args.verbose:
            days_until_next = args.interval - (
                (day_of_year - args.offset) % args.interval
            )
            print(
                f"Condition not met (day {day_of_year}, interval {args.interval}, offset {args.offset}). "
            )
            print(f"Next execution in {days_until_next} day(s).")
            print("Not executing command.")
        sys.exit(0)


if __name__ == "__main__":
    main()
