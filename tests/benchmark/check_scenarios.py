"""Model-free check that each risk scenario's hidden attacks discriminate and are satisfiable.

For every scenarios/<s>/hidden/: the original repo must fail acceptance; the naive overlay must
pass acceptance and the visible suite but fail an attack; the reference overlay must pass all three.
Usage: python3 tests/benchmark/check_scenarios.py [scenario ...]
"""
import pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent / "scenarios"
EVAL = '''
import importlib.util, sys, unittest
sys.path.insert(0, sys.argv[2])
spec = importlib.util.spec_from_file_location("checker", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
r = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromModule(m))
sys.exit(not r.wasSuccessful() or r.testsRun == 0)
'''
VISIBLE = '''
import os, sys, unittest
sys.path.insert(0, os.getcwd())
r = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.discover("tests", top_level_dir="."))
sys.exit(not r.wasSuccessful() or r.testsRun == 0)
'''


def passes(work, checker=None):
    args = [sys.executable, "-I", "-c", EVAL, str(checker), str(work)] if checker else [sys.executable, "-I", "-c", VISIBLE]
    return subprocess.run(args, cwd=work, capture_output=True, timeout=60).returncode == 0


def tree(scenario, overlay=None):
    work = pathlib.Path(tempfile.mkdtemp()) / "work"
    shutil.copytree(scenario / "repo", work)
    if overlay:
        shutil.copytree(scenario / "hidden" / overlay, work, dirs_exist_ok=True)
    return work


def check(scenario):
    accept, attack = scenario / "accept.py", scenario / "hidden" / "attack.py"
    errors = []
    if passes(tree(scenario), accept):
        errors.append("original passes acceptance (task is not real)")
    naive = tree(scenario, "naive")
    if not (passes(naive, accept) and passes(naive)):
        errors.append("naive fix does not pass acceptance and the visible suite")
    if passes(naive, attack):
        errors.append("naive fix passes the attacks (attacks do not discriminate)")
    ref = tree(scenario, "reference")
    if not (passes(ref, accept) and passes(ref, attack) and passes(ref)):
        errors.append("reference fix does not pass acceptance, attacks, and the visible suite")
    if not (scenario / "elevated").exists():
        errors.append("missing elevated marker")
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
