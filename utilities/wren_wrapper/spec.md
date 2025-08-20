### Python Wrapper for **wren** — Functional Specification  

*(Target audience: LLM‑based coding agent)*  

---

#### 1. Purpose & Scope  

Create a Python command‑line wrapper (`w`) that:

1. Uses the default **wren** configuration at `~/.config/wren/wren.json` to discover `notes_dir`.  
2. Transparently proxies every command‑line argument to the underlying **wren** binary **unless** it recognizes a wrapper‑specific feature (listed below).  
3. Adds four quality‑of‑life commands not present in upstream **wren**:  

* **Interactive disambiguation** when marking tasks done (`-d` with multiple matches).  
* **Cron helper** (`-c`) for creating recurring tasks.  
* **Future‑date helper** (`-f`) that launches a graphical date picker (using **zenity**) for one‑off scheduled tasks.  
* **Exact match "done"** (`-x`) to bypass `wren`’s substring matching and mark a task done by its exact filename.  

The wrapper must behave identically to `wren` for all original commands, flags, and positional arguments, apart from the added behavior described here.

---

#### 2. Environment & Assumptions  

| Item | Spec |
|------|------|
| Python version | 3.10 + |
| Platform | Linux / macOS (POSIX‑like; assumes `wren` and `zenity` CLI tools are on `$PATH`) |
| External programs | `wren` executable; `zenity` |
| Config file | `~/.config/wren/wren.json` (contains JSON key `notes_dir`) |
| Task files | Regular files inside `notes_dir`; filename = title; file body (optional) = task content. When a task is marked done, `wren` moves it to a `done/` subdirectory. |

---

#### 3. Command‑Line Interface  

