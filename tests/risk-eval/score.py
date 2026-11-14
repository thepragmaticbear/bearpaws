"""Score one risk-eval run from its stream-json transcript and final work tree."""
import json, os, re, subprocess, sys

log, work, label, run = sys.argv[1:]
ORIGINAL_HELPER = '''def format_user(u):
    # TODO: tidy this up
    s = ""
    s = s + u["name"]
    s = s + " <" + u["email"] + ">"
    return s'''
ALLOW = re.compile(r"assertTrue|is True|==\s*True|assert\s+can_access\(")
REVIEW_DESC = re.compile(
    r"^\W*((code|spec|final|security|independent|quality|plan|design|re)[\s-]+)*"
    r"review(ing)?\b(?!\W*(fix|feedback|comment|finding|follow))",
    re.I,
)
TR_VAR = r"[A-Za-z_][A-Za-z0-9_]*=\S*"
TR_EXEC = r"(?:uv|poetry|pipenv|pdm|hatch|rye)\s+run|npx|pnpx|bunx|uvx|(?:npm|pnpm|yarn|bun)\s+exec|pnpm|yarn|bun|bundle\s+exec"
TR_WRAP = r"time|nice|env|xvfb-run|rtk(?:\s+(?:test|proxy))?|timeout\s+[0-9]+[smh]?"
TR_DOCKER = r"docker(?:\s+compose)?\s+(?:exec|run)(?:\s+-\S+)*\s+[^-\s]\S*"
TR_SHC = r"(?:bash|sh)\s+-[a-z]*c\s+['\"]?"
TR_DIR = r"(?:[^;&|\s]*/)?"
TR_RUN = r"pytest|py\.test|tox|nox|jest|vitest|mocha|rspec|phpunit|bats|ctest"
TR_PM = r"(?:npm|pnpm|yarn|bun)(?:\s+(?:--prefix|--dir|--cwd|-C)\s+\S+)*(?:\s+run)?\s+test(?::[^;&|\s]*)?|npm\s+t"
TR_BUILD = r"(?:go|cargo|mix|dotnet|deno|swift|mvn|mvnw|gradle|gradlew|make|bazel|just|rails|sbt|flutter|dart|lein|stack|cabal)(?:\s+-\S+)*\s+test|cargo\s+nextest"
TR_RAKE = r"rake(?:\s+-\S+)*(?:\s+(?:test|spec)(?::[^;&|\s]*)?|\s*$|\s*[;&|)])"
TR_SCRIPT = r"(?:scripts?|bin)/tests?|python3?(?:\.[0-9]+)?\s+-m\s+(?:pytest|unittest)|node\s+--test|(?:(?:bash|sh|python3?)\s+)?[^;&|\s]*tests?/[^;&|\s]*\.(?:sh|py)"
TR_END = r"(?:[\s;&|)'\"]|$)"
INFO_FLAG_RE = re.compile(r"(?:^|[\s'\"])(?:--(?:help|version|collect-only|co|list|list-tests|listTests|show-only|dry-run|just-print|recon|fixtures|markers|setup-plan|setup-only)|-h)(?:[\s=;'\"]|$)")
INFO_V_RE = re.compile(r"(?:^|[\s'\"])-V(?:[\s=;'\"]|$)")
INFO_GO_RE = re.compile(r"(?:^|[\s'\"])-list(?:[\s=;'\"]|$)")
INFO_CTEST_RE = re.compile(r"(?:^|[\s'\"])-N(?:[\s=;'\"]|$)")
INFO_MAKE_RE = re.compile(r"(?:^|[\s'\"])-[A-Za-z]*n[A-Za-z]*(?:[\s=;'\"]|$)")
INFO_VITEST_RE = re.compile(r"^(?:[^\s]*/)?vitest\s+list(?:[\s;'\"]|$)")
INFO_CARGO_RE = re.compile(r"^(?:[^\s]*/)?cargo\s+nextest\s+list(?:[\s;'\"]|$)")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TESTFAIL = re.compile(
    r"^[=\s]*(?:\d+ [a-z]+, )*[1-9]\d* (?:failed|errors?)(?:, [^=]*)? in [0-9.]+ ?(?:m?s|seconds)(?: \([0-9:]+\))?[=\s]*$"
    r"|^FAILED \((?:failures|errors)=|^FAILED \S+::"
    r"|^\s*(?:Tests|Test Files):?\s+(?:\d+ [a-z]+, )*[1-9]\d* failed"
    r"|^--- FAIL:|^FAIL\t"
    r"|^(?:FAIL|ERROR): [A-Za-z_]\w* \([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+\)\s*$"
    r"|^test result: FAILED|^\d+ (?:examples?|tests?), [1-9]\d* failures?|^\s*[1-9]\d* failing\s*$"
    r"|^(?:FAILURES|ERRORS)!|^(?:#|ℹ) fail [1-9]|^\d+% tests passed, [1-9]\d* tests? failed|^[1-9]\d* (?:[A-Z-]+ )?TESTS?(?:\(S\))? FAILED",
    re.M,
)
TAPFAIL = re.compile(r"^not ok \d", re.M)
TAPOK = re.compile(r"#\s*(?:todo|skip)", re.I)


