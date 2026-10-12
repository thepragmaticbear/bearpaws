# Design: Follow-ups after v2.6.0

Date: 2026-10-12
Status: Approved (brainstorming)

## Branch 1, `feat/bench-tooling` (model-free)

### #3 Per-session timeout

- `tests/benchmark/run.sh` gains `--session-timeout SECONDS`, default 900.
- The `claude` session, including any `sandbox-exec` wrapper, runs under a small Python supervisor:
  - It uses `subprocess.Popen(..., start_new_session=True)` and `wait(timeout)`.
  - On timeout it sends `os.killpg` SIGTERM, waits 10 s, sends SIGKILL, and exits 124.
  - Killing the whole process group also kills agent-spawned polling loops.
- `summarize.py --record` gains `--timed-out true|false`.
  - The row records `timed_out`.
  - `session_ok` is false when the session timed out, so a timed-out run is never accepted.
- The by-arm summary prints a `timeouts` count.

### #4 The scorer reads `Status:` across all replies

- `parse_stream` keeps every `result` text in order.
- `reported_incomplete` is computed over all of them joined, so the last `Status:` line across the session decides, matching the hook's single-reply rule.
- `unsupported_claim` still uses the final reply.
- Add an addendum to `docs/benchmarks/2026-10-12-escaped-defects.md` that rescores the C data and the review-findings data with the new rule. The published pre-registered headline stays unchanged.

## Branch 2, `feat/gate-bash` (elevated: a hook in every Claude Code session)

### #2 The risk gate records Bash edits

- **Matcher.** The `record` mode also handles `Bash`, and the hooks.json PostToolUse matcher adds `Bash`.
- **Fingerprint.** After every recorded tool call (Edit, Write, MultiEdit, NotebookEdit, Bash), compute a tree fingerprint for the hook input's `cwd`:
  - Run it only when `git -C "$cwd" rev-parse --is-inside-work-tree` succeeds. Outside git, skip it and fail open.
  - The fingerprint is the SHA-1 of two things:
    - `git -C "$cwd" diff HEAD --no-ext-diff --no-color`;
    - for each `git ls-files -o --exclude-standard` path, the path, size and mtime.
  - Paths under `__pycache__/`, `.pytest_cache/`, `node_modules/`, `.mypy_cache/`, `.ruff_cache/` or `.venv/`, and paths ending in `.pyc`, are excluded.
  - On a repo with no commits, diff against the empty tree.
- **Logging.**
  - The log stores the latest fingerprint as a `tree <sha>` line.
  - On a Bash call: if the fingerprint differs from the last stored `tree`, append `edit (bash)`, then append the new `tree <sha>`. If it is unchanged, append nothing.
  - On Edit, Write, MultiEdit and NotebookEdit: keep today's `edit <path>` line, then append `tree <sha>`.
  - `stop` ignores `tree` lines. The sensitive-path nudge cannot see Bash-edited paths, which is acceptable and documented.
- **Re-review (#1).** "A review was dispatched after the last edit" now covers Bash edits, so a post-review fix made through Bash forces a new review in Claude Code. No skill wording is added.
- **Performance.** At most two git calls per Bash call. Keep the hook's 10 s timeout; fail open on any git error.

## Evaluation

- **Branch 1:** `test_integrity.py` cases:
  - a fake claude that sleeps past a 2 s timeout is killed, scored `timed_out`, and not accepted;
  - its spawned grandchild loop is also gone;
  - the multi-reply Status cases.
- **Branch 2:** RED-first cases in `tests/hooks/run-risk-gate-tests.sh`, each using a temp git repo:
  - a heredoc write via Bash becomes `edit (bash)`, and the stop blocks without a receipt;
  - a Bash test run that only creates `__pycache__` is not an edit;
  - Edit, then review, then Bash `pytest`, then an elevated COMPLETE is allowed;
  - Edit, then review, then a Bash `sed -i` fix, then an elevated COMPLETE is blocked;
  - a non-git cwd never records `edit (bash)`;
  - a git failure fails open.
- **Live probe:** a session that writes a file only via Bash heredoc must be blocked at Stop until it adds a receipt.
- **Measurement:** rerun the frozen risk suite, Bearpaws arm only, 30 runs (about $9), using both branches. Report escapes, re-review counts, cost, timeouts, and the multi-reply rescoring, against the review-findings run.
