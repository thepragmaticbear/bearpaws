# Full-session benchmark

Measures what a user pays for an accepted result, not how large the skill files are. The primary metric is **cost per accepted task**: total model cost across all runs of an arm, divided by the runs that pass held-out acceptance tests.

## Usage

```bash
tests/benchmark/run.sh                                   # 3 runs x all scenarios x baseline,bearpaws
tests/benchmark/run.sh --runs 1 --scenarios small-bug    # quick smoke
SUPERPOWERS_DIR=/path/to/superpowers tests/benchmark/run.sh --arms "baseline bearpaws superpowers"
tests/benchmark/summarize.py /tmp/bearpaws-tests/benchmark/<stamp>/results.jsonl
```

Options: `--runs N`, `--arms`, `--scenarios`, `--model` (default `sonnet`, or `BENCH_MODEL`), `--budget` (USD cap per run, default 5), `--jobs` (parallel runs, default 3), `--out DIR`.

## How a run works

1. Copy `scenarios/<name>/repo` into a fresh git repo.
2. Run `claude -p` with the scenario prompt plus a fixed non-interactive suffix (same for every arm). `--setting-sources project,local` and `--strict-mcp-config` keep the user's installed plugins and MCP servers out of every arm; the arm adds only its own `--plugin-dir`.
3. Import `scenarios/<name>/accept.py` from a temp directory outside the repo and run it. The agent never sees it.
4. Append one JSON row to `results.jsonl`: accepted, cost, turns, tokens, skills invoked, subagents dispatched, whether the agent asked the user, seconds, and how many existing test files it modified or deleted.

Runs are interleaved by run index so time-of-day drift hits every arm alike.

## Scenarios

| Scenario | Measures |
|---|---|
| `small-bug` | Workflow overhead on a one-line fix |
| `simple-feature` | Implementation efficiency on a small, fully specified feature |
| `security-fix` | Risk handling: the acceptance tests include symlink and sibling-prefix escapes the prompt does not mention |

## Reading results

- Compare `$/accepted`, not raw cost: a cheap arm that fails costs the user a retry.
- Rows flagged "tests_touched" modified or deleted existing test files. Adding assertions is fine; weakening them is not. Inspect `runs/<scenario>/<arm>/<run>/work` before trusting that row.
- n=3 per cell is a smoke-level sample. Treat differences under ~30% as noise until repeated.

## Not covered yet

New subsystem, multi-file refactor, and forced-compaction scenarios from the roadmap. Superpowers needs a local checkout via `SUPERPOWERS_DIR`.
