# Scoped Re-review Prompt Template

Use this template after a fix round, instead of a second full review. The final whole-branch review stays full.

**Inputs:** the open Critical and Important findings, pasted verbatim, one per bullet; the full task text; and `FIX_BASE_SHA`, the head the previous review saw. Minor findings are not re-reviewed.

**Dispatch:** the description must be `Re-review Task N` or `Re-review Task N fix round K` so the risk gate counts it as a review. Never follow `Re-review` with fix, finding, feedback, comment or follow: the gate does not count that as a review. Use the cheapest model that handles review: the fix diff is small.

```
Agent tool (general-purpose):
  description: "Re-review Task N fix round K"
  prompt: |
    You are re-reviewing a fix round. A full review already ran; do not repeat it.

    ## Task

    [TASK_TEXT]

    ## Open Findings (verbatim from the previous review)

    [FINDINGS]

    ## Scope

    The findings above and `git diff [FIX_BASE_SHA]..[HEAD_SHA]` only. Read surrounding code when a
    finding or a changed line needs it, but anything you notice outside the fix diff is an
    out-of-scope observation: it never blocks and never starts another fix round.

    - The checkout is read-only: do not change the working tree, the index, HEAD or branch state.
    - You do not dispatch subagents.
    - Do not re-run the test suite. Run one focused test or snippet only when reading leaves a
      specific doubt.

    ## Output, in this order

    ### Finding Verdicts
    For each finding, as written: ADDRESSED or NOT ADDRESSED, with the `file:line` that shows it.
    Attempted is not addressed: a change that touches the area but leaves the finding's failure
    reachable is NOT ADDRESSED.

    ### New Breakage in the Fix Diff
    Defects in the lines the fix diff adds or changes, including a changed line that still falls
    short of the task text. Give each a severity (Critical, Important or Minor) by the rules in
    requesting-code-review/code-reviewer.md: a task requirement unmet or misread, or a failure mode
    a caller or a user's input can reach, is Important or higher; hardening the task did not ask
    for is Minor. Write "None" if there is none.

    ### Break Attempts
    At least one line per finding, against the fix diff:
    "Tried: [executed] X — Y" or "Tried: [reasoned] X — Y". Use [executed] only for a command you
    ran in this re-review.

    ### What I didn't check

    ### Out-of-Scope Observations
    Anything outside the fix diff and the findings, including pre-existing defects. Never blocking.

    ### Verdict
    "All findings addressed, no new Critical/Important" or
    "Findings remain open: [each NOT ADDRESSED finding and each new Critical/Important item]".
```
