# Code Quality Reviewer Prompt Template

Use this template when dispatching a code quality reviewer subagent.

**Purpose:** Verify implementation is well-built (clean, tested, maintainable). For routine tasks this is the only review, so it also checks spec compliance: pass the full task text as PLAN_OR_REQUIREMENTS.

**Elevated-risk tasks:** only dispatch after spec compliance review passes.

```
Agent tool (bp:code-reviewer):
  Use template at requesting-code-review/code-reviewer.md

  WHAT_WAS_IMPLEMENTED: {WHAT_WAS_IMPLEMENTED}
  PLAN_OR_REQUIREMENTS: {PLAN_OR_REQUIREMENTS}
  PROJECT_CONVENTIONS: {PROJECT_CONVENTIONS}
  BASE_SHA: {BASE_SHA}
  HEAD_SHA: {HEAD_SHA}
  DESCRIPTION: {DESCRIPTION}
  CHANGED_FILE_DIFF: {CHANGED_FILE_DIFF}
  VERIFICATION_EVIDENCE: {VERIFICATION_EVIDENCE}
  KNOWN_DECISIONS: {KNOWN_DECISIONS}
  UNRESOLVED_CONCERNS: {UNRESOLVED_CONCERNS}
```

Fill every field. Diff scope includes committed and working changes (staged, unstaged and untracked), using exact diff text or scoped commands/paths. Evidence records commands, exit status/results and checks not run; decisions and concerns use "none known" or "not supplied" when absent.

**In addition to standard code quality concerns, the reviewer should check:**
- Does each file have one clear responsibility with a well-defined interface?
- Are units decomposed so they can be understood and tested independently?
- Is the implementation following the file structure from the plan?
- Did this implementation create new files that are already large, or significantly grow existing files? (Don't flag pre-existing file sizes — focus on what this change contributed.)

**Code reviewer returns:** Strengths, Issues (Critical/Important/Minor), Assessment
