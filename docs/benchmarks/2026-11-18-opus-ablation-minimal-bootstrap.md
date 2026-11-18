---
name: using-bearpaws
description: Use when starting any conversation, before responding or exploring the project
---

<skill>

  <subagent-stop>If you were dispatched as a subagent to execute a specific task, skip this skill.</subagent-stop>

  ## Elevated risk

  Neither size nor a pure rename or refactor lowers risk: risk follows the code touched. Work is elevated-risk if it touches authentication or authorization, secrets or cryptography, moving money (charging, refunding, paying out, transferring, or writing balances; price display, formatting, and cart or discount arithmetic are routine), data deletion or migration, untrusted input reaching paths, SQL, shell, or deserialization, concurrency, or a public API or schema. Elevated-risk work needs tests pinning the behavior that must not change, run and seen passing in a step before your edit; a failing test for the risk first if behavior changes (`bp:test-driven-development`); a diff limited to the fix, with no unrelated cleanup; an independent review (`bp:requesting-code-review`) before any completion claim; and a risk receipt with verification evidence (`bp:verification-before-completion`). Saying you skipped a step does not satisfy it. A defect the review finds in the same risk class as the task, in the code you changed, is part of the fix, not unrelated cleanup: fix it with its own failing test, or end `Status: INCOMPLETE` naming it. Review at most three times in all (the review and two re-reviews of fixes; `bp:subagent-driven-development` keeps its own per-task cap); after the third returns, edit nothing more, and list any finding still open in `Open:` with `Status: INCOMPLETE`. A defect is behavior a caller in this codebase or a user's input can reach: a negative or oversized amount is one. A guard for a type no caller passes (a NaN amount, a bool flag, a string timestamp) is not, and the review is not asked for one. Dispatch the review before your final report; if it has not returned, the report's status is INCOMPLETE, never done.

  **Risk receipt.** End every reply that changed files with `Risk: routine` or `Risk: elevated ([surface])`, `Verified:` (command and result), `Not checked:` (what you did not run, or none), and `Status: COMPLETE` or `Status: INCOMPLETE`. Elevated work adds `Pinned:` (tests passing before the edit), `Failing first:` (or, only if no behavior changes, `none, behavior preserved; pinned by [test names]`), `Review:` (reviewer and verdict), `Open:` (each unfixed Critical or Important review finding, or `none`; any open finding means `Status: INCOMPLETE`), and `Assumptions:` (what you took as true without checking).

  Other bearpaws skills are optional: use one when your human partner asks for it or the task clearly needs it.

</skill>
