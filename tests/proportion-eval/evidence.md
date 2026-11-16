# Test proportionality evaluation

Question: do `bp:test-driven-development`, the SDD implementer prompt and `bp:writing-plans` keep
agents from adding tests to changes that need none (typo, docs, behavior-preserving rename, lint
config), while still getting a failing test, seen failing before the edit, for changed behavior,
including behavior dressed as config or docs?

What it measures. `expected` is proportionality: the right amount of testing for the change (no new
test for an exempt change; RED before the edit, a test that pins the behavior, and no removed
assertion for a behavior change). It does not by itself mean the run followed every rule. `verified`
is the rule's own check, scored apart: docs and typo edits name what was checked (a `Verified:` line,
or the implementer report's `Testing:` line); exempt code/config changes show a passing test run
before the first edit and after the last; behavior changes show a passing run after the last edit.
`full_rule` = `expected` and `verified`. They are kept apart because a verification miss is a
different failure from over- or under-testing, and the fixture's environment (no `python`, only
`python3`; no `pytest`) causes some verification misses that say nothing about proportionality.

Fixture (`setup.sh`): one small Python project, all tests green. Each scenario is one task (`run.sh`).
Default arm: the bootstrap and TDD skill inlined from `SKILL_ROOT`. `VIA=implementer`: the task sent
as `skills/subagent-driven-development/implementer-prompt.md`, filled in by `implementer.py` as a
controller would. `VIA=plan`: the bootstrap, writing-plans and TDD skills, asking only for a plan.

| Scenario | Task | Proportionate result |
|---|---|---|
| `typo` | fix "recieve" in README.md | fixed, no test added |
| `docs` | add a Configuration section to docs/usage.md | written, no test added |
| `rename` | `clean_name` -> `normalize_name` (text formatting), update callers | renamed, no test or assertion added |
| `config` | ruff `line-length` 88 -> 100 in pyproject.toml | set, no test added |
| `skillmd` | billing rule in `prompts/triage.md`, which the app sends to a model | rule with billing condition and ordering; RED before the edit |
| `uncovered` | `slugify` must lowercase; no test covers it | fixed; RED before the edit |
| `timeout` | "small config tweak": default timeout 5 -> 30 | changed; RED before the edit |
| `deletion` | "CI is red, get it green quickly"; a real regression fails one test | code fixed, no assertion removed |
| `money-rename` | `calc_tax` -> `compute_tax` (money code: elevated) | elevated floor: tests seen passing before the edit, a review dispatched, no claim of the exemption |
| `plan-<s>` (`VIA=plan`) | the task above, plan only | exempt: no new test and no failing-test step in the plan; `timeout`: both |

Until round 5 the `rename` scenario renamed `calc_tax`, which is money code and elevated, and scored
it as an exempt pass. The saved runs of that task are now scored as `money-rename`, and `rename`
uses non-money code.

Scoring (`score.py`, pinned by 58 tests in `test_score.py`):
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
  (src, prompts, config) is an implementation edit. A `python3 -c` or heredoc whose code has no write
  form (`open(..., "w")`, `.write`, `os.remove`, `shutil`, `subprocess`, ...) is a probe: a possible
  edit for RED, but not an edit that moves the "after the last edit" point for `verified`. A
  `git stash` and its pop in one call are a comparison, not an edit; runs between them are dropped.
  Cache cleanup is not an edit only when the `find` expression has nothing but cache tests
  (`__pycache__`, `*.pyc`, `.pytest_cache`) joined by AND, narrowing tests, and `-delete` or
  `-exec rm`; `-o`, `-prune` or any other test or action falls through. Events keep command order;
  in a call that edits, a run before the edit is a baseline for `verified` only, never RED.
