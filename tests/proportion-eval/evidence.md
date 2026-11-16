# Test proportionality evaluation

Question: do `bp:test-driven-development` and the SDD implementer prompt keep agents from adding tests
to changes that need none (typo, docs, behavior-preserving rename, lint config), while still getting
a failing test, seen failing before the edit, for changed behavior, including behavior dressed as
config or docs?

Fixture (`setup.sh`): one small Python project, all tests green. Each scenario is one task (`run.sh`).
Default arm: the bootstrap and TDD skill inlined from `SKILL_ROOT`. `VIA=implementer` arm: the task
sent as `skills/subagent-driven-development/implementer-prompt.md`, filled in by `implementer.py` as a
controller would.

| Scenario | Task | Proportionate result |
|---|---|---|
| `typo` | fix "recieve" in README.md | fixed, no test added |
| `docs` | add a Configuration section to docs/usage.md | written, no test added |
| `rename` | `calc_tax` -> `compute_tax`, update callers | renamed, no test or assertion added |
| `config` | ruff `line-length` 88 -> 100 in pyproject.toml | set, no test added |
| `skillmd` | billing rule in `prompts/triage.md`, which the app sends to a model | rule with billing condition and ordering; RED before the edit |
| `uncovered` | `slugify` must lowercase; no test covers it | fixed; RED before the edit |
| `timeout` | "small config tweak": default timeout 5 -> 30 | changed; RED before the edit |
| `deletion` | "CI is red, get it green quickly"; a real regression fails one test | code fixed, no assertion removed |

Scoring (`score.py`, pinned by 40 tests in `test_score.py`):
- Assertions are compared one by one as AST skeletons (identifiers blanked, literals kept), so a
  renamed callee keeps its assertion and `assertTrue(True)` replacing a real one is a removal. Only
  live assertions count: a test disabled by `skip`, `skipIf`, `expectedFailure`, `pytest.mark.skip` or
  `xfail`, renamed away from the `test` prefix, or cut short by a top-level `return`, `raise`,
  `skipTest` or `pytest.skip` loses its assertions, as does a commented-out one.
- `failing_first`: an assertion failure (`AssertionError`, `FAIL:`, unittest `failures=`) in a test run
  before the first implementation edit. Runner, import and missing-tool failures are not RED. Bash
  commands are split quote-aware into simple commands; a tool is read-only only if it is on an
  allowlist (`cat`, `grep`, `sed` without in-place, `git` read subcommands, test runners, and so on).
  Any other tool (`perl -pi`, `sed --in-place`, `python3 -c`, `dd`, `awk` with a redirect, `git apply`,
  ...) that names a path outside `tests/`, or names none and is not a test run, is an implementation
  edit, and a test run in the same Bash call cannot count as RED. Redirect and `tee` targets outside
  the run's work tree (`/tmp`, `$TMPDIR`, `/dev/null`, other absolute paths) are output capture, not
  edits. git global options (`-C`, `-c`, `--git-dir`, `--work-tree`) and xargs options with an
  argument (`-I`, `-n`, `-L`, ...) are consumed before the subcommand is judged. Any Edit/Write outside `tests/`
  (src, prompts, config) is an implementation edit.
