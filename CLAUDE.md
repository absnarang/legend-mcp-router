# CLAUDE.md

Operating guide for Claude Code sessions in this repository.

## What this repo is

The **Legend MCP Router**: a rules-based router that takes a natural-language
financial-data question, has the model extract a *structured intent* (facets),
and then **deterministically** routes that intent to the single correct hosted
FINOS Legend MCP tool.

This repo is **unrelated to pylegend arrow serialization** (that work lives in
`pylegend-sandbox`). Do not pull arrow/serialization context into this session.
If a task seems to belong to pylegend, stop and flag it.

## The one architectural rule

Routing is **two-stage**, and the stages must never blur:

1. **Stage 1 — LLM extracts facets.** The model's only job is to collapse
   phrasing variance ("Apple's EBITDA", "AAPL profitability") into one canonical
   `Intent`. The model does **not** pick an MCP tool.
2. **Stage 2 — `route_capability()` picks the tool, deterministically.** A rules
   engine matches facets against the registry, applies most-specific-wins,
   checks entitlement, and returns exactly one tool or a typed refusal
   (`ambiguous` / `no_match` / `blocked`).

When asked to "make the router smarter," the answer is almost always *add or
refine facets*, never *let the model choose the tool*. The determinism is the
product — it's what makes routing auditable for a bank.

## Repository layout

- `router/intent.py` — the facet schema (`Intent`, enums). Source of truth for
  what a question decomposes into.
- `router/route_capability.py` — the `route_capability` tool spec (what the agent
  sees) and the deterministic routing function (Stage 2).
- `registry/legend_mcp.py` — the `#LegendMCP` sentinel decorator, `FacetMatch`,
  and the in-memory `REGISTRY`. Hosting a Legend MCP == decorating a LegendLambda.
- `registry/mcp_*.py` — one file per hosted Legend MCP tool.
- `evals/eval_*.py` — one eval file per MCP tool (routing test cases).
- `evals/run_evals.py` — runs all eval cases against the live registry.
- `evals/ci_check.py` — enforces colocation: every `#LegendMCP` tool must have
  a co-committed eval that asserts a successful route to it.

## Non-negotiable workflow (the colocation discipline)

This mirrors how Anthropic's internal analytics team keeps a semantic layer from
rotting: **the PR that changes capability is the PR that updates its evals.**

When adding or changing an MCP tool, the SAME commit must:
1. Add/edit the `registry/mcp_<name>.py` lambda with its `FacetMatch`.
2. Add/edit `evals/eval_<name>.py` with positive + negative cases.
3. Update **any existing eval whose expected result the change invalidates**
   (e.g. a question that was `no_match` may now route to the new tool).
4. Sync the docs that mirror capability: the `README.md` eval count and worked
   example, and the `SPEC.md` §3 facet tables + §4 tool list. These restate
   facts the code owns, so they rot silently if left.
5. Leave both checks green.

Never split these across commits. A capability change with stale evals — or
stale docs — is a routing regression waiting to happen.

## Commands to run (always, before declaring done)

```bash
python3 evals/ci_check.py     # colocation: no MCP without eval coverage
python3 evals/run_evals.py    # all routing eval cases pass
```

Both must exit 0. Treat a red eval as a blocking failure, not a warning.

## Facet design notes (read before touching facets)

- **Collisions come from overlapping `concept × asset_class × periodicity`
  tuples.** Two tools that match the same intent at the same specificity produce
  an `ambiguous` result by design — resolve by refining a facet, not by
  hardcoding precedence.
- **Bitemporality is two facets, not one.** `knowledge_time` (as-known-on vs
  latest-known) and `event_time` (as-reported vs time-series) are distinct.
  Collapsing them produces silent wrong-vintage answers — the worst failure mode
  for a bank. A point-in-time (`as_known_on`) request with no `as_of_date` must
  return `ambiguous` and ask, never guess.
- **Use `None` (wildcard) deliberately**, not lazily. MSCI fund returns set
  *both* `knowledge_time=None` and `event_time=None` — a latest-known price
  series has no as-known-on axis and is always a time-series, so neither facet
  is meaningful. Document why whenever you wildcard.
- **Optional facets are default-filled; required ones are not.**
  `route_capability` fills `knowledge_time`/`event_time` with
  `latest_known`/`as_reported` when omitted (mirroring the `Intent` defaults), so
  Stage 1 may leave them unset. `concept`, `entity_id`, `asset_class`, and
  `periodicity` have **no default** — omit one and the route is `no_match`, not a
  guess; they are `required` in the agent-facing tool spec.
- **One canonical value per real-world distinction.** Synonyms collapse at
  Stage 1 ("exchange-traded fund" → `etf`); genuinely different instruments get
  different facet values (`etf` vs `mutual_fund`). A sub-attribute that no tool
  routes on (open- vs closed-ended) is *not* a facet — it absorbs into the
  nearest value (`mutual_fund`) until some tool must discriminate it.
- **`asset_class` is the instrument's type, not its underlying exposure.** A
  bond ETF (e.g. AGG) resolves to `asset_class=etf`, not `bond` — classify by
  what the identifier *is*, not what it holds. Mis-classifying by holdings sends
  an answerable returns question to `no_match`. This is Stage 1 / entity
  resolution's job, and a recurring footgun for fund identifiers.

## What NOT to do

- Do not let the model select MCP servers directly.
- Do not hardcode tool names in routing logic; route by querying the registry.
- Do not add an MCP without its eval in the same commit.
- Do not assume entitlements come from the agent — in production they come from
  caller identity. Treat the `entitlements` arg as trusted-caller-supplied only.
- Do not hardcode absolute paths. Scripts derive the repo root from `__file__`
  (`os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`); the original
  scaffold hardcoded `/home/claude/...` and broke when run off-sandbox.
- Do not pull pylegend / arrow-serialization concerns into this repo.

## Session hygiene

- Keep this work in its own folder and session, separate from pylegend-sandbox.
- `save-session-context` / `resume-session` operate per-folder; this folder's
  context is router-only.
- **Published public repo:** `origin` = https://github.com/absnarang/legend-mcp-router
  (public). `README.md` and `SPEC.md` are world-readable — never commit secrets,
  tokens, or internal hostnames. `main` tracks `origin/main`.
- `.claude/settings.local.json` (local machine-specific permissions) is
  gitignored and must stay out of the public repo; the shareable
  `.claude/settings.json` convention remains open.