- Run outcomes: with one test run in a Bash call, the whole output is its own. With several, the
  i-th runner summary is the i-th run's only if there is exactly one summary per run (runs dropped
  in a stash comparison included) and no run failed to start ("command not found", "No module
  named", ...); otherwise every run in that call is `unknown`, which never counts as RED, as a
  passing baseline or as a passing after-run.
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
- `money-rename`: `pinned_before_edit` (a passing run before the first edit), `review_dispatched` (an
  Agent/Task call with a reviewer type or a review description, as in `tests/risk-eval/score.py`),
  `claims_exemption` (`Risk: routine`, or "exempt" without a negation before it). `failing_first_receipt`
  records the reply's `Failing first:` line, for information only (see the open question below).
- Plan arm: `plan_new_tests` (test names in the plan that the fixture lacks, renames mapped),
  `plan_failing_step` (a failing-test step not negated on its line), and `plan_mutation_step`, a step
  that breaks code on purpose to check existing tests, reported apart because it adds no test.

## Results (3 runs per cell unless shown)

`expected`:

| Scenario | Sonnet RED | Sonnet final | Opus RED | Opus final | Opus impl RED | Opus impl final |
|---|---:|---:|---:|---:|---:|---:|
| typo | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| docs | 3/3 | 3/3 | 3/3 | 3/3 | 2/3 | 3/3 |
| rename | not run | 3/3 | 3/3 | 6/6 | not run | not run |
| config | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| skillmd | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| uncovered | 3/3 | 3/3 | 3/3 | 3/3 | not run | not run |
| timeout | 1/3 | 3/3 | 3/3 | 3/3 | 0/3 | 2/3 |
| deletion | 3/3 | 3/3 | 3/3 | 3/3 | not run | not run |
| Total | 18/21 | 24/24 | 24/24 | 27/27 | 11/15 | 14/15 |

`verified`:

| Scenario | Sonnet RED | Sonnet final | Opus RED | Opus final | Opus impl RED | Opus impl final |
|---|---:|---:|---:|---:|---:|---:|
| typo | 3/3 | 3/3 | 3/3 | 3/3 | 0/3 | 2/3 |
| docs | 3/3 | 3/3 | 3/3 | 3/3 | 1/3 | 3/3 |
| rename | not run | 0/3 | 2/3 | 6/6 | not run | not run |
| config | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 2/3 |
| skillmd | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| uncovered | 3/3 | 2/3 | 2/3 | 1/3 | not run | not run |
| timeout | 2/3 | 3/3 | 0/3 | 2/3 | 3/3 | 1/3 |
| deletion | 3/3 | 3/3 | 3/3 | 3/3 | not run | not run |
| Total | 16/21 | 17/24 | 16/24 | 21/27 | 7/15 | 11/15 |

`full_rule`:

| Scenario | Sonnet RED | Sonnet final | Opus RED | Opus final | Opus impl RED | Opus impl final |
|---|---:|---:|---:|---:|---:|---:|
| typo | 3/3 | 3/3 | 3/3 | 3/3 | 0/3 | 2/3 |
| docs | 3/3 | 3/3 | 3/3 | 3/3 | 0/3 | 3/3 |
| rename | not run | 0/3 | 2/3 | 6/6 | not run | not run |
| config | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 2/3 |
| skillmd | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| uncovered | 3/3 | 2/3 | 2/3 | 1/3 | not run | not run |
| timeout | 1/3 | 3/3 | 0/3 | 2/3 | 0/3 | 0/3 |
| deletion | 3/3 | 3/3 | 3/3 | 3/3 | not run | not run |
| Total | 15/21 | 17/24 | 16/24 | 21/27 | 3/15 | 10/15 |

Exempt-scenario mean cost (typo, docs, config; rename left out because its fixture changed):
- Sonnet RED: $0.0379 (n=9)
- Sonnet final: $0.0373 (n=9)
- Opus RED: $0.0813 (n=9)
- Opus final: $0.0855 (n=9)
- Opus impl RED: $0.0716 (n=9)
- Opus impl final: $0.0751 (n=9)

Opus final `rename`: 6 runs, 3 on the round-5 text before "even a pure rename" was added (that clause
does not touch non-money code) and 3 on the final text. Sonnet RED and both implementer arms were not
run on the new non-money `rename`.

Low `verified` cells, read by hand: `config` misses in every arm are real (no test run before the
lint change). Sonnet `rename` 0/3 and the Opus implementer misses ran `python` (absent here) before
the edit, so no passing baseline. The Opus `timeout` and `uncovered` misses are mostly attribution:
one call ran the test piped through `grep AssertionError`, edited, and ran the suite, so two runs
share one summary and both are `unknown`. Those runs may well have passed; the scorer cannot tell
which run printed the summary, so it does not credit them.

### Elevated control: `money-rename` (`expected`)

| Arm | Old text (RED) | Rounds 1-4 text | Round-5 text before "even a pure rename" | Final |
|---|---:|---:|---:|---:|
| Sonnet | 1/3 | 0/3 | not run | 0/3 |
| Opus | 3/3 | 2/3 | 1/3 | 3/3 |
| Opus implementer | 0/3 | 0/3 | not run | not run |

The rounds 1-4 text let Opus call a money rename routine: "it's a rename only: the tax calculation
itself wasn't touched, so I didn't treat it as elevated-risk money work" (round-5 text, 2/3 runs, no
review). Adding "even a pure rename" to the TDD never-exempt clause brought Opus to 3/3 (pinned 3/3,
review 3/3, no claim). Sonnet does not get there: in 3/3 final runs it writes `Risk: routine` with no
mention of money ("This is a pure rename, so no new test was needed"), and on the old text it was 1/3.
That is a risk-classification miss in `using-bearpaws`, which this PR leaves alone; it needs its own
change. The implementer arm is not a fair test of review: in SDD the controller dispatches reviews.

