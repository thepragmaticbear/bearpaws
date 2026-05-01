---
name: using-git-worktrees
description: Use when starting feature work that needs isolation from current workspace or before executing implementation plans - creates isolated git worktrees with smart directory selection and safety verification
---

<skill>

  <purpose>
    Create isolated git workspaces for feature work. Systematic directory selection + safety verification = reliable isolation.
  </purpose>

  <triggers>
    <rule>Use before executing implementation plans (required by subagent-driven-development and executing-plans).</rule>
    <rule>Use when starting feature work that needs isolation from current workspace.</rule>
  </triggers>

  <warning level="soft">
    Announce at start: "I'm using the using-git-worktrees skill to set up an isolated workspace."
  </warning>

  <process>
    <step>**Directory selection** — Priority: (1) existing `.worktrees/` or `worktrees/` dir, (2) CLAUDE.md preference, (3) ask user: `.worktrees/` (project-local, hidden) or `~/.config/bearpaws/worktrees/{project}/` (global).</step>
    <step>**Safety verification** — For project-local dirs: `git check-ignore -q .worktrees`. If NOT ignored: add to .gitignore + commit immediately, then proceed. Global dirs need no verification.</step>
    <step>**Create worktree** — `git worktree add "{path}/{branch}" -b "{branch}"` → `cd` into it.</step>
    <step>**Run project setup** — Auto-detect: `package.json` → `npm install`, `Cargo.toml` → `cargo build`, `requirements.txt` → `pip install -r`, `go.mod` → `go mod download`.</step>
    <step>**Verify clean baseline** — Run test suite. If pass: report ready. If fail: report failures, ask whether to proceed.</step>
  </process>

  <rules>
    <rule>Never create project-local worktree without verifying it's git-ignored.</rule>
    <rule>Never skip baseline test verification.</rule>
    <rule>Never proceed with failing tests without asking.</rule>
    <rule>Follow directory priority — don't assume location when ambiguous.</rule>
  </rules>

  ## Integration

  **Called by:** bp:brainstorming (after design approved), bp:subagent-driven-development, bp:executing-plans.
  **Pairs with:** bp:finishing-a-development-branch (cleanup after work complete).

</skill>
