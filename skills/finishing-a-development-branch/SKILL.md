---
name: finishing-a-development-branch
description: Use when implementation on a branch is complete, tests pass, and it's time to decide how to integrate the work (merge, PR, keep, or discard)
---

<skill>

  <purpose>
    Guide completion of development work. Verify tests → Check drift → Present options → Execute choice → Clean up.
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
    <step>**Check drift** — If a plan under `docs/bearpaws/plans/` drove this branch and no final review checked the whole branch against it, read each task against the current code and `git diff <base>...HEAD`. Passing tests and checked boxes do not show a task was built. Report only divergences: behavior a task names that the code lacks, a planned name, field or argument missing or hardcoded, a source change no task covers (tests, docs, release notes and the plan itself do not count). If there are none, say "No drift." Otherwise write `Drift:` followed by one bullet per divergence, and offer: fix, update the plan to match, or proceed. Wait for the choice. After a fix, return to Verify tests.</step>
    <step>**Present exactly 4 options** — (1) Merge locally, (2) Push and create PR, (3) Keep branch as-is, (4) Discard. No explanation — keep concise.</step>
    <step>**Check commit identity** — before options 1 and 2, once per branch. Run `git log <base>..HEAD --format='%h %ae %ce'` and scan `Co-authored-by` trailers (`git log <base>..HEAD --format='%h %(trailers:key=Co-authored-by,valueonly)'`). Flag each email that is neither `*@users.noreply.github.com` (or GitHub's `noreply@github.com`) nor on the project's `Allowed commit emails:` line from onboarding; a noreply address is never flagged. If any are flagged, list them and offer: rewrite (`git rebase -r <base> --exec 'git commit --amend --no-edit --reset-author'` after setting `user.email`; trailers are edited by hand), proceed, or stop. Wait for the choice.</step>
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
    <rule>Never rewrite commits or authorship without your human partner's choice.</rule>
    <rule>When committing, put the risk receipt in the commit message as trailers (the same lines as the chat receipt).</rule>
  </rules>

  ## Integration

  **Called by:** bp:subagent-driven-development (after all tasks), bp:executing-plans (after all batches).
  **Pairs with:** bp:using-git-worktrees (cleans up worktree created by that skill).

</skill>
