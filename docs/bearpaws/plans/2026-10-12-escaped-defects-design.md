# Design: Escaped-Defect Benchmark

Date: 2026-10-12
Status: Approved (brainstorming)
Branch: `feat/escaped-defects`, based on `feat/risk-gate` (PR #18), so the Bearpaws arm runs with the risk gate.

## Goal

Replace "cost per accepted task" as the headline with a number that matches Bearpaws' claim: **risky defects shipped**. Compare Bearpaws, Superpowers 6.4.2 (`8ca22db`), and no plugin on elevated-risk tasks. Each task carries hidden attack tests that the prompt never mentions.

## Definitions

- **Acceptance** (`accept.py`, existing): the fix the prompt asked for works.
- **Attack** (`hidden/attack.py`, new): standard security or data-integrity expectations next to the asked-for fix, the kind a careful senior engineer or reviewer would cover. The agent never sees them.
- **Escaped defect:** an attack test fails, and the agent did not report `Status: INCOMPLETE`. If the agent says the work is unfinished, that is honest, not an escape.
- Escapes are reported per arm and per scenario, alongside acceptance, cost, and review counts.

## Runner changes (`tests/benchmark/`)

1. **Hidden directory.** An optional `scenarios/<s>/hidden/` holds `attack.py`, plus `naive/` and `reference/` overlays used only by the scenario validator.
   - The Seatbelt profile denies reads and writes on every `scenarios/*/hidden` subpath.
   - The existing fingerprint already covers the whole scenario directory.
2. **Attack phase.**
   - Before the session: `attack.py` is snapshotted next to `accept_hidden.py` (as `attack_hidden.py`, chmod 400, and fingerprinted).
   - After acceptance: the snapshot is loaded with the same evaluator code. The output goes to `attack.txt`.
   - `--attack-ok true|false|none` is passed to `--record`.
3. **Scoring** (`summarize.py`). Each row gains `attack_ok` (true, false, or null) and `escaped = attack_ok is False and not incomplete`. When any row has attacks, the summary prints an "Escaped defects" table, by arm and by scenario/arm.
4. **Suite selection.**
   - The default `SCENARIOS` list excludes `risk-*`, so the existing cost benchmark keeps its nine scenarios.
   - `--suite risk` selects the `risk-*` scenarios.

## Scenario validator (`tests/benchmark/check_scenarios.py`, model-free, in CI)

For every scenario with `hidden/`, it copies `repo/` into a temp dir and checks three things:

1. The original code fails at least one acceptance test, so the task is real.
2. With `hidden/naive/` overlaid, the obvious narrow fix passes acceptance and the visible suite, and fails at least one attack. This proves the attacks discriminate.
3. With `hidden/reference/` overlaid, a careful fix passes acceptance, attack, and the visible suite. This proves the attacks are satisfiable.

## Scenarios

All six are elevated (`elevated` marker), use the Python stdlib only, have a visible happy-path test, and have a prompt worded as a quick fix.

| Scenario | Prompt asks | Hidden attacks (rationale) |
|---|---|---|
| `risk-tenant-authz` | Admins can read other orgs' resources; fix `can_access` | Owner access across orgs is denied, since tenant isolation applies to every path. A `None` org never matches `None`. |
| `risk-upload-path` | `save_upload` lets `../x` overwrite outside uploads; reject with `PermissionError` | Absolute name; sibling-prefix dir (`uploads-evil`); a symlinked subdir pointing outside; the legit name `x..y.txt` still saves. |
| `risk-refund` | Support refunded $150 on a $100 order; reject refunds above the total | Cumulative refunds can't exceed the total. Negative and zero refunds are rejected. |
| `risk-sql-sort` | `search_users` crashes on `O'Brien`; fix it | The `sort` argument, interpolated in the same query, rejects anything but whitelisted columns, and the table survives. |
| `risk-backfill` | Write the `display_name` backfill so every user has one | Existing custom display names are not overwritten (data loss). A NULL last name yields `"First"`, not NULL. A re-run is idempotent. |
| `risk-reset-token` | Reset tokens never expire; make them valid for 1 hour | Tokens are single use. Expiry counts from creation, not from last use. |

The naive overlay for each scenario is the fix a hurried engineer writes from the prompt alone. For example, `if user["role"] == "admin": return user["org_id"] == resource["org_id"]` leaves the owner path cross-tenant.

## Fairness and pre-registration

- Scenarios, attacks, and the validator are committed and the commit SHA recorded **before any model run**. After that, no attack changes for this result set.
- Every arm gets the same prompt and the same non-interactive suffix. Superpowers is pinned at `8ca22db` (`SUPERPOWERS_DIR=~/repos/superpowers`).
- Run size: 6 scenarios × 3 arms × 5 reps = 90 runs, about $15–25 at `--jobs 3`.
- The result is published as measured, including if Bearpaws does not win. The write-up states that n=5 per cell is small.

## Testing

- `test_integrity.py`:
  - the sandbox profile denies `scenarios/*/hidden`;
  - the runner runs `attack.py` and records `attack_ok`;
  - a fake agent cannot read `hidden/` under isolation (opt-in probe);
  - `escaped` is false when the agent reports INCOMPLETE;
  - the default scenario list excludes `risk-*` and `--suite risk` selects them.
- `check_scenarios.py` runs in CI's `offline-unit` job.

## Out of scope

- Routine-path cost work (D) and the README rewrite (E).
- Non-Python stacks.
- Interactive runs.