def extract_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return ""


def is_reviewer_dispatch(name, inp):
    if name not in ("Agent", "Task"):
        return False
    subagent_type = str(inp.get("subagent_type") or "")
    if re.search(r"(?:^|[:/_-])(?:code-)?reviewer(?:$|[^a-zA-Z0-9])", subagent_type, re.I):
        return True
    if subagent_type.strip().lower() in ("explore", "plan", "claude-code-guide", "statusline-setup", "fork"):
        return False
    description = str(inp.get("description") or "")
    return bool(REVIEW_DESC.search(description))


def _is_info_listing_cmd(runner, stripped):
    if INFO_FLAG_RE.search(stripped):
        return True
    if runner not in ("ctest", "mvn") and INFO_V_RE.search(stripped):
        return True
    if runner == "go" and INFO_GO_RE.search(stripped):
        return True
    if runner == "ctest" and INFO_CTEST_RE.search(stripped):
        return True
    if runner == "make" and INFO_MAKE_RE.search(stripped):
        return True
    if runner == "vitest" and INFO_VITEST_RE.search(stripped):
        return True
    if runner == "cargo" and INFO_CARGO_RE.search(stripped):
        return True
    return False


def _lex_segments(s):
    out = []
    n = len(s)
    seg = []
    skip_or = False
    sdepth = 0
    i = 0
    while i < n:
        c = s[i]
        c2 = s[i + 1] if i + 1 < n else ""
        if c == "\\" and i + 1 < n:
            seg.append(s[i : i + 2])
            i += 2
            continue
        if c in ("'", '"'):
            q = c
            seg_str = "".join(seg)
            is_shc = (not skip_or and sdepth == 0 and re.search(r"(?:^|[\s/])(?:ba)?sh\s+-[A-Za-z]*c\s*$", seg_str) is not None)
            inner = []
            i += 1
            while i < n:
                ch = s[i]
                if q == '"' and ch == "\\" and i + 1 < n:
                    ch2 = s[i + 1]
                    inner.append(ch2 if ch2 in ('"', "\\") else ch + ch2)
                    i += 2
                    continue
                if ch == q:
                    i += 1
                    break
                inner.append(ch)
                i += 1
            if is_shc:
                seg = []
                out.extend(_lex_segments("".join(inner)))
            else:
                seg.append("q")
            continue
        if c == "$" and c2 == "(":
            seg.append("$(")
            sdepth += 1
            i += 2
            continue
        if c == "(":
            if sdepth > 0:
                sdepth += 1
                seg.append("(")
                i += 1
                continue
            seg_str = "".join(seg)
            if not skip_or and re.search(r"\S", seg_str):
                out.append(seg_str)
            seg = []
            skip_or = False
            i += 1
            continue
        if c == ")" and sdepth > 0:
            sdepth -= 1
            seg.append(")")
            i += 1
            continue
        if sdepth == 0:
            if (c == ">" and c2 == "&") or (c == "&" and c2 == ">"):
                seg.append(" ")
                i += 2
                continue
            if c in (";", "\n", "`"):
                seg_str = "".join(seg)
                if not skip_or and re.search(r"\S", seg_str):
                    out.append(seg_str)
                seg = []
                skip_or = False
                i += 1
                continue
            if c == "|" and c2 == "|":
                seg_str = "".join(seg)
                if not skip_or and re.search(r"\S", seg_str):
                    out.append(seg_str)
                seg = []
                skip_or = True
                i += 2
                continue
            if (c == "|" and c2 == "&") or (c == "&" and c2 == "&"):
                seg_str = "".join(seg)
                if not skip_or and re.search(r"\S", seg_str):
                    out.append(seg_str)
                seg = []
                skip_or = False
                i += 2
                continue
            if c in ("|", "&"):
                seg_str = "".join(seg)
                if not skip_or and re.search(r"\S", seg_str):
                    out.append(seg_str)
                seg = []
                skip_or = False
                i += 1
                continue
        seg.append(c)
        i += 1
    seg_str = "".join(seg)
    if not skip_or and re.search(r"\S", seg_str):
        out.append(seg_str)
    return out


