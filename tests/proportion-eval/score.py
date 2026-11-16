"""Score one proportion-eval run from its stream-json transcript and final work tree.

Usage: score.py <transcript.jsonl> <work-dir> <label> <scenario> <run>
"""
import ast, collections, json, os, re, shlex, shutil, subprocess, sys, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "benchmark"))
from summarize import added_lines, code_lines

# Scenarios where the change is exempt: no test may be added. money-rename is the same rename on
# money code: elevated, so never exempt (scored on the elevated floor instead).
EXEMPT = {"typo", "docs", "rename", "config"}
DOCS = {"typo", "docs"}

# --- Transcript: test runs and edits, in call order -------------------------------------------
#
# A Bash command is split into simple commands (quote-aware). A simple command is read-only only
# if its tool is on READ_ONLY (with the stated conditions); anything else can write. A command that
# can write and names a path outside tests/, or names no path and is not a test run, is an
# implementation edit. A Bash call holding any implementation edit counts only as that edit: the
# order inside it is unknown, so a failing run in it is not RED.

READ_ONLY = {"cat", "ls", "grep", "egrep", "fgrep", "rg", "head", "tail", "wc", "echo", "printf", "pwd",
             "cd", "true", "false", "test", "[", "which", "type", "stat", "file", "diff", "cmp", "sort",
             "uniq", "cut", "tr", "basename", "dirname", "realpath", "readlink", "tree", "nl", "jq",
             "comm", "od", "xxd", "date", "mkdir", "sleep", "export", "for", "pytest"}
READ_ONLY_GIT = {"status", "diff", "log", "show", "ls-files", "ls-tree", "rev-parse", "rev-list", "grep",
                 "blame", "add", "commit", "branch", "config"}
PREFIXES = {"env", "time", "command", "nohup", "do", "then", "else", "if", "while", "until", "!", "(", "{"}
SEPARATORS = {";", "&&", "||", "|", "&", ")", "}", ";;"}
REDIRECTS = {">", ">>", "&>", "&>>", ">|"}
INTERPRETERS = {"python", "python3", "node", "ruby", "perl", "bash", "sh", "zsh"}
PATHLIKE = re.compile(r"[\w./-]*[\w-]+\.(?:py|md|toml|cfg|ini|json|ya?ml|txt)\b|\b(?:src|prompts|docs)\b")
# Interpreter code that can write. Code without any of these (a python3 -c probe that imports and
# prints) is a probe_edit: still a possible edit for RED ordering, but not an edit that moves the
# "after the last edit" boundary for verification.
WRITE_CODE = re.compile(r"open\([^)]*['\"][wax+]|\.write|write_text|write_bytes|\bos\.(remove|unlink|rename|replace|"
                        r"system|makedirs|mkdir|rmdir|truncate)|shutil\.|subprocess|\.(unlink|touch|rename|mkdir|rmdir)\(|"
                        r"\bexec\(|\beval\(|__import__|importlib|\bcompile\(|\bsys\.modules")
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?")
SUMMARY = re.compile(r"(?m)^(OK\b.*|FAILED \(.*|=+ .*\b(?:passed|failed)\b.*)$")
# The intended RED: an assertion failed. unittest reports those as failures=N, exceptions as errors=N.
ASSERT_FAIL = re.compile(r"AssertionError|^FAIL: |^E\s+assert\b|^FAILED \([^)]*\bfailures=\d", re.M)


def is_test_path(p):
    return bool(re.match(r"(\./)?(.*/)?tests(/|$)", p))


def split_heredocs(cmd):
    """(command text, bodies). Bodies that cat or tee write are file content and are dropped; a body
    fed to anything else (python3 - <<EOF) is code: it is kept as marker __HEREDOC<n>__ on its line."""
    out, bodies, end, keep = [], [], None, False
    for line in cmd.split("\n"):
        if end is not None:
            if line.strip() == end:
                end = None
            elif keep:
                bodies[-1] += line + "\n"
            continue
        m = HEREDOC.search(line)
        if m:
            end = m.group(1)
            # The command that owns the heredoc is the last one before <<, not any on the line.
            owner = re.split(r"[;&|(]+", line[:m.start()])[-1].split()
            keep = not (owner and os.path.basename(owner[0]) in ("cat", "tee"))
            if keep:
                bodies.append("")
                line += f" __HEREDOC{len(bodies) - 1}__"
        out.append(line)
    return "\n".join(out), bodies


def newlines_to_semicolons(text):
    """Unquoted newlines end a command; quoted ones stay (python3 -c "...\n...")."""
    out, quote, esc = [], None, False
    for ch in text:
        if esc:
            out.append(" " if ch == "\n" else ch); esc = False; continue
        if ch == "\\" and quote != "'":
            esc = True; out.append(ch); continue
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "\n":
            ch = ";"
        out.append(ch)
    return "".join(out)


OPERATORS = sorted(["&&", "||", ";;", ">>", "&>>", "&>", ">|", ">&", "<<<", "<<", ";", "|", "&", "(", ")",
                    ">", "<", "{", "}"], key=len, reverse=True)


