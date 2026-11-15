# Cost by source — 2026-11-06

This splits each benchmark run's cost by where the billed tokens came from, over the preserved 2026-11-04 transcripts (no new runs). **The routine rise from $0.109 to $0.126 is mostly one scenario dispatching review where the control did not.** Review subagents (+$0.006 per run), the root agent's own output and re-reads (+$0.005) and the harness re-read on the extra calls (+$0.002) make up most of the $0.017 gap; `multi-file-refactor` alone accounts for $0.012 of it. The bootstrap costs about $0.003 per run in both arms, under 4% of the total. Root `Bash` output, which includes the `grep -rn` reads, moved by under $0.001.

The 2.4× gap against the earlier comparison plugin (2026-10-12) could **not** be split: that run's directories were emptied afterwards, so its transcripts are gone. Splitting it needs a new three-way run.

## Method

- `tests/benchmark/summarize.py --cost-sources RUNS_DIR` reads every `RUNS_DIR/<scenario>/<arm>/<n>/stream.jsonl` and prints mean USD per run by source, by arm and by scenario/arm. Logic: `cost_sources()`; tests: `CostSourceTests` in `tests/benchmark/test_integrity.py`.
- Prices are fitted, not assumed. Least squares over the 212 session records in these transcripts gives, per million tokens for `claude-sonnet-5-5`: input $2, output $10, cache read $0.10 (0.05× input), 5-minute cache write $2.50 (1.25×), 1-hour write $4 (2×). These reproduce every recorded `costUSD` to float precision. Cache reads are not counted at full price, and not at the 0.1× the handoff assumed either.
- Input-side cost is exact per API call (each assistant message's usage; the CLI repeats a message once per content block, and each id is charged once). Inside a root call, cache-read cost is shared over everything already in context, and write cost over what entered since the previous call, in proportion to estimated tokens. Tokens are estimated as characters divided by the stream's median characters-per-token of context growth. That ratio is low (median 1.9 over these runs) because tool-result framing and reminders add tokens the stream does not show, so most hidden overhead is spread over the visible sources. The split inside a call is an estimate.
- Sources:
  - `harness`: the first call's context minus the bootstrap: Claude Code's system prompt, tool schemas, the skill listing (which includes Bearpaws' skills) and the task prompt. It is fixed per call but re-read on every call, so its total grows with the number of calls.
  - `bootstrap`: the SessionStart `additionalContext`, sized at 3.5 characters per token (5285 bytes, about 1500 tokens). This is an estimate; no tokenizer was run.
  - `skills`: skill bodies loaded by the `Skill` tool.
  - `output`: the root agent's output tokens, plus re-reading its own earlier messages.
  - `Bash`, `Read`, `Grep`, `Edit`, `Agent`, `tools*`: tool results read by the root agent. `Agent` is the subagent's report as the root reads it.
  - `subagents`: every call inside a subagent thread (here all `bp:code-reviewer`).
  - `other`: context growth the median fit leaves over, on calls whose visible new content is small (hook reasons, reminders, fit residue). It is not a measure of hook text.
  - `unstreamed`: input cost in the session totals that no streamed call accounts for. 15 of 114 runs have some: API retries (two `resume-after-context-loss` runs with no subagents, where the missing call equals the first call's context) and calls in runs that dispatched subagents.
  - `overstreamed`: a negative correction for calls streamed after the last result event, which the recorded cost never counted. No run here has one.
- Streamed output token counts are partial (taken at stream start; median 24% of the true count), so each session's output cost, which is exact, is spread over its messages by visible size. Hidden thinking is spread the same way.
- Check: per-run sums equal the recorded `cost_usd` on all 114 runs (to $0.0001). One timed-out run (`risk-sql-sort/control/1`) has no result event and counts as $0, as in the results file. A run with a model missing from `PRICES` is skipped and named in the output.

## Routine suite (9 scenarios × 3 runs)

Arms: `control` = `main` at `2bfe625`; `bearpaws` = the reuse branch at `73915b0` with candidate (c) in place (since reverted). Mean USD per run.

| Source | Control | Candidate | Δ |
|---|---:|---:|---:|
| harness | 0.0563 | 0.0583 | +0.0020 |
| bootstrap | 0.0026 | 0.0027 | +0.0001 |
| skills | 0.0004 | 0.0019 | +0.0015 |
| output | 0.0292 | 0.0346 | +0.0054 |
| Bash results | 0.0025 | 0.0031 | +0.0006 |
| Read results | 0.0003 | 0.0000 | −0.0003 |
| Agent reports | 0.0027 | 0.0032 | +0.0005 |
| review subagents | 0.0137 | 0.0195 | +0.0058 |
| other | 0.0009 | 0.0013 | +0.0004 |
| unstreamed | 0.0004 | 0.0011 | +0.0007 |
| **total** | **0.1092** | **0.1258** | **+0.0166** |

Edit results are $0.0002 in both arms; Grep and other tools round to zero.

- `multi-file-refactor` dispatched a review in 3/3 candidate runs and 0/3 control runs: $0.179 against $0.075 per run. That is $0.0115 of the $0.0166 average gap. Its review adds subagents ($0.045), a longer root conversation (output +$0.031, harness +$0.017) and the report the root reads ($0.007).
- Per dispatch, review subagent cost was $0.046 control and $0.048 candidate on routine, $0.041 and $0.042 on risk (control's timed-out run counts $0, so its figure is slightly low). These are lower bounds: they leave out `unstreamed` and the report the root reads back, and 8 against 11 dispatches is too few to give a spread. On this evidence the rise comes from **more dispatches** (routine 8 → 11, risk 40 → 44) rather than pricier reviews; (c)'s instruction to grep the whole tree did not make a review visibly more expensive.
- Root `Bash` output, which holds the agent's own `grep -rn` and test runs, is $0.003 per run in both arms. The earlier guess that extra `grep -rn` reads drove the rise is not supported.
- `skills` rose $0.0015 because the candidate invoked `Skill` 5 times against 1. This data cannot say whether that is (c) or seed noise. The [noise-floor run](2026-11-06-noise-floor.md) covered only the risk suite: identical arms there differed by 14 against 11 invocations, so the risk suite's 2026-11-04 doubling (10 → 20) is outside that gap and unexplained. The routine count was not tested.

## Risk suite (6 scenarios × 5 runs)

| Source | Control | Candidate | Δ |
|---|---:|---:|---:|
| harness | 0.0647 | 0.0698 | +0.0051 |
| bootstrap | 0.0030 | 0.0032 | +0.0002 |
| skills | 0.0038 | 0.0075 | +0.0037 |
| output | 0.0512 | 0.0586 | +0.0074 |
| Bash results | 0.0029 | 0.0037 | +0.0008 |
| Agent reports | 0.0103 | 0.0115 | +0.0012 |
| review subagents | 0.0553 | 0.0615 | +0.0062 |
| other | 0.0018 | 0.0019 | +0.0001 |
| unstreamed | 0.0010 | 0.0018 | +0.0008 |
| **total** | **0.1943** | **0.2199** | **+0.0256** |

(Control's $0.1943 counts the timed-out run as $0, as the 2026-11-04 writeup's $0.194 does. Read, Edit and other tools are under $0.0003 in both arms.)

## What this says about where Bearpaws' cost goes

On a risk task the candidate run splits roughly: harness 32%, the agent's own output and re-reads 27%, review subagents plus the reports read back 33%, skills 3%, bootstrap under 2%, tool output under 2%. On routine tasks without a review: harness 50–76%, output 17–38%, bootstrap 2–4%, tool output under 3%.

- **Review dispatch is the lever.** Reviews and their reports are a third of a risk run, and a review also lengthens the root conversation, which re-reads the harness on every extra call. On routine, whether a scenario dispatches a review decides most of its cost. Dispatching reviews only where the risk policy requires them is worth more than making each review cheaper.
- **Turn count is a lever of its own.** The harness is paid on every call, so fewer root calls lower cost even when nothing else changes.
- **The bootstrap is not the problem.** At about $0.003 per run, cutting it in half saves under 1% of a risk run.
- **Cutting tool output would save almost nothing here.** Root tool results are under 3% of cost on these scenarios, so an output cutter, which would also break the rule that test failures are never compressed, has no target in this benchmark. Real repositories with longer outputs may differ.
- **The harness is mostly not Bearpaws'.** Claude Code's system prompt and tool schemas cost the same per call in every arm; Bearpaws adds its entries to the skill listing and, through extra turns, more calls.

## Read against the noise floor

The [same-version noise-floor run](2026-11-06-noise-floor.md) found two identical arms 13% apart on the risk suite, with 39 against 47 review dispatches, and the difference sitting in the same sources: output, review subagents and harness re-reads. So the risk-suite delta above (1.13×, 40 against 44 dispatches) is within noise. What this writeup establishes is **where** cost goes and which sources vary, not that candidate (c) raised it.

## Not done

- The gap against the earlier comparison plugin (transcripts not preserved).
- Whether the deltas exceed seed noise: see [2026-11-06-noise-floor.md](2026-11-06-noise-floor.md) for the risk suite. The routine figure is not tested by that run.