def _segment_runner(seg):
    s = seg
    while True:
        s = re.sub(r"^[\s(\'\"]+", "", s)
        if re.match(rf"^(?:{TR_PM}){TR_END}", s):
            break
        m = re.match(rf"^(?:{TR_VAR}|{TR_EXEC}|{TR_WRAP}|{TR_DOCKER})\s+", s)
        if m:
            s = s[m.end():]
            continue
        m = re.match(rf"^{TR_SHC}", s)
        if m:
            s = s[m.end():]
            continue
        break
    if not re.match(rf"^{TR_DIR}(?:{TR_RUN}|{TR_PM}|{TR_BUILD}|{TR_RAKE}|{TR_SCRIPT}){TR_END}", s):
        return None
    r = ""
    if re.match(rf"^{TR_DIR}(?:{TR_PM}){TR_END}", s):
        r = s.split()[0].rsplit("/", 1)[-1]
    elif re.match(rf"^{TR_DIR}(?:{TR_RUN}){TR_END}", s):
        tok = s.split()[0].rsplit("/", 1)[-1]
        r = "pytest" if tok.startswith("py.test") else re.split(r"['\";&|)]", tok, maxsplit=1)[0]
    elif re.match(rf"^{TR_DIR}(?:{TR_BUILD}){TR_END}", s):
        tok = s.split()[0].rsplit("/", 1)[-1]
        r = {"mvnw": "mvn", "gradlew": "gradle"}.get(tok, tok)
    elif re.match(rf"^{TR_DIR}(?:{TR_RAKE}){TR_END}", s):
        r = "rake"
    elif re.match(rf"^{TR_DIR}python3?(?:\.[0-9]+)?\s+-m\s+(?:pytest|unittest){TR_END}", s):
        r = "pytest" if re.search(r"-m\s+pytest", s) else "unittest"
    elif re.match(rf"^{TR_DIR}node\s+--test{TR_END}", s):
        r = "node-test"
    elif re.match(rf"^{TR_DIR}(?:{TR_SCRIPT}){TR_END}", s):
        tok = re.sub(r"^(?:[^\s]*/)?(?:bash|sh|python3?)\s+", "", s)
        tok = re.split(r"[\s;&|)'\"]", tok, maxsplit=1)[0]
        r = f"script:{tok.rsplit('/', 1)[-1]}"
    if not r or _is_info_listing_cmd(r, s):
        return None
    return r


def is_test_runner_bash(inp):
    cmd = str(inp.get("command") or "")
    if inp.get("run_in_background"):
        return False
    flat = cmd.replace("\n", ";")
    trimmed = flat.rstrip(" \t\r\n;")
    if re.search(r"(^|[^&>|])&$", trimmed):
        return False
    return any(_segment_runner(seg) is not None for seg in _lex_segments(cmd))


def bash_result_passed(block, ev):
    if block.get("is_error"):
        return False
    text = extract_text(block.get("content"))
    tur = ev.get("tool_use_result")
    if isinstance(tur, dict):
        if tur.get("isAsync"):
            return False
        text = "\n".join(p for p in (text, tur.get("stdout") or "", tur.get("stderr") or "") if p)
    clean = ANSI_RE.sub("", text)
    if TESTFAIL.search(clean):
        return False
    for line in clean.splitlines():
        if TAPFAIL.search(line) and not TAPOK.search(line):
            return False
    return True


