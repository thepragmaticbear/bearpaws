---
name: verification-before-completion
description: Use when about to claim work is complete, fixed, or passing, or before committing or opening a PR
---

<skill>

  <purpose>
    Claiming work is complete without verification is dishonesty, not efficiency. Evidence before claims, always. Violating the letter of this rule is violating the spirit.
  </purpose>

  <triggers>
    <rule>Use before ANY success/completion claim, expression of satisfaction, or positive statement about work state.</rule>
    <rule>Use before committing, PR creation, task completion, moving to next task.</rule>
  </triggers>

  <warning level="hard">
    NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE. If you haven't run the verification command in this message, you cannot claim it passes.
  </warning>

  <process>
    <step>**IDENTIFY** — What command proves this claim?</step>
    <step>**RUN** — Execute the FULL command (fresh, complete).</step>
    <step>**READ** — Full output, check exit code, count failures.</step>
    <step>**VERIFY** — Does output confirm the claim? If NO: state actual status with evidence. If YES: state claim WITH evidence.</step>
    <step>**ONLY THEN** — Make the claim.</step>
  </process>

  ## What requires verification

  | Claim | Requires | Not sufficient |
  |---|---|---|
  | Tests pass | Test output: 0 failures, and the test count before and after your edit (write `no baseline` if you did not run them before); say so if added tests didn't change the count | Previous run, "should pass", a bare count |
  | Linter clean | Linter output: 0 errors | Partial check, extrapolation |
  | Build succeeds | Build command: exit 0 | Linter passing, logs look good |
  | Bug fixed | Original symptom test passes | Code changed, assumed fixed |
  | Agent completed | VCS diff shows changes | Agent reports "success" |
  | Requirements met | Line-by-line checklist | Tests passing alone |
  | Pure move/refactor | Diff of the moved code only (old body vs new body) | Whole-file diff, `git diff --stat` |

  ## Risk receipt

  End every reply that changed files with a receipt. Each line is a claim; each claim needs the evidence in the table above.

  ```text
  Risk: elevated (authorization)                      ← or: Risk: routine
  Pinned: test_owner_allowed, test_admin_same_org passed before edit
  Failing first: test_admin_cross_org_denied failed, then passed
  Review: bp:code-reviewer — Ready to merge: Yes
  Assumptions: org_id is never null on users or resources
  Verified: pytest — 12 passed before, 14 passed after, 0 failed
  Not checked: ruff, mypy (CI runs both); the CLI by hand
  Status: COMPLETE                                    ← INCOMPLETE if any step is missing
  ```

  Routine work needs only `Risk:`, `Verified:`, `Not checked:`, and `Status:`. `Not checked:` names every check you did not run (CI jobs, linters, manual paths), or `none`. A missing step means `Status: INCOMPLETE`, never a softened line.

  When committing, put the same receipt lines in the commit message as trailers.

  ## Red Flags — STOP

  - Using "should", "probably", "seems to"
  - Expressing satisfaction before verification ("Great!", "Perfect!", "Done!")
  - About to commit/push/PR without verification
  - Trusting agent success reports without independent check
  - ANY wording implying success without having run verification

  ## Rationalizations

  | Excuse | Reality |
  |---|---|
  | "Should work now" | RUN the verification |
  | "I'm confident" | Confidence ≠ evidence |
  | "Linter passed" | Linter ≠ compiler |
  | "Agent said success" | Verify independently |
  | "Partial check is enough" | Partial proves nothing |

  <example type="good">
    `[Run test command]` → See: 34/34 pass → "All tests pass"
  </example>

  <example type="bad">
    "Should pass now" / "Looks correct" / "I've written a regression test" (without red-green verification)
  </example>

</skill>
