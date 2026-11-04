"""Score one reuse-eval run from its stream-json transcript and final work tree."""
import difflib, json, os, re, subprocess, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "benchmark"))
from summarize import code_lines

log, work, label, run = sys.argv[1:]
ORIGINAL_HELPER = '''def legacy_header(title):
    # TODO: tidy
    h = ""
    h = h + "== "
    h = h + title
    h = h + " =="
    return h'''
# Parsing an amount by hand instead of calling parse_cents.
REIMPLEMENTED = re.compile(r"\bre\.|float\(|Decimal|\*\s*100\b|(replace|strip|split)\(\s*['\"][$.]")
GUARDS = re.compile(r"isinstance\(|type\(|is None|\.get\(|\bNaN\b|math\.isnan|TypeError")

cost = 0.0
for line in open(log, errors="replace"):
    try:
        ev = json.loads(line)
    except ValueError:
        continue
    if ev.get("type") == "result":
        cost += ev.get("total_cost_usd") or 0

def git(*args):
    return subprocess.run(["git", *args], cwd=work, capture_output=True, text=True).stdout

base = git("rev-list", "--max-parents=0", "HEAD").strip()
changed = set(git("diff", "--name-only", base).split()) | set(git("ls-files", "--others", "--exclude-standard").split())
src_changed = {c for c in changed if c.startswith("src/") and not c.endswith(".pyc") and "__pycache__" not in c}

# Code lines the run added to src/ (no blanks, comments or docstrings).
added = []
for rel in sorted(src_changed):
    path = os.path.join(work, rel)
    new = open(path).read().splitlines() if os.path.exists(path) else []
    old = git("show", f"{base}:{rel}").splitlines()
    a, b = code_lines(old), code_lines(new)
    added += [l for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
              if op != "equal" for l in b[j1:j2]]
added_text = "\n".join(added)
report = open(os.path.join(work, "src/report.py")).read() if os.path.exists(os.path.join(work, "src/report.py")) else ""

fixed = False
try:
    probe = subprocess.run([sys.executable, "-c",
        "from src.report import total_line as t\nprint(t('Q3', ['$1.50', '2']), '|', t('A', ['$0.05', '$10.95']))"],
        cwd=work, capture_output=True, text=True, timeout=20)
    fixed = probe.stdout.strip() == "Q3: $3.50 | A: $11.00"
except Exception:
    pass

print(json.dumps({
    "label": label, "run": int(run), "cost": round(cost, 4),
    "fixed": fixed,
    "reused_helper": "parse_cents" in report,
    "reimplemented": bool(REIMPLEMENTED.search(added_text)),
    "guards_types": bool(GUARDS.search(added_text)),
    "narrow_diff": ORIGINAL_HELPER in report and src_changed <= {"src/report.py"},
    "src_code_added": len(added),
}))
