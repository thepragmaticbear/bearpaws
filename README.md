# Bearpaws

**Adaptive engineering discipline for coding agents.**

Bearpaws separates difficulty from danger. Elevated-risk work gets more proof: pinned behavior, a failing test first, an independent review, and verification evidence. Routine work stays light, however large it is. In Claude Code, the risk floor is enforced by a hook, not just requested.

## Difficulty is not danger

A one-line change to authentication logic is simple to write but carries high risk. A 500-line UI refactor is complex but carries low risk. Bearpaws treats complexity and risk as separate axes:

|  | **Low risk** | **High risk** |
|---|---|---|
| **Low complexity** | Implement with TDD where it applies, verify with fresh evidence | Pin existing behavior, failing test first, narrow diff, stated assumptions, independent review, verification evidence |
| **High complexity** | Written plan, a fresh subagent per task, one combined review per task | Written plan, a fresh subagent per task, spec review then quality review, a final review |

The deciding factor is **blast radius, not code size**:

| Change | Complexity | Risk | Treatment |
|---|---|---|---|
| Rename button text | Low | Low | Routine |
| Rewrite animation system | High | Low | Routine, planned |
| Change password-reset validation | Low | High | Elevated: authentication |
| Modify tenant authorization | Medium | Very high | Elevated: authorization |
| Add a database migration | Medium | High | Elevated: data migration |
| Change payment rounding | Low | High | Elevated: money |

Risk has two levels: routine and elevated. Bearpaws does not grade it any finer. When the classification is arguable, the change is elevated.

## Show me

Every reply that changed files ends with a risk receipt. Routine work needs only `Risk:`, `Verified:`, and `Status:`. Elevated work adds the rest:

```text
Risk: elevated (authorization)
Pinned: test_owner_allowed, test_admin_same_org passed before edit
Failing first: test_admin_cross_org_denied failed, then passed
Review: bp:code-reviewer — Ready to merge: Yes
Assumptions: org_id is never null on users or resources
Verified: pytest — 14 passed, 0 failed
Status: COMPLETE
```

In Claude Code, a `Stop` hook enforces the floor:

- A reply that leaves file edits pending without a receipt is blocked.
- Elevated work cannot end `Status: COMPLETE` unless a review was dispatched after the last edit. `Status: INCOMPLETE` is always allowed.
- Routine work that edited sensitive-looking paths (auth, token, payment, migration, sql, …) gets a one-time nudge to reclassify or say why it is routine.

Set `BEARPAWS_ENFORCE=0` to turn it off. It needs `jq` and Claude Code 2.1.163 or later; without either it does nothing. Elsewhere, these rules are instructions only. The hook checks that a receipt and a review exist, not that every line in the receipt is true.

## Evidence

The [escaped-defect benchmark](docs/benchmarks/2026-10-12-escaped-defects.md) was pre-registered: six elevated-risk tasks with hidden attack tests, 5 runs per task per arm, Sonnet in Claude Code.

