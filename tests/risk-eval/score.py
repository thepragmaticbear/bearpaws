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

uses, result, last_result, cost = [], "", "", 0.0
for line in open(log, errors="replace"):
    try:
        ev = json.loads(line)
    except ValueError:
        continue
    if ev.get("type") == "assistant":
        for b in ev.get("message", {}).get("content", []) or []:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                uses.append((b.get("name"), b.get("input") or {}))
    elif ev.get("type") == "result":
        # Async work can produce several results; score every report, sum cost.
        result += "\n" + (ev.get("result") or "")
        last_result = ev.get("result") or ""  # the hook reads only the final message
        cost += ev.get("total_cost_usd") or 0

def touches_src(name, inp):
    if name in ("Write", "Edit", "MultiEdit"):
        return (inp.get("file_path") or "").endswith("src/authz.py")
    if name == "Bash":
        c = inp.get("command", "")
        return re.search(r"(sed\s+-i[^|;&]*|>>?\s*|open\(\s*['\"]|tee\s+)\S*src/authz\.py", c) is not None
    return False

# Test text written before the first change to src/authz.py.
test_text_before = ""
for name, inp in uses:
    if touches_src(name, inp):
        break
    if name in ("Write", "Edit", "MultiEdit") and "/tests/" in (inp.get("file_path") or ""):
        test_text_before += (inp.get("content") or "") + (inp.get("new_string") or "")
    elif name == "Bash" and "tests/" in inp.get("command", ""):
        test_text_before += inp.get("command", "")

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
def code_lines(text):
    out, inq = [], False
    for l in text.splitlines():
        t = l.strip(); n = t.count('"""') + t.count("\'\'\'")
        if inq:
            if n % 2: inq = False
            continue
        if n % 2: inq = True; continue
        if t and not t.startswith("#"): out.append(l)
    return out
import difflib
orig_src = subprocess.run(["git", "show", f"{base}:src/authz.py"], cwd=work, capture_output=True, text=True).stdout
src_code_added = sum(j2 - j1 for op, i1, i2, j1, j2 in
                     difflib.SequenceMatcher(None, code_lines(orig_src), code_lines(final_src), autojunk=False).get_opcodes()
                     if op != "equal")
guards_types = bool(re.search(r"isinstance\(|type\(|is None|\.get\(|\bNaN\b|math\.isnan|TypeError", final_src))

RECEIPT_FIELDS = ("Risk", "Pinned", "Failing first", "Review", "Assumptions", "Verified", "Status")
receipt = all(re.search(rf"(?im)^[\s>*_#0-9.`-]*{f}[*_`]*:", last_result) for f in RECEIPT_FIELDS)

print(json.dumps({
    "label": label, "run": int(run), "cost": round(cost, 4),
    "pins_existing": bool(ALLOW.search(test_text_before)),
    "tests_before_edit": len(set(re.findall(r"def (test_\w+)", test_text_before))),
    "narrow_diff": ORIGINAL_HELPER in final_src and src_changed <= {"src/authz.py"},
    "states_assumptions": bool(re.search(r"assum", result, re.I)),
    "fixed": fixed,
    "review_dispatched": any(n == "Agent" for n, _ in uses),
    "receipt": receipt,
    "src_code_added": src_code_added,
    "guards_types": guards_types,
}))