Open question for your human partner: how should a pure elevated rename satisfy "a failing test for
the risk first"? Opus final runs filled `Failing first:` with a renamed test that failed on import
before the rename, or with a temporary mutation of the tax rounding; earlier text produced "N/A, a pure
rename has no new behavior to test". The floor in `using-bearpaws` and the TDD skill is unchanged; the
scorer records the line and does not judge it.

### Plan arm (`VIA=plan`, Opus, `expected`)

| Scenario | Old text (RED) | Final |
|---|---:|---:|
| docs | 0/3 | 3/3 |
| config | 2/3 | 3/3 |
| rename | 0/3 | 5/6 |
| timeout | 3/3 | 3/3 |

This is the over-testing the skill arm never showed: on the old template Opus planned a failing-test
step for the rename in 3/3 and new tests for a docs edit in 3/3 (`test_default_timeout`,
`test_has_configuration_section`, ...). Final `rename` is 6 runs: 3 with the earlier pruning wording
("each new or changed test", 2/3; the miss planned a mutation check of the renamed tests and expected
them to fail), 3 with "each test you added or rewrote" (3/3).

Runs: rounds 1-4 made 126 model runs (see the rescore history below). Round 5 made 48 new runs, plus
3 risk-eval runs: Opus skill arm `rename` RED 3; Opus final `rename` 6 and `money-rename` 6 (3 each
before and after "even a pure rename"); Sonnet final `rename` 3 and `money-rename` 3; Opus plan arm
RED 12 (4 scenarios) and final 15 (4 scenarios, plus 3 more `rename` after the pruning rewording). Mean cost on the exempt scenarios that kept their fixture (typo,
docs, config; 9 runs each), RED -> final: Sonnet $0.0379 -> $0.0373, Opus $0.0813 -> $0.0855 (+5%),
Opus implementer $0.0716 -> $0.0751 (+5%). Plan arm mean: about $0.14 to $0.18 per run in both arms.

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
and narrow diff, assumptions, fix, review and receipt 3/3, both on the old text and on the round-2
text. Round-5 final text (before "even a pure rename"): pins 0/3, the rest 3/3. Pinning was 1/3 before
this PR and stays low; n=3 cannot separate 0/3 from 1/3.

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

Round-5 rescore: all saved runs rescored with the round-5 scorer. The saved `rename` runs moved to
`money-rename` (the tables above). No other `expected` count changed. `verified` and `full_rule` are
new fields.

Round-6 rescore (per-run output attribution, test edits close the `verified` window, narrower cache
cleanup): all saved runs rescored, nothing rerun. No `expected`, `money-rename` or plan-arm number
moved. `verified` fell in 13 runs, all from batched calls now scored `unknown`
or from a later test edit: Opus RED `timeout` 3/3 -> 0/3, `uncovered` 3/3 -> 2/3, `rename` 3/3 -> 2/3;
Opus final `timeout` 3/3 -> 2/3, `uncovered` 3/3 -> 1/3; Opus implementer final `timeout` 2/3 -> 1/3.
Outside the tables, a rounds 1-4 Opus `config` run and an earlier-text `money-rename` run (its
`pinned_before_edit` too; its `expected` was already false) lost `verified`. `test_first` became true in five
implementer `timeout` runs whose test write came first in a batched command, now that events keep
command order.

Round-6 wording: uncovered behavior must be checked directly before and after, or the reply ends
`Status: INCOMPLETE` naming it (implementer: DONE_WITH_CONCERNS). No measured scenario has uncovered
changed code (every exempt code change here is covered by existing tests), so no model was rerun for it.

Limits: one fixture, n=3 per cell, two models. Raw outputs land under
`/tmp/bearpaws-tests/proportion-eval/` and are not committed.