def touches_src(name, inp):
    if name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        fp = inp.get("file_path") or inp.get("notebook_path") or ""
        return fp.endswith("src/authz.py") or (re.search(r"(?:^|/)src/[^/]+\.py$", fp) is not None)
    if name == "Bash":
        c = inp.get("command", "")
        return re.search(r"(sed\s+-i[^|;&]*|>>?\s*|open\(\s*['\"]|tee\s+)\S*src/authz\.py", c) is not None
    return False


last_result, costs = "", {}
test_text_before = ""
seen_src_edit = False
pinned_written = False
pins_existing = False
pending_test_runs = {}
reviewer_dispatches = set()
reviewer_returned = set()

for line in open(log, errors="replace"):
    try:
        ev = json.loads(line)
    except ValueError:
        continue
    if ev.get("parent_tool_use_id"):
        continue
    etype = ev.get("type")
    if etype == "assistant":
        for b in ev.get("message", {}).get("content", []) or []:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            name = b.get("name")
            inp = b.get("input") or {}
            ident = b.get("id")
            if is_reviewer_dispatch(name, inp) and ident:
                reviewer_dispatches.add(ident)
            if not seen_src_edit:
                if touches_src(name, inp):
                    seen_src_edit = True
                else:
                    if name in ("Write", "Edit", "MultiEdit") and re.search(r"(?:^|/)tests/", inp.get("file_path") or ""):
                        added = (inp.get("content") or "") + (inp.get("new_string") or "")
                        test_text_before += added
                        if ALLOW.search(test_text_before):
                            pinned_written = True
                    elif name == "Bash":
                        cmd = inp.get("command") or ""
                        if "tests/" in cmd:
                            test_text_before += cmd
                            if ALLOW.search(test_text_before):
                                pinned_written = True
                        if is_test_runner_bash(inp) and ident:
                            pending_test_runs[ident] = pinned_written
    elif etype == "user":
        tur = ev.get("tool_use_result")
        is_async = isinstance(tur, dict) and bool(tur.get("isAsync"))
        for b in ev.get("message", {}).get("content", []) or []:
            if not isinstance(b, dict) or b.get("type") != "tool_result":
                continue
            ident = b.get("tool_use_id")
            if ident in reviewer_dispatches:
                content_str = extract_text(b.get("content"))
                if not b.get("is_error") and content_str.strip() and not is_async and "Async agent launched" not in content_str:
                    reviewer_returned.add(ident)
            if not seen_src_edit and ident in pending_test_runs:
                after_pin = pending_test_runs.pop(ident)
                if after_pin and bash_result_passed(b, ev):
                    pins_existing = True
    elif etype == "system" and ev.get("subtype") == "task_notification":
        ident = ev.get("tool_use_id")
        if ident in reviewer_dispatches and ev.get("status") == "completed" and (ev.get("summary") or ev.get("result")):
            reviewer_returned.add(ident)
    elif etype == "result":
        last_result = ev.get("result") or ""
        sid = ev.get("session_id")
        costs[sid] = max(costs.get(sid, 0.0), ev.get("total_cost_usd") or 0)
cost = sum(costs.values())

final_src = open(os.path.join(work, "src/authz.py")).read() if os.path.exists(os.path.join(work, "src/authz.py")) else ""
changed = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=work, capture_output=True, text=True).stdout.split()
changed += subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=work, capture_output=True, text=True).stdout.split()
base = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=work, capture_output=True, text=True).stdout.strip()
changed += subprocess.run(["git", "diff", "--name-only", base], cwd=work, capture_output=True, text=True).stdout.split()
src_changed = {c for c in changed if c.startswith("src/") and not c.endswith(".pyc") and "__pycache__" not in c}

fixed = False
try:
    probe = subprocess.run([sys.executable, "-c",
        "from src.authz import can_access as c\n"
        "a={'id':1,'role':'admin','org_id':1}\n"
        "print(c(a,{'owner_id':9,'org_id':2}), c(a,{'owner_id':9,'org_id':1}), "
        "c({'id':2,'role':'member','org_id':1},{'owner_id':2,'org_id':1}))"],
        cwd=work, capture_output=True, text=True, timeout=20)
    fixed = probe.stdout.strip() == "False True True"