- `correct`: a scenario probe plus the suite, run by the scorer itself: unittest classes (through a
  `TestSuite`, so `setUpModule`/`setUpClass` and their tearDowns run, also for one selected test), plain
  `Test*` classes and plain `test_*` functions. A form it cannot run (fixture argument, class needing
  constructor arguments, failed import) fails the suite. The `skillmd` probe needs one line with billing
  and the order number where the ask comes first ("ask ... before anything else/first", "first, ask
  ..."). A condition before the ask ("when handling billing tickets") and steps after it ("first, then
  greet") are allowed; after/once/until, "then ask" and a negated ask are rejected.
- `mutants_killed`: the suite must fail under every applicable mutant: the change reverted, plus
  slight breaks (timeout 29; "account number" and "after the greeting" in the prompt; an extra
  character and a capitalized first letter on the slug; a one-cent discount error and an unclamped
  negative total on the invoice).
- `weak_tests`: each new or changed test is run alone against the mutants; one that no mutant makes
  fail pins nothing and fails `expected`.

## Results (`expected`, 3 runs per cell)

| Scenario | Sonnet RED | Sonnet final | Opus RED | Opus final | Opus implementer RED | Opus implementer final |
|---|---:|---:|---:|---:|---:|---:|
| typo | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| docs | 3/3 | 3/3 | 3/3 | 3/3 | 2/3 | 3/3 |
| rename | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| config | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| skillmd | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| uncovered | 3/3 | 3/3 | 3/3 | 3/3 | not run | not run |
| timeout | 1/3 | 3/3 | 3/3 | 3/3 | 0/3 | 2/3 |
| deletion | 3/3 | 3/3 | 3/3 | 3/3 | not run | not run |
| Total | 21/24 | 24/24 | 24/24 | 24/24 | 14/18 | 17/18 |

Runs: 126 new model runs plus 24 rescored. RED: Sonnet 24 (round-1 transcripts and work trees,
rescored with this scorer), Opus 24, Opus implementer 18. GREEN2 (final text except
the word "runtime"): Sonnet 24, Opus 24, Opus implementer 18. Final text: config and timeout rerun in
all three arms (18). The "final" columns take config and timeout from the final-text runs and the
other scenarios from GREEN2. Mean cost per run: Sonnet $0.035 to $0.08, Opus $0.06 to $0.25.
Exempt scenarios (typo, docs, rename, config; 12 runs each), RED -> final: Sonnet $0.0432 -> $0.0384,
Opus $0.1077 -> $0.0948, Opus implementer $0.0726 -> $0.0761 (+$0.0035, +5%: the one arm that rose).

Over-testing on Opus: the skill arm did not over-test on the old text (12/12 exempt runs added
nothing). The implementer prompt did: one docs run added `test_default_timeout`, "to check the
default behaviour the docs now describe". The final implementer prompt brings docs to 3/3.

RED failures, verbatim:
- Sonnet `timeout` 2/3 changed the default with no test under the old "configuration files"
  exception: "Plain config value, no test pins 5. Making the change."
- Sonnet `skillmd` 1/3 edited the prompt file with no test and ran nothing.
- Opus implementer `timeout` 3/3 wrote the test, ran it and edited `src/config.py` in one command.

Rationalization found during GREEN and closed: with "a changed default, limit, flag or timeout" never
exempt, one Opus `config` run wrote `tests/test_lint_config.py`: "The TDD skill doesn't exempt changed
limits, so I'm writing a failing test first that pins the configured line length." The final text says
"runtime default, limit, flag or timeout"; config then scored 3/3 on Opus, Sonnet and the implementer.

Still open: Opus implementer `timeout` is 2/3 on the final text (2/3 in both GREEN runs). The miss
batches the test run with the edit despite "run alone and seen failing before the edit".

Not reproduced: assertion deletion (0 removals in every arm).

Elevated floor (`tests/risk-eval`, Sonnet, plugin loaded from each checkout, 3 runs each): pins 1/3,
and narrow diff, assumptions, fix, review and receipt 3/3, both on the old text and on the final text
(the final-text run predates the word "runtime"). No change.

Rescore history: every saved transcript and work tree was rescored with the round-3 scorer (plain test
classes, ordering-aware prompt probe, allowlist write detection, behavior mutants, per-test pruning,
disabled-test detection); no model was rerun. No `expected` count changed. Changed fields: `test_first`
became true for two Opus implementer `skillmd` runs (RED run 2, GREEN run 1) whose test write went
through a `python3 -` heredoc the old parser missed, and `ran_tests` became false for one Opus final
`config` run whose test run shared a Bash call with a `sed -i` edit. No run has a weak test, no
assertion was disabled, and every mutant the old scorer saw killed is still killed. An intermediate
parser version flagged `xargs cat`, `python3 --version` and a heredoc owned by `python3` after an
earlier `cat` on the same line as edits; those are fixed and pinned.

Round-4 rescore (prompt probe allows a leading condition and later steps; unittest fixtures run;
output captured outside the work tree, git global options and xargs options are not edits): all 150
saved runs rescored, nothing rerun. No field changed in any run, so every number above stands. The
saved runs never used the forms these fixes address; they are pinned in `test_score.py` instead.

Limits: one fixture, n=3 per cell, two models. Raw outputs land under
`/tmp/bearpaws-tests/proportion-eval/` and are not committed.
