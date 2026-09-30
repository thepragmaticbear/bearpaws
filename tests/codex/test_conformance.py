"""Offline regression checks; no Codex requests or installed skills required."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import evidence

HERE = Path(__file__).resolve().parent


def command(text, output="<skill>real body</skill>", rc=0, status="completed"):
    return {"type": "item.completed", "item": {
        "type": "command_execution", "command": text,
        "aggregated_output": output, "exit_code": rc, "status": status}}


class Evidence(unittest.TestCase):
    def shell(self, expression, events):
        # Load just the runner helpers, without starting paid CLI scenarios.
        script = (HERE / "run-conformance.sh").read_text().split("# Run scenarios.")[0]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "stream.jsonl"
            path.write_text("".join(json.dumps(e, separators=(",", ":")) + "\n" for e in events))
            result = subprocess.run(["bash", "-c", script + "\n" + expression,
                                     str(HERE / "run-conformance.sh"), str(path)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout.strip()

    def read_skill(self, events):
        return int(self.shell('read_skill "$1" systematic-debugging', events))

    def test_skill_mentions_are_not_reads(self):
        self.assertEqual(self.read_skill([{"type": "item.completed", "item": {
            "type": "agent_message", "text": "Read skills/systematic-debugging/SKILL.md"}}]), 0)

    def test_failed_read_is_not_loaded(self):
        self.assertEqual(self.read_skill([command(
            "cat .agents/skills/systematic-debugging/SKILL.md", "missing", 1, "failed")]), 0)

    def test_echo_is_not_a_read(self):
        self.assertEqual(self.read_skill([command(
            "echo .agents/skills/systematic-debugging/SKILL.md")]), 0)

    def test_successful_cat_and_rtk_read_are_loaded(self):
        for tool in ["cat", "rtk read"]:
            self.assertEqual(self.read_skill([command(
                f"/bin/zsh -lc '{tool} .agents/skills/systematic-debugging/SKILL.md'")]), 1)

    def test_timeout_with_completed_items_stays_blocked(self):
        self.assert_cli_blocked(142, [command("cat README.md")])

    def test_nonzero_cli_exit_stays_blocked(self):
        self.assert_cli_blocked(1, [{"type": "turn.completed"}])

    def test_no_terminal_turn_stays_blocked(self):
        self.assert_cli_blocked(0, [command("cat README.md")])

    def assert_cli_blocked(self, rc, events):
        script = (HERE / "run-conformance.sh").read_text().split("# Run scenarios.")[0]
        with tempfile.TemporaryDirectory() as d:
            stream = Path(d) / "input.jsonl"
            stream.write_text("".join(json.dumps(e, separators=(",", ":")) + "\n" for e in events))
            cli = Path(d) / "codex"
            cli.write_text(f'#!/bin/sh\ncat "{stream}"\nexit {rc}\n')
            cli.chmod(0o755)
            result = subprocess.run(["bash", "-c", script +
                '\nrun_codex "$1" read-only prompt "$1/output.jsonl" 5',
                str(HERE / "run-conformance.sh"), d], capture_output=True, text=True,
                env={**os.environ, "PATH": d + os.pathsep + os.environ["PATH"]})
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def review(self, events):
        return evidence.completed_review(events)

    def test_empty_wait_is_not_a_completed_reviewer(self):
        self.assertFalse(self.review([collab("wait")]))

    def test_spawn_without_result_is_not_a_completed_reviewer(self):
        self.assertFalse(self.review([collab("spawn_agent", ["reviewer"], "Review src/files.py")]))

    def test_completed_independent_reviewer_counts(self):
        self.assertTrue(self.review(review_events()))

    def old_condition(self, check, events):
        return evidence.passes(events, check)

    def test_explicit_answer_without_skill_read_is_not_activation(self):
        self.assertFalse(self.old_condition("C2", [message("IDENTIFY")]))

    def test_onboarding_requires_actual_contributing_read(self):
        self.assertFalse(self.old_condition("C5", [command(
            "cat .agents/skills/onboarding-to-a-project/SKILL.md"), message("CONTRIBUTING.md")]))

    def test_verification_requires_exact_incomplete_line_and_skill(self):
        self.assertFalse(self.old_condition("C7", [message("I am not INCOMPLETE")]))

    def test_bootstrap_and_tools_and_completion_have_distinct_checks(self):
        script = (HERE / "run-conformance.sh").read_text()
        for check in ["C0 bootstrap", "C8 completion", "C9 tool mapping"]:
            self.assertIn(check, script)

    def test_echoing_a_cat_command_is_not_reading(self):
        self.assertEqual(self.read_skill([command(
            "echo cat .agents/skills/systematic-debugging/SKILL.md")]), 0)

    def test_echoing_tests_is_not_verification(self):
        self.assertFalse(evidence.passes([
            command("cat .agents/skills/verification-before-completion/SKILL.md"),
            command("echo python3 -m unittest discover -s tests -t ."), message("COMPLETE")], "C8", accepted=True))

    def test_positive_completion_and_tool_mapping(self):
        stream = [command("cat .agents/skills/verification-before-completion/SKILL.md"),
                  command("cat src/slug.py"), edit(),
                  command("python3 -m unittest discover -s tests -t .", "Ran 5 tests\nOK"),
                  message("COMPLETE")]
        self.assertTrue(evidence.passes(stream, "C8", accepted=True))
        self.assertTrue(evidence.passes(stream, "C9"))
        self.assertFalse(evidence.passes(stream, "C8", accepted=False))
        self.assertFalse(evidence.passes(stream + [edit()], "C8", accepted=True))

    def test_empty_test_discovery_is_not_verification(self):
        self.assertFalse(evidence.passes([
            command("cat .agents/skills/verification-before-completion/SKILL.md"),
            command("python3 -m unittest discover -s tests -t .", "Ran 0 tests\nOK"),
            message("COMPLETE")], "C8", accepted=True))

    def test_missing_python_is_not_expected_integration_block(self):
        self.assertFalse(evidence.passes([
            command("cat .agents/skills/verification-before-completion/SKILL.md"),
            command("python3 tests/integration/run.py", "python3: command not found", 127, "failed"),
            message("INCOMPLETE")], "C7"))

    def test_summary_keeps_failed_and_blocked_separate(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "c2.jsonl").write_text(json.dumps(message("wrong")) + "\n" + json.dumps({"type": "turn.completed"}) + "\n")
            (p / "c2.jsonl.status.json").write_text(json.dumps({"status": "ready", "exit_code": 0}))
            result = subprocess.run(["python3", str(HERE / "evidence.py"), "--summary", d], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            summary = json.loads((p / "summary.json").read_text())
            self.assertEqual(summary["counts"], {"passed": 0, "failed": 1, "blocked": 9})

    def test_bootstrap_does_not_replace_latest_fix_commit(self):
        script = (HERE / "run-conformance.sh").read_text().split("# Run scenarios.")[0]
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([str(HERE.parent / "verification-eval/setup-unverifiable.sh"), d],
                           check=True, capture_output=True)
            before = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=d, text=True).strip()
            result = subprocess.run(["bash", "-c", script + '\nmkrepo "$1"\ngit -C "$1" rev-parse HEAD',
                                     str(HERE / "run-conformance.sh"), d], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), before)

    def test_fallback_output_is_not_a_successful_skill_read(self):
        for operator in ["||", ";"]:
            with self.subTest(operator=operator):
                self.assertEqual(self.read_skill([command(
                    f"cat .agents/skills/systematic-debugging/SKILL.md {operator} echo fallback", "fallback")]), 0)

    def test_inconsistent_test_status_is_not_verification(self):
        self.assertFalse(evidence.test_run([command(
            "python3 -m unittest discover -s tests -t .", "Ran 5 tests\nOK", status="failed")]))

    def test_shell_edits_after_gate_invalidate_completion(self):
        for shell_edit in ["python3 -c 'from pathlib import Path; Path(\"src/slug.py\").write_text(\"broken\")'",
                           "sed -i '' 's/good/bad/' src/slug.py", "cat replacement > src/slug.py"]:
            with self.subTest(shell_edit=shell_edit):
                review = [command("cat .agents/skills/requesting-code-review/SKILL.md"),
                          *review_events(), command(shell_edit), message("COMPLETE")]
                verified = [command("cat .agents/skills/verification-before-completion/SKILL.md"),
                            command("python3 -m unittest discover -s tests -t .", "Ran 5 tests\nOK"),
                            command(shell_edit), message("COMPLETE")]
                self.assertFalse(evidence.passes(review, "C4", accepted=True))
                self.assertFalse(evidence.passes(verified, "C8", accepted=True))

    def test_readonly_followups_preserve_gate_evidence(self):
        for readonly in ["rtk git diff --check && rtk git status --short",
                         "git add -A && git commit -m 'chore: format'",
                         "cat src/slug.py", "pwd && rg -n slugify src tests"]:
            with self.subTest(readonly=readonly):
                review = [command("cat .agents/skills/requesting-code-review/SKILL.md"),
                          *review_events(), command(readonly), message("COMPLETE")]
                verified = [command("cat .agents/skills/verification-before-completion/SKILL.md"),
                            command("python3 -m unittest discover -s tests -t .", "Ran 5 tests\nOK"),
                            command(readonly), message("COMPLETE")]
                self.assertTrue(evidence.passes(review, "C4", accepted=True))
                self.assertTrue(evidence.passes(verified, "C8", accepted=True))

    def test_combined_shell_flags_support(self):
        parts = evidence.command_parts('bash -ec "cat .agents/skills/using-bearpaws/SKILL.md"')
        self.assertEqual(parts, ["cat", ".agents/skills/using-bearpaws/SKILL.md"])

    def test_markdown_formatting_in_text_checks(self):
        skills = ("`bp:onboarding-to-a-project`, `bp:brainstorming`, `bp:writing-plans`, `bp:executing-plans`, "
                  "`bp:subagent-driven-development`, `bp:test-driven-development`, `bp:systematic-debugging`, "
                  "`bp:requesting-code-review`, `bp:receiving-code-review`, `bp:verification-before-completion`, "
                  "`bp:finishing-a-development-branch`, `bp:using-git-worktrees`, `bp:dispatching-parallel-agents`, "
                  "`bp:writing-skills`, `bp:using-bearpaws`")
        self.assertTrue(evidence.passes([message(skills)], "C1"))
        c2_stream = [command("cat .agents/skills/verification-before-completion/SKILL.md"), message("**IDENTIFY**")]
        self.assertTrue(evidence.passes(c2_stream, "C2"))

    def test_c7_failed_integration_with_completed_status(self):
        c7_stream = [command("cat .agents/skills/verification-before-completion/SKILL.md"),
                     command("python3 tests/integration/run.py", "ERROR: PAYMENTS_DB_URL is not set", rc=1, status="completed"),
                     message("INCOMPLETE")]
        self.assertTrue(evidence.passes(c7_stream, "C7"))


def message(text):
    return {"type": "item.completed", "item": {"type": "agent_message", "text": text}}


def edit():
    return {"type": "item.completed", "item": {"type": "file_change", "status": "completed",
            "changes": [{"path": "/repo/src/slug.py", "kind": "update"}]}}


def collab(tool, receivers=None, prompt=None, states=None):
    return {"type": "item.completed", "item": {
        "type": "collab_tool_call", "tool": tool, "status": "completed",
        "sender_thread_id": "parent", "receiver_thread_ids": receivers or [],
        "prompt": prompt, "agents_states": states or {}}}


def review_events():
    return [collab("spawn_agent", ["reviewer"], "Review src/files.py for security bugs"),
            collab("wait", ["reviewer"], states={"reviewer": {
                "status": "completed", "message": "Review complete. No findings."}})]


if __name__ == "__main__":
    unittest.main()
