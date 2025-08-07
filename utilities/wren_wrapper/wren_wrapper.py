#!/usr/bin/env python3
"""
wren_wrapper - A Python wrapper for the 'wren' CLI task manager.

This script provides quality-of-life enhancements to wren, including:
- Interactive task completion for ambiguous patterns.
- A cron helper for creating recurring tasks.
- A future-date helper using a graphical calendar for scheduled tasks.
"""

import argparse
import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import textwrap
from typing import List, Optional, Sequence

# Globals for verbosity and quietness
VERBOSE = False
QUIET = False


def print_verbose(message: str):
    """Prints a message to stderr if verbose mode is enabled."""
    if VERBOSE and not QUIET:
        print(f"wren_wrapper: {message}", file=sys.stderr)


def print_quiet(message: str):
    """Prints a message to stdout unless quiet mode is enabled."""
    if not QUIET:
        print(message)


def find_wren_executable() -> str:
    """Finds the path to the 'wren' executable."""
    wren_path = shutil.which("wren")
    if not wren_path:
        print("Error: 'wren' executable not found on $PATH.", file=sys.stderr)
        sys.exit(2)
    print_verbose(f"Found wren executable at {wren_path}")
    return wren_path


def get_notes_dir() -> pathlib.Path:
    """
    Determines the notes directory path from wren config.
    """
    config_path = pathlib.Path.home() / ".config" / "wren" / "wren.json"
    print_verbose(f"Reading config from {config_path}")
    if not config_path.is_file():
        print(f"Error: Config file not found at {config_path}", file=sys.stderr)
        sys.exit(2)
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        notes_dir_str = config["notes_dir"]
        notes_dir = pathlib.Path(notes_dir_str).expanduser()
    except (json.JSONDecodeError, KeyError) as e:
        print(
            f"Error: Could not read 'notes_dir' from {config_path}. {e}",
            file=sys.stderr,
        )
        sys.exit(2)

    if not notes_dir.exists():
        print_verbose(f"Notes directory {notes_dir} does not exist. Creating it.")
        try:
            notes_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(
                f"Error: Could not create notes directory {notes_dir}: {e}",
                file=sys.stderr,
            )
            sys.exit(1)

    return notes_dir


def run_wren(
    wren_path: str, args: List[str], check: bool = False, capture_output: bool = False
) -> subprocess.CompletedProcess:
    """Runs the wren command with the given arguments."""
    command = [wren_path] + args
    print_verbose(f"Executing: {' '.join(command)}")
    return subprocess.run(
        command, text=True, check=check, capture_output=capture_output, encoding="utf-8"
    )


def handle_interactive_done(wren_path: str, pattern: str, remaining_args: List[str]):
    """Handles interactive task completion."""
    print_verbose(f"Finding candidates for pattern: {pattern}")

    # To find candidates, execute `wren -d <pattern>` and parse its stdout.
    list_result = run_wren(wren_path, ["-d", pattern], capture_output=True)

    candidates = []
    print_verbose(f"list_result.stdout: {list_result.stdout}")
    if list_result.stdout:
        lines = [line.strip() for line in list_result.stdout.strip().split("\n")]
        candidates = [
            line[2:] if line.startswith("- ") else line
            for line in lines
            if line and not line.startswith("Error -")
        ]

    if len(candidates) > 1:
        print_quiet(f'Multiple tasks match "{pattern}". Mark which one as done?')
        for i, task in enumerate(candidates):
            print_quiet(f"{i+1}) {task}")

        while True:
            try:
                selection = input(f"Selection (1-{len(candidates)}, q to abort) > ")
                if selection.lower() == "q":
                    print_quiet("Aborted.")
                    sys.exit(1)
                choice = int(selection)
                if 1 <= choice <= len(candidates):
                    chosen_task = candidates[choice - 1]

                    # Reconstruct original command, replacing pattern with exact filename
                    final_args = list(remaining_args)
                    p_index = final_args.index(pattern)
                    final_args[p_index] = chosen_task

                    result = run_wren(wren_path, final_args)
                    sys.exit(result.returncode)
                else:
                    print_quiet("Invalid selection.")
            except (ValueError, IndexError):
                print_quiet("Invalid input. Please enter a number from the list.")
            except (EOFError, KeyboardInterrupt):
                print("\nAborted by user.", file=sys.stderr)
                sys.exit(1)
    else:
        # If 0 or 1 candidates, just run the original command.
        # This allows wren to handle success or "no matches found" errors.
        print_verbose("Zero or one candidate found, proxying original command to wren.")
        result = run_wren(wren_path, remaining_args)
        sys.exit(result.returncode)