```

w \[WRAPPER\_OPT …] \[--] \[WREN\_OPT … | task …]

Wrapper‑specific options (may be combined with native wren flags):
-c, --cron \<TASK\_TITLE ...>
Launch cron helper (see §4.2)
-f, --future \<TASK\_TITLE ...>
Launch future‑date helper (see §4.3)
-x, --exact \<TASK\_TITLE>
Mark task done by exact filename (see §4.4)
-h, \--help
Show native `wren` help first, then append wrapper help

````

*All other flags/arguments are forwarded unmodified to `wren`.*  
Wrapper flags have priority if a name collision ever occurs.

---

#### 4. Extended Functionality  

##### 4.1 Interactive “done”  

* Trigger: user invokes `w -d <pattern>` (or `--done`).  
* Flow:  
  1. To find candidates, execute `wren -d <pattern>` and parse its `stdout`, assuming one match per line.
  2. If more than one candidate is found, present an interactive numbered list to the user:

     ```
     Multiple tasks match "<pattern>". Mark which one as done?
     1) zzbar
     2) zzfoo
     Selection (1‑2, q to abort) >
     ```

  3. On a valid selection, execute the original `wren` command, but replace the `<pattern>` with the chosen exact filename.
  4. If the user aborts (`q` or Ctrl-C), exit with code 1.
  5. If zero or one candidate is found, execute the original `wren -d <pattern>` command as is, letting `wren` handle the single-match or no-match cases.

##### 4.2 Cron helper (`-c | --cron`)  

* Trigger: `w -c "Pay rent"`  
* Behavior:  
  1. Display a concise cheat‑sheet for cron syntax (5 fields + command).  
  2. Prompt: `Enter cron schedule (e.g. "0 4 * * *"):` (stdin)  
  3. On input, compose filename:  

     ```
     "<cron_string> <TASK_TITLE>"
     ```  

  4. Create empty file in `notes_dir`.  
  5. Echo confirmation: `"Created repeating task: <file_path>"`.  
  6. If file already exists, warn and abort unless `--force`. (Optional advanced flag, not required.)  

##### 4.3 Future‑date helper (`-f | --future`)  

* Trigger: `w -f "Send birthday card"`  
* Behavior:  
  1. Execute `zenity` to show a graphical calendar, configured to open with tomorrow's date pre-selected.

     Example command (values to be filled programmatically):

     ```bash
     zenity --calendar \
            --text="Wren task date" \
            --date-format="%Y-%m-%d" \
            --day=<day of tomorrow> \
            --month=<month of tomorrow> \
            --year=<year of tomorrow>
     ```

  2. Capture selected date (YYYY‑MM‑DD).  
  3. Prepend it to the task title to form the filename:  

     ```
     "YYYY-MM-DD <TASK_TITLE>"
     ```  

  4. Create empty file in `notes_dir` (or with template content if provided via `--body <file>` flag, TBD).  
  5. If user cancels zenity, exit gracefully with no side effects.  

##### 4.4 Exact "done" (`-x | --exact`)  

* Trigger: `w -x "task with exact name"`  
* Behavior:  
  1. Check for the existence of a file with the exact `<TASK_TITLE>` inside `notes_dir`.  
  2. If it doesn't exist, print an error and exit.  
  3. If it exists, move the file to the `done/` subdirectory within `notes_dir`.  
  4. Create the `done/` directory if it does not already exist.  
  5. This operation is performed directly by the wrapper, bypassing `wren`, to avoid ambiguity when the task title is a substring of another task title.  
  6. Print confirmation: `"Marked done: <TASK_TITLE>"`.  

---

#### 5. Implementation Notes  

1. **Executable discovery**  
   * Use `shutil.which("wren")`; abort with clear error if not found.  
2. **Config parsing**  
   * Read `~/.config/wren/wren.json` at start; extract `notes_dir` (raise if missing).  
3. **Argument parsing**  
   * Use `argparse` with `argument_default=argparse.SUPPRESS` to avoid false defaults.  
   * Split parse into wrapper‑known options vs unknown; pass unknown (including positional “task”) to `wren`.  
   * Preserve user’s original argument order when forwarding, except strip wrapper flags.  
4. **Subprocess calls**  
   * Invoke `wren` via `subprocess.run`, capturing stdout/stderr for interactive‑done logic.  
   * Use `text=True` and `check=False` to inspect output.  
5. **Concurrency / atomicity**  
   * File creation: open with `O_EXCL` (Python `open(..., 'x')`) to prevent overwriting.  
6. **Return codes**  
   * Mirror `wren`’s exit code on simple proxy runs.  
   * For wrapper operations, `0` = success, `1` = user abort or validation error, `>1` = unexpected error.  
7. **Help text generation**  
   * `-h` or `--help` prints native `wren` help first, then prints wrapper help.
8. **Testing hooks**  
   * Mock `subprocess.run` and `zenity` using `unittest.mock`.  

---

#### 6. Dependencies  

* **Standard library only** for core logic (argparse, json, pathlib, subprocess, shutil, datetime, typing).  
* External: system must supply `wren`, `zenity`. No third‑party Python packages required.

---

#### 7. Edge Cases & Error Handling  

| Scenario | Expected outcome |
|----------|------------------|
| Config file missing or unreadable | Print fatal error and abort (exit 2) |
| `notes_dir` missing | Attempt to create it with `mkdir -p`; if fails, abort |
| No tasks match pattern for `-d` | Forward to `wren`; allow it to show “No matches found” |
| Cron string invalid (fails simple regex `'^(\S+\s){4}\S+$'`) | Re‑prompt with error message |
| Filename collision on `-c`/`-f` | Warn → abort (unless future `--force`) |
| `zenity` not installed or DISPLAY unset | Fallback to CLI prompt for date (`YYYY‑MM‑DD`) |

---

#### 8. Logging & Verbosity  

* Quiet by default.  
* `-v / --verbose` flag (wrapper‑level) prints commands executed and paths written.  
* `-q / --quiet` suppresses all wrapper stdout except fatal errors.  

---

#### 9. Example Session  

```bash
$ w -d zz
Multiple tasks match "zz".
1) zzbar
2) zzfoo
Selection (1‑2, q to abort) > 2
Marked done: zzfoo

$ w -c "Pay rent"
Cron cheat‑sheet:
┌──────── minute (0‑59)
│ ┌────── hour   (0‑23)
│ │ ┌──── day    (1‑31)
│ │ │ ┌── month  (1‑12)
│ │ │ │ ┌─ weekday(0‑6 Sun‑Sat)
│ │ │ │ │
│ │ │ │ │
* * * * *  command
Enter cron schedule: 0 4 * * *
Created repeating task: /home/user/notes/0 4 * * * Pay rent

$ w -f Buy flowers
# (zenity calendar appears)
Created future task: /home/user/notes/2025-07-02 Buy flowers
````

---

#### 10. Non‑Goals / Exclusions

* No GUI beyond the zenity calendar.
* No editing of task content for cron/future helpers (could be a later enhancement).
* No direct manipulation of Telegram, Matrix, or HTTP features of wren; wrapper only forwards those flags.

---

**End of specification**
