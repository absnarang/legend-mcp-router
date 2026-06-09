# Legend MCP Router

Natural-language financial-data questions → a structured intent → **deterministic**
routing to the single correct hosted FINOS Legend MCP tool.

> "What's Apple's EBITDA?" → `LegendFactsetMCPForPointInTimeFundamentals`
> "Daily returns of SPY last week?" → `LegendMSCIMCPForFundDailyReturns`

## Why this exists

Letting an LLM free-hand its choice of data source is fast to build and
impossible to audit. In a regulated environment you need to explain *why* a
question went to FactSet rather than MSCI — and prove it routes the same way
every time. This router splits the problem in two so each half does what it is
good at:

- **The model** handles language: it collapses phrasing variance into one
  canonical intent. ("Apple's EBITDA", "AAPL profitability", "how much does
  Apple make before interest and tax" → the same intent.)
- **A rules engine** handles the decision: it maps that intent to a tool on
  explicit *facets*, deterministically and explainably.

The model proposes; the rules engine disposes. Every route is a rule that fired
on named facets — testable, versioned, and reviewable.

## How it works

```
question ──▶ [LLM skill: extract facets] ──▶ Intent ──▶ route_capability() ──▶ one MCP tool
                                                              │
                                                              ├─ filter registry by FacetMatch
                                                              ├─ most-specific-wins
                                                              ├─ entitlement check
                                                              └─ else: ambiguous / no_match / blocked
```

A hosted Legend MCP is just a `LegendLambda` (a `.project()` over Legend classes
with filter/window ops) decorated with the `#LegendMCP` sentinel. The decorator
registers the lambda as a governed capability product carrying its routing
facets, vendor, certification tier, and required entitlement. The router never
hardcodes tool names — it queries the registry by facet.

## Quickstart

```bash
# Colocation gate: every MCP tool has eval coverage
python3 evals/ci_check.py

# All routing eval cases pass
python3 evals/run_evals.py
```

Expected: `CI PASS` and `ROUTING EVALS: 17/17 passed`.

## Worked example: routing decisions

| Question (paraphrased) | Facets that matter | Result |
|---|---|---|
| Apple's EBITDA | concept=ebitda, equity, fundamental, latest_known | → FactSet |
| Apple EBITDA "before restatements" (no date) | knowledge_time=as_known_on, **no as_of_date** | **ambiguous** — ask for the date |
| Apple EBITDA as known on 2021-06-30 | knowledge_time=as_known_on, as_of_date set | → FactSet |
| Apple's EBITDA, caller lacks entitlement | — | **blocked** |
| Tesla's EPS / P/E ratio | concept=eps or pe_ratio, equity, fundamental | → FactSet |
| Daily returns of SPY | concept=daily_return, etf, daily | → MSCI |
| Daily returns of a mutual fund (open- or closed-ended) | concept=daily_return, mutual_fund, daily | → MSCI |
| Daily returns, caller has wrong entitlement | — | **blocked** |

The "before restatements with no date" case is the one to study: a point-in-time
request without a knowledge date is *refused with a clarifying question*, never
silently answered with the wrong data vintage.

## Adding a new MCP tool

Three edits, one commit (see `CLAUDE.md` for the full rule):

1. `registry/mcp_<name>.py` — the decorated LegendLambda + its `FacetMatch`.
2. `evals/eval_<name>.py` — positive + negative routing cases.
3. Update any existing eval the new tool invalidates (a `no_match` that now
   routes somewhere), then keep both checks green.

This repo ships two tools (FactSet fundamentals, MSCI fund returns) precisely to
show that second commit — adding MSCI flipped a FactSet eval from `no_match` to
`routed → MSCI`, and that edit lives in the MSCI commit.

## Project layout

```
router/
  intent.py              facet schema (Intent + enums)
  route_capability.py    tool spec (agent-facing) + deterministic router
registry/
  legend_mcp.py          #LegendMCP sentinel, FacetMatch, REGISTRY
  mcp_factset_pit_fundamentals.py
  mcp_msci_fund_daily_returns.py
evals/
  eval_factset_pit_fundamentals.py
  eval_msci_fund_daily_returns.py
  run_evals.py           runs all cases
  ci_check.py            colocation enforcement
```

## Status & scope

Reference implementation. Registry is in-memory; in production it is the Legend
registry. Entitlements and entity resolution (name → ticker/ISIN) are assumed
upstream — see "Hardening" in `SPEC.md`.