def handle_cron(notes_dir: pathlib.Path, task_title: str):
    """Handles the cron helper to create a recurring task."""
    cheat_sheet = textwrap.dedent("""
        Cron cheat-sheet:
        ┌──────── minute (0-59)
        │ ┌────── hour   (0-23)
        │ │ ┌──── day    (1-31)
        │ │ │ ┌── month  (1-12)
        │ │ │ │ ┌─ weekday(0-6 Sun-Sat)
        │ │ │ │ │
        * * * * *  command""")
    print_quiet(cheat_sheet)

    cron_regex = re.compile(r"^(\S+\s+){4}\S+$")

    while True:
        try:
            schedule = input('Enter cron schedule (e.g. "0 4 * * *"): ')
            if cron_regex.match(schedule.strip()):
                break
            else:
                print(
                    "Invalid cron string format. It must have 5 space-separated fields.",
                    file=sys.stderr,
                )
        except (EOFError, KeyboardInterrupt):
            print("\nAborted by user.", file=sys.stderr)
            sys.exit(1)

    filename = f"{schedule.strip()} {task_title}"
    filepath = notes_dir / filename

    print_verbose(f"Creating cron task file: {filepath}")
    try:
        with open(filepath, "x", encoding="utf-8") as f:
            pass  # Create empty file
        print_quiet(f"Created repeating task: {filepath}")
        sys.exit(0)
    except FileExistsError:
        print(f"Error: Task file already exists: {filepath}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error: Could not create task file {filepath}: {e}", file=sys.stderr)
        sys.exit(1)


def handle_future(notes_dir: pathlib.Path, task_title: str):
    """Handles the future-date helper to create a scheduled task."""
    date_str = ""
    use_zenity = shutil.which("zenity") and os.environ.get("DISPLAY")

    if use_zenity:
        print_verbose("Using zenity for date selection.")
        try:
            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            cmd = [
                "zenity",
                "--calendar",
                "--text=Wren task date",
                "--date-format=%Y-%m-%d",
                f"--day={tomorrow.day}",
                f"--month={tomorrow.month}",
                f"--year={tomorrow.year}",
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8"
            )
            if result.returncode == 0:
                date_str = result.stdout.strip()
            else:
                print_quiet("Date selection cancelled.")
                sys.exit(1)  # Graceful exit on cancel
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print_verbose(f"Zenity call failed: {e}. Falling back to CLI prompt.")
            use_zenity = False  # Fallback

    if not use_zenity:
        print_verbose("Zenity not available or failed. Using CLI prompt for date.")
        while True:
            try:
                date_input = input("Enter date (YYYY-MM-DD): ")
                datetime.datetime.strptime(date_input, "%Y-%m-%d")
                date_str = date_input
                break
            except ValueError:
                print("Invalid date format. Please use YYYY-MM-DD.", file=sys.stderr)
            except (EOFError, KeyboardInterrupt):
                print("\nAborted by user.", file=sys.stderr)
                sys.exit(1)

    if not date_str:
        print("Error: Could not determine date.", file=sys.stderr)
        sys.exit(1)

    filename = f"{date_str} {task_title}"
    filepath = notes_dir / filename

    print_verbose(f"Creating future task file: {filepath}")
    try:
        with open(filepath, "x", encoding="utf-8") as f:
            pass  # Create empty file
        print_quiet(f"Created future task: {filepath}")
        sys.exit(0)
    except FileExistsError:
        print(f"Error: Task file already exists: {filepath}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error: Could not create task file {filepath}: {e}", file=sys.stderr)
        sys.exit(1)


