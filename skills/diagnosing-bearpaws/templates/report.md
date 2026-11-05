# Diagnosis: <session-id>

## Problem statement

<One line: which session, what was expected, what happened, the observable.>

## Sessions read

- <absolute transcript path> — <N> lines, first prompt "<first 80 chars>" at <timestamp>
- <absolute subagent transcript path> — <N> lines, <agentType>

## Findings by dimension

Every finding: `- [severity] claim — path:line — "evidence quote ≤ 1 line"`. A dimension with nothing
to report says `No findings.` as plain text, not a list item.

### Receipt vs transcript

### Quality evidence

### Plan adherence

### Request conflicts

### Cost and time

## Receipt reconciliation

One row per receipt line. Every row cites the receipt line and the transcript line that confirms or
contradicts it.

| Receipt line (path:line) | Transcript shows (path:line) | Holds? |
|---|---|---|

## Coverage

What was not read or could not be checked (subagent transcripts skipped, lines truncated, the
project itself not run).

## Verdict

<Two or three sentences: what happened, in order, and whether the receipt was honest. Name any fix
here; do not apply it.>
