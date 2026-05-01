---
name: writing-skills
description: Use when creating new skills, editing existing skills, or verifying skills work before deployment
---

<skill>

  <purpose>
    Writing skills IS Test-Driven Development applied to process documentation. Write pressure scenarios (tests), watch agents fail without the skill (RED), write the skill (GREEN), close loopholes (REFACTOR). If you didn't watch an agent fail without the skill, you don't know if the skill teaches the right thing.
  </purpose>

  <triggers>
    <rule>Use when creating a new skill.</rule>
    <rule>Use when editing an existing skill.</rule>
    <rule>Use when verifying a skill works before deployment.</rule>
  </triggers>

  <warning level="hard">
    NO SKILL WITHOUT A FAILING TEST FIRST. This applies to new skills AND edits. Write skill before testing? Delete it. Start over. Not for "simple additions", not for "just adding a section", not for "documentation updates."
  </warning>

  <rules>
    <rule>**REQUIRED BACKGROUND:** You MUST understand bp:test-driven-development before using this skill.</rule>
    <rule>Personal skills live in agent-specific directories (`~/.claude/skills` for Claude Code, `~/.agents/skills/` for Codex).</rule>
  </rules>

  ## What is a skill?

  A reusable reference guide for proven techniques, patterns, or tools. Skills are NOT narratives about how you solved a problem once.

  | Create when | Don't create for |
  |---|---|
  | Technique wasn't intuitively obvious | One-off solutions |
  | You'd reference this across projects | Standard well-documented practices |
  | Pattern applies broadly | Project-specific conventions (use CLAUDE.md) |
  | Others would benefit | Mechanical constraints (automate with regex/validation) |

  ## Skill types

  - **Technique** — concrete method with steps (condition-based-waiting, root-cause-tracing)
  - **Pattern** — way of thinking about problems (flatten-with-flags, test-invariants)
  - **Reference** — API docs, syntax guides, tool documentation

  ## SKILL.md structure

  **Frontmatter (YAML):** Two required fields: `name` and `description` (see [agentskills.io/specification](https://agentskills.io/specification)). Max 1024 chars total. `name`: letters, numbers, hyphens only. `description`: third-person, starts with "Use when...", describes ONLY triggering conditions (see CSO below).

  **Body:** Use the XML schema (see bottom of this file). For skills not yet migrated, use the legacy markdown structure:

  ```
  # Skill Name
  ## Overview — core principle in 1-2 sentences
  ## When to Use — symptoms, use cases, when NOT to use
  ## Core Pattern — before/after code comparison
  ## Quick Reference — table or bullets
  ## Implementation — inline code or link to file
  ## Common Mistakes — what goes wrong + fixes
  ```

  **Directory structure:** flat namespace under `skills/`. Heavy reference (100+ lines) and reusable tools go in sibling files; keep SKILL.md focused.

  ## Claude Search Optimization (CSO)

  Future Claude reads `description` to decide which skills to load. Make it answer: "Should I read this skill right now?"

  <warning level="hard">
    Description = WHEN to use, NOT what the skill does. Testing revealed that when a description summarizes workflow, Claude follows the description instead of reading the full skill. A description saying "code review between tasks" caused ONE review; the skill's flowchart showed TWO. When changed to just triggering conditions, Claude correctly read and followed the flowchart.
  </warning>

  <example type="bad">
    ```yaml
    # Summarizes workflow — Claude may follow this instead of reading skill
    description: Use when executing plans - dispatches subagent per task with code review between tasks
    # Too much process detail
    description: Use for TDD - write test first, watch it fail, write minimal code, refactor
    ```
  </example>

  <example type="good">
    ```yaml
    # Just triggering conditions
    description: Use when executing implementation plans with independent tasks in the current session
    # Technology-specific with explicit trigger
    description: Use when using React Router and handling authentication redirects
    ```
  </example>

  **Keyword coverage:** Use words Claude would search for — error messages, symptoms, synonyms, tool names.

  **Naming:** Active voice, verb-first. `creating-skills` not `skill-creation`. Gerunds work well for processes.

  **Token efficiency:** Getting-started skills: aim for under 150 words. Frequently-loaded: under 200. Others: under 500. Move details to `--help`, use cross-references, compress examples, eliminate redundancy.

  **Cross-referencing:** Use skill name with requirement markers: `**REQUIRED SUB-SKILL:** Use bp:test-driven-development`. Never use `@` links (force-loads files, burns context).

  ## Flowcharts

  Use ONLY for non-obvious decision points, process loops, or "A vs B" decisions. Never for reference material, code examples, or linear instructions. See graphviz-conventions.dot for style rules.

  ## RED-GREEN-REFACTOR for skills

  <process>
    <step>**RED** — Run pressure scenario with subagent WITHOUT the skill. Document: what choices did they make, what rationalizations (verbatim), which pressures triggered violations.</step>
    <step>**GREEN** — Write skill addressing those specific rationalizations. Run same scenario WITH skill. Agent should comply.</step>
    <step>**REFACTOR** — Agent found new rationalization? Add explicit counter. Re-test until bulletproof.</step>
  </process>

  ## Bulletproofing against rationalization

  Skills enforcing discipline need to resist rationalization. Agents find loopholes under pressure.

  - **Close every loophole explicitly.** Don't just state the rule — forbid specific workarounds ("Don't keep it as reference", "Don't adapt it").
  - **Address spirit-vs-letter arguments.** Add early: "Violating the letter of the rules is violating the spirit."
  - **Build rationalization tables** from baseline testing. Every excuse agents make goes in the table.
  - **Create red flags lists** for easy self-checking.

  ## Testing skill types

  | Type | Test with | Success = |
  |---|---|---|
  | Discipline (TDD, verification) | Pressure scenarios: time + sunk cost + authority + exhaustion | Agent follows rule under max pressure |
  | Technique (how-to) | Application scenarios, edge cases, missing info | Agent applies technique to new scenario |
  | Pattern (mental model) | Recognition, application, counter-examples | Agent identifies when/how to apply |
  | Reference (docs/APIs) | Retrieval, application, gap testing | Agent finds and correctly uses info |

  ## Common rationalizations for skipping testing

  | Excuse | Reality |
  |---|---|
  | "Skill is obviously clear" | Clear to you ≠ clear to agents. Test it. |
  | "Testing is overkill" | Untested skills have issues. Always. |
  | "I'll test if problems emerge" | Problems = agents can't use skill. Test BEFORE deploying. |
  | "Too tedious to test" | Less tedious than debugging a bad skill in production. |

  <antipattern>
    Narrative storytelling: "In session 2025-10-03, we found empty projectDir caused..." — too specific, not reusable.
  </antipattern>

  <antipattern>
    Multi-language dilution: example-js.js, example-py.py, example-go.go — mediocre quality, maintenance burden. One excellent example beats many mediocre ones.
  </antipattern>

  <antipattern>
    Code in flowcharts: `step1 [label="import fs"]` — can't copy-paste, hard to read.
  </antipattern>

  ## Skill creation checklist

  **RED Phase:**
  - [ ] Create pressure scenarios (3+ combined pressures for discipline skills)
  - [ ] Run WITHOUT skill — document baseline behavior verbatim
  - [ ] Identify rationalization patterns

  **GREEN Phase:**
  - [ ] Frontmatter: `name` (hyphens), `description` (third-person, "Use when...", triggers only)
  - [ ] Address specific baseline failures from RED
  - [ ] One excellent example (not multi-language)
  - [ ] Run WITH skill — verify compliance

  **REFACTOR Phase:**
  - [ ] Add counters for new rationalizations
  - [ ] Build rationalization table + red flags list
  - [ ] Re-test until bulletproof

  **STOP:** After writing ANY skill, complete the full checklist above. Do NOT batch-create skills without testing each.

  <see file="anthropic-best-practices.md"/>
  <see file="testing-skills-with-subagents.md"/>
  <see file="persuasion-principles.md"/>
  <see file="graphviz-conventions.dot"/>

## XML schema (Phase 1+)

Bearpaws skill bodies use a structural XML format with a closed tag whitelist. YAML frontmatter is unchanged (it's loader metadata). Markdown is allowed *inside* element content.

### Tag whitelist

| Tag | Purpose |
|---|---|
| `<skill>` | Root element. Wraps the entire skill body. |
| `<purpose>` | One-paragraph what-this-skill-does. |
| `<triggers>` | When the agent should reach for this skill. Contains `<rule>` children. |
| `<rules>` / `<rule>` | Non-negotiable directives. One per `<rule>`. |
| `<process>` / `<step>` | Ordered workflow. `<step>` children are sequential. |
| `<flow format="dot\|mermaid">` | Diagram block. Markdown content (fenced code) inside. |
| `<example type="good\|bad">` | Example with explicit polarity. Markdown allowed inside. |
| `<antipattern>` | Common mistake to avoid. |
| `<warning level="hard\|soft">` | Hard = critical behavioral imperative; soft = caution. |
| `<gate name="...">` | Named blocking gate that must pass before proceeding. |
| `<subagent-stop>` | "Skip this skill if dispatched as a subagent." |
| `<include ref="...">` | Structural dedup marker for extracted shared content. **Advisory only** — agents do not auto-read it. Reserve for content reused by ≥2 skills and >25 lines. |
| `<see file="...">` | Pointer to auxiliary content; load only if explicitly relevant. |
| `<placeholder name="...">` | Template variable. |

Any tag outside this list fails the schema-validator test in `tests/schema-validator/`.

### `<include>` vs. `<see>`

- `<include ref="references/red-flags-tdd"/>` — *structural dedup marker*. Agent does **not** auto-read (Phase 1 finding: agents treat the tag as advisory annotation, not an imperative `Read` call). Use only when the extraction rule is met: **>25 lines AND ≥2 consumers**. As of v1.1.0, no skill uses `<include>`; the tag remains in the schema for future use.
- `<see file="references/anthropic-best-practices.md"/>` — *auxiliary; consult only if explicitly relevant*. Use for heavy refs that should not pre-load. Demotion rule: **>150 lines AND used in <30% of skill invocations**.

### Skill-body shape

```xml
<skill>
  <purpose>One paragraph.</purpose>

  <triggers>
    <rule>Use when X</rule>
    <rule>Use before Y</rule>
  </triggers>

  <warning level="hard">
    Don't do Z without W.
  </warning>

  <process>
    <step>First, ...</step>
    <step>Then, ...</step>
  </process>

  <flow format="dot">
    ```dot
    digraph foo { ... }
    ```
  </flow>

  <example type="bad">
    <!-- markdown allowed inside -->
  </example>

  <see file="references/deep-dive.md"/>
</skill>
```

### Bootstrap exception

`skills/using-bearpaws/SKILL.md` is the bootstrap. It cannot use `<include>` because at session start the agent has not yet been taught the convention — the include would be circular. `<see>` is fine in the bootstrap (opt-in pointer).

### When the schema is too rigid

If you find legitimate skill content that has no home in the whitelist: **grow the whitelist with documented justification** in this file. Do NOT add ad-hoc tags. The schema's value is uniform parseability; ad-hoc tags defeat that.

</skill>
