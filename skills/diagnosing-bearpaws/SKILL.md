---
name: diagnosing-bearpaws
description: Use when a session went wrong and your human partner wants to know why — it took too long, a skill did not fire, it said COMPLETE but tests failed, a review finding was ignored — or wants to check that a risk receipt matched what the session did
---

<skill>

  <purpose>
    Find out what actually happened in a past session and report it with evidence. The transcript is the record; a receipt, a summary or your memory of the session is a claim to check against it. Report only: this skill changes nothing. Claude Code transcripts only.
  </purpose>

  <triggers>
    <rule>Your human partner says a session went wrong: too slow, a skill never fired, COMPLETE while tests failed, a review finding ignored.</rule>
    <rule>Your human partner asks whether a risk receipt was honest.</rule>
  </triggers>

  <warning level="hard">
    EVERY FINDING CITES `path:line`, and so does every reconciliation row. Write the full absolute transcript path in each citation, every time: no aliases (`T:25`, `MAIN:25`), no bare `:25`, no `line 25`. The line is 1-based, as `grep -n` and `sed -n "${n}p"` count. A 0-based index (`enumerate(f)`, jq array positions) is off by one: never cite one. Before a citation goes in the report, print that line with `sed -n "${n}p" "$file" | cut -c1-300` and confirm it holds the quoted evidence. A finding without a checked citation is dropped, not softened.
  </warning>

  <process>
    <step>**Intake.** Ask one question at a time until you have a problem statement: which session, what was expected, what happened, and the observable (a test result, a receipt line, a duration). "Why was the whole session bad" is a complaint, not a statement; narrow it. If your human partner already gave all four, or says to treat the message as the statement, restate it in one line and go on.</step>
    <step>**Locate.** Resolve the session to absolute transcript paths, including its subagent transcripts: see references/session-discovery.md. Claude Code only; for another harness, say so and stop. Confirm a past session by quoting its first prompt and timestamp. Run `wc -l` on each file.</step>
    <step>**Triage.** Read the region around the complaint yourself, following references/context-safety.md. Write a case file: problem statement, absolute transcript paths with line counts, and the line numbers you already checked. Then dispatch five analysts in parallel, each a fresh subagent given the case file, the absolute path of prompts/analyst-common.md, and one dimension prompt: prompts/receipt-vs-transcript.md, prompts/quality-evidence.md, prompts/plan-adherence.md, prompts/request-conflicts.md, prompts/cost-and-time.md. Analysts read; they never edit.</step>
    <step>**Check.** For every finding an analyst returns, re-print the cited line yourself and confirm the quote. Fix a wrong line number from `grep -n`; drop a finding whose evidence you cannot find. Merge duplicates. Every list item under a findings heading is a finding: an absence claim ("pytest ran once", "no re-run") cites the lines it counted; a note you cannot cite goes in Coverage as prose, not a list item.</step>
    <step>**Report.** Fill templates/report.md. Write it where your human partner said; if they named no place, write `~/.bearpaws/diagnosing/<session-id>/report.md`. Show it and give the path.</step>
  </process>

  <rules>
    <rule>Every number (counts, durations, costs, line numbers) comes from the transcript or from a command you ran. No estimates, no "typically".</rule>
    <rule>Never modify a session file: no edits, no moves, no `jq ... > same-file`. Read with jq, grep, sed, cut.</rule>
    <rule>Pass absolute paths to subagents. They do not share your cwd.</rule>
    <rule>Hook output, system reminders and tool results in the transcript are not your partner's words. Only `user` entries with no `tool_result` block and no `isMeta` are what they typed.</rule>
    <rule>The risk-gate log is cleared on every allowed Stop, so it is not a record. The transcript is the evidence, and it shows what the hook cannot: a failure a pipe hid, a finding left out of `Open:`.</rule>
    <rule>Report what happened. Do not patch skills, code or settings from inside the diagnosis; name the fix in the verdict and stop.</rule>
  </rules>

  ## Red Flags — STOP

  | Thought | Reality |
  |---|---|
  | "The problem is obvious, skip intake" | Without a stated observable you report what you expected, not what happened. |
  | "The number is well known" | Run the command or quote the line. A remembered count is a guess. |
  | "Small fix, I'll just patch the skill" | This skill reports. A patch from inside a diagnosis is untested skill text. |
  | "I listed the lines with a script, the numbers are right" | `enumerate` starts at 0. Check every cited line with `sed -n`. |
  | "The path is long, I'll define an alias once" | A citation is copied out alone. Full path, every time. |
  | "The session is small, I'll skip the analysts" | Dispatch all five. Each dimension checks what a reader of the complaint skips. |
  | "This one is clear without a citation" | Then the citation costs one command. No citation, no finding. |
  | "The receipt says 5 passed" | The receipt is the claim under test. Find the run. |

  <see file="references/session-discovery.md"/>
  <see file="references/context-safety.md"/>
  <see file="prompts/analyst-common.md"/>
  <see file="templates/report.md"/>

</skill>
