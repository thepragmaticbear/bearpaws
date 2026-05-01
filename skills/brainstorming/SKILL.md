---
name: brainstorming
description: "You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation."
---

<skill>

  <purpose>
    Turn ideas into fully formed designs through collaborative dialogue. Understand the project context, ask questions one at a time, present the design, get user approval.
  </purpose>

  <triggers>
    <rule>Use before any creative work: new features, components, modifications.</rule>
    <rule>Use before any implementation skill — brainstorming produces the spec.</rule>
  </triggers>

  <gate name="no-implementation">
    Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity.
  </gate>

  <antipattern>
    "This is too simple to need a design." Every project goes through this process — a todo list, a single-function utility, a config change. "Simple" projects are where unexamined assumptions cause the most wasted work. The design can be short, but you MUST present it and get approval.
  </antipattern>

  <process>
    <step>**Explore project context** — check files, docs, recent commits.</step>
    <step>**Offer visual companion** (if visual questions ahead) — own message, no other content. See visual-companion.md.</step>
    <step>**Ask clarifying questions** — one at a time. Multiple choice preferred. Understand purpose, constraints, success criteria.</step>
    <step>**Scope check** — if the request spans multiple independent subsystems, flag it. Decompose into sub-projects before refining details. Each sub-project gets its own spec → plan → implementation cycle.</step>
    <step>**Propose 2-3 approaches** — with trade-offs and your recommendation. Lead with recommended option.</step>
    <step>**Present design** — scale each section to complexity. Ask after each section if it looks right. Cover: architecture, components, data flow, error handling, testing.</step>
    <step>**Write design doc** — save to `docs/bearpaws/plans/YYYY-MM-DD-{topic}-design.md` (user prefs override). Commit.</step>
    <step>**Spec self-review** — scan for placeholders/TBD, internal contradictions, scope creep, ambiguity. Fix inline.</step>
    <step>**User reviews spec** — ask user to review before proceeding. Wait for approval.</step>
    <step>**Transition** — invoke bp:writing-plans. That is the ONLY next skill.</step>
  </process>

  <flow format="dot">
    ```dot
    digraph brainstorming {
      "Explore context" [shape=box];
      "Visual ahead?" [shape=diamond];
      "Offer companion\n(own message)" [shape=box];
      "Clarifying Qs" [shape=box];
      "Propose approaches" [shape=box];
      "Present design" [shape=box];
      "Approved?" [shape=diamond];
      "Write spec" [shape=box];
      "Self-review" [shape=box];
      "User reviews?" [shape=diamond];
      "Invoke writing-plans" [shape=doublecircle];

      "Explore context" -> "Visual ahead?";
      "Visual ahead?" -> "Offer companion\n(own message)" [label="yes"];
      "Visual ahead?" -> "Clarifying Qs" [label="no"];
      "Offer companion\n(own message)" -> "Clarifying Qs";
      "Clarifying Qs" -> "Propose approaches";
      "Propose approaches" -> "Present design";
      "Present design" -> "Approved?";
      "Approved?" -> "Present design" [label="revise"];
      "Approved?" -> "Write spec" [label="yes"];
      "Write spec" -> "Self-review";
      "Self-review" -> "User reviews?";
      "User reviews?" -> "Write spec" [label="changes"];
      "User reviews?" -> "Invoke writing-plans" [label="approved"];
    }
    ```
  </flow>

  <warning level="hard">
    The terminal state is invoking bp:writing-plans. Do NOT invoke frontend-design, mcp-builder, or any other implementation skill directly from brainstorming.
  </warning>

  <rules>
    <rule>**One question at a time** — don't overwhelm with multiple questions.</rule>
    <rule>**YAGNI ruthlessly** — remove unnecessary features from all designs.</rule>
    <rule>**Design for isolation** — smaller units with clear boundaries and well-defined interfaces. Each unit has one purpose, can be understood and tested independently.</rule>
    <rule>**Follow existing patterns** in existing codebases. Only propose improvements that serve the current goal.</rule>
  </rules>

  <see file="visual-companion.md"/>
  <see file="spec-document-reviewer-prompt.md"/>

</skill>