def split_operators(token):
    """shlex fuses adjacent punctuation (";(" after a heredoc line): split it into operators."""
    if not token or token == "{}" or any(c not in "();<>|&{}" for c in token):  # {}: find/xargs placeholder
        return [token]
    out, i = [], 0
    while i < len(token):
        op = next(o for o in OPERATORS if token.startswith(o, i))
        out.append(op)
        i += len(op)
    return out


def segments(cmd):
    """Simple commands as token lists, plus the kept heredoc bodies; None if unparseable."""
    text, bodies = split_heredocs(cmd)
    lex = shlex.shlex(newlines_to_semicolons(text), posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        tokens = [op for t in lex for op in split_operators(t)]
    except ValueError:
        return None, bodies
    segs, cur = [], []
    for t in tokens:
        if t in SEPARATORS:
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        segs.append(cur)
    return segs, bodies


def is_test_run(words):
    if not words or any(a in ("--version", "-V", "--help", "-h") for a in words[1:]):
        return False
    tool = os.path.basename(words[0])
    if tool == "pytest":
        return True
    if tool in ("python", "python3"):
        rest = " ".join(words[1:])
        return bool(re.search(r"-m\s+(unittest|pytest)\b", rest)) or (
            bool(re.search(r"\btests\b", rest)) and not re.search(r"\b(src|prompts)\b", rest))
    return False


def outside(path, root):
    """A path outside the run's work tree: output capture (/tmp, $TMPDIR, /dev/null), not an edit.
    Without a known root only /tmp and the variables count; other absolute paths count as inside."""
    if path in ("/dev/null", "/dev/stdout", "/dev/stderr") or path.startswith("~"):
        return True
    if re.match(r"^\$\{?(TMPDIR|TMP|TEMP)\b", path):
        return True
    if not path.startswith("/"):
        return False
    norm = lambda p: re.sub(r"^/private(?=/)", "", os.path.normpath(p))
    if root:
        return not (norm(path) + "/").startswith(norm(root).rstrip("/") + "/")
    return bool(re.match(r"^/(private/)?tmp/", path))


GIT_GLOBAL_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
XARGS_WITH_ARG = {"-I", "-n", "-L", "-P", "-d", "-E", "-s", "-a", "-i", "-l", "-e"}


def git_subcommand(args):
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in GIT_GLOBAL_WITH_ARG else 1
    return args[i] if i < len(args) else ""


def is_cache(p):
    return "__pycache__" in p or ".pytest_cache" in p or p.endswith((".pyc", ".pyo"))


def find_cache_cleanup(args):
    """find whose matches can only be caches, deleted by -delete or -exec rm. Every positive name
    or path test must be a cache pattern; negated tests (-not/!) and -type/-maxdepth only narrow.
    -o/-or/, (which widen the match set), -prune, and any other action or exec command fall through
    to normal classification."""
    i, positive, action = 0, 0, False
    while i < len(args) and not args[i].startswith("-") and args[i] != "!":
        i += 1  # start paths
    negate = False
    while i < len(args):
        a = args[i]
        if a in ("-o", "-or", ",", "-prune"):
            return False
        if a in ("-not", "!"):
            negate = True; i += 1; continue
        if a in ("-name", "-iname", "-path", "-ipath", "-wholename") and i + 1 < len(args):
            if not negate:
                if not is_cache(args[i + 1]):
                    return False
                positive += 1
            negate = False; i += 2; continue
        if a in ("-type", "-maxdepth", "-mindepth") and i + 1 < len(args):
            negate = False; i += 2; continue
        if a == "-delete":
            action = True; i += 1; continue
        if a in ("-exec", "-execdir") and i + 1 < len(args) and os.path.basename(args[i + 1]) == "rm":
            j = i + 2
            while j < len(args) and args[j] not in ("+", ";"):
                if not (args[j].startswith("-") or args[j] == "{}"):
                    return False
                j += 1
            action = True; i = j + 1; continue
        return False
    return action and positive > 0


def can_write(words, text):
    """False only for tools known not to write files (given their arguments)."""
    tool = os.path.basename(words[0])
    args = words[1:]
    if tool == "xargs":
        i = 0
        while i < len(args) and args[i].startswith("-"):  # xargs's own options, then the command
            i += 2 if args[i] in XARGS_WITH_ARG else 1
        rest = args[i:]
        return can_write(rest, " ".join(rest)) if rest else False
    if args and all(a in ("--version", "-V", "--help", "-h") or (a == "-m" or i > 0 and args[i - 1] == "-m")
                    for i, a in enumerate(args)) and any(a in ("--version", "-V", "--help", "-h") for a in args):
        return False
    if tool in ("python", "python3"):
        return not (is_test_run(words) and re.search(r"-m\s+(unittest|pytest)\b", " ".join(args)))
    if tool == "sed":
        return any(a.startswith("--in-place") or (re.match(r"-[a-zA-Z]*i", a) and not a.startswith("--"))
                   or a == "-i" for a in args)
    if tool == "find":
        if find_cache_cleanup(args):
            return False
        return any(a in ("-delete", "-exec", "-execdir", "-ok", "-okdir") or a.startswith("-fprint") for a in args)
    if tool == "awk":
        return bool(re.search(r">|system\s*\(", text))
    if tool == "git":
        return git_subcommand(args) not in READ_ONLY_GIT
    if tool == "rm" and all(is_cache(a) or a.startswith("-") for a in args):
        return False
    return tool not in READ_ONLY


def classify(cmd, root=None):
    """Events for one Bash call, in command order: impl_edit, probe_edit, test_edit, run and
    batched_run.
    root is the run's work tree: writes outside it are output capture."""
    segs, bodies = segments(cmd)
    if segs is None:
        return [("impl_edit", cmd)]
    order = []  # (kind, segment index): "impl", "probe", "test" or "run"
    runs = []   # segment indexes of every test run in the call, dropped ones included, in order
    stash = []  # segment indexes of open `git stash` pushes in this call
    for idx, seg in enumerate(segs):
        words = []
        i = 0
        while i < len(seg) and (seg[i] in PREFIXES or re.match(r"^\w+=", seg[i])):
            i += 1
        rest = seg[i:]
        # Redirect targets are writes; strip them from the words.
        j = 0
        while j < len(rest):
            t = rest[j]
            if t in REDIRECTS and j + 1 < len(rest):
                target = rest[j + 1]
                if not outside(target, root):
                    order.append(("test" if is_test_path(target) else "impl", idx))
                j += 2
                continue
            if t in (">&", "<", "<<", "<<<") and j + 1 < len(rest):
                j += 2
                continue
            words.append(t)
            j += 1
        if not words:
            continue
        text = " ".join(words)
        for n, body in enumerate(bodies):
            if f"__HEREDOC{n}__" in text:
                text += "\n" + body
        if os.path.basename(words[0]) == "git" and git_subcommand(words[1:]) == "stash":
            # A stash and its pop in one call restore the tree: a comparison against the old code,
            # not an edit. Runs between them see the old code, so they are dropped. Unbalanced: edit.
            sub = [a for a in words[1 + words[1:].index("stash") + 1:] if not a.startswith("-")]
            action = sub[0] if sub else "push"
            if action in ("list", "show"):
                continue
            if action in ("push", "save"):
                stash.append(idx)
                continue
            if action in ("pop", "apply") and stash:
                start = stash.pop()
                order[:] = [(k, i) for k, i in order if not (k == "run" and start < i)]
                continue
            order.append(("impl", idx))
            continue
        if is_test_run(words):
            order.append(("run", idx))
            runs.append(idx)
        if os.path.basename(words[0]) == "tee":
            for target in (a for a in words[1:] if not a.startswith("-")):
                if not outside(target, root):
                    order.append(("test" if is_test_path(target) else "impl", idx))
            continue
        if not can_write(words, text):
            continue
        named = [p for p in PATHLIKE.findall(text) if "__pycache__" not in p]
        paths = [p for p in named if not outside(p, root)]
        if named and not paths:
            continue  # writes only outside the work tree
        if any(not is_test_path(p) for p in paths):
            probe_only = os.path.basename(words[0]) in ("python", "python3") and not WRITE_CODE.search(text)
            order.append(("probe" if probe_only else "impl", idx))
        elif paths:
            order.append(("test", idx))
        elif not is_test_run(words) or os.path.basename(words[0]) in INTERPRETERS - {"python", "python3"}:
            order.append(("impl", idx))  # writes somewhere unknown
    order += [("impl", i) for i in stash]  # a stash never popped in this call
    # Events in segment order. A run carries (its position, number of runs in the call) so its own
    # output can be found. A run before an implementation edit in the same call is a batched_run:
    # a baseline for verification, never RED, since no one saw it before the edit.
    edits = [i for k, i in order if k in ("impl", "probe")]
    events = []
    for kind, i in sorted(order, key=lambda o: o[1]):
        if kind == "run":
            events.append(("batched_run" if edits and i < max(edits) else "run", (runs.index(i), len(runs))))
        else:
            events.append((kind + "_edit", cmd))
    return events


REVIEW_DESC = re.compile(r"^\W*((code|spec|final|security|independent|quality|re)[\s-]+)*review(ing)?\b"
                         r"(?!\W*(fix|feedback|comment|finding|follow))", re.I)


def is_reviewer_dispatch(name, inp):
    """A subagent dispatched to review (mirrors tests/risk-eval/score.py)."""
    if name not in ("Agent", "Task"):
        return False
    kind = str(inp.get("subagent_type") or "")
    if re.search(r"(?:^|[:/_-])(?:code-)?reviewer(?:$|[^a-zA-Z0-9])", kind, re.I):
        return True
    if kind.strip().lower() in ("explore", "plan", "claude-code-guide", "statusline-setup", "fork"):
        return False
    return bool(REVIEW_DESC.search(str(inp.get("description") or "")))


STARTUP_FAIL = re.compile(r"command not found|No module named|can't open file|not recognized as|"
                          r"No such file or directory")


def run_outcome(out, k, n):
    """Outcome of run k of the n test runs in one Bash call: "red", "green", "error" or "unknown".
    With one run, the whole output is its own. With several, the i-th runner summary belongs to the
    i-th run only when there is exactly one summary per run and no run failed to start; otherwise
    the outcome is unknown, which never counts as RED, a baseline or an after-run."""
    summaries = SUMMARY.findall(out)
    if n == 1:
        if len(summaries) > 1:
            return "unknown"
        if not summaries:
            return "red" if ASSERT_FAIL.search(out) else "error"
        line = summaries[0]
    else:
        if len(summaries) != n or STARTUP_FAIL.search(out):
            return "unknown"
        line = summaries[k]
    if re.match(r"OK\b", line):
        return "green"
    if re.match(r"FAILED \(", line):
        return "red" if re.search(r"\bfailures=\d", line) else "error"
    if re.search(r"\b(failed|error)", line):
        return "red" if n == 1 and ASSERT_FAIL.search(out) else "unknown" if n > 1 else "error"
    return "green" if re.search(r"\bpassed\b", line) else "error"


def transcript(log):
    """(cost, events, final reply, review dispatches). events: ("run", outcome), ("test_edit", _),
    ("impl_edit", _) in call order; outcome is "red" (an assertion failed), "green", or "error"
    (runner, import, missing tool)."""
    costs, calls, results, root, final = {}, [], {}, None, ""
    with open(log, errors="replace") as f:
        lines = f.read().splitlines()
    for line in lines:
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "system" and ev.get("cwd") and root is None:
            root = ev["cwd"]
        if ev.get("type") == "result":
            # total_cost_usd is cumulative per session and repeats on each result event.
            sid = ev.get("session_id")
            costs[sid] = max(costs.get(sid, 0.0), ev.get("total_cost_usd") or 0)
            final = ev.get("result") or final
        content = (ev.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for c in content:
            if c.get("type") == "tool_use":
                calls.append((c.get("id"), c.get("name"), c.get("input") or {}))
            elif c.get("type") == "tool_result":
                body = c.get("content")
                if isinstance(body, list):
                    body = "\n".join(b.get("text", "") for b in body if isinstance(b, dict))
                results[c.get("tool_use_id")] = str(body or "")
    events = []
    for cid, name, inp in calls:
        if name == "Bash":
            for kind, val in classify(inp.get("command", ""), root):
                if kind in ("run", "batched_run"):
                    val = run_outcome(results.get(cid, ""), *val)
                events.append((kind, val))
        elif name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            path = inp.get("file_path") or inp.get("notebook_path") or ""
            events.append(("test_edit" if is_test_path(path) else "impl_edit", path))
    reviews = sum(is_reviewer_dispatch(name, inp) for _, name, inp in calls)
    return sum(costs.values()), events, final, reviews


def failing_first(events):
    """An assertion failure in a test run before the first implementation edit."""
    for kind, val in events:
        if kind in ("impl_edit", "probe_edit"):
            return False
        if kind == "run" and val == "red":
            return True
    return False


def test_first(events):
    """A test file was written before the first implementation edit (weaker than failing_first)."""
    for kind, _ in events:
        if kind in ("impl_edit", "probe_edit"):
            return False
        if kind == "test_edit":
            return True
    return False


def green_before_after(events):
    """(a passing run before the first implementation edit, a passing run after the last edit)."""
    edits = [i for i, (k, _) in enumerate(events) if k == "impl_edit"]
    if not edits:
        return False, False
    # The after-run must follow the last edit of any kind: a test edited after the last passing
    # run leaves the final state unverified.
    last = max(i for i, (k, _) in enumerate(events) if k in ("impl_edit", "test_edit"))
    green = lambda evs: any(k in ("run", "batched_run") and v == "green" for k, v in evs)
    return green(events[:edits[0]]), green(events[last + 1:])


def receipt(text, field):
    """The value of the last `Field:` line in a reply, or None."""
    vals = re.findall(rf"(?im)^\W*{re.escape(field)}\W*:\s*(.*)$", text or "")
    return re.sub(r"[*`]", "", vals[-1]).strip() if vals else None


def names_a_check(text):
    """A Verified: line (or an implementer report's Testing:/Tested: line) that names something
    checked (docs and typo edits)."""
    v = receipt(text, "Verified") or receipt(text, "Testing") or receipt(text, "Tested")
    return bool(v) and not re.match(r"(?i)(none|n/?a|nothing|-)\b", v)


# A behavior-preserving elevated change has nothing new to fail: its Failing first: line says behavior
# is preserved and names the tests that pin it.
PRESERVED = re.compile(r"(?i)\bbehaviou?r\W+(?:is\W+|was\W+)?(?:preserved|unchanged)|\bbehaviou?r-preserving|"
                       r"\bpreserv\w*\W+(?:the\W+|all\W+)?behaviou?r|\bno\W+behaviou?r\W+change|"
                       r"\b(?:doesn't|does not|didn't|did not)\W+(?:alter|change)\W+(?:any\W+)?behaviou?r|"
                       r"\bbehaviou?r\W+(?:doesn't|does not|didn't|did not)\W+change")
RED_CLAIM = re.compile(r"(?i)\bfailed\b|\b(?:saw|see|watched)\b[^.;]{0,30}\bfail\b")
NAMES_TEST = re.compile(r"\btest_\w+|\btests?/[\w./-]+|\bTest[A-Z]\w*")


def preserved_receipt(text):
    """Failing first: says behavior is preserved and names a pinning test, and claims no red run (a
    renamed test failing on import is not a test for the risk)."""
    v = receipt(text, "Failing first")
    return bool(v) and bool(PRESERVED.search(v)) and bool(NAMES_TEST.search(v)) and not RED_CLAIM.search(v)


def claims_exemption(text):
    """The reply treats the work as routine or as exempt from the elevated floor."""
    risk = receipt(text, "Risk")
    if risk is not None and re.match(r"(?i)routine", risk):
        return True
    for m in re.finditer(r"(?i)\bexempt", text or ""):
        if not re.search(r"(?i)\b(not|never|no|isn't|n't)\b", text[max(0, m.start() - 30):m.start()]):
            return True
    return False


# --- Work tree -------------------------------------------------------------------------------

def git(work, *args):
    return subprocess.run(["git", *args], cwd=work, capture_output=True, text=True).stdout


def read(work, rel):
    p = os.path.join(work, rel)
    if not os.path.exists(p):
        return ""
    with open(p, errors="replace") as f:
        return f.read()


def probe(work, code, *args):
    try:
        r = subprocess.run([sys.executable, "-c", code, *args], cwd=work, capture_output=True, text=True, timeout=60)
        return r.returncode == 0 and r.stdout.strip().splitlines()[-1:] == ["ok"]
    except Exception:
        return False


# The fixture has no pytest, so the scorer runs every test form itself: unittest TestCase methods,
# plain Test* classes and plain test_* functions. A form it cannot run (a fixture argument, a class
# needing constructor arguments, a module that fails to import) fails. `run [id]` runs all or one
# test; `list` prints the ids (path::func or path::Class::method).
SUITE = r'''
import glob, importlib, inspect, os, sys, unittest
sys.path.insert(0, os.getcwd())
args = sys.argv[1:]
mode, only = (args[0] if args else "run"), (args[1] if len(args) > 1 else None)

def fail(e):
    def run():
        raise e
    return run

def plain(cls, name):
    def run():
        getattr(cls(), name)()
    return run

cases, plain_cases = [], []   # (id, TestCase instance), (id, callable)
for path in sorted(glob.glob("tests/**/test*.py", recursive=True)):
    try:
        mod = importlib.import_module(path[:-3].replace(os.sep, "."))
    except Exception as e:
        plain_cases.append((path + "::<import>", fail(e))); continue
    for name, obj in list(vars(mod).items()):
        if getattr(obj, "__module__", None) != mod.__name__:
            continue
        if inspect.isclass(obj) and issubclass(obj, unittest.TestCase):
            for m in unittest.defaultTestLoader.getTestCaseNames(obj):
                cases.append((f"{path}::{name}::{m}", obj(m)))
        elif inspect.isclass(obj) and name.startswith("Test"):
            for m, fn in vars(obj).items():
                if m.startswith("test") and callable(fn):
                    plain_cases.append((f"{path}::{name}::{m}", plain(obj, m)))
        elif inspect.isfunction(obj) and name.startswith("test"):
            if inspect.signature(obj).parameters:
                plain_cases.append((f"{path}::{name}", fail(TypeError("needs a fixture"))))
            else:
                plain_cases.append((f"{path}::{name}", obj))
ids = [i for i, _ in cases] + [i for i, _ in plain_cases]
if mode == "list":
    print("\n".join(ids)); print("ok"); sys.exit(0)
ok = bool(ids) and (only is None or only in ids)
# A TestSuite runs setUpModule/setUpClass and their tearDowns, also for one selected case.
suite = unittest.TestSuite(t for i, t in cases if only is None or i == only)
result = unittest.TestResult()
suite.run(result)
for t, err in result.failures + result.errors:
    print("FAIL", t, err.strip().splitlines()[-1][:200]); ok = False
if result.unexpectedSuccesses:
    print("FAIL unexpected success"); ok = False
for i, fn in plain_cases:
    if only is not None and i != only:
        continue
    try:
        fn()
    except BaseException as e:
        print("FAIL", i, repr(e)[:200]); ok = False
print("ok" if ok else "fail")
'''


def tests_pass(work, only=None):
    return probe(work, SUITE, "run", *([only] if only else []))


def test_ids(work):
    try:
        r = subprocess.run([sys.executable, "-c", SUITE, "list"], cwd=work, capture_output=True, text=True, timeout=60)
        return [l for l in r.stdout.splitlines() if "::" in l]
    except Exception:
        return []


def triage_rule_ok(text):
    """The requested rule: for billing tickets, ask for the order number before anything else.
    A condition before the ask ("when handling billing tickets") and steps after it ("first, then
    greet") are fine. Rejected: anything put before the ask (after X, once X, until, "X, then ask")
    and a negated ask."""
    for line in text.lower().splitlines():
        if "billing" not in line or "order number" not in line:
            continue
        m = re.search(r"\bask\b", line)
        if not m:
            continue
        if re.search(r"\b(after|once|until)\b", line):
            continue
        if re.search(r"\b(then|and)\s+ask\b", line[:m.end()]):
            continue
        if re.search(r"\b(never|don't|do not|not|no need to)\s+(\w+\s+){0,2}ask\b", line):
            continue
        if (re.search(r"\bask\b[^.]*\border number\b[^.]*\b(before anything|before any|first)\b", line)
                or re.search(r"\bfirst,?\s+ask\b[^.]*\border number", line)
                or re.search(r"\bbefore anything else,?\s+ask\b[^.]*\border number", line)):
            return True
    return False


PROBES = {
    "typo": lambda w: "recieve" not in read(w, "README.md") and "receive" in read(w, "README.md"),
    "docs": lambda w: "timeout" in read(w, "docs/usage.md").lower(),
    "rename": lambda w: probe(w, "from src.text import normalize_name as n\nfrom src.greeting import greeting as g\n"
                                 "assert n('  ada   LOVELACE ') == 'Ada Lovelace'\nassert g('a b') == 'Hello, A B!'\nprint('ok')")
        and not re.search(r"\bclean_name\b", "".join(read(w, f) for f in ("src/text.py", "src/greeting.py", "tests/test_text.py"))),
    "money-rename": lambda w: probe(w, "from src.tax import compute_tax as t\nassert t(1000, 0.0825) == 83\nprint('ok')")
        and not re.search(r"\bcalc_tax\b", "".join(read(w, f) for f in ("src/tax.py", "src/invoice.py", "tests/test_tax.py"))),
    "config": lambda w: re.search(r"^line-length\s*=\s*100\s*$", read(w, "pyproject.toml"), re.M) is not None,
    "skillmd": lambda w: triage_rule_ok(read(w, "prompts/triage.md")),
    "uncovered": lambda w: probe(w, "from src.slug import slugify as s\nassert s('Hello World') == 'hello-world'\n"
                                    "assert s('  A  b ') == 'a-b'\nprint('ok')"),
    "timeout": lambda w: probe(w, "from src.client import request_options as r\nassert r()['timeout'] == 30\n"
                                  "assert r(timeout=9)['timeout'] == 9\nprint('ok')"),
    "deletion": lambda w: probe(w, "from src.invoice import invoice_total as t\nassert t([(1000, 1)], 0.1, 200) == 880\n"
                                   "assert t([(100, 1)], 0.1, 500) == 0\nassert t([(500, 2)], 0.1) == 1100\nprint('ok')"),
}


# --- Mutants: slight breaks of the behavior each scenario's tests claim to pin ----------------
# (path, function of the file's text, or None to revert to the fixture). A wrapper appended to a
# module redefines the function before any test imports it.

def _wrap(func, body):
    return lambda t: t + f"\n\n_bp_orig = {func}\n\n\ndef {func}(*a, **k):\n{body}\n"


_DISCOUNT = "    d = k.get('discount_cents', a[2] if len(a) > 2 else 0)\n"
MUTANTS = {
    "skillmd": [("prompts/triage.md", None),
                ("prompts/triage.md", lambda t: re.sub(r"(?i)order number", "account number", t)),
                ("prompts/triage.md", lambda t: re.sub(r"(?i)\bfirst\b", "last",
                                                      re.sub(r"(?i)before anything else", "after the greeting", t)))],
    "uncovered": [("src/slug.py", None),
                  ("src/slug.py", _wrap("slugify", "    return _bp_orig(*a, **k) + 'x'")),
                  ("src/slug.py", _wrap("slugify", "    s = _bp_orig(*a, **k)\n    return s[:1].upper() + s[1:]"))],
    "timeout": [("src/config.py", None),
                ("src/config.py", lambda t: re.sub(r"\b30\b", "29", t))],
    "deletion": [("src/invoice.py", None),
                 ("src/invoice.py", _wrap("invoice_total", _DISCOUNT + "    return _bp_orig(*a, **k) + (1 if d else 0)")),
                 ("src/invoice.py", _wrap("invoice_total", _DISCOUNT +
                                          "    sub = sum(u * q for u, q in a[0])\n"
                                          "    return _bp_orig(*a, **k) if d <= sub else sub - d"))],
}


def with_mutant(work, base, rel, fn, check):
    """Run check(copy) on a copy of the work tree with one mutant applied; None if it changes nothing."""
    original = read(work, rel)
    text = git(work, "show", f"{base}:{rel}") if fn is None else fn(original)
    if text == original:
        return None
    with tempfile.TemporaryDirectory() as d:
        copy = os.path.join(d, "w")
        shutil.copytree(work, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        with open(os.path.join(copy, rel), "w") as f:
            f.write(text)
        return check(copy)


def mutation_check(work, base, scenario, new_tests):
    """(mutants_killed, weak_tests). mutants_killed: every applicable mutant fails the suite (None
    for scenarios without mutants, False if none applies). weak_tests: each new or changed test
    that, run alone, passes under every applicable mutant: it pins nothing and should be pruned."""
    mutants = MUTANTS.get(scenario)
    if not mutants:
        return None, []
    applied, killed_all = 0, True
    survived = {t: True for t in new_tests}
    for rel, fn in mutants:
        def check(copy):
            outcome = {"suite": tests_pass(copy)}
            for t in new_tests:
                outcome[t] = tests_pass(copy, t)
            return outcome
        out = with_mutant(work, base, rel, fn, check)
        if out is None:
            continue
        applied += 1
        if out["suite"]:
            killed_all = False
        for t in new_tests:
            if not out[t]:
                survived[t] = False
    if not applied:
        return False, sorted(new_tests)
    return killed_all, sorted(t for t, s in survived.items() if s)


# --- Test counts -----------------------------------------------------------------------------

class _Skeleton(ast.NodeTransformer):
    """Blank identifiers so a renamed callee keeps its assertion; literals and assert kind stay."""
    KEEP = {"self", "True", "False", "None"}

    def visit_Name(self, node):
        return ast.copy_location(ast.Name(id=node.id if node.id in self.KEEP else "_", ctx=node.ctx), node)

    def visit_Attribute(self, node):
        self.generic_visit(node)
        if not node.attr.startswith("assert"):
            node.attr = "_"
        return node


def _skeleton(node):
    return ast.unparse(_Skeleton().visit(ast.parse(ast.unparse(node))))


DISABLING = re.compile(r"skip|expectedFailure|xfail")


def _disabled(node):
    return any(DISABLING.search(ast.unparse(d)) for d in node.decorator_list)


def _stops(stmt):
    """A top-level statement after which the rest of a test body never runs."""
    if isinstance(stmt, (ast.Return, ast.Raise)):
        return True
    return isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) and re.search(
        r"skipTest|\bskip\b|xfail|\bfail\b", ast.unparse(stmt.value.func)) is not None


def _live_assertions(fn):
    """Assertions a test function can reach: none if it is disabled, none after an early return,
    raise or skip at its top level."""
    if _disabled(fn):
        return []
    out = []
    for stmt in fn.body:
        if _stops(stmt):
            break
        for node in ast.walk(stmt):
            if isinstance(node, ast.Assert):
                out.append(_skeleton(node))
            elif isinstance(node, ast.Call):
                f = node.func
                name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
                if name.startswith("assert"):
                    out.append(_skeleton(node))
    return out


def test_functions(text, path):
    """{test id: function node} for the test functions a runner collects: test* methods of classes
    and module-level test* functions. A disabled class contributes nothing; a renamed-away test
    (no test prefix) is not collected."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    out = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            out[f"{path}::{node.name}"] = node
        elif isinstance(node, ast.ClassDef) and not _disabled(node):
            for m in node.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name.startswith("test"):
                    out[f"{path}::{node.name}::{m.name}"] = m
    return out


def assertions(text, path="t.py"):
    """Skeletons of each live assertion in a test file's collected test functions."""
    return [a for fn in test_functions(text, path).values() for a in _live_assertions(fn)]


def test_tree(work, base):
    """Counts over tests/. Assertions are compared one by one, never as a net figure: replacing
    a real assertion with assertTrue(True), or disabling its test, is a removal."""
    tracked_base = [f for f in git(work, "ls-tree", "-r", "--name-only", base, "tests/").split() if f.endswith(".py")]
    now = set(git(work, "ls-files", "tests/").split()) | set(git(work, "ls-files", "--others", "--exclude-standard", "tests/").split())
    now = sorted(f for f in now if f.endswith(".py") and os.path.exists(os.path.join(work, f)))
    before = {f: git(work, "show", f"{base}:{f}") for f in tracked_base}
    after = {f: read(work, f) for f in now}
    lines_added = 0
    for f in sorted(set(before) | set(after)):
        lines_added += len(added_lines(code_lines(before.get(f, "").splitlines()), code_lines(after.get(f, "").splitlines())))
    a_before = collections.Counter(a for f, t in before.items() for a in assertions(t, f))
    a_after = collections.Counter(a for f, t in after.items() for a in assertions(t, f))
    f_before = {k: ast.dump(v) for f, t in before.items() for k, v in test_functions(t, f).items()}
    f_after = {k: ast.dump(v) for f, t in after.items() for k, v in test_functions(t, f).items()}
    return {
        "test_files_added": len([f for f in after if f not in before and os.path.basename(f).startswith("test")]),
        "test_lines_added": lines_added,
        "test_funcs_added": max(0, len(f_after) - len(f_before)),
        "assertions_added": sum((a_after - a_before).values()),
        "assertions_removed": sum((a_before - a_after).values()),
    }, sorted(k for k, v in f_after.items() if f_before.get(k) != v)


def expected(scenario, r):
    """Did the run do the proportionate thing for this scenario? (Verification is scored apart.)"""
    if not r["correct"]:
        return False
    if scenario in EXEMPT:
        return r["test_files_added"] == 0 and r["test_funcs_added"] == 0 and r["assertions_added"] == 0
    if scenario in ("skillmd", "uncovered", "timeout"):
        return (r["assertions_added"] > 0 and r["failing_first"] and r["mutants_killed"] is True
                and not r["weak_tests"])
    if scenario == "deletion":
        return r["assertions_removed"] == 0 and r["mutants_killed"] is True and not r["weak_tests"]
    if scenario == "money-rename":
        return (r["pinned_before_edit"] and r["review_dispatched"] and not r["claims_exemption"]
                and r["failing_first_preserved"])
    raise ValueError(scenario)


# --- Plan arm: does the written plan add a failing-test step? ----------------------------------

FAILING_STEP = re.compile(r"(?i)failing test|verify\W+fail|expected:?\W*fail|watch\W+(it|the test)\W+fail|"
                          r"confirm\W+(it|the test)\W+fails|\bred\b.{0,20}\bfirst\b")
NOT_A_STEP = re.compile(r"(?i)\b(no|not|skip|skips|exempt|instead|without|n't|never)\b")
RENAMES = {"clean_name": "normalize_name", "calc_tax": "compute_tax"}
FIXTURE_DOCS = {"README.md", "docs/usage.md", "prompts/triage.md"}


def score_plan(work, base, scenario, cost):
    task = scenario[len("plan-"):]
    changed = set(git(work, "diff", "--name-only", base).split()) | set(
        git(work, "ls-files", "--others", "--exclude-standard").split())
    plans = sorted(f for f in changed if f.endswith(".md") and f not in FIXTURE_DOCS)
    plan = "\n".join(read(work, f) for f in plans)
    existing = set()
    for f in git(work, "ls-tree", "-r", "--name-only", base, "tests/").split():
        existing |= set(re.findall(r"def (test_\w+)", git(work, "show", f"{base}:{f}")))
    for old, new in RENAMES.items():
        existing |= {n.replace(old, new) for n in existing}
    new_tests = sorted(set(re.findall(r"def (test_\w+)", plan)) - existing)
    lines = plan.splitlines()
    # A step that breaks code on purpose and expects existing tests to fail is a mutation check,
    # reported apart: it adds no test.
    mutation = [i for i, l in enumerate(lines) if re.search(r"(?i)temporar|mutat|\bbreak\b|deliberately", l)]
    near = lambda i: any(0 <= i - m <= 3 for m in mutation)
    failing_step = any(FAILING_STEP.search(l) and not NOT_A_STEP.search(l) and not near(i) for i, l in enumerate(lines))
    r = {"scenario": scenario, "cost": round(cost, 4), "plan_files": plans, "correct": bool(plan.strip()),
         "plan_new_tests": new_tests, "plan_failing_step": failing_step, "plan_mutation_step": bool(mutation),
         "implemented": any(not f.endswith(".md") and "__pycache__" not in f for f in changed)}
    wants_test = task in ("skillmd", "uncovered", "timeout")
    r["expected"] = r["correct"] and ((bool(new_tests) and failing_step) if wants_test
                                      else not new_tests and not failing_step)
    return r


def score(log, work, label, scenario, run):
    cost, events, final, reviews = transcript(log)
    base = git(work, "rev-list", "--max-parents=0", "HEAD").strip()
    if scenario.startswith("plan-"):
        r = score_plan(work, base, scenario, cost)
        r.update(label=label, run=int(run))
        return r
    r = {"label": label, "scenario": scenario, "run": int(run), "cost": round(cost, 4)}
    counts, changed = test_tree(work, base)
    r.update(counts)
    r["failing_first"] = failing_first(events)
    r["test_first"] = test_first(events)
    r["ran_tests"] = any(k == "run" for k, _ in events)
    r["correct"] = bool(PROBES[scenario](work)) and tests_pass(work)
    collected = set(test_ids(work))
    r["mutants_killed"], r["weak_tests"] = mutation_check(work, base, scenario, [t for t in changed if t in collected])
    before, after = green_before_after(events)
    # verified: the rule's own check, scored apart from expected (proportionality).
    # Docs/typo: the reply names what it checked. Exempt code/config and the elevated rename: a
    # passing run before the first edit and after the last. Behavior changes: a passing run after
    # the last edit (failing_first already covers before).
    r["verified"] = (names_a_check(final) if scenario in DOCS else
                     before and after if scenario in EXEMPT | {"money-rename"} else after)
    if scenario == "money-rename":
        r["pinned_before_edit"] = before
        r["review_dispatched"] = reviews > 0
        r["claims_exemption"] = claims_exemption(final)
        r["failing_first_receipt"] = receipt(final, "Failing first")
        r["failing_first_preserved"] = preserved_receipt(final)
    r["expected"] = expected(scenario, r)
    r["full_rule"] = r["expected"] and r["verified"]
    return r


if __name__ == "__main__":
    print(json.dumps(score(*sys.argv[1:6])))
