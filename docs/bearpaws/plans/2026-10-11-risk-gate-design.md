# Design: Enforced Risk Gate and Risk Receipt

Date: 2026-10-11
Status: Approved (brainstorming)
Target release: 2.6.0

## Goal

Turn the elevated-risk floor from an instruction into a Claude Code–enforced gate, and give every code-editing turn a visible, structured completion block (the risk receipt). The gate targets the failure the three-way benchmark measured: two of six security runs ended without a review and without declaring INCOMPLETE ([docs/benchmarks/2026-09-30-three-way.md](../../benchmarks/2026-09-30-three-way.md)).

## Evidence

From the Claude Code hooks reference (`code.claude.com/docs/en/hooks`, read 2026-10-11):

- `Stop` input carries `session_id`, `stop_hook_active`, and `last_assistant_message`. Use `last_assistant_message`; the transcript may not include the final message at Stop time.
- `{"decision":"block","reason":"..."}` keeps Claude working and delivers `reason` as the explanation.
- Loop protection: `stop_hook_active` is true when Claude is already continuing because of a stop hook, and Claude Code overrides the next block after eight consecutive continuations (the count resets on any tool call).
- `Stop` ignores matchers. `PostToolUse` receives `tool_name` and `tool_input`. `UserPromptSubmit` fires on each prompt. Hooks inside subagents carry `agent_id`/`agent_type`.
- The transcript JSONL format is internal and changes between versions. Do not parse it.
- `${CLAUDE_PLUGIN_DATA}` is a persistent per-plugin data directory.

## Design

### 1. One hook script, three modes: `hooks/risk-gate`

Extensionless bash, called through `run-hook.cmd` like `session-start`. It needs `jq`. If `jq` is missing, it exits 0 and prints a stderr note. If `BEARPAWS_ENFORCE=0` is set, it exits 0 silently. It acts only under Claude Code: `CLAUDE_PLUGIN_ROOT` must be set, and `COPILOT_CLI`, `CURSOR_PLUGIN_ROOT`, and the `DEVIN_*` variables must be unset. Every other harness that reads `hooks/hooks.json` gets exit 0.

State: one append-only log per session at `${CLAUDE_PLUGIN_DATA:-${TMPDIR:-/tmp}}/risk-gate/<session_id>.log`. `session_id` is untrusted input that reaches a filesystem path. If it does not match `^[A-Za-z0-9_-]{1,128}$`, the hook exits 0 and writes nothing.

