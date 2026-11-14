# Unreleased

## Breaking changes

- **Removed deprecated slash commands (`commands/*.md`):** deleted `commands/brainstorm.md`, `commands/write-plan.md`, and `commands/execute-plan.md`. Use the equivalent skills directly: `bp:brainstorming`, `bp:writing-plans`, and `bp:executing-plans`.

## Enforcement gates (`risk-gate` & `git-commit-msg`)

- **Receipt fields required on every edited reply:** both the Claude Code `Stop` gate and the git `commit-msg` gate now require `Verified:` and `Status:` (`COMPLETE` or `INCOMPLETE`, with optional trailing note) on every reply or commit with edits (and `Not checked:` in Claude Code, plus `Pinned:`, `Failing first:`, `Review:`, `Open:`, and `Assumptions:` on elevated-risk Stop receipts). Bare `Risk: routine` lines are refused, multi-line bulleted field values are supported, and `>`-quoted receipt lines no longer count.
- **Returned foreground reviewer required:** `SendMessage` no longer counts as a review. An `Agent` or `Task` review counts only when targeted to a reviewer `subagent_type` or a non-Explore/Plan/guide/statusline/fork agent with a review description and a returned non-error, non-async `tool_response` with text.
- **Placeholder `Review:` list tightened:** elevated `Status: COMPLETE` refuses empty or placeholder `Review:` values (`none`, `skipped`, `n/a`, `n.a.`, `na`, `-`, `—`, `todo`, `tbd`, `pending`, `self`, `self-review`, `not done`/`run`/`yet`, `no review`, and `none found, approved`), while real verdicts such as `No issues found by bp:code-reviewer` or `Not blocking: minor nits only` are allowed.
- **Runner-aware `Verified:` matching:** claims naming a runner (`pytest`, `npm test`, `go test`, …) now require a logged run of that canonical runner or a passing wrapper runner (`npm`, `pnpm`, `yarn`, `bun`, `make`, `just`, `tox`, `nox`, `rake`, or a test `script`) after the last edit. If a named runner failed after the last edit, that runner itself must pass after the failure (a wrapper pass cannot mask its failure). Parenthetical asides without a pass/fail result word (e.g. `(jest config unchanged)`) are not treated as separate runner claims, and glob tokens (`*`, `?`) are ignored as runner names.
- **Test-command filtering:** info, listing, and dry-run flags (`--version`, `--help`, `-h`, `-V`, `--collect-only`, `--co`, `--list`, `--list-tests`, `-list`, `ctest -N`, `make -n`, `vitest list`, `cargo nextest list`, …), segments after `||`, and quoted spans outside `sh -c`/`bash -c` no longer count as test runs.
- **Sensitive-path boundary matching:** `sensitive_paths` now splits camelCase/acronym boundaries (keeping `getACLs` intact) and anchors short stems while keeping longer stems (`login`, `permission`, `polic`, `migrat`, `crypt`, `postgres`, `price`, `pricing`) unanchored and filtering benign words (`tokenizer`, `schematic`, `priceless`, `police`, `policeman`, `cryptic`, `author`, `secretary`).
- **Large-repo fingerprint cap (`BEARPAWS_FINGERPRINT_MAX`):** `risk-gate` caps full-tree `stat` at `BEARPAWS_FINGERPRINT_MAX` (default `20000` files) and falls back above the cap to `git --no-optional-locks status --porcelain -z -uall` plus `stat` of listed files. Windows backslash paths and drive letters are normalized before stripping `cwd` / `HOME` / `CLAUDE_CONFIG_DIR`.

## Session bootstrap & hooks

- **Compaction re-injection:** `hooks/hooks.json` `SessionStart` matcher is now `startup|clear|compact` so the `using-bearpaws` bootstrap is re-injected after context compaction.
- **Skill directory in bootstrap:** `hooks/session-start` appends the resolved `using-bearpaws` skill directory path so relative `references/...` links resolve without guessing.

## Tooling, CI, & evals

- **`./install.sh --doctor`:** read-only diagnostic check for `jq`, `bash`, Claude Code (`>= 2.1.163`), `BEARPAWS_ENFORCE`, `CLAUDE_PLUGIN_DATA`/`TMPDIR` writability, installed git hooks, linked agent skill directories, and Windows `bash` resolution.
- **Cross-platform CI:** added `macos-latest` and `windows-latest` (Git Bash) hook and installer CI jobs.
- **Eval scorers & UTF-8 token metric:** tightened `tests/risk-eval/score.py` and `tests/review-eval/score.py` (requiring returned reviewer dispatches, valid pre-edit test runs aligned with gate rules, substantive `Assumptions:`, diagnosis-backed defect matching, and accuracy/format breakdowns); `tests/token-measurement/measure.sh` now reports UTF-8 byte counts, approximate `bytes / 4` token estimates, typical-session totals, and normalizes the machine-specific plugin root in `bootstrap_additional_context_bytes`.