def handle_exact_done(notes_dir: pathlib.Path, task_title: str):
    """Marks a task as done by moving it to the 'done' directory."""
    source_path = notes_dir / task_title
    print_verbose(f"Attempting to mark exact task as done: {source_path}")

    if not source_path.is_file():
        print(f"Error: Task not found with exact name: '{task_title}'", file=sys.stderr)
        sys.exit(1)

    done_dir = notes_dir / "done"
    dest_path = done_dir / task_title

    try:
        done_dir.mkdir(parents=True, exist_ok=True)
        print_verbose(f"Ensured 'done' directory exists: {done_dir}")
    except OSError as e:
        print(
            f"Error: Could not create 'done' directory {done_dir}: {e}", file=sys.stderr
        )
        sys.exit(1)

    try:
        shutil.move(source_path, dest_path)
        print_quiet(f"Marked done: {task_title}")
        sys.exit(0)
    except OSError as e:
        print(
            f"Error: Could not move task file '{task_title}' to done directory: {e}",
            file=sys.stderr,
        )
        sys.exit(1)


def main(argv: Optional[Sequence[str]] = None):
    """Main function for the wren_wrapper."""
    global VERBOSE, QUIET
    parser = argparse.ArgumentParser(
        description="A Python wrapper for the 'wren' CLI task manager.",
        add_help=False,
        argument_default=argparse.SUPPRESS,
    )
    # Wrapper-specific arguments
    parser.add_argument(
        "-c",
        "--cron",
        metavar="TASK_TITLE",
        help="Launch cron helper for a new repeating task.",
    )
    parser.add_argument(
        "-f",
        "--future",
        metavar="TASK_TITLE",
        help="Launch future-date helper for a new one-off task.",
    )
    parser.add_argument(
        "-x",
        "--exact",
        metavar="TASK_TITLE",
        help="Mark task done by exact filename, bypassing wren's substring match.",
    )
    parser.add_argument(
        "-h",
        "--help",
        action="store_true",
        help="Show native wren help, then wrapper help",
    )

    # Verbosity arguments
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print verbose output from the wrapper.",
    )
    verbosity_group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress all wrapper stdout except fatal errors.",
    )

    # Parse only the arguments known to the wrapper
    args, remaining_args = parser.parse_known_args(argv)

    if "verbose" in args and args.verbose:
        VERBOSE = True
    if "quiet" in args and args.quiet:
        QUIET = True

    wren_path = find_wren_executable()

    if "help" in args and args.help:
        run_wren(wren_path, ["--help"])
        print("\n--- wren_wrapper help ---")
        parser.print_help()
        sys.exit(0)

    # Check for mutually exclusive wrapper commands
    command_count = sum(1 for cmd in ["cron", "future", "exact"] if cmd in args)
    if command_count > 1:
        print(
            "Error: --cron, --future, and --exact are mutually exclusive.",
            file=sys.stderr,
        )
        sys.exit(1)

    notes_dir = get_notes_dir()

    if "cron" in args:
        handle_cron(notes_dir, args.cron)
    elif "future" in args:
        handle_future(notes_dir, args.future)
    elif "exact" in args:
        handle_exact_done(notes_dir, args.exact)

    # Interactive 'done' logic
    is_done_command = False
    done_pattern = None

    if "-d" in remaining_args or "--done" in remaining_args:
        is_done_command = True
        try:
            d_index = (
                remaining_args.index("-d")
                if "-d" in remaining_args
                else remaining_args.index("--done")
            )
            print_verbose(f"d_index: {d_index}")
            if d_index + 1 < len(remaining_args) and not remaining_args[
                d_index + 1
            ].startswith("-"):
                done_pattern = remaining_args[d_index + 1]
                print_verbose(f"done_pattern: {done_pattern}")
        except (ValueError, IndexError):
            is_done_command = False

    if is_done_command and done_pattern:
        print_verbose(f"remaining_args: {remaining_args}")
        print_verbose("calling handle_interactive_done")
        handle_interactive_done(wren_path, done_pattern, remaining_args)
    else:
        # If no wrapper command was used, just proxy to wren
        print_verbose("proxying to wren")
        result = run_wren(wren_path, remaining_args)
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
