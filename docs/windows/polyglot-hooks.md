# Cross-Platform Polyglot Hooks for Claude Code

Claude Code plugins need hooks that work on Windows, macOS, and Linux from a single `hooks.json` entry. This document explains `hooks/run-hook.cmd`, the polyglot wrapper Bearpaws uses.

## The Problem

Claude Code runs hook commands through the platform's shell (`cmd.exe` on Windows; `bash`/`sh` on macOS and Linux):

1. **`.sh` auto-detection on Windows**: Claude Code prepends `bash` to hook commands containing `.sh`, which breaks or double-wraps a `.cmd` wrapper if the target filename ends in `.sh`.
2. **Direct `.sh` execution**: Windows `cmd.exe` cannot run `.sh` scripts directly.
3. **`bash` may not be on `PATH`**: Git for Windows is often installed at its standard `Program Files` path without `bash` in `PATH`.
4. **Paths with spaces**: `${CLAUDE_PLUGIN_ROOT}` may contain spaces on Windows (for example, `C:\Program Files\...`), so the wrapper path must be quoted.

## The Solution: `hooks/run-hook.cmd`

`hooks/run-hook.cmd` is valid syntax in both `cmd.exe` and `bash`, and dispatches **extensionless** bash hook scripts (`session-start`, `risk-gate`) in the same directory:

```text
Usage: run-hook.cmd <script-name> [args...]
```

```cmd
: << 'CMDBLOCK'
@echo off
if "%~1"=="" (
    echo run-hook.cmd: missing script name >&2
    exit /b 1
)

set "HOOK_DIR=%~dp0"

if exist "C:\Program Files\Git\bin\bash.exe" (
    "C:\Program Files\Git\bin\bash.exe" "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)
if exist "C:\Program Files (x86)\Git\bin\bash.exe" (
    "C:\Program Files (x86)\Git\bin\bash.exe" "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

where bash >nul 2>nul
if %ERRORLEVEL% equ 0 (
    bash "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

echo run-hook.cmd: bash not found, Bearpaws bootstrap skipped. Install Git for Windows to enable it. >&2
exit /b 0
CMDBLOCK

# Unix: run the named script directly
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -z "${1:-}" ]; then
    echo "run-hook.cmd: missing script name" >&2
    exit 1
fi
SCRIPT_NAME="$1"
shift
exec bash "${SCRIPT_DIR}/${SCRIPT_NAME}" "$@"
```

### How It Works

#### On Windows (`cmd.exe`)

1. `: << 'CMDBLOCK'` — `cmd.exe` treats `:` as a batch label and ignores the rest of the line.
2. `@echo off` — suppresses command echoing.
3. `if "%~1"==""` — fails loudly (exit `1`, stderr) if no script name was passed.
4. `set "HOOK_DIR=%~dp0"` — resolves the directory containing `run-hook.cmd` (with trailing backslash).
5. **Bash lookup order** (passing `"%HOOK_DIR%%~1"` and arguments `%2` through `%9` directly — no `cygpath` or `bash -l -c`):
   - `C:\Program Files\Git\bin\bash.exe`
   - `C:\Program Files (x86)\Git\bin\bash.exe`
   - `bash` on `PATH` (via `where bash`) — covers custom Git Bash, MSYS2, or Cygwin installs.
6. **Fallback when no `bash` is found**: prints a notice to `stderr` and exits `0` (`exit /b 0`) so Claude Code keeps working without hook errors.

#### On Unix (macOS / Linux)

1. `: << 'CMDBLOCK'` — `:` is a shell no-op and `<< 'CMDBLOCK'` starts a quoted heredoc, so the shell skips everything through `CMDBLOCK`.
2. Checks `${1:-}` and exits `1` on missing script name (tested by `tests/hooks/run-hook-tests.sh`).
3. Shifts `$1` and runs `exec bash "${SCRIPT_DIR}/${SCRIPT_NAME}" "$@"` (all remaining arguments forwarded).

## File Structure & `hooks.json`

Hook scripts under `hooks/` are intentionally **extensionless** so Claude Code's Windows `.sh` auto-detection never interferes:

```text
hooks/
├── hooks.json        # Claude Code hook registrations
├── hooks-cursor.json # Cursor hook registration
├── run-hook.cmd      # Cross-platform polyglot wrapper
├── session-start     # SessionStart bootstrap script (extensionless bash)
├── risk-gate         # PreToolUse/PostToolUse/PostToolUseFailure/Stop gate (extensionless bash)
└── lib-receipt       # Shared receipt helpers sourced by risk-gate
```

`hooks/hooks.json` invokes `run-hook.cmd` with the script name and optional subcommand arguments:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|clear",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start",
            "async": false
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" risk-gate baseline",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

## Requirements

- **Windows**: Git for Windows (or `bash` on `PATH`, e.g., MSYS2 or Cygwin). Without `bash`, `run-hook.cmd` logs to `stderr` and exits `0`. Arguments beyond `%9` (8 args after `<script-name>`) are not forwarded by the batch path.
- **Unix**: Standard `bash`. `run-hook.cmd` and the target hook scripts must be executable (`chmod +x`).
- **Hook scripts**: `session-start` relies on bash builtins (e.g., parameter substitution in `escape_for_json`) and `cat`/`dirname`; `risk-gate` additionally uses `jq` (failing open if absent).

## Troubleshooting

### `run-hook.cmd: bash not found, Bearpaws bootstrap skipped`
Neither standard Git for Windows path exists and `bash` is not on `PATH`. Install Git for Windows or add your `bash.exe` directory to `PATH`.

### `run-hook.cmd: missing script name`
`run-hook.cmd` was invoked with no `<script-name>` argument (for example, missing `session-start` or `risk-gate`).

### Works in terminal but not as a hook
Simulate how `cmd.exe` invokes the wrapper in PowerShell:

```powershell
$env:CLAUDE_PLUGIN_ROOT = "C:\path\to\bearpaws"
cmd /c "`"C:\path\to\bearpaws\hooks\run-hook.cmd`" session-start"
```

## Related Issues

- [anthropics/claude-code#9758](https://github.com/anthropics/claude-code/issues/9758) - `.sh` scripts open in editor on Windows
- [anthropics/claude-code#3417](https://github.com/anthropics/claude-code/issues/3417) - Hooks don't work on Windows
- [anthropics/claude-code#6023](https://github.com/anthropics/claude-code/issues/6023) - `CLAUDE_PROJECT_DIR` not found