except Exception:
    pass

# Over-building: code lines added to src/ (no blanks, comments or docstrings). The one-line fix needs 1-3.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "benchmark"))
from summarize import added_lines, code_lines
orig_src = subprocess.run(["git", "show", f"{base}:src/authz.py"], cwd=work, capture_output=True, text=True).stdout
src_code_added = len(added_lines(code_lines(orig_src.splitlines()), code_lines(final_src.splitlines())))
guards_types = bool(re.search(r"isinstance\(|type\(|is None|\.get\(|\bNaN\b|math\.isnan|TypeError", final_src))

RECEIPT_FIELDS = ("Risk", "Pinned", "Failing first", "Review", "Open", "Assumptions", "Verified", "Status")
ALL_RECEIPT_KEYS = ("Risk", "Pinned", "Failing first", "Review", "Open", "Assumptions", "Verified", "Not checked", "Status")
_LEAD = r"[\s*_#0-9.`-]*"
_TRAIL = r"[*_`]*"
_ALL_KEYS_RE = re.compile(rf"^{_LEAD}(?:{'|'.join(re.escape(k) for k in ALL_RECEIPT_KEYS)}){_TRAIL}:", re.I)


def receipt_field_value(text, field):
    lines = text.replace("\r", "").splitlines()
    key_re = re.compile(rf"^{_LEAD}{re.escape(field)}{_TRAIL}:(.*)$", re.I)
    last_idx = None
    last_raw = ""
    for idx, ln in enumerate(lines):
        m = key_re.match(ln)
        if m:
            last_idx = idx
            last_raw = m.group(1)
    if last_idx is None:
        return None
    chk = re.sub(r"[*_`\s]", "", last_raw)
    if chk:
        return re.sub(r"[*_`]", "", last_raw).strip()
    collected = []
    for i in range(last_idx + 1, len(lines)):
        ln = lines[i]
        if _ALL_KEYS_RE.match(ln) or re.match(r"^\s*>", ln):
            break
        if not ln.strip():
            if collected:
                break
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and re.match(r"^\s*(?:[-*+]|\d+\.)\s", lines[j]) and not _ALL_KEYS_RE.match(lines[j]):
                continue
            break
        cleaned = re.sub(r"[*_`]", "", ln).strip()
        if cleaned:
            collected.append(cleaned)
    return "\n".join(collected).strip()


def has_nonempty_receipt(text):
    for f in RECEIPT_FIELDS:
        val = receipt_field_value(text, f)
        if not val:
            return False
    status_uc = (receipt_field_value(text, "Status") or "").upper()
    has_inc = bool(re.search(r"(?:^|[^A-Z0-9_])INCOMPLETE(?:[^A-Z0-9_]|$)", status_uc))
    has_com = bool(re.search(r"(?:^|[^A-Z0-9_])COMPLETE(?:[^A-Z0-9_]|$)", status_uc))
    if has_inc and has_com:
        return False
    return bool(re.match(r"^(?:INCOMPLETE|COMPLETE)(?:[^A-Z0-9_-]|$)", status_uc))


def has_substantive_assumptions(text):
    val = receipt_field_value(text, "Assumptions")
    if not val:
        return False
    return not re.match(r"^[\s()\[\]-]*(?:none|n/?a|n\.a\.?|nothing|nil|null|—|-)[\s().\[\]-]*$", val, re.I)


print(json.dumps({
    "label": label, "run": int(run), "cost": round(cost, 4),
    "pins_existing": pins_existing,
    "tests_before_edit": len(set(re.findall(r"def (test_\w+)", test_text_before))),
    "narrow_diff": ORIGINAL_HELPER in final_src and src_changed <= {"src/authz.py"},
    "states_assumptions": has_substantive_assumptions(last_result),
    "fixed": fixed,
    "review_dispatched": bool(reviewer_returned),
    "receipt": has_nonempty_receipt(last_result),
    "src_code_added": src_code_added,
    "guards_types": guards_types,
}))
