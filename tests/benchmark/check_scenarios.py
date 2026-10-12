"""Model-free check that each risk scenario's hidden attacks discriminate and are satisfiable.

For every scenarios/<s>/hidden/: the original repo must pass its visible suite and fail acceptance; the naive overlay must
pass acceptance and the visible suite but fail an attack; the reference overlay must pass all three.
Checkers run through the runner's own evaluator (summarize.CHECKER_SOURCE); trees are temporary and no bytecode is written.
Usage: python3 tests/benchmark/check_scenarios.py [scenario ...]
"""
import contextlib, os, pathlib, shutil, subprocess, sys, tempfile

import summarize

ROOT = pathlib.Path(__file__).resolve().parent / "scenarios"


def passes(work, checker=None):
    """Run the runner's evaluator (summarize.CHECKER_SOURCE) with the runner's interpreter flags."""
    args = [sys.executable, "-I", "-B", "-c", summarize.CHECKER_SOURCE, str(work)] + ([str(checker)] if checker else [])
    try:  # the evaluator's own alarm fires first; this backstops a hang it cannot interrupt
        return subprocess.run(args, cwd=work, capture_output=True,
                              timeout=int(os.environ.get("BENCH_CHECKER_TIMEOUT", "120")) + 30).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def tree(stack, scenario, overlay=None):
    """A scratch copy of the repo, removed when `stack` closes."""
    work = pathlib.Path(stack.enter_context(tempfile.TemporaryDirectory())) / "work"
    shutil.copytree(scenario / "repo", work)
    if overlay:
        shutil.copytree(scenario / "hidden" / overlay, work, dirs_exist_ok=True)
    return work


def check(scenario):
    accept, attack = scenario / "accept.py", scenario / "hidden" / "attack.py"
    errors = [f"missing {p.relative_to(scenario)}" for p in
              (scenario / "repo", accept, attack, scenario / "hidden" / "naive", scenario / "hidden" / "reference")
              if not p.exists()]
    if not (scenario / "elevated").exists():
        errors.append("missing elevated marker")
    if any(e.startswith("missing ") and "elevated" not in e for e in errors):
        return errors
    with contextlib.ExitStack() as stack:
        original = tree(stack, scenario)
        if not passes(original):
            errors.append("original repo does not pass its own visible suite")
        if passes(original, accept):
            errors.append("original passes acceptance (task is not real)")
        naive = tree(stack, scenario, "naive")
        if not (passes(naive, accept) and passes(naive)):
            errors.append("naive fix does not pass acceptance and the visible suite")
        if passes(naive, attack):
            errors.append("naive fix passes the attacks (attacks do not discriminate)")
        ref = tree(stack, scenario, "reference")
        if not (passes(ref, accept) and passes(ref, attack) and passes(ref)):
            errors.append("reference fix does not pass acceptance, attacks, and the visible suite")
    return errors


def main(names):
    scenarios = [ROOT / n for n in names] if names else sorted(p.parent for p in ROOT.glob("*/hidden"))
    failed = 0
    for s in scenarios:
        errors = check(s)
        failed += bool(errors)
        print(("FAIL " if errors else "OK   ") + s.name + "".join(f"\n     - {e}" for e in errors))
    if not scenarios:
        print("no scenarios with hidden/ found")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