- **Escaped defects:** Bearpaws 9/30, no plugin 12/30, Superpowers 6.4.2 12/30. The difference is **not statistically significant** (Fisher exact p = 0.59). Counting one run that ended INCOMPLETE with the defect still present, Bearpaws' figure is 10/30.
- Bearpaws eliminated the negative-refund defect (0/5 against 5/5 in each other arm). That comparison is post hoc and uncorrected, and rests on one attack. It was no better on reset tokens and slightly worse, within noise, on SQL sort injection and tenant authorization.
- In 7 of 9 Bearpaws escapes, its own reviewer flagged the defect and the agent still shipped `Status: COMPLETE`. That motivated the review-findings rule: a same-risk defect the review finds in the code you changed is part of the fix.
- **After that rule** (a same-arm before/after on the same frozen scenarios, not pre-registered): Bearpaws escapes fell from 9/30 to 3/30 (p = 0.10). SQL sort and tenant authorization went to 0, mostly through broader first fixes rather than fixes after review. All 3 remaining escapes are the reset-token single-use attack, which the agents' reviewers flagged and the agents left as outside the request. Cost rose about 33% per task. [Results](docs/bearpaws/plans/2026-10-12-review-findings.md#results-2026-10-12).
- **Over-building:** a [diff-size measurement](docs/benchmarks/2026-10-21-diff-size-baseline.md) on the same six tasks found Bearpaws writing about 1.9× the code lines of a careful reference fix (no plugin 0.8×, with 15 of 32 escapes). The extra lines were NaN, bool and type guards that reviewers filed as Important and agents fixed under the same-class rule. After the reviewer templates and the bootstrap's definition of a defect were changed, the ratio fell to 1.4× with escapes unchanged at 5 of 30 and cost down about 13%. One intermediate wording let a negative-refund check be dropped; the final wording and a review fixture pin that case.
- **Cost:** on these risky tasks, Bearpaws cost about 2.4× Superpowers per task (and 4.7× no plugin); that includes a review on every run. On routine tasks it is about level with Superpowers: $0.098 against $0.096 per task in the [2026-09-30 run](docs/benchmarks/2026-09-30-three-way.md).

Small samples, Python stdlib scenarios, one model. Read the write-ups' limits before quoting these numbers.

## Install

**Claude Code:**

```bash
claude plugin marketplace add thepragmaticbear/bearpaws
claude plugin install bp@bearpaws
```

For a local checkout, run `claude --plugin-dir /path/to/bearpaws`. For non-trivial work we recommend `/model opusplan`: Opus plans in native Plan Mode and Sonnet executes, and Bearpaws never switches models itself.

**Google Antigravity IDE:** clone, install, then restart Antigravity.

```bash
git clone https://github.com/thepragmaticbear/bearpaws.git && cd bearpaws
./install.sh --antigravity --global
```

Codex, OpenCode, Grok Build, Copilot CLI, Cursor, Devin (experimental): see [docs/install.md](docs/install.md).

## How it works

```mermaid
flowchart TD
    Start([User prompt]) --> Bootstrap[bp:using-bearpaws<br/>bootstrap: skill discovery + elevated-risk rule]
    Bootstrap --> Check{Project<br/>context?}
    Check -->|yes| Onboard[bp:onboarding-to-a-project]
    Check -->|abstract design| Brainstorm
    Onboard --> Brainstorm[bp:brainstorming]
    Brainstorm --> Plan[bp:writing-plans<br/>native Plan Mode in Claude Code]
    Plan --> Risk{Elevated<br/>risk?}
    Risk -->|routine| Light[TDD<br/>one combined review per task under subagents]
    Risk -->|elevated| Strong[Pin behavior + failing test first<br/>narrow diff + stated assumptions<br/>independent review]
    Light --> Verify[bp:verification-before-completion<br/>risk receipt]
    Strong --> Verify
    Verify --> Gate{{Claude Code Stop hook<br/>checks receipt and review}}
```

A fully specified small fix goes straight to TDD and verification; plans are for non-trivial work. The bootstrap is small (about 4.9 KB, 4,989 bytes) and is the only thing loaded every session; every other skill loads on demand.

## Skills

| Skill | Type | Purpose |
|---|---|---|
| `bp:using-bearpaws` | Bootstrap | Skill discovery, the elevated-risk rule, and the risk receipt. Loaded at session start, never invoked directly. |
| `bp:onboarding-to-a-project` | Always first | Read the stack, project guidance, sample files, and test command before touching the codebase |
| `bp:brainstorming` | Process | Agree a design before creative work |
| `bp:writing-plans` | Process | Write implementation plans from specs |
| `bp:executing-plans` | Process | Execute a written plan with checkpoints |
| `bp:subagent-driven-development` | Process | A fresh subagent per task, with risk-proportional review |
| `bp:dispatching-parallel-agents` | Process | Run independent tasks in parallel subagents |
| `bp:test-driven-development` | Process | RED → GREEN → REFACTOR |
| `bp:systematic-debugging` | Process | Find the root cause before fixing |
| `bp:requesting-code-review` | Process | Dispatch an independent reviewer |
| `bp:receiving-code-review` | Process | Evaluate review feedback before applying it |
| `bp:verification-before-completion` | Process | Fresh evidence and the risk receipt before any completion claim |
| `bp:finishing-a-development-branch` | Process | Merge, PR, keep, or discard finished work |
| `bp:using-git-worktrees` | Process | Isolate feature work in git worktrees |
| `bp:writing-skills` | Process | Write and test skills with RED/GREEN evals |

