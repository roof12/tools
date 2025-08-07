import json
import os
import pathlib
import shutil
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, call, patch

from utilities.wren_wrapper import wren_wrapper


class TestWrenWrapper(unittest.TestCase):
    """Tests for wren_wrapper.py."""

    def setUp(self):
        """Set up a temporary environment for each test."""
        # Use a temporary directory that is definitely not in the repo
        self.temp_dir = pathlib.Path(
            shutil.get_terminal_size((80, 20)).columns * "_"
        ) / "test_wren_wrapper_temp"
        self.config_dir = self.temp_dir / ".config" / "wren"
        self.notes_dir = self.temp_dir / "notes"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.notes_dir.mkdir(parents=True, exist_ok=True)

        self.config_path = self.config_dir / "wren.json"
        with self.config_path.open("w", encoding="utf-8") as f:
            json.dump({"notes_dir": str(self.notes_dir)}, f)

        # Patch filesystem and external commands
        self.home_patch = patch("pathlib.Path.home", return_value=self.temp_dir)
        self.mock_home = self.home_patch.start()

        self.which_patch = patch("shutil.which")
        self.mock_which = self.which_patch.start()
        # Default to wren executable being found
        self.mock_which.return_value = "/fake/path/to/wren"

        self.run_patch = patch("subprocess.run")
        self.mock_run = self.run_patch.start()
        self.mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        # Patch system-level calls
        self.exit_patch = patch("sys.exit")
        self.mock_exit = self.exit_patch.start()

        self.input_patch = patch("builtins.input")
        self.mock_input = self.input_patch.start()

        # Patch print functions to capture output
        self.print_quiet_patch = patch("utilities.wren_wrapper.wren_wrapper.print_quiet")
        self.mock_print_quiet = self.print_quiet_patch.start()

        self.print_verbose_patch = patch(
            "utilities.wren_wrapper.wren_wrapper.print_verbose"
        )
        self.mock_print_verbose = self.print_verbose_patch.start()

        # Reset globals
        wren_wrapper.VERBOSE = False
        wren_wrapper.QUIET = False

    def tearDown(self):
        """Clean up after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.home_patch.stop()
        self.which_patch.stop()
        self.run_patch.stop()
        self.exit_patch.stop()
        self.input_patch.stop()
        self.print_quiet_patch.stop()
        self.print_verbose_patch.stop()

    # --- Test Core Functions ---

    def test_find_wren_executable_found(self):
        self.assertEqual(wren_wrapper.find_wren_executable(), "/fake/path/to/wren")
        self.mock_which.assert_called_once_with("wren")

    def test_find_wren_executable_not_found(self):
        self.mock_which.return_value = None
        wren_wrapper.find_wren_executable()
        self.mock_exit.assert_called_once_with(2)

    def test_get_notes_dir_success(self):
        notes_dir = wren_wrapper.get_notes_dir()
        self.assertEqual(notes_dir, self.notes_dir.resolve())

    def test_get_notes_dir_config_missing(self):
        self.config_path.unlink()
        wren_wrapper.get_notes_dir()
        self.mock_exit.assert_called_once_with(2)

    def test_get_notes_dir_bad_json(self):
        with self.config_path.open("w", encoding="utf-8") as f:
            f.write("this is not json")
        wren_wrapper.get_notes_dir()
        self.mock_exit.assert_called_once_with(2)

    def test_get_notes_dir_key_missing(self):
        with self.config_path.open("w", encoding="utf-8") as f:
            json.dump({"another_key": "value"}, f)
        wren_wrapper.get_notes_dir()
        self.mock_exit.assert_called_once_with(2)

    def test_get_notes_dir_creates_dir_if_missing(self):
        shutil.rmtree(self.notes_dir)
        self.assertFalse(self.notes_dir.exists())
        wren_wrapper.get_notes_dir()
        self.assertTrue(self.notes_dir.exists())

    # --- Test Wrapper Features ---

    def test_handle_exact_done_success(self):
        task_title = "my-exact-task-name"
        task_file = self.notes_dir / task_title
        task_file.touch()
        done_dir = self.notes_dir / "done"

        wren_wrapper.handle_exact_done(self.notes_dir, task_title)

        self.assertFalse(task_file.exists())
        self.assertTrue((done_dir / task_title).exists())
        self.mock_print_quiet.assert_called_once_with(f"Marked done: {task_title}")
        self.mock_exit.assert_called_once_with(0)

    def test_handle_exact_done_task_not_found(self):
        wren_wrapper.handle_exact_done(self.notes_dir, "non-existent-task")
        self.mock_exit.assert_called_once_with(1)

    def test_handle_cron_success(self):
        self.mock_input.return_value = "0 9 * * 1"  # Every Monday at 9am
        task_title = "Weekly report"
        wren_wrapper.handle_cron(self.notes_dir, task_title)

        expected_file = self.notes_dir / f"0 9 * * 1 {task_title}"
        self.assertTrue(expected_file.exists())
        self.mock_print_quiet.assert_called_with(
            f"Created repeating task: {expected_file}"
        )
        self.mock_exit.assert_called_once_with(0)

    def test_handle_cron_file_exists(self):
        self.mock_input.return_value = "0 9 * * 1"
        task_title = "Weekly report"
        (self.notes_dir / f"0 9 * * 1 {task_title}").touch()

        wren_wrapper.handle_cron(self.notes_dir, task_title)
        self.mock_exit.assert_called_once_with(1)

    def test_handle_future_with_zenity(self):
        # Pretend zenity is installed and DISPLAY is set
        self.mock_which.side_effect = lambda x: f"/usr/bin/{x}" if x in ["wren", "zenity"] else None
        with patch.dict(os.environ, {"DISPLAY": ":0"}):
            self.mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="2025-12-25\n"
            )
            task_title = "Buy presents"
            wren_wrapper.handle_future(self.notes_dir, task_title)

            expected_file = self.notes_dir / f"2025-12-25 {task_title}"
            self.assertTrue(expected_file.exists())
            self.mock_print_quiet.assert_called_with(
                f"Created future task: {expected_file}"
            )
            self.mock_exit.assert_called_once_with(0)
            self.assertIn("zenity", self.mock_run.call_args[0][0])

    def test_handle_future_zenity_cancel(self):
        self.mock_which.side_effect = lambda x: f"/usr/bin/{x}" if x in ["wren", "zenity"] else None
        with patch.dict(os.environ, {"DISPLAY": ":0"}):
            self.mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout=""  # User cancelled
            )
            wren_wrapper.handle_future(self.notes_dir, "A task")
            self.mock_print_quiet.assert_called_once_with("Date selection cancelled.")
            self.mock_exit.assert_called_once_with(1)

    def test_handle_future_cli_fallback(self):
        self.mock_which.side_effect = lambda x: "/usr/bin/wren" if x == "wren" else None  # zenity not found
        self.mock_input.return_value = "2026-01-15"
        task_title = "New year resolutions"
        wren_wrapper.handle_future(self.notes_dir, task_title)

        expected_file = self.notes_dir / f"2026-01-15 {task_title}"
        self.assertTrue(expected_file.exists())
        self.mock_exit.assert_called_once_with(0)

    def test_handle_interactive_done_multiple_matches_select_one(self):
        self.mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="  - task one\n  - task two")
        self.mock_input.return_value = "2" # Select "task two"

        wren_path = "/fake/wren"
        pattern = "task"
        remaining_args = ["-d", "task", "--other-flag"]
        final_args = ["-d", "task two", "--other-flag"]


        wren_wrapper.handle_interactive_done(wren_path, pattern, remaining_args)

        # Check that we first listed candidates, then executed the specific one
        self.mock_run.assert_has_calls([
            call([wren_path, '-d', pattern], capture_output=True),
            call([wren_path, *final_args])
        ])
        self.mock_exit.assert_called_once() # Should exit with wren's return code

    def test_handle_interactive_done_single_match(self):
        # wren returns the single match
        self.mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="- the-only-task")

        wren_path = "/fake/wren"
        pattern = "the-only"
        remaining_args = ["-d", "the-only"]

        wren_wrapper.handle_interactive_done(wren_path, pattern, remaining_args)

        # Should call to list candidates, find one, then proxy original command
        self.mock_run.assert_has_calls([
            call([wren_path, '-d', pattern], capture_output=True),
            call([wren_path, *remaining_args])
        ])
        self.mock_exit.assert_called_once()

    def test_handle_interactive_done_no_matches(self):
        # wren returns an error or empty stdout
        self.mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="Error - No matches found for 'nonexistent'")

        wren_path = "/fake/wren"
        pattern = "nonexistent"
        remaining_args = ["-d", "nonexistent"]

        wren_wrapper.handle_interactive_done(wren_path, pattern, remaining_args)

        # Should call to list, find none, then proxy original command
        self.mock_run.assert_has_calls([
            call([wren_path, '-d', pattern], capture_output=True),
            call([wren_path, *remaining_args])
        ])
        self.mock_exit.assert_called_once()

    # --- Test `main` function (integration) ---
    def test_main_proxy_to_wren(self):
        wren_wrapper.main(["-l", "some_pattern"])
        self.mock_run.assert_called_once_with(
            ['/fake/path/to/wren', '-l', 'some_pattern'],
            text=True, check=False, capture_output=False, encoding='utf-8'
        )
        self.mock_exit.assert_called_once_with(0)

    def test_main_help_command(self):
        with patch("argparse.ArgumentParser.print_help") as mock_print_help:
            wren_wrapper.main(["--help"])
            self.mock_run.assert_called_once_with(['/fake/path/to/wren', '--help'])
            self.mock_print_quiet.assert_called_with("\n--- wren_wrapper help ---")
            mock_print_help.assert_called_once()
            self.mock_exit.assert_called_once_with(0)

    def test_main_verbose_flag(self):
        self.assertFalse(wren_wrapper.VERBOSE)
        wren_wrapper.main(["-v", "-l"])
        self.assertTrue(wren_wrapper.VERBOSE)

    def test_main_quiet_flag(self):
        self.assertFalse(wren_wrapper.QUIET)
        wren_wrapper.main(["-q", "-l"])
        self.assertTrue(wren_wrapper.QUIET)

    def test_main_mutually_exclusive_commands(self):
        wren_wrapper.main(["--cron", "a", "--future", "b"])
        self.mock_exit.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
