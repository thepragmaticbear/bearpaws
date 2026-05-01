---
name: executing-plans
description: Use when you have a written implementation plan to execute in a separate session with review checkpoints
---

<skill>

  <purpose>
    Load plan, review critically, execute all tasks, report when complete. For inline execution without subagents. If subagents are available, use bp:subagent-driven-development instead — quality is significantly higher.
  </purpose>

  <triggers>
    <rule>Use when you have a written implementation plan and the user chose inline execution.</rule>
    <rule>Use when subagents are unavailable but a plan needs executing.</rule>
  </triggers>

  <warning level="soft">
    Announce at start: "I'm using the executing-plans skill to implement this plan."
  </warning>

  <process>
    <step>**Load and review** — Read plan. Review critically for questions or concerns. If concerns: raise with human partner before starting. If clear: create TodoWrite and proceed.</step>
    <step>**Execute tasks** — For each task: mark in_progress, follow steps exactly (plan has bite-sized steps), run verifications as specified, mark completed.</step>
    <step>**Complete development** — After all tasks verified, invoke bp:finishing-a-development-branch.</step>
  </process>

  <rules>
    <rule>Follow plan steps exactly — don't skip verifications.</rule>
    <rule>Stop when blocked — don't guess. Ask for clarification.</rule>
    <rule>Never start implementation on main/master without explicit user consent.</rule>
  </rules>

  <gate name="blockers">
    STOP executing immediately when: hit a blocker (missing dep, test fails, instruction unclear), plan has critical gaps, or verification fails repeatedly. Ask for help rather than guessing.
  </gate>

  ## Integration

  - **bp:using-git-worktrees** — set up isolated workspace before starting
  - **bp:writing-plans** — creates the plan this skill executes
  - **bp:finishing-a-development-branch** — complete development after all tasks

</skill>
