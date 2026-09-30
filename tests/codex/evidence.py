"""Read completed Codex JSONL events; prose and partial turns are not tool evidence."""
import itertools
import json
from pathlib import Path
import shlex
import sys
import re
import importlib.util
import unittest


def events(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def completed(stream, kind):
    return [e["item"] for e in stream if e.get("type") == "item.completed"
            and (e.get("item") or {}).get("type") == kind]


def command_parts(text):
    try:
        words = shlex.split(text)
        if words and Path(words[0]).name in {"bash", "sh", "zsh"}:
            index = next(i for i, word in enumerate(words) if word.startswith("-") and "c" in word)
            text = words[index + 1]
        lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|<>()")
        lexer.whitespace_split = True
        return list(lexer)
    except (ValueError, StopIteration, IndexError):
        return []


def commands(text):
    return [list(group) for is_sep, group in itertools.groupby(
        command_parts(text), lambda w: w in {"&&", ";", "||", "|"}) if not is_sep]


def reads(stream, suffix):
    for item in completed(stream, "command_execution"):
        if item.get("exit_code") != 0 or item.get("status") != "completed":
            continue
        # An aggregate exit code cannot prove a clause before a fallback/pipeline succeeded.
        if any(word in {"||", ";", "|", "&"} for word in command_parts(item.get("command", ""))):
            continue
        for words in commands(item.get("command", "")):
            if words[0] not in {"cat", "head", "tail"} and words[:2] != ["rtk", "read"]:
                continue
            args = words[2:] if words[0] == "rtk" else words[1:]
            if any(arg.endswith(suffix) for arg in args) and item.get("aggregated_output", "").strip():
                return True
    return False


def skill_loaded(stream, name):
    return reads(stream, f"skills/{name}/SKILL.md")


def completed_review(stream):
    reviewers = set()
    for item in completed(stream, "collab_tool_call"):
        if item.get("status") != "completed":
            continue
        if item.get("tool") in {"spawn_agent", "spawn"} and "review" in (item.get("prompt") or "").lower():
            reviewers.update(agent for agent in item.get("receiver_thread_ids", [])
                             if agent != item.get("sender_thread_id"))
        if item.get("tool") in {"wait", "wait_agent"}:
            for agent, state in item.get("agents_states", {}).items():
                if agent in reviewers and state.get("status") == "completed" and state.get("message", "").strip():
                    return True
    return False


def final_text(stream):
    messages = completed(stream, "agent_message")
    return messages[-1].get("text", "").strip() if messages else ""


def test_run(stream, success=True, suffix=None):
    for item in completed(stream, "command_execution"):
        if success and item.get("status") != "completed":
            continue
        if any(word in {"||", ";", "|", "&"} for word in command_parts(item.get("command", ""))):
            continue
        for words in commands(item.get("command", "")):
            if Path(words[0]).name not in {"python", "python3"}:
                continue
            if suffix:
                is_test = (any(word.endswith(suffix) for word in words)
                           and item.get("exit_code") == 1
                           and "PAYMENTS_DB_URL" in item.get("aggregated_output", ""))
            else:
                output = item.get("aggregated_output", "")
                is_test = ("unittest" in words and "discover" in words and "tests" in words
                           and re.search(r"Ran [1-9][0-9]* tests?", output)
                           and (not success or re.search(r"(?m)^OK\s*$", output)))
            if is_test and (item.get("exit_code") == 0) == success and item.get("exit_code") is not None:
                return True
    return False


def readonly_command(text):
    """Known inspection/test commands only; unfamiliar shell work requires a fresh gate."""
    if "$" in text or "`" in text:
        return False
    words = command_parts(text)
    if not words or any(word in {"&", "(", ")"} or any(char in word for char in "<>") for word in words):
        return False
    for group in commands(text):
        if group[0] == "rtk":
            group = group[1:]
        if not group:
            return False
        name = Path(group[0]).name
        if name in {"pwd", "ls", "cat", "read", "head", "tail", "echo", "printf", "grep"}:
            continue
        if name == "rg" and not any(arg.startswith("--pre") for arg in group):
            continue
        if name == "find" and not any(arg.startswith(("-exec", "-ok", "-delete", "-fprint", "-fls")) for arg in group):
            continue
        if name == "git" and len(group) > 1 and group[1] in {"status", "diff", "log", "show", "rev-parse", "ls-files", "add", "commit"} and not any(arg.startswith("--output") for arg in group):
            continue
        if name in {"python", "python3"} and (group[1:3] == ["-m", "unittest"] or group[1:] == ["tests/integration/run.py"]):
            continue
        return False
    return True


def last_unproven_revision(stream):
    return max((n for n, event in enumerate(stream)
                if event.get("type") in {"item.started", "item.completed"}
                and ((event.get("item") or {}).get("type") == "file_change"
                     or ((event.get("item") or {}).get("type") == "command_execution"
                         and not readonly_command((event.get("item") or {}).get("command", ""))))), default=-1)


def passes(stream, check, accepted=False):
    text = final_text(stream)
    if check == "C0":
        return skill_loaded(stream, "using-bearpaws")
    if check == "C1":
        expected = {"onboarding-to-a-project", "brainstorming", "writing-plans", "executing-plans",
                    "subagent-driven-development", "test-driven-development", "systematic-debugging",
                    "requesting-code-review", "receiving-code-review", "verification-before-completion",
                    "finishing-a-development-branch", "using-git-worktrees", "dispatching-parallel-agents",
                    "writing-skills", "using-bearpaws"}
        listed = {name.strip("`'\" \t\n\r").removeprefix("bp:") for name in re.split(r"[,\s]+", text)}
        return expected <= listed
    if check == "C2":
        cleaned = re.sub(r"[*`_.]", "", text).strip()
        return skill_loaded(stream, "verification-before-completion") and cleaned == "IDENTIFY"
    if check == "C3":
        return skill_loaded(stream, "systematic-debugging")
    if check == "C4":
        # A review before a later edit does not sign off the delivered revision.
        last_edit = last_unproven_revision(stream)
        return (skill_loaded(stream, "requesting-code-review")
                and completed_review(stream[last_edit + 1:]) and accepted)
    if check == "C5":
        return skill_loaded(stream, "onboarding-to-a-project") and reads(stream, "CONTRIBUTING.md")
    if check == "C6":
        return completed_review(stream)
    if check == "C7":
        return (skill_loaded(stream, "verification-before-completion")
                and test_run(stream, suffix="tests/integration/run.py", success=False)
                and text.splitlines()[-1:] == ["INCOMPLETE"])
    if check == "C8":
        last_edit = last_unproven_revision(stream)
        return (skill_loaded(stream, "verification-before-completion") and accepted
                and test_run(stream[last_edit + 1:]) and text.splitlines()[-1:] == ["COMPLETE"])
    if check == "C9":
        return (reads(stream, "src/slug.py") and test_run(stream)
                and any(i.get("status") == "completed" and any(
                    c.get("path", "").endswith("src/slug.py") for c in i.get("changes", []))
                    for i in completed(stream, "file_change")))
    raise ValueError("unknown check: " + check)


def turn_status(stream, rc):
    if rc == 142:
        return "blocked", "time limit reached; partial work is not a completed turn"
    if rc:
        return "blocked", f"Codex CLI exited {rc}; inspect stderr"
    failed = next((e for e in stream if e.get("type") == "turn.failed"), None)
    if failed:
        return "blocked", str(failed.get("error", "Codex turn failed"))
    if not stream or stream[-1].get("type") != "turn.completed":
        return "blocked", "no terminal turn.completed event"
    return "ready", "completed turn"


def summary(directory):
    root = Path(directory)
    checks = [("C0", "bootstrap", "c3"), ("C1", "discovery", "c1"),
              ("C2", "explicit load", "c2"), ("C3", "automatic activation", "c3"),
              ("C4", "review gate", "c4"), ("C5", "onboarding", "c5"),
              ("C6", "independent subagent completion", "c4"),
              ("C7", "verification gate", "c7"), ("C8", "completion", "c8"),
              ("C9", "tool mapping", "c8")]
    results = []
    counts = dict(passed=0, failed=0, blocked=0)
    for check, surface, case in checks:
        path = root / f"{case}.jsonl"
        try:
            status = json.loads(Path(str(path) + ".status.json").read_text())
            stream = events(path)
            state, reason = turn_status(stream, status["exit_code"])
            if state == "ready":
                acceptance = root / f"{case}.accept.exit"
                accepted = acceptance.exists() and acceptance.read_text().strip() == "0"
                state = "passed" if passes(stream, check, accepted) else "failed"
                reason = "required evidence present" if state == "passed" else "required completed evidence missing; inspect transcript"
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            state, reason = "blocked", f"missing or invalid run evidence: {error}"
        counts[state] += 1
        results.append(dict(check=check, surface=surface, status=state, reason=reason,
                            transcript=str(path)))
        print(f"[{state.upper()}] {check} {surface}: {reason}")
    (root / "summary.json").write_text(json.dumps(dict(counts=counts, checks=results), indent=2) + "\n")
    print(f"Codex conformance: {counts['passed']} passed, {counts['failed']} failed, {counts['blocked']} blocked ({root})")
    return 2 if counts["blocked"] else int(bool(counts["failed"]))


if __name__ == "__main__":
    if sys.argv[1] == "--summary":
        sys.exit(summary(sys.argv[2]))
    elif sys.argv[1] == "--accept":
        sys.path.insert(0, sys.argv[3])
        spec = importlib.util.spec_from_file_location("accept", sys.argv[2])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromModule(module))
        sys.exit(not result.wasSuccessful() or result.testsRun == 0 or bool(result.skipped) or bool(result.expectedFailures))
    elif sys.argv[1] == "--status":
        path, rc = sys.argv[2], int(sys.argv[3])
        try:
            state, reason = turn_status(events(path), rc)
        except (ValueError, OSError) as error:
            state, reason = "blocked", f"unreadable JSONL: {error}"
        Path(path + ".status.json").write_text(json.dumps({"status": state, "reason": reason, "exit_code": rc}) + "\n")
        if state == "blocked":
            print("BLOCKED: " + reason)
            sys.exit(2)
    elif sys.argv[1] == "--review":
        print(int(completed_review(events(sys.argv[2]))))
    elif sys.argv[1] == "--check":
        print(int(passes(events(sys.argv[2]), sys.argv[3])))
    else:
        print(int(skill_loaded(events(sys.argv[1]), sys.argv[2])))
