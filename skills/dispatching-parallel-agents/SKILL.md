---
name: dispatching-parallel-agents
description: Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies
---

<skill>

  <purpose>
    When you have multiple independent problems, dispatch one agent per problem domain and let them work concurrently. Each agent gets isolated context — never your session's history. This preserves your context for coordination.
  </purpose>

  <triggers>
    <rule>Use when 2+ independent tasks exist (different test files, subsystems, bugs).</rule>
    <rule>Use when each problem can be understood without context from others.</rule>
    <rule>Use when agents won't interfere (no shared state, no same-file edits).</rule>
  </triggers>

  <flow format="dot">
    ```dot
    digraph when_to_use {
      "Multiple failures?" [shape=diamond];
      "Independent?" [shape=diamond];
      "Can parallelize?" [shape=diamond];
      "Single agent" [shape=box];
      "Parallel dispatch" [shape=box];
      "Sequential agents" [shape=box];

      "Multiple failures?" -> "Independent?" [label="yes"];
      "Independent?" -> "Single agent" [label="no - related"];
      "Independent?" -> "Can parallelize?" [label="yes"];
      "Can parallelize?" -> "Parallel dispatch" [label="yes"];
      "Can parallelize?" -> "Sequential agents" [label="shared state"];
    }
    ```
  </flow>

  <process>
    <step>**Identify independent domains** — Group failures by what's broken. Each domain is one agent's scope.</step>
    <step>**Create focused prompts** — Each agent gets: specific scope (one file/subsystem), clear goal, constraints (don't change other code), expected output format.</step>
    <step>**Dispatch in parallel** — Use Task tool for all agents concurrently.</step>
    <step>**Review and integrate** — Read each summary, verify fixes don't conflict, run full test suite, integrate changes.</step>
  </process>

  ## Prompt structure

  Good agent prompts are focused, self-contained, and specific about output:

  ```markdown
  Fix the 3 failing tests in src/agents/agent-tool-abort.test.ts:

  1. "should abort tool with partial output" - expects 'interrupted at'
  2. "should handle mixed completed and aborted" - fast tool aborted
  3. "should track pendingToolCount" - expects 3 results, gets 0

  These are timing/race condition issues. Your task:
  1. Read test file, understand what each verifies
  2. Identify root cause
  3. Fix (don't just increase timeouts)

  Return: Summary of root cause and changes made.
  ```

  <rules>
    <rule>Each agent gets narrow, self-contained scope.</rule>
    <rule>Never dispatch without specific error messages and test names.</rule>
    <rule>Always run full test suite after integrating all fixes.</rule>
    <rule>Spot-check agent work — agents can make systematic errors.</rule>
  </rules>

  <antipattern>
    "Fix all the tests" — too broad, agent gets lost. Be specific: one file or subsystem per agent.
  </antipattern>

  <antipattern>
    Dispatching agents for related failures — fix one might fix others. Investigate together first.
  </antipattern>

</skill>
