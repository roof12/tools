#!/usr/bin/env python3

import argparse
import datetime
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


if __name__ == "__main__":
    unittest.main()
