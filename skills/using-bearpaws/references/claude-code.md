# Claude Code Capability Mapping

BearPaws skills define intent. Use the Claude Code native capability when it
implements that intent more strongly than prompt instructions do.

| BearPaws intent | Claude Code capability |
|---|---|
| Protected implementation planning | Native Plan Mode (`/plan`, permission mode `plan`, `EnterPlanMode` / `ExitPlanMode`) |
| Skill execution | `Skill` |
| Isolated worker or reviewer | `Agent` subagent, packaged `code-reviewer` agent |
| Project exploration | `Read`, `Grep`, `Glob` |
| Implementation | `Write`, `Edit` |
| Command execution | `Bash` |
| Verification | Fresh commands plus BearPaws evidence rules |

## Native planning

For a non-trivial plan, prefer native Plan Mode. Enter it with `EnterPlanMode`
when that tool is available and the session is not already in Plan Mode; if
it is unavailable or declined, use bp:writing-plans normally.

While in Plan Mode:

- Use bp:writing-plans normally: explore, map files, define tasks, self-review.
- Write the plan to the plan file Claude Code designates, using the BearPaws
  plan format. Do not leave Plan Mode to save it under `docs/bearpaws/plans/`.
- If bp:brainstorming applies, keep the design in the native plan instead of
  writing a design doc.
- Do not edit project files, commit, create worktrees, install dependencies,
  or start TDD. Research an open question or ask it; do not implement to
  answer it.
- If the user asks for changes, stay in Plan Mode, revise, self-review, and
  present again. Persist no drafts.

After the user approves the plan (`ExitPlanMode` accepted):

- Approval is the go-ahead. Do not ask again whether to start or which
  execution mode to use; pick it yourself unless the user stated a preference.
- Continue in the same session. Establish the workspace (bp:using-git-worktrees
  or the current branch the user authorized; main/master still needs explicit
  consent), save the approved plan to `docs/bearpaws/plans/` there with
  `**Status:** Approved`, then invoke bp:subagent-driven-development (tasks
  mostly independent) or bp:executing-plans.
- The saved plan is the durable record. After compaction or resume, re-read
  it instead of relying on recollection. Record material deviations under
  `## Plan Amendments` instead of rewriting approved tasks.
- A rejected or abandoned plan gets no implementation and no saved file
  unless the user asks to keep the draft.

Plan approval does not replace TDD, review, or verification gates.

## Model selection

Model selection belongs to Claude Code and the user; BearPaws never requires
or switches a model. `/model opusplan` (one model in Plan Mode, another for
execution, same session) fits this lifecycle and is optional.
