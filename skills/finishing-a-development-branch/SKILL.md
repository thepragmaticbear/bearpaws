---
name: finishing-a-development-branch
description: Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development work by presenting structured options for merge, PR, or cleanup
---

<skill>

  <purpose>
    Guide completion of development work. Verify tests → Present options → Execute choice → Clean up.
  </purpose>

  <triggers>
    <rule>Use when all tasks are complete and tests pass.</rule>
    <rule>Use at the end of subagent-driven-development or executing-plans.</rule>
  </triggers>

  <warning level="soft">
    Announce at start: "I'm using the finishing-a-development-branch skill to complete this work."
  </warning>

  <process>
    <step>**Verify tests** — Run project's test suite. If tests fail: show failures, stop. Cannot proceed until green.</step>
    <step>**Determine base branch** — `git merge-base HEAD main` or ask.</step>
    <step>**Present exactly 4 options** — (1) Merge locally, (2) Push and create PR, (3) Keep branch as-is, (4) Discard. No explanation — keep concise.</step>
    <step>**Execute choice** — see option details below.</step>
    <step>**Cleanup worktree** — For options 1, 2, 4: `git worktree remove <path>`. For option 3: keep.</step>
  </process>

  ## Option details

  **1. Merge locally:** checkout base → pull → merge feature branch → verify tests on merged result → delete feature branch.

  **2. Push and create PR:** push branch with `-u` → `gh pr create` with Summary + Test Plan.

  **3. Keep as-is:** Report branch name and worktree path. Don't cleanup.

  **4. Discard:** Confirm first (show branch, commits, worktree path). Require typed "discard". Then: checkout base → force-delete feature branch → remove worktree.

  <rules>
    <rule>Never proceed with failing tests.</rule>
    <rule>Never merge without verifying tests on result.</rule>
    <rule>Never delete work without typed confirmation.</rule>
    <rule>Never force-push without explicit request.</rule>
  </rules>

  ## Integration

  **Called by:** bp:subagent-driven-development (after all tasks), bp:executing-plans (after all batches).
  **Pairs with:** bp:using-git-worktrees (cleans up worktree created by that skill).

</skill>