| Mode | Event | Behavior |
|---|---|---|
| `reset` | `UserPromptSubmit` | Truncate the session log. Each turn is judged on its own tool use. |
| `record` | `PostToolUse` (matcher `Edit\|Write\|MultiEdit\|NotebookEdit\|Agent\|Task`) | Append `edit <path>` (relative to the hook input's `cwd`) or `review` (an Agent/Task call whose `subagent_type` contains `review` at a word boundary, or whose `description` starts with `review`, case-insensitive; only code, spec, final, security, independent, quality, plan, design, or re may precede it, and the description must not be followed by fix, feedback, comment, finding, or follow; never the `prompt`). Subagent edits count too. |
| `stop` | `Stop` | Apply the gate below to `last_assistant_message` and the log. |

### 2. Gate rules (`stop` mode)

Read the log in order. `edited` means at least one `edit` line. `reviewed` means a `review` line appears after the last `edit` line, so a review that predates a later edit does not count (same rule as Codex C4).

1. Not `edited` → allow.
2. No line matching `^\s*\**Risk:\**\s*(routine|elevated)` → block: "This turn edited files. End with a risk receipt (see bp:verification-before-completion)."
3. `Status: INCOMPLETE` present → allow. Honest incompleteness is never blocked.
4. `Risk: elevated` and not `reviewed` → block: "Elevated-risk work needs an independent review dispatched after the last edit. Dispatch bp:requesting-code-review, or set Status: INCOMPLETE."
5. `Risk: routine` and an edited path matches the sensitive-path pattern → block once per turn (marker line `nudged` in the log): "Edited <paths> look elevated-risk. Reclassify, or keep routine and say why in the receipt." The second time, allow.

Edited paths have CR and LF replaced with spaces before they are logged, so a crafted file name cannot forge a `review` line.
6. Otherwise allow.

No custom loop guard. The agent can satisfy every block by changing only its message: it can add the receipt, add `Status: INCOMPLETE`, or (rule 5) repeat itself once. A guard that allowed a stop whenever `stop_hook_active` was set would turn every gate into a single nudge. Claude Code's eight-continuation cap is the backstop.

Sensitive-path pattern (case-insensitive, on the path): `auth|login|session|token|passw|credential|secret|crypt|permission|acl|polic|payment|billing|invoice|money|price|migrat|schema|sql|\.sql$`. A false positive costs one nudge. A false negative falls back to the agent's own classification.

### 3. `hooks/hooks.json`

Add `UserPromptSubmit`, `PostToolUse`, and `Stop` entries next to `SessionStart`. All call `"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd" risk-gate <mode>`, with `timeout: 10`. `hooks-cursor.json` and `.devin/hooks.v1.json` do not change.

### 4. Risk receipt (skill text)

Define it once in `skills/verification-before-completion/SKILL.md`:

```text
Risk: elevated (<surface>)            # or: Risk: routine
Pinned: <tests> passed before edit    # elevated only
Failing first: <test> failed, then passed   # elevated only
Review: <reviewer> — <verdict>        # elevated only
Assumptions: <what you took as true without checking>   # elevated only
Verified: <command> — <result>
Status: COMPLETE | INCOMPLETE
```

Routine work needs `Risk:`, `Verified:`, and `Status:`. The bootstrap gets a short **Risk receipt** paragraph that names the required lines, because the hook demands them on every editing turn whether or not the verification skill is loaded. It replaces the current "**Assumptions:** list in the report" wording, keeping net growth to about 400 bytes. Use `[...]` or `<placeholder>` tags, never raw tags (schema validator whitelist).

Wording changes follow `bp:writing-skills`: first a baseline run without the receipt text (RED), then the minimal text, then a re-run (GREEN).

### 5. What the gate does not check

- That "Pinned" and "Failing first" are true. Evals check those from tool order. The hook only checks that the receipt exists, that a review happened, and that the classification looks plausible.
- Whether an asynchronous review returned. A dispatch after the last edit is enough for the gate. The bootstrap's "not returned → INCOMPLETE" rule stays instruction-only. Upgrade path: record `SubagentStop` for reviewer agents.
- Other harnesses. They get the receipt as instruction only.
- Edits made through the Bash tool (`sed -i`, redirects, `git apply`) are not recorded.
- An agent running in the background from an earlier turn can record edits into a later turn.
- Rule 2 checks only the `Risk:` line; `Verified:` and `Status:` are required by the skill text, not the hook.
- An implementer's own PostToolUse events precede its parent's Agent event, so a review counts only by reviewer `subagent_type` or a description that starts with review.
- A reviewer described in other words, for example "Thorough review", is blocked. The agent clears that by rewording the description or setting `Status: INCOMPLETE`.

## Testing

- `tests/hooks/run-hook-tests.sh`: fixture JSON on stdin for each gate rule (allow/block), a repeated stop while still unmet (still blocks, except rule 5's second nudge), a malformed `session_id` (rejected, no file written), missing `jq` (exit 0 with stderr), `BEARPAWS_ENFORCE=0`, non-Claude harness env (exit 0), and the packaging check extended to the new entries and executable bit. Failing tests are written first.
- `tests/risk-eval/score.py`: parse the receipt (`Risk:`, `Assumptions:`, `Status:`) instead of matching `assum`.
- Live check: a fresh `claude --plugin-dir .` session on `tests/risk-eval` with the hooks active, confirming one block then compliance.
- An independent code review before completion (this change is elevated: untrusted input reaching a path, and a hook that runs in every user session).

## Out of scope

The escaped-defect benchmark (C), routine-path cost work (D), and the README rewrite (E). Each gets its own design after this ships.
