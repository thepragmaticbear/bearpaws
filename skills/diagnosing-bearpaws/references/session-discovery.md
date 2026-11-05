# Session discovery (Claude Code)

Claude Code only. Other harnesses keep transcripts elsewhere or not at all: say so and stop.

## Where transcripts live

```text
~/.claude/projects/<project-dir>/<session-id>.jsonl                          main session, one JSON event per line
~/.claude/projects/<project-dir>/<session-id>/subagents/agent-<agentId>.jsonl  one per dispatched subagent
~/.claude/projects/<project-dir>/<session-id>/subagents/agent-<agentId>.meta.json  agentType, description, toolUseId
```

`<project-dir>` is the session's cwd with every character that is not a letter or digit replaced by `-`:
`/Users/me/repos/app/.claude/worktrees/x` → `-Users-me-repos-app--claude-worktrees-x`. A session started
in a worktree lives under the worktree's dir, not the main checkout's. If your partner names another
root (a copied `projects/` dir), use it the same way.

```bash
ls -t ~/.claude/projects/<project-dir>/*.jsonl | head        # newest first
ls ~/.claude/projects/<project-dir>/<session-id>/subagents/    # its subagents, if any
wc -l <transcript>                                             # always, before reading
```

## Matching a session

"My last session" is the newest file by mtime in the project dir, but the session you are in now is
also there: exclude your own session id. Confirm with your partner by quoting the first prompt and its
timestamp:

```bash
jq -c 'select(.type=="user" and (.message.content|type)=="string" and (.isMeta|not))
       | {timestamp, prompt: .message.content[0:200]}' <transcript> | head -1
```

With several candidates, list each file's first prompt and timestamp the same way and ask which.

## Event shape (keys, not content)

- Every line has `type`. Conversation lines are `user`, `assistant`, `system`, `attachment`; bookkeeping
  lines include `permission-mode`, `mode`, `file-history-snapshot`, `last-prompt`, `ai-title`, `cost-state`.
- Conversation lines carry `uuid`, `parentUuid`, `sessionId`, `timestamp`, `cwd`, `gitBranch`, `isSidechain`.
- `assistant`: `.message.content[]` blocks of `text`, `thinking` or `tool_use` (`id`, `name`, `input`);
  `.message.usage` has token counts.
- Tool results arrive as `user` lines: `.message.content[]` holds a `tool_result` block (`tool_use_id`,
  `content`, `is_error`) and `.toolUseResult` holds the tool's structured result (Bash: `stdout`,
  `stderr`, `interrupted`). `is_error: false` means the command exited 0; with a pipe that is the exit
  of the last stage, so read the output text too.
- A subagent dispatch is a `tool_use` named `Agent` (older: `Task`) with `subagent_type`, `description`,
  `prompt`. Its result's `.toolUseResult.agentId` names the subagent file; the `.meta.json` `toolUseId`
  points back to the dispatch.
- `cost-state` (when present) holds session totals: `totalCostUSD`, `totalDuration`, `totalAPIDuration`,
  `totalToolDuration` (ms), `modelUsage`.
- Your partner's own words are `user` lines with no `tool_result` block and no `isMeta`.
