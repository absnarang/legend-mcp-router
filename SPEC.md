# SPEC.md — Legend MCP Router

Design specification. Defines the data model, the routing contract, the
invariants the system guarantees, and the path to production hardening.

## 1. Problem statement

Given a natural-language question about financial data, route it to exactly one
hosted Legend MCP tool such that:

- **Correctness:** the chosen tool can actually answer the question's intent.
- **Determinism:** identical intent always routes to the same tool.
- **Auditability:** every route is explainable as facets-matched-tool.
- **Safety:** ambiguity and missing entitlement produce explicit refusals, never
  a plausible-but-wrong answer.

Non-goals: query execution semantics, answer synthesis, multi-tool fan-out.
The router selects; it does not compute.

## 2. Two-stage architecture

### Stage 1 — Intent extraction (model, non-deterministic)
The LLM skill reads the question and emits an `Intent`. It must:
- resolve phrasing variance to canonical `concept` values;
- populate facets it can infer; leave genuinely-unknown facets unset;
- never select a tool.

Stage 1 is allowed to be probabilistic because Stage 2 is not. A mis-extracted
facet produces a wrong-but-explainable route or an explicit refusal — both
catchable by evals — rather than a silent model whim.

### Stage 2 — Routing (rules engine, deterministic)
`route_capability(facets, entitlements)`:
1. **Guard** — if `knowledge_time = as_known_on` and `as_of_date` is missing →
   `ambiguous` (ask for the knowledge date).
2. **Match** — collect every registry tool whose `FacetMatch` accepts the facets.
3. **Resolve** — sort by `specificity()` (count of constrained facets) descending;
   the most specific tool wins.
4. **Tie** — if ≥2 tools tie at top specificity → `ambiguous` with candidates
   (a registry collision to be fixed by facet refinement).
5. **Entitle** — if the winning tool's entitlement ∉ caller entitlements →
   `blocked`.
6. **Route** — else return the tool with a reason string.

## 3. Data model

### Intent (facets)
| Facet | Values | Notes |
|---|---|---|
| `concept` | ebitda, revenue, net_income, eps, debt_to_capital, pe_ratio, daily_return, price, esg_rating | **required**; the metric/measure asked for |
| `entity_raw` / `entity_id` | free text / resolved id | **required** (`entity_id`); resolution is upstream (see §7) |
| `asset_class` | equity, etf, mutual_fund, bond, index | **required** — no default; must be set or the route is `no_match`. `mutual_fund` absorbs open- and closed-ended fund phrasings (structure is not a routing facet) |
| `periodicity` | fundamental, daily, intraday | **required** — no default; must be set or the route is `no_match` |
| `knowledge_time` | as_known_on, latest_known | **bitemporal axis 1**: what was known; *defaulted* to `latest_known` if omitted |
| `event_time` | as_reported, time_series | **bitemporal axis 2**: which period; *defaulted* to `as_reported` if omitted |
| `as_of_date` | ISO date | required iff `knowledge_time=as_known_on` |
| `consequence` | Read (here) | consequence-ladder tier; routing is read-only |

**Bitemporality is two facets on purpose.** Conflating "what did we know on date
X" (knowledge time) with "which fiscal period" (event time) yields silent
wrong-vintage answers — the highest-severity failure for a regulated data
consumer. The router refuses rather than guesses when the knowledge date is
required but absent.

**Required vs. defaulted facets.** Stage 1's "leave genuinely-unknown facets
unset" applies only to facets the router defaults: `knowledge_time` and
`event_time` fall back to `latest_known` / `as_reported` inside
`route_capability` (mirroring the `Intent` dataclass defaults), so omitting them
routes identically to passing the canonical values. `concept`, `entity_id`,
`asset_class`, and `periodicity` have **no default** — every registered tool
constrains `asset_class`/`periodicity` non-wildcard, so leaving them unset yields
`no_match`, not a route. They are therefore `required` in the agent-facing tool
spec, and Stage 1 must resolve them.

### FacetMatch (per tool)
A tool declares, per facet, the tuple of values it serves, or `None` for
wildcard (facet not meaningful for this tool). `matches()` is logical AND across
facets; `specificity()` counts non-wildcard facets and breaks ties.

