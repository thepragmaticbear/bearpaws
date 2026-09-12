# Antigravity Capability Mapping

BearPaws skills define intent. Use the equivalent native Antigravity capability
when a skill names a platform-oriented action.

| BearPaws reference | Antigravity behavior |
|---|---|
| Read | Native file reading (`view_file`) |
| Write | Native file creation (`write_to_file`) |
| Edit | Native file editing (`replace_file_content`) |
| Bash | Native command execution (`run_command`) |
| Grep | Native content/code search (`grep_search`) |
| Glob | Native file discovery (`find_by_name`, `list_dir`) |
| TodoWrite | Native planning/task tracking (`implementation_plan.md`) |
| Skill | Native Agent Skill discovery/activation |
| WebSearch / WebFetch | Native search/browser capability (`search_web`, `read_url_content`) |
| Task / subagent | `invoke_subagent` or packaged custom agent |

Do not use legacy Gemini CLI `activate_skill`.

When a BearPaws skill applies, load/use the native Antigravity skill before
performing the governed work.

When BearPaws requests a fresh implementer, reviewer, research agent, or
parallel worker, use an isolated Antigravity subagent.

Use the packaged `code-reviewer` agent when `requesting-code-review` calls for it.

Native speed or parallelism does not override BearPaws workflow gates.

**Momentum does not waive gates.**
