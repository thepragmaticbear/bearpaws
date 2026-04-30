# Bearpaws — Fork Design Spec

**Status:** Approved (brainstorming complete)
**Date:** 2026-04-30
**Author:** Brandon Fitzgerald
**Source repo at time of writing:** [/Users/brandon/Downloads/superpowers-main](/Users/brandon/Downloads/superpowers-main) (superpowers v5.0.7)
**Target version at v1.0 ship:** `bearpaws@1.0.0`
**Brainstorming session:** 2026-04-30 (this spec is the artifact)

---

## Summary

Bearpaws is a hard fork of the [superpowers](https://github.com/anthropics/superpowers-main) Claude Code plugin (forking from v5.0.7) that:

1. Renames and restructures into its own product identity.
2. Reduces token cost per session and across the skill suite without regressing reliability.
3. Adopts a structured XML schema for all skill bodies (with markdown allowed inside element content).
4. Adds 10 new domain-knowledge skills covering Google Cloud, Google ADK, Vite, JS/TS, and Cloud Run.
5. Ships only on Claude Code and Gemini CLI (drops Cursor and Codex from superpowers' four-platform matrix).

The work is delivered as a phased program in four phases (0–3), with eval gates at each phase boundary.

---

## Goals

- **Identity.** Establish Bearpaws as its own plugin with clean naming, manifests, and namespace.
- **Token efficiency.** Reduce per-session bootstrap cost ~50% and aggregate skill-body content ~25–30%.
- **Format consistency.** Every skill body conforms to a small, documented XML tag whitelist.
- **Domain depth.** Provide actionable in-flight knowledge for the technologies the team uses daily (GCP/ADK/Vite/JS-TS/Cloud Run).
- **Reliability discipline.** No skill ships under the new schema or condensed wording without eval evidence (writing-skills TDD-on-prose loop).

## Non-Goals

- Tracking superpowers upstream changes after the fork (hard fork — see Question 7 in Brainstorming Decisions).
- Cursor or OpenAI Codex platform support.
- A formal XML schema validator (XSD or grammar) — grep-based whitelist test is sufficient for v1.0.
- Service-specific GCP skills (BigQuery, Pub/Sub, Firestore, etc.). The `google-cloud` skill is cross-cutting only.
- Framework wrappers around Vite (Astro, SvelteKit, Nuxt) — pointers only.
- A separate Bearpaws marketplace distinct from the Claude Code marketplace.
- Migration tooling for existing superpowers users. Coexistence in a single Claude Code config is supported but not promoted.

---

## Brainstorming Decisions (locked-in answers)

| # | Decision | Implication |
|---|---|---|
| Q1 | Single combined spec, phased program | This document |
| Q2 | XML format option (d): structural XML + tag whitelist + markdown body | See §2 |
| Q3 | Claude Code + Gemini CLI only | Drops `.cursor-plugin/`, `.codex-plugin/`; keeps `.claude-plugin/`, `gemini-extension.json` |
| Q4 | Both reference and workflow domain skills | Each tech gets a pair |
| Q5 | One-per-technology, ref + workflow pair = 10 new skills | See §4 |
| Q6 | Aggressive token-efficiency tier (c) | bootstrap shrink + `_shared/` extraction + lazy-load heavy refs + condense long process skills |
| Q7 | Hard fork from superpowers | No upstream sync; clean restructure permitted |
| Q8 | Inherit + extend tests | Both `tests/skill-triggering/` and `tests/claude-code/` ported and extended |

Approach: **Approach 2 — Identity-First, Parallel Tracks** (vertical-slice validation in Phase 1, then parallel rollout).

---

## Section 1 — Identity & Repo Layout

### Plugin identity

- **Plugin slug:** `bearpaws`. External skill invocations: `bearpaws:writing-plans`, etc.
- **Hook namespace:** `bearpaws-session-start`.
- **Repo name:** `bearpaws` (top-level directory). Top-level `CLAUDE.md` and `README.md` rewritten for the new identity. README carries an attribution paragraph: *"Forked from superpowers at v5.0.7. License preserved."*

### Kept vs. dropped from the superpowers tree

| Kept (renamed where applicable) | Dropped |
|---|---|
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | `.cursor-plugin/` |
| `gemini-extension.json` | `.codex-plugin/` |
| `package.json` (renamed) | `skills/using-superpowers/references/copilot-tools.md` |
| `hooks/` (rewritten internally — see §3) | `skills/using-superpowers/references/codex-tools.md` |
| `scripts/bump-version.sh` + `.version-bump.json` (path list updated) | Any Cursor/Codex-specific test fixtures (audit during Phase 0) |
| `tests/` — both harnesses | |
| `agents/code-reviewer.md` | |
| `commands/` (renamed: `bearpaws:brainstorm`, etc.) | |

### Top-level layout

```
bearpaws/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── gemini-extension.json
├── package.json
├── hooks/
│   ├── hooks.json
│   ├── run-hook.cmd
│   └── session-start
├── skills/
│   ├── _shared/                  ← NEW: extracted Red Flags, dot graphs, common rules
│   ├── using-bearpaws/           ← renamed from using-superpowers; rewritten in §3
│   ├── <existing process skills, XML-migrated>
│   └── <10 new domain skills, see §4>
├── agents/
│   └── code-reviewer.md
├── commands/
├── scripts/
│   └── bump-version.sh
├── tests/
│   ├── claude-code/
│   └── skill-triggering/
├── docs/
│   └── bearpaws/specs/
├── CLAUDE.md
├── README.md
└── .version-bump.json
```

### Versioning

Bearpaws starts at `0.1.0` after Phase 0 (identity-only fork) and crosses `1.0.0` only after Phase 3 ships everything. Version is duplicated across four manifests (down from six in superpowers); `.version-bump.json` is the source of truth and `scripts/bump-version.sh` performs coordinated bumps.

---

## Section 2 — XML Schema

### Constraints

- **YAML frontmatter stays.** Claude Code's skill loader expects YAML frontmatter (`name:`, `description:`). That's loader metadata, not a prompt. "XML format" applies only to skill bodies (everything below `---`).
- **Markdown is allowed inside element content** — tables, fenced code (including `dot` blocks), lists, emphasis. XML supplies *structure and enforcement semantics*; markdown supplies *prose and visual layout*.

### The tag whitelist

The only legal tags inside skill bodies and any reference file:

| Tag | Purpose | Replaces in superpowers |
|---|---|---|
| `<skill>` | Root element of every skill body | (implicit, none) |
| `<purpose>` | One-paragraph what-this-skill-does | scattered intros |
| `<triggers>` | When the agent should reach for this skill | scattered prose |
| `<rules>` / `<rule>` | Non-negotiable directives (one per `<rule>`) | bullet lists labeled "Rules" |
| `<process>` / `<step>` | Ordered workflow | numbered markdown lists |
| `<flow format="dot\|mermaid">` | Diagram block (markdown content inside) | bare ` ```dot ` blocks |
| `<example type="good\|bad">` | Example with explicit polarity | `<Good>` / `<Bad>` ad-hoc tags |
| `<antipattern>` | Common mistake to avoid | "Anti-Pattern: ..." H2 sections |
| `<warning level="hard\|soft">` | Hard = critical behavioral imperative; soft = caution | `<EXTREMELY-IMPORTANT>`, `<EXTREMELY_IMPORTANT>` |
| `<gate name="...">` | Named blocking gate that must be passed before proceeding | `<HARD-GATE>` |
| `<subagent-stop>` | "Skip this skill if dispatched as a subagent" | `<SUBAGENT-STOP>` |
| `<include ref="_shared/...">` | Lazy-load shared content; agent calls Read when invoking the skill | (new — enables dedup) |
| `<see file="...">` | Pointer to auxiliary content; load only if explicitly relevant | implicit references/ links |
| `<placeholder name="...">` | Template variable | `<feature-name>`, `<base-branch>` ad-hoc |

### File-inclusion modes — explicit, distinct semantics

- `<include ref="_shared/red-flags-tdd"/>` — *the agent should Read this file when invoking the skill* (small/medium content extracted for dedup).
- `<see file="references/anthropic-best-practices.md"/>` — *auxiliary; consult only if explicitly relevant* (heavy refs that don't pre-load).

**Skill-author rule.** Extract content to `<include>` only if it is **>25 lines AND reused by ≥2 skills**. Demote content to `<see>` only if it is **>150 lines AND used in <30% of skill invocations**.

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
    digraph foo { ... }
  </flow>

  <example type="bad">
    <!-- markdown allowed inside -->
  </example>

  <include ref="_shared/red-flags-process"/>
  <see file="references/deep-dive.md"/>
</skill>
```

### Sharp edges to validate

1. **Bootstrap wrapper.** [hooks/session-start](hooks/session-start) currently wraps the skill in a custom `<EXTREMELY_IMPORTANT>` tag at the *outside* of the body. Under the schema, the body itself is `<skill>...</skill>` — the hook wraps the whole thing in `<warning level="hard">` instead of `<EXTREMELY_IMPORTANT>`. Two implications: hook script needs updating, and we need to confirm the model still treats `<warning level="hard">` as the imperative the old tag triggered. Validated in Phase 1.
2. **`<include>` follow-through.** Requires the agent to actually Read the included file when invoking the skill. If the model sometimes skips includes, dedup wins evaporate. Validated in Phase 1 by asserting consistent behavior between an `<include>`-using skill and a baseline skill that inlines the same content.

### Enforcement mechanism

A grep-based test under [tests/skill-triggering/](tests/skill-triggering/) fails on any tag outside the whitelist anywhere in `skills/`. Documented in `skills/writing-skills/SKILL.md` as part of the schema spec.

---

## Section 3 — Token-Efficiency Mechanics

### 3a. The `skills/_shared/` library — extractions

| New file | Source content | Skills consuming it | Mechanism |
|---|---|---|---|
| `_shared/red-flags-skill-discipline.md` | Rationalization tables in [skills/using-superpowers/SKILL.md:78-95](skills/using-superpowers/SKILL.md#L78-L95) and similar tables across ≥2 other skills | using-bearpaws, writing-skills, test-driven-development | `<include>` |
| `_shared/tdd-cycle-flow.md` | RED-GREEN-REFACTOR dot graph in [skills/test-driven-development/SKILL.md:31-69](skills/test-driven-development/SKILL.md#L31-L69) and overlapping content in writing-skills "TDD on prose" | test-driven-development, writing-skills | `<include>` |
| `_shared/yagni-rules.md` | Repeated "violating the letter is violating the spirit" YAGNI/TDD reminders | test-driven-development, writing-skills, brainstorming | `<include>` |
| `_shared/dot-flow-template.md` | Boilerplate dot setup repeated across ~10 diagrams (shape conventions, doublecircle = terminal state, etc.) | most skills with flows | `<include>` |
| `_shared/skill-instructions-priority.md` | Instruction priority hierarchy (user > skill > default) currently inlined in [skills/using-superpowers/SKILL.md](skills/using-superpowers/SKILL.md) | using-bearpaws, others | `<include>` |

Extraction rule (re-stated): >25 lines AND ≥2 consumers.

### 3b. Lazy-loading heavy references via `<see>`

| File | Current size | Demotion |
|---|---|---|
| [skills/writing-skills/anthropic-best-practices.md](skills/writing-skills/anthropic-best-practices.md) | 1,150 lines | `<see>` — loads only when authoring a new skill |
| [skills/writing-skills/testing-skills-with-subagents.md](skills/writing-skills/testing-skills-with-subagents.md) | 384 lines | `<see>` — loads only when running the eval workflow |
| `skills/test-driven-development/anti-patterns.md` (~299 lines, if present) | ~299 lines | `<see>` — loads only when the agent has hit one of the patterns |
| Per-platform tool mappings under `skills/using-superpowers/references/` | ~150 lines each | Drop `copilot-tools.md` and `codex-tools.md`; keep Gemini mapping under `<see>` |

### 3c. Process-skill condensation

Subject to the writing-skills TDD-on-prose loop in [CLAUDE.md:60-68](CLAUDE.md#L60-L68):

| Skill | Current | Target | What goes |
|---|---|---|---|
| [skills/writing-skills/SKILL.md](skills/writing-skills/SKILL.md) | 655 | ~400 | Cursor/Codex platform notes; duplicate TDD-basics teaching now in `_shared/tdd-cycle-flow.md`; some explanatory prose without behavioral payload |
| [skills/test-driven-development/SKILL.md](skills/test-driven-development/SKILL.md) | 371 | ~250 | RED-GREEN-REFACTOR diagram (now `_shared/`); duplicate YAGNI prose; redundant "violating the letter" reminders |
| [skills/systematic-debugging/SKILL.md](skills/systematic-debugging/SKILL.md) | 296 | ~220 | Overlap with `_shared/red-flags-skill-discipline.md`; long Why-it-works prose |
| [skills/brainstorming/SKILL.md](skills/brainstorming/SKILL.md) | 164 | ~130 | Visual-companion section compression; checklist-instructions duplication |

**Eval gate per condensed skill:** must pass its existing skill-triggering test AND a fresh pressure scenario in a clean subagent. If either regresses, condensation reverts and we ship the un-condensed version. **No skill ships condensed without eval evidence.**

### 3d. Bootstrap rewrite

The bootstrap is `skills/using-bearpaws/SKILL.md`, injected verbatim by [hooks/session-start](hooks/session-start) into every session.

**Cannot use `<include>` inside the bootstrap.** `<include>` requires the agent to actively Read the referenced file when invoking the skill — at session start the agent hasn't yet been taught to do that, so `<include>` in the bootstrap is circular. `<see>` is fine in the bootstrap because it's opt-in (the agent only follows the pointer if explicitly relevant); for example, the Gemini tool-mapping reference is reachable from the bootstrap via `<see>`. Bootstrap content reduction therefore comes from compression of the bootstrap body itself, not from `<include>`-based extraction.

| Section | Current | New |
|---|---|---|
| Tag wrapping | `<EXTREMELY_IMPORTANT>` from [hooks/session-start](hooks/session-start) | `<warning level="hard">` (matches schema) |
| Platform adaptation block ([skills/using-superpowers/SKILL.md:33-39](skills/using-superpowers/SKILL.md#L33-L39)) | 7 lines (Copilot/Codex/Gemini) | 2 lines (Claude+Gemini only) |
| Red Flags table | 12 rows, ~25 lines | Trimmed to 6–8 highest-leverage rows; the rest moves to `_shared/red-flags-skill-discipline.md` and the bootstrap *names* the file as a "if rationalizing further, see X" pointer |
| Process flow dot graph | ~30 lines | Stays — load-bearing |
| "How to access skills" platform block | ~8 lines (four platforms) | ~4 lines (Claude+Gemini) |
| "Skill priority" + "Skill types" + "User instructions" | ~30 lines | ~15 lines, same content |

**Target:** 117 → **~60 lines** (~50% reduction). Validated in Phase 1.

### 3e. Honest projections

These are projections; Phase 1 produces real measurements:

- Per-session bootstrap injection: **~6 KB → ~3 KB** JSON-escaped payload
- Suite-wide skill body content (15 process skills): **~7,000 lines → ~5,000 lines** (~28%); ~1,200 lines from dedup, ~800 from condensation
- Heavy reference content **no longer pre-loaded** in typical sessions: ~1,800 lines (anthropic-best-practices + testing-skills-with-subagents + dropped platform mappings)

If Phase 1 measurements come in materially below projection, that's a Phase 2 design conversation, not a Phase 1 ship-blocker.

---

## Section 4 — The 10 Domain Skills

**Authoritativeness rule.** Every domain skill claim cites a source — either an official doc URL via `<see file="..."/>` or a labeled "team convention" inline. No orphan claims.

**Phase 1 vertical-slice pair:** `cloud-run` + `deploying-to-cloud-run`. Cleanest official docs, hard checklist items, real `gcloud run deploy` command at the end.

### Skill-pair specs

#### 1. Google Cloud (broad)

- **`google-cloud`** (ref) — Triggers: `gcloud`, `*.googleapis.com`, `gcp`, `google-cloud-*` SDK packages. Scope: project/billing/IAM mental model; service catalog at "which service for what job"; `gcloud` CLI mechanics; auth (ADC, service accounts, Workload Identity Federation). **Out of scope:** deep dives into individual services.
- **`working-on-google-cloud`** (workflow) — Triggers: starting work on a GCP project. Scope: project bootstrap (set project, enable APIs, ADC); permissions troubleshooting flow; cost-aware decisions (tier, region, free-tier).

#### 2. Google ADK (Agent Development Kit)

- **`google-adk`** (ref) — Triggers: imports of `@google/genai-adk` / `google.adk`; project files like `adk.config.*`. Scope: agent shapes (single, sequential, parallel, loop); Tool/FunctionTool/built-in tools; sessions, state, memory; runners; deployment targets (local Web UI, API server, Vertex AI Agent Engine). **Version pinned in frontmatter.** **Out of scope:** OpenAI Agents SDK, LangChain agents, generic agent design.
- **`building-with-adk`** (workflow) — Triggers: scaffolding a new ADK agent or adding a tool. Scope: project init, defining tools, wiring sessions, choosing a runner, local testing, deploying to Cloud Run or Agent Engine. Hands off to `deploying-to-cloud-run` for deploy.

#### 3. Vite

- **`vite`** (ref) — Triggers: `vite.config.{js,ts,mjs}`, `package.json` with `"vite"` dependency, `import.meta.env`, `.env.local` in a Vite project. Scope: dev server vs. build pipeline; plugin model + ordering; HMR mechanics; `import.meta.env` and env-var conventions; common plugins (`@vitejs/plugin-react`, `vite-plugin-vue`, `unplugin-*`, `vite-tsconfig-paths`); SSR mode. **Out of scope:** framework wrappers (Astro/SvelteKit/Nuxt) — pointer only.
- **`working-with-vite`** (workflow) — Triggers: starting/modifying a Vite project. Scope: project init; "module not found" / alias debugging; production build sanity (preview, asset hashing, base path); test integration via Vitest; proxy configuration.

#### 4. JavaScript / TypeScript

- **`javascript-typescript`** (ref) — Triggers: `.ts`/`.tsx`/`.mts`/`.cts` files, `tsconfig.json`, `package.json` with `"typescript"`. Scope: ES2022+ language idioms; TS 5.x type-system features; behavior-changing `tsconfig.json` flags (`strict`, `moduleResolution: "bundler"`, `verbatimModuleSyntax`, `noUncheckedIndexedAccess`); Node vs. browser vs. worker module resolution; ESM/CJS interop. **Out of scope:** library-specific patterns; framework-specific React/Vue typing.
- **`writing-typescript`** (workflow) — Triggers: writing or refactoring TypeScript. Scope: `unknown` vs. `any` vs. generics vs. assertions; type-narrowing toolbox (discriminated unions, predicates, `satisfies`); error-handling patterns (Result types vs. throw); structuring `tsconfig.json` for a new project. Plays nicely with `test-driven-development` (no duplication).

#### 5. Cloud Run *(Phase 1 vertical slice)*

- **`cloud-run`** (ref) — Triggers: `gcloud run`, `Dockerfile` in a GCP project context, `service.yaml`, `cloudrun.yaml`. Scope: services vs. jobs; revision/traffic model; cold starts and instance scaling (CPU always allocated vs. request-based); concurrency; secrets via Secret Manager; VPC connectors and serverless VPC access; min/max instances; identity (runtime SA, deployer SA); auth modes (allow-unauthenticated vs. IAM-invoker). **Out of scope:** App Engine, GKE, Cloud Functions (mentioned only as "use this instead when X").
- **`deploying-to-cloud-run`** (workflow) — Triggers: about to deploy a Cloud Run service. Scope: pre-deploy checklist (region, image source, runtime SA, secrets bound, min-instance decision, concurrency, ingress, allow-unauthenticated decision); the `gcloud run deploy` invocation with the right flags; post-deploy verification (URL, logs, metrics). Hard `<gate name="checklist-complete">` blocks the deploy command until the checklist is walked.

### Per-skill structural template

Every domain skill follows the same XML body shape: `<purpose>` → `<triggers>` → `<rules>` (small handful of non-negotiables) → `<process>` (workflow only) or content blocks (reference only) → `<example>`s → `<see file="...">` pointers to official docs. Reference skills are heavier on `<rule>` and content; workflow skills invert.

### What's *not* a domain skill

- No general-purpose Google Cloud reference. Specific services get their own skills if and when needed, in a later spec.
- No general-purpose JS reference. That's MDN's job.
- No tutorial content. Skills are for in-flight working knowledge, not learning a tech cold.

---

## Section 5 — Phasing & Milestones

### Phase 0 — Fork & Rebrand *(workstream A)*

Goal: Bearpaws exists as a working plugin with the new identity. Zero content changes.

| Deliverable | Notes |
|---|---|
| New repo `bearpaws/` per §1 layout | Hard fork; commit history strategy is an open question — see §Open Questions |
| Manifests slimmed to Claude+Gemini | `.claude-plugin/{plugin,marketplace}.json`, `gemini-extension.json`, `package.json`. `.cursor-plugin/`, `.codex-plugin/` deleted. |
| `.version-bump.json` updated | Drops 2 entries, renames 4 |
| Hook namespace renamed to `bearpaws-session-start` | Script content unchanged |
| `skills/using-superpowers/` → `skills/using-bearpaws/` | Content unchanged |
| Per-platform reference docs trimmed | Drop `copilot-tools.md`, `codex-tools.md`; keep Gemini |
| `commands/` renamed to `bearpaws:` slash commands | Same content |
| README + CLAUDE.md rewritten | README carries superpowers attribution paragraph |

**Exit criteria:** All existing skill-triggering tests pass against the renamed plugin in a fresh Claude Code session. Plugin loads in Gemini CLI without error.

**Version on ship:** `0.1.0`.

### Phase 1 — Vertical Slice *(B + C + D, small surface)*

Goal: Prove the XML schema, `_shared/` library, lazy-load convention, and eval workflow on a controlled set of skills.

| Deliverable | Notes |
|---|---|
| `skills/_shared/` populated | 5 files per §3a |
| `skills/using-bearpaws/SKILL.md` rewritten in XML schema | Bootstrap. ~60 lines. Highest-stakes file. |
| `skills/test-driven-development/SKILL.md` rewritten + condensed | ~250 lines (down from 371) |
| `skills/cloud-run/SKILL.md` + `skills/deploying-to-cloud-run/SKILL.md` written fresh | First domain pair, citing official Cloud Run docs via `<see>` |
| Hook script updated | Wraps injection in `<warning level="hard">` instead of `<EXTREMELY_IMPORTANT>` |
| Skill-triggering tests added | One per new/migrated skill |
| Schema-validator test added | Greps unknown tags; fails build |
| Token-measurement script | Bootstrap size + suite-wide content size; runs at every phase boundary |

**Exit criteria — all four must pass:**

1. Bootstrap eval ≥ baseline (writing-skills pressure scenarios in fresh subagents).
2. TDD eval ≥ baseline (same protocol).
3. Cloud Run pair triggers on naive prompts.
4. Bootstrap shrink ≥ 40% (target 50%; accept 40% as pass).

**If exit criteria fail:** adjust schema or `_shared/` extractions and rerun. Don't move to Phase 2 with a known schema flaw.

**Version on ship:** `0.2.0`.

### Phase 2 — Parallel Tracks *(B + C + D, full rollout)*

Begins only after Phase 1 exit criteria are met. Two tracks share the schema validated in Phase 1.

#### Track A — Migrate remaining 14 process skills

| Batch | Skills |
|---|---|
| A.1 | brainstorming, writing-plans, **writing-skills** *(largest single token win — 655 → ~400)* |
| A.2 | systematic-debugging, verification-before-completion, executing-plans |
| A.3 | requesting-code-review, receiving-code-review, finishing-a-development-branch |
| A.4 | subagent-driven-development, dispatching-parallel-agents, using-git-worktrees |

#### Track B — Build remaining 8 domain skills

| Batch | Skills |
|---|---|
| B.1 | vite + working-with-vite *(second proof of pattern)* |
| B.2 | javascript-typescript + writing-typescript |
| B.3 | google-cloud + working-on-google-cloud |
| B.4 | google-adk + building-with-adk *(newest tech, most likely to need iteration)* |

**Coordination rule.** If Track A discovers a schema flaw mid-batch, Track B pauses at its next batch boundary; we adjust the schema once, then both tracks resume.

**Exit criteria:**
- All 25 skills (15 process + 10 domain) in XML schema.
- Schema validator passes for the whole `skills/` tree.
- All skill-triggering tests pass.
- Aggregate suite-wide content reduction ≥ 25% (vs. 28% projection).

**Version on ship:** `0.5.0`.

### Phase 3 — Integration & Release

Goal: Final lazy-load tightening, full integration suite, ship `1.0.0`.

| Deliverable | Notes |
|---|---|
| Heavy reference demotions applied | `<see>` pointers per §3b |
| Full [tests/claude-code/](tests/claude-code/) integration suite run | Includes `subagent-driven-development` integration test (10–30 min) |
| Transcript audit | Sample 5 normal sessions; confirm `<see>`-demoted files unread by default |
| Final token measurement documented | `docs/bearpaws/release-notes/1.0.0.md` |
| README final pass | Install instructions, examples, attribution |
| Coordinated version bump to `1.0.0` | Via `scripts/bump-version.sh` |

**Exit criteria:**
- All tests pass (skill-triggering + integration).
- Lazy-load `<see>` files confirmed unread by default in transcript audit.
- Final token-reduction numbers within target bands or explicit ship-decision conversation.

---

## Section 6 — Testing, Eval Gates & Risks

### Test surface after the fork

| Harness | Source | Bearpaws change |
|---|---|---|
| `tests/skill-triggering/` | Inherited | Plugin slug rename; one new triggering test per skill (15 migrated + 10 new = 25 total) |
| `tests/claude-code/` | Inherited | Plugin slug rename; new integration test for `subagent-driven-development → executing-plans` handoff under XML schema |
| Schema validator (new) | — | Grep-based test in `tests/skill-triggering/`; fails on any tag outside the §2 whitelist |
| Token-measurement script (new) | — | Reports bootstrap size + suite-wide skill-body line count; runs at every phase boundary |
| Transcript audit (Phase 3 only) | — | Manual review of 5 sessions; confirms `<see>`-demoted files unread by default |

### Eval gates — consolidated

| Phase | Gate | Source of truth |
|---|---|---|
| 0 | Existing skill-triggering tests pass against renamed plugin | `tests/skill-triggering/run-all.sh` |
| 1 | Bootstrap eval ≥ baseline | Manual eval per [CLAUDE.md:60-68](CLAUDE.md#L60-L68) |
| 1 | TDD eval ≥ baseline | Manual eval |
| 1 | Cloud Run pair triggers on naive prompts | `tests/skill-triggering/run-all.sh` |
| 1 | Bootstrap shrink ≥ 40% | Token-measurement script |
| 2 | Per-batch skill-triggering eval | `tests/skill-triggering/run-all.sh` |
| 2 | Aggregate content reduction ≥ 25% | Token-measurement script |
| 3 | Full integration suite pass | `tests/claude-code/run-skill-tests.sh --integration` |
| 3 | `<see>`-demoted files unread in normal sessions | Transcript audit |

### Risks

| # | Risk | Mitigation | Phase to validate |
|---|---|---|---|
| R1 | XML schema regresses skill-triggering reliability (eval-tuned phrasing depends on markdown structure) | Phase 1 vertical slice on highest-stakes skills (bootstrap + TDD); fail-and-revise; willing to cut condensation but not the schema | Phase 1 |
| R2 | `<include>` tool-call cost negates dedup wins | Token-measurement tracks net bytes saved minus tool-call cost; >25-line + ≥2-skills extraction rule is the ex-ante guard | Phase 1, recheck Phase 2 |
| R3 | `<see>` pointers followed by default, defeating lazy-load | Phase 3 transcript audit with explicit accept criterion; if observed behavior diverges, add `<see when="...">` attribute or fall back to fewer demotions | Phase 3 |
| R4 | Bootstrap shrink loses a load-bearing rule | Phase 1 bootstrap eval on a *broad* set of pressure scenarios; if any regress, offending content moves back inline | Phase 1 |
| R5 | Domain content bit-rots (Cloud Run, ADK, Vite, TS evolve fast) | `<see>` pointers to official docs (single source of truth); ADK frontmatter pins version; release notes flag version-sensitive sections | Ongoing |
| R6 | Integration suite runtime (10–30 min) discourages frequent runs | Skill-triggering suite (~2 min) gates per-batch; integration suite required only at Phase 1 exit and Phase 3 | Phase 1, Phase 3 |
| R7 | Hard fork loses upstream improvements | Intentional choice (Q7); occasional manual triage of superpowers releases is the accepted maintenance cost | Ongoing |
| R8 | Gemini CLI's skill-loading differs from Claude Code's, interacting badly with our XML schema | Phase 0 exit includes "loads in Gemini CLI without error"; Phase 1 includes triggering test in Gemini for the bootstrap; if Gemini can't parse, add Gemini-specific transformation in `hooks/run-hook.cmd` | Phase 0 (load), Phase 1 (trigger) |
| R9 | Schema design too rigid for some legitimate skill content | Phase 1 surfaces these cases; response is to *grow the whitelist* with documented justification, not abandon the schema | Phase 1 |

---

## Open Questions Deferred to Implementation

These are flagged open in the spec; resolved during writing-plans pass or during authoring:

1. **Commit-history strategy for the fork** — preserved (rebase from superpowers) vs. restarted (squashed initial commit + Bearpaws history forward). **Recommendation:** restarted, since this is a hard fork.
2. **`<include>` resolution semantics** — does the bootstrap explicitly teach the agent to follow includes, or does the schema documentation suffice? Phase 1 will determine.
3. **ADK version to pin against** at v1.0. Decision at authoring time during Track B Batch B.4.
4. **Whether `working-with-vite` should know about Vitest specifically** or hand off to a future `using-vitest` skill. Decision at authoring time.
5. **Whether the `code-reviewer` agent persona** in `agents/code-reviewer.md` needs updating for the new domain skills. Likely yes; lightweight update in Phase 3.

---

## Out of Scope for v1.0

Explicit, so the spec doesn't grow:

- Schema validator as XSD or formal grammar.
- Service-specific GCP skills (BigQuery, Pub/Sub, Firestore, etc.).
- Framework wrappers around Vite (Astro, SvelteKit, Nuxt).
- A separate Bearpaws marketplace.
- Migration tooling for existing superpowers users.

---

## Appendix — Source Audit Snapshot (2026-04-30)

Captured here so future readers see what Bearpaws is forking from:

- 15 skills, 37 markdown files, ~7,000 lines under [skills/](skills/)
- Top weights: [skills/writing-skills/anthropic-best-practices.md](skills/writing-skills/anthropic-best-practices.md) (1,150 lines), [skills/writing-skills/SKILL.md](skills/writing-skills/SKILL.md) (655), [skills/test-driven-development/SKILL.md](skills/test-driven-development/SKILL.md) (371)
- Bootstrap injection: 117 lines (~12–15 KB JSON-escaped) into every session via [hooks/session-start](hooks/session-start)
- Custom tags in use: `<EXTREMELY-IMPORTANT>`, `<EXTREMELY_IMPORTANT>`, `<HARD-GATE>`, `<SUBAGENT-STOP>`, `<Good>`/`<Bad>` — ad-hoc, no schema
- Repetition hotspots: Red Flags tables in 3+ skills, ~10 dot diagrams, repeated TDD/YAGNI reminders
- Six version-bearing manifests in superpowers; Bearpaws reduces to four
- Tests are bash + Node; no Python or other runtime dependencies
