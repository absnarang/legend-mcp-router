"""
ci_check.py — The colocation enforcement hook (the Anthropic discipline:
the PR that adds an MCP is the PR that adds its eval, or review fails).

Rule: for every #LegendMCP-decorated lambda in registry/, there must exist
at least one eval case in evals/ whose expected tool == that lambda's name.
"""
import sys, glob, os, importlib, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def registered_tool_names():
    from registry.legend_mcp import REGISTRY
    for path in glob.glob(f"{ROOT}/registry/mcp_*.py"):
        mod = os.path.splitext(os.path.basename(path))[0]
        importlib.import_module(f"registry.{mod}")
    return set(REGISTRY.keys())


def tools_covered_by_evals():
    covered = set()
    for path in glob.glob(f"{ROOT}/evals/eval_*.py"):
        mod = os.path.splitext(os.path.basename(path))[0]
        m = importlib.import_module(f"evals.{mod}")
        for c in getattr(m, "EVAL_CASES", []):
            t = c.get("expect", {}).get("tool")
            if t:
                covered.add(t)
    return covered


def main():
    tools = registered_tool_names()
    covered = tools_covered_by_evals()
    uncovered = tools - covered
    print(f"Registered MCPs: {sorted(tools)}")
    print(f"MCPs with positive eval coverage: {sorted(covered)}")
    if uncovered:
        print(f"\nCI FAIL: these #LegendMCP tools have no co-committed eval "
              f"asserting a successful route to them: {sorted(uncovered)}")
        sys.exit(1)
    print("\nCI PASS: every LegendMCP has eval coverage.")


if __name__ == "__main__":
    main()