Wildcards must be justified, not convenient. Example: MSCI fund returns wildcard
*both* bitemporal axes (`knowledge_time=None` and `event_time=None`) — a
latest-known price series has no as-known-on axis and is always a time-series, so
neither facet discriminates the route.

## 4. Hosting model — the `#LegendMCP` sentinel

A hosted tool is a `LegendLambda` doing `.project()` over Legend classes with
filter/window operations, decorated with `@LegendMCP(...)`. The decorator:
- registers the lambda as an `MCPToolProduct` in the `REGISTRY` at import time;
- captures `name`, `vendor`, `certification`, `entitlement`, and `FacetMatch`;
- tags the function so the CI hook can assert eval coverage.

Hosting therefore equals *decorating plus passing CI*. There is no separate
deployment descriptor to drift out of sync — facets live next to the lambda.

Current tools:
- **LegendFactsetMCPForPointInTimeFundamentals** — concept ∈ {ebitda, revenue,
  net_income, eps, debt_to_capital, pe_ratio}, equity, fundamental, both
  knowledge/event-time axes. Bitemporal
  window: latest knowledge ≤ as_of_date per fiscal period.
- **LegendMSCIMCPForFundDailyReturns** — concept = daily_return, asset_class ∈
  {etf, mutual_fund} (open- and closed-ended), daily; both bitemporal axes
  (`knowledge_time`, `event_time`) wildcard — a return series has no
  as-known-on dimension and is always a time-series. Window: lag(close) per
  fund ordered by date.

## 5. Routing contract (`route_capability`)

**Input (agent-facing tool spec):** facets as a flat object; `concept`,
`entity_id`, `asset_class`, and `periodicity` are required. The two bitemporal
facets are optional and default-filled by the router (see §3); `as_of_date` is
required only when `knowledge_time=as_known_on`.

**Output:** one of —
- `routed` — `{tool, vendor, certification, reason}`
- `ambiguous` — needs clarification (missing as_of_date, or a tie); includes
  `candidates` on a tie
- `no_match` — no registered tool serves the facets
- `blocked` — matched a tool but caller lacks its entitlement

The agent must treat `ambiguous` as "ask the user", `no_match`/`blocked` as
terminal refusals. It must not retry by mutating facets to force a route.

## 6. Invariants (enforced by evals + CI)

1. **Eval coverage** — every `#LegendMCP` tool has ≥1 eval asserting a successful
   route to it (`ci_check.py`).
2. **No silent vintage** — `as_known_on` without `as_of_date` ⇒ `ambiguous`.
3. **Entitlement is mandatory** — a matched tool with missing entitlement ⇒
   `blocked`, never `routed`.
4. **No cross-tool regression** — adding a tool that newly serves an intent must
   update every prior eval that asserted `no_match` for that intent, in the same
   commit.
5. **Most-specific-wins** — a wildcard-heavy tool never shadows a precise one;
   genuine ties surface as `ambiguous`, not arbitrary picks.

## 7. Hardening roadmap (before production)

- **Entitlements from identity, not agent.** The `entitlements` arg must be
  populated from authenticated caller identity server-side. The agent must have
  no path to supply or widen it.
- **Entity resolution as its own step.** "Apple" → AAPL/ISIN/CUSIP is a separate
  MCP or skill. Cross-vendor identifier mismatch (I/B/E/S vs ISIN vs CUSIP) is a
  known hazard; add a resolution-confidence facet and refuse low-confidence
  matches rather than routing on a guess.
- **Registry backed by Legend.** Replace the in-memory dict with the Legend
  registry; `FacetMatch`, certification tier, and entitlement become governed
  registry attributes, not code literals.
- **Collision detection in CI.** Add a check that fails the build if two
  registered tools can tie at top specificity for any reachable intent.
- **Consequence ladder.** Routing here is `Read`-only. When mutate/transact
  capabilities are registered, the router must enforce consequence-tier checks
  before returning a tool.
- **Provenance on every answer.** Downstream of routing, every response carries
  source tool, vendor, certification tier, as-of date, and entitlement-checked
  flag — a runtime certification stamp.