## How Bearpaws differs from Superpowers

Bearpaws began as a fork of [Superpowers](https://github.com/obra/superpowers), and the core discipline is shared: brainstorm, plan, test first, debug systematically, review, verify. The main differences are how much process a change gets and how the end of a change is checked. The table lists those and a few smaller ones.

| | Superpowers 6.4.2 | Bearpaws |
|---|---|---|
| What sets the amount of process | Scope: the agent classifies a request as spike, bounded, or architectural and says so, so the human can override | Scope and blast radius, as two separate axes |
| Small but risky changes | No separate risk tier. Risk is one input to choosing the reviewer's model, and a security-sensitive action stops execution to ask the human | A fixed floor for [elevated-risk changes](#difficulty-is-not-danger): pinned behavior, failing test first, narrow diff, stated assumptions, independent review |
| Finishing a change | Verify before claiming done | Verify, then end every reply that changed files with a risk receipt (`Risk`, `Verified`, `Status`) |
| Findings from review | Critical and Important findings go through a fix loop with re-review. Minor ones are logged for the final review | The same, plus: a same-risk defect found in the changed code is part of the fix even if it falls outside the request, or the work ends `INCOMPLETE` |
| How the rules are applied | Instructions to the agent | Instructions, plus a Claude Code hook (see [Show me](#show-me)) |
| Getting to know a project | Part of brainstorming | A separate onboarding step that runs first |
| Trade-off | No added process for risk, so no added cost for it | Similar cost on routine work in the 2026-09-30 run; more time and cost on elevated work, for pinned tests, failing-first tests and reviews |

Measured results, including where Bearpaws did no better, are in [Evidence](#evidence).

## Support status

| Agent | Status | Evidence |
|---|---|---|
| Claude Code | Primary | Working |
| Google Antigravity IDE | Primary | Native plugin, skills, subagents, and capability adapter |
| OpenCode | Experimental | Wiring checked in CI: repo-level and global `.agents/skills` discovery, `instructions` bootstrap resolves; live bootstrap smoke-tested |
| Grok Build | Experimental | `./install.sh --grok --global`; `grok inspect` lists the bootstrap rule and all skills (1.0.45, built from source); no live session run |
| Other Agent Skills agents (Codex, Devin, Cursor, Copilot, …) | Experimental | Codex skills and `AGENTS.md` bootstrap checked in CI, activation smoke-tested; Copilot CLI installs the plugin (CI); Devin and Cursor hook payloads follow their docs, unverified live. Expanded conformance requires completed-action evidence. |

See [docs/agent-support.md](docs/agent-support.md) for the support policy and the evidence behind each status.

## More

- [Release notes](docs/bearpaws/release-notes/)
- Benchmarks: [escaped defects](docs/benchmarks/2026-10-12-escaped-defects.md), [three-way cost](docs/benchmarks/2026-09-30-three-way.md)
- [Skill structure](docs/skill-structure.md) and [testing](docs/testing.md)
- [CLAUDE.md](CLAUDE.md) for contributors: repo layout, the full test list, and how skills are edited

## Attribution

Bearpaws originated as a fork of **[superpowers](https://github.com/obra/superpowers)** v5.0.7 by Jesse Vincent and contributors, released under the MIT license. The MIT terms and upstream copyright are preserved in [LICENSE](LICENSE); Bearpaws now develops on its own line and is not affiliated with or endorsed by the superpowers project.

## License

MIT — see [LICENSE](LICENSE).
