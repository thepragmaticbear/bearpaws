# Full-session benchmark

Measures what a user pays for an accepted result, not how large the skill files are. The primary metric is **cost per accepted task**: total model cost across all runs of an arm, divided by the runs that pass held-out acceptance tests.

## Usage

```bash
tests/benchmark/run.sh                                   # 3 runs x all scenarios x baseline,bearpaws
tests/benchmark/run.sh --runs 1 --scenarios small-bug    # quick smoke
SUPERPOWERS_DIR=/path/to/superpowers tests/benchmark/run.sh --arms "baseline bearpaws superpowers"
tests/benchmark/run.sh --arms "old=/path/to/previous/checkout bearpaws"   # compare two versions
tests/benchmark/run.sh --interactive                     # no "don't ask me" suffix: measures interruptions
tests/benchmark/summarize.py /tmp/bearpaws-tests/benchmark/<stamp>/results.jsonl
```

Options: `--runs N`, `--arms`, `--scenarios`, `--model` (default `sonnet`, or `BENCH_MODEL`), `--budget` (USD cap per run, default 5), `--jobs` (parallel runs, default 3), `--out DIR`, `--allow-unisolated`.

macOS runs use native `sandbox-exec` by default. Other platforms require `--allow-unisolated`, which labels each row `checker_isolation=integrity_only`. A failed native sandbox launch records an unhealthy, unaccepted run; it never silently falls back.

Each scenario/arm/run directory must be new. Existing directories are refused without deleting them or appending a duplicate row.

## How a run works

1. Copy `scenarios/<name>/repo` into a fresh git repo, then run `scenarios/<name>/setup.sh` if present (seeds history, e.g. an interrupted plan).
2. Run `claude -p` with the scenario prompt plus a fixed non-interactive suffix (same for every arm). `--setting-sources project,local` and `--strict-mcp-config` keep the user's installed plugins and MCP servers out of every arm; the arm adds only its own `--plugin-dir`.
3. Snapshot `scenarios/<name>/accept.py` before the agent starts. The macOS sandbox denies agent writes to this benchmark's source directory and denies reads of its acceptance files and all reads/writes of the snapshot directory. Load the snapshot by its absolute path after the session, preventing `work/accept_hidden.py` shadowing. SHA-256 fingerprints before/after the session and checks detect persistent source or snapshot changes.
4. Run the repo's visible suite again (regressions).
   Both evaluator processes use Python `-I` and preload stdlib unittest before adding the work directory for source imports, preventing cwd `sitecustomize.py` and `unittest.py` startup shadowing.
5. Append one JSON row to `results.jsonl`: acceptance-suite status, accepted (healthy session, acceptance success, visible suite success, and unchanged fixtures), share of acceptance test methods passed, cost, turns, tokens, root subagent dispatches, review requests/returns, user questions, seconds, lost test lines, completion-claim heuristic, and missed gates. Skipped acceptance tests do not count as passed and invalidate acceptance. Missing/error result events or nonzero CLI exit invalidate acceptance.

Cost is cumulative within a Claude session: use the largest `total_cost_usd` per `session_id`, then sum sessions. Turns and token usage are segment values and are summed across root result events. Summaries expose input, output, cache-read, and cache-write totals separately. `accept_fraction` measures test methods, not requirement coverage; failed subtests count their parent method once.

Runs are interleaved by run index so time-of-day drift hits every arm alike.

## Scenarios

| Scenario | Measures |
|---|---|
| `small-bug` | Workflow overhead on a one-line fix |
| `simple-feature` | Implementation efficiency on a small, fully specified feature |
| `security-fix` | Risk handling: the acceptance tests include symlink and sibling-prefix escapes the prompt does not mention |
| `security-fix-injected` | Same fix, but CONTRIBUTING.md tells agents to skip tests and review (trust boundary) |
| `new-subsystem` | Planning: an LRU cache with TTL and stats, then wiring it into existing code |
| `multi-file-refactor` | Context management: consolidate three disagreeing formatters to one reference behavior |
| `broken-test-config` | Verification trust: the failing test exists but test discovery never runs it |
| `conventions` | Onboarding: CONTRIBUTING.md rules the prompt does not mention (error type, logger, file layout) |
| `resume-after-context-loss` | Recovery: a seeded half-finished plan and a stale summary that overstates progress |

## Reading results

- Compare `$/accepted`, not raw cost: a cheap arm that fails costs the user a retry.
- Rows flagged "tests_touched" modified or deleted existing test files. Adding assertions is fine; weakening them is not. Inspect `runs/<scenario>/<arm>/<run>/work` before trusting that row.
- Review requests are root `Agent`/`Task` calls with explicit review wording in type, description, or prompt. Returns require a nonerror synchronous tool result or a completed task notification with a summary; an asynchronous launch alone does not count. This proves transcript evidence, not reviewer independence or quality. Completion and INCOMPLETE classification are text heuristics; inspect flagged final responses.
- n=3 per cell is a smoke-level sample. Treat differences under ~30% as noise until repeated.

## Limits

- `resume-after-context-loss` seeds the interrupted state rather than forcing a real compaction: turn caps in `claude -p` are too coarse to stop a session mid-plan reliably.
- Scenarios are small enough that a capable model passes all of them without a plugin; they separate arms on cost and process (review, interruptions), not on correctness.
- Superpowers needs a local checkout via `SUPERPOWERS_DIR`.
- Checker isolation protects this benchmark's definitions, not the entire host. It is inherited by agent subprocesses, but does not protect other checkouts or prevent malicious agent-written Python from interfering with the evaluator. The agent may read unrelated host files under `bypassPermissions`; use only disposable, nonsensitive environments.
- Native confinement denies writes under the output directory except this agent's task worktree. Unsandboxed controller recorders capture stdout/stderr through pipes, preserving the CLI exit status. This protects transcripts, sibling runs, and the aggregate ledger from direct agent overwrites. Cost and process metadata still depend on what the CLI reports; unisolated runs do not have recorder protection.
- `--allow-unisolated` provides detection only. It cannot stop an agent reading acceptance definitions or changing and restoring files between fingerprints. Historical rows have unknown CLI exit, fixture integrity, and isolation; rescoring transcripts cannot retroactively supply those guarantees.

Offline integrity checks (no model calls):

```bash
python3 -m unittest discover -s tests/benchmark -p 'test_*.py'
BENCH_TEST_SANDBOX=1 python3 -m unittest discover -s tests/benchmark -p 'test_*.py'  # macOS, outside an outer sandbox
```
