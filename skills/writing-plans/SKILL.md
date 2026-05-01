---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

<skill>

  <purpose>
    Write implementation plans assuming the engineer has zero codebase context and questionable taste. Document everything: which files to touch, code, testing, docs to check. Bite-sized tasks. DRY. YAGNI. TDD. Frequent commits. Assume a skilled developer who knows nothing about this toolset or domain.
  </purpose>

  <triggers>
    <rule>Use after brainstorming produces an approved spec.</rule>
    <rule>Use when you have requirements for a multi-step task, before writing code.</rule>
  </triggers>

  <warning level="soft">
    Announce at start: "I'm using the writing-plans skill to create the implementation plan."
  </warning>

  <rules>
    <rule>**Save plans to:** `docs/bearpaws/plans/YYYY-MM-DD-{feature-name}.md` (user prefs override).</rule>
    <rule>**Scope check:** If spec covers multiple independent subsystems, suggest separate plans — one per subsystem. Each plan produces working, testable software on its own.</rule>
  </rules>

  <process>
    <step>**Map file structure** — which files will be created or modified, what each is responsible for. Design units with clear boundaries. Prefer smaller focused files. Files that change together should live together.</step>
    <step>**Define tasks** — each task produces self-contained changes. Each step is one action (2-5 min): write failing test, run it, implement minimal code, run tests, commit.</step>
    <step>**Self-review** — (1) spec coverage: can you point to a task for every requirement? (2) placeholder scan: no TBD/TODO/vague steps. (3) type consistency: names in later tasks match definitions in earlier tasks. Fix inline.</step>
    <step>**Execution handoff** — offer choice: **Subagent-Driven** (bp:subagent-driven-development, recommended) or **Inline** (bp:executing-plans).</step>
  </process>

  ## Plan document header

  Every plan MUST start with:

  ```markdown
  # [Feature Name] Implementation Plan

  > **For agentic workers:** REQUIRED SUB-SKILL: Use bp:subagent-driven-development (recommended) or bp:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

  **Goal:** [One sentence]

  **Architecture:** [2-3 sentences]

  **Tech Stack:** [Key technologies/libraries]

  ---
  ```

  ## Task structure

  ````markdown
  ### Task N: [Component Name]

  **Files:**
  - Create: `exact/path/to/file.py`
  - Modify: `exact/path/to/existing.py:123-145`
  - Test: `tests/exact/path/to/test.py`

  - [ ] **Step 1: Write the failing test**

  ```python
  def test_specific_behavior():
      result = function(input)
      assert result == expected
  ```

  - [ ] **Step 2: Run test — verify FAIL**

  Run: `pytest tests/path/test.py::test_name -v`
  Expected: FAIL with "function not defined"

  - [ ] **Step 3: Write minimal implementation**

  ```python
  def function(input):
      return expected
  ```

  - [ ] **Step 4: Run test — verify PASS**

  Run: `pytest tests/path/test.py::test_name -v`
  Expected: PASS

  - [ ] **Step 5: Commit**
  ````

  <gate name="no-placeholders">
    Every step must contain actual content. These are plan failures — never write them:
    - "TBD", "TODO", "implement later", "fill in details"
    - "Add appropriate error handling" / "add validation"
    - "Write tests for the above" (without actual test code)
    - "Similar to Task N" (repeat the code)
    - Steps describing what to do without showing how
    - References to types/functions not defined in any task
  </gate>

  <see file="plan-document-reviewer-prompt.md"/>

</skill>
