"""
run_evals.py — Executes routing eval cases against the live registry.
Loads every eval module, runs each case through route_capability, asserts the
returned status/tool match. Exits non-zero on any failure (CI gate).
"""
import sys, importlib, pkgutil, glob, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from router.route_capability import route_capability


def load_all_mcps():
    # Importing the modules triggers the @LegendMCP decorators -> populates REGISTRY
    for path in glob.glob(f"{ROOT}/registry/mcp_*.py"):
        mod = os.path.splitext(os.path.basename(path))[0]
        importlib.import_module(f"registry.{mod}")


def load_all_evals():
    cases = []
    for path in glob.glob(f"{ROOT}/evals/eval_*.py"):
        mod = os.path.splitext(os.path.basename(path))[0]
        m = importlib.import_module(f"evals.{mod}")
        cases.extend(getattr(m, "EVAL_CASES", []))
    return cases


def run():
    load_all_mcps()
    cases = load_all_evals()
    passed, failed = 0, []
    for c in cases:
        res = route_capability(c["facets"], c["entitlements"])
        exp = c["expect"]
        ok = res.status == exp["status"]
        if ok and "tool" in exp:
            ok = (res.tool is not None and res.tool.name == exp["tool"])
        if ok:
            passed += 1
        else:
            failed.append((c["id"], exp, res.to_dict()))

    print(f"\n{'='*70}\nROUTING EVALS: {passed}/{len(cases)} passed\n{'='*70}")
    for cid, exp, got in failed:
        print(f"  FAIL {cid}\n    expected={exp}\n    got     ="
              f"{{'status': '{got['status']}', 'tool': {got['tool']!r}}}\n"
              f"    reason  ={got['reason']}")
    if failed:
        sys.exit(1)
    print("All routing evals passed.\n")


if __name__ == "__main__":
    run()
