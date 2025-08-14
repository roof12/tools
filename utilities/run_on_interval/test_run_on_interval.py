#!/usr/bin/env python3

import argparse
import datetime
import io
import subprocess
import sys
import unittest
from unittest.mock import patch

from utilities.run_on_interval import main, non_negative_int, positive_int


class TestRunOnInterval(unittest.TestCase):
    """Tests for run_on_interval.py."""

    def test_positive_int_valid(self):
        """Test that positive_int accepts positive integers."""
        self.assertEqual(positive_int("1"), 1)
        self.assertEqual(positive_int("100"), 100)

    def test_positive_int_invalid(self):
        """Test that positive_int raises errors for non-positive integers."""
        with self.assertRaises(argparse.ArgumentTypeError):
            positive_int("0")
        with self.assertRaises(argparse.ArgumentTypeError):
            positive_int("-1")
        with self.assertRaises(ValueError):
            positive_int("not-a-number")

    def test_non_negative_int_valid(self):
        """Test that non_negative_int accepts non-negative integers."""
        self.assertEqual(non_negative_int("0"), 0)
        self.assertEqual(non_negative_int("1"), 1)

    def test_non_negative_int_invalid(self):
        """Test that non_negative_int raises errors for negative integers."""
        with self.assertRaises(argparse.ArgumentTypeError):
            non_negative_int("-1")
        with self.assertRaises(ValueError):
            non_negative_int("not-a-number")

    @patch("utilities.run_on_interval.run_on_interval.argparse.ArgumentParser")
    @patch("utilities.run_on_interval.run_on_interval.datetime.date")
    def test_main_creates_parser_with_usage_info(self, mock_date, mock_ArgumentParser):
        """Test that main creates ArgumentParser with dynamic usage info."""
        mock_date.today.return_value.timetuple.return_value.tm_yday = 42

        mock_parser_instance = mock_ArgumentParser.return_value

        # To prevent the rest of main() from running, we can make parse_args() raise an exception.
        class SentinelException(Exception):
            pass

        mock_parser_instance.parse_args.side_effect = SentinelException

        with self.assertRaises(SentinelException):
            main([])  # argv doesn't matter here

        # Now check how ArgumentParser was called.
        mock_ArgumentParser.assert_called_once()
        _, kwargs = mock_ArgumentParser.call_args
        self.assertEqual(
            kwargs["description"],
            "Conditionally execute a command based on the day of the year.",
        )
        self.assertIn("day 42", kwargs["epilog"])
        self.assertEqual(
            kwargs["formatter_class"], argparse.RawDescriptionHelpFormatter
        )

    @patch("utilities.run_on_interval.run_on_interval.subprocess.run")
    @patch("utilities.run_on_interval.run_on_interval.datetime.date")
    def test_command_executes_on_schedule(self, mock_date, mock_run):
        """Test that the command is executed when the day matches the schedule."""
        # (day_of_year - offset) % interval == 0 -> (10 - 0) % 5 == 0
        mock_date.today.return_value.timetuple.return_value.tm_yday = 10
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

        with self.assertRaises(SystemExit) as cm:
            main(["5", "0", "echo", "Success"])

        self.assertEqual(cm.exception.code, 0)
        mock_run.assert_called_once_with(["echo", "Success"], check=False)

    @patch("utilities.run_on_interval.run_on_interval.subprocess.run")
    @patch("utilities.run_on_interval.run_on_interval.datetime.date")
    def test_command_does_not_execute_off_schedule(self, mock_date, mock_run):
        """Test that the command is not executed when the day is off schedule."""
        # (day_of_year - offset) % interval != 0 -> (11 - 0) % 5 != 0
        mock_date.today.return_value.timetuple.return_value.tm_yday = 11

        with self.assertRaises(SystemExit) as cm:
            main(["5", "0", "echo", "Success"])

        self.assertEqual(cm.exception.code, 0)
        mock_run.assert_not_called()

    @patch("utilities.run_on_interval.run_on_interval.subprocess.run")
    @patch("utilities.run_on_interval.run_on_interval.datetime.date")
    def test_exit_code_propagation(self, mock_date, mock_run):
        """Test that the script's exit code matches the command's exit code."""
        mock_date.today.return_value.timetuple.return_value.tm_yday = 10
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1)

        with self.assertRaises(SystemExit) as cm:
            main(["5", "0", "false"])

        self.assertEqual(cm.exception.code, 1)
        mock_run.assert_called_once_with(["false"], check=False)

    def test_cli_missing_arguments(self):
        """Test CLI for missing arguments."""
        result = subprocess.run(
            ["utilities/run_on_interval/run_on_interval.py"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "the following arguments are required: interval, offset, command",
            result.stderr,
        )

    def test_cli_missing_command(self):
        """Test CLI for missing command argument."""
        result = subprocess.run(
            ["utilities/run_on_interval/run_on_interval.py", "1", "0"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("the following arguments are required: command", result.stderr)

    def test_cli_invalid_interval(self):
        """Test CLI for invalid interval value."""
        result = subprocess.run(
            ["utilities/run_on_interval/run_on_interval.py", "-1", "0", "echo"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("argument interval: -1 is not a positive integer", result.stderr)

    def test_cli_invalid_offset(self):
        """Test CLI for invalid offset value."""
        result = subprocess.run(
            ["utilities/run_on_interval/run_on_interval.py", "1", "-1", "echo"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "argument offset: -1 is not a non-negative integer", result.stderr
        )

    @patch("utilities.run_on_interval.run_on_interval.subprocess.run")
    @patch("utilities.run_on_interval.run_on_interval.datetime.date")
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_verbose_output_when_executing(self, mock_stdout, mock_date, mock_run):
        """Test verbose output is printed when the command is executed."""
        mock_date.today.return_value.timetuple.return_value.tm_yday = 10
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

        with self.assertRaises(SystemExit):
            main(["--verbose", "5", "0", "echo", "Success"])

        output = mock_stdout.getvalue()
        self.assertIn("Condition met", output)
        self.assertIn("Executing command", output)

    @patch("utilities.run_on_interval.run_on_interval.subprocess.run")
    @patch("utilities.run_on_interval.run_on_interval.datetime.date")
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_verbose_output_when_not_executing(self, mock_stdout, mock_date, mock_run):
        """Test verbose output is printed when the command is not executed."""
        mock_date.today.return_value.timetuple.return_value.tm_yday = 11

        with self.assertRaises(SystemExit):
            main(["-v", "5", "0", "echo", "Success"])

        output = mock_stdout.getvalue()
        self.assertIn("Condition not met", output)
        self.assertIn("Next execution in 4 day(s).", output)
        self.assertIn("Not executing command", output)
        mock_run.assert_not_called()

    @patch("utilities.run_on_interval.run_on_interval.subprocess.run")
    @patch("utilities.run_on_interval.run_on_interval.datetime.date")
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_no_verbose_output_by_default(self, mock_stdout, mock_date, mock_run):
        """Test no verbose output is printed by default."""
        mock_date.today.return_value.timetuple.return_value.tm_yday = 10
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

        with self.assertRaises(SystemExit):
            main(["5", "0", "echo", "Success"])

        self.assertEqual(mock_stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
