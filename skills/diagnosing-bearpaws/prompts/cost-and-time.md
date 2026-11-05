# Dimension: cost and time

Measure where the session's time and tokens went.

Look for:
- Session totals: the `cost-state` line (`totalCostUSD`, `totalDuration`, `totalAPIDuration`,
  `totalToolDuration`, `modelUsage`) if present; otherwise first and last `timestamp`.
- The longest gaps between consecutive timestamps, and what ran there (tool, subagent, retries).
- Repeated work: the same command or file read many times, edit-run loops on one failure,
  subagents re-dispatched for the same task.
- Large tool results (lines over 100 KB: `awk '{ if (length($0) > 100000) print NR": "length($0) }'`).
- Subagent cost: per-agent token usage from their transcripts' `message.usage`.

You may not claim: a cost, duration or count you did not compute from the transcript with a command
you ran; a cause for slowness without the lines that show it.
