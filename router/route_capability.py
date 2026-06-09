"""
route_capability.py — Stage 2. The DETERMINISTIC router.

The agent never picks an MCP server. It calls this tool with the structured
intent; the tool queries the registry by facet, applies a most-specific-wins
rule, checks entitlement, and returns exactly one MCPToolProduct or a refusal.
Every decision is explainable: which facets matched which tool.
"""
from __future__ import annotations
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from registry.legend_mcp import REGISTRY, MCPToolProduct


# ---- What the LLM agent actually sees (the tool spec) ----
ROUTE_CAPABILITY_TOOL_SPEC = {
    "name": "route_capability",
    "description": (
        "Route a structured financial-data intent to the single correct hosted "
        "Legend MCP tool. Call this AFTER extracting intent facets. DO NOT "
        "select an MCP server yourself. Returns the governed tool + entitlement "
        "check, or asks for clarification if the intent is ambiguous."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "concept": {"type": "string",
                        "enum": ["ebitda", "revenue", "net_income",
                                 "eps", "debt_to_capital", "pe_ratio",
                                 "daily_return", "price", "esg_rating"]},
            "entity_id": {"type": "string",
                          "description": "Resolved identifier (ticker/ISIN)."},
            "asset_class": {"type": "string",
                            "enum": ["equity", "etf", "mutual_fund",
                                     "bond", "index"]},
            "periodicity": {"type": "string",
                            "enum": ["fundamental", "daily", "intraday"]},
            "knowledge_time": {"type": "string",
                               "enum": ["as_known_on", "latest_known"],
                               "description": "as_known_on = pre-restatement, "
                                              "bitemporal point-in-time."},
            "event_time": {"type": "string",
                           "enum": ["as_reported", "time_series"]},
            "as_of_date": {"type": "string",
                           "description": "ISO date; required iff "
                                          "knowledge_time=as_known_on."},
        },
        "required": ["concept", "entity_id", "asset_class", "periodicity"],
    },
}


class RouteResult:
    def __init__(self, status, tool=None, reason="", candidates=None):
        self.status = status          # "routed" | "ambiguous" | "no_match" | "blocked"
        self.tool = tool
        self.reason = reason
        self.candidates = candidates or []

    def to_dict(self):
        return {
            "status": self.status,
            "tool": self.tool.name if self.tool else None,
            "vendor": self.tool.vendor if self.tool else None,
            "certification": self.tool.certification if self.tool else None,
            "reason": self.reason,
            "candidates": [c.name for c in self.candidates],
        }


def route_capability(facets: dict, entitlements: set[str]) -> RouteResult:
    # Apply the Intent-level defaults for the OPTIONAL bitemporal facets. These
    # are optional in the tool spec, but the registry's FacetMatch constrains them
    # strictly (no implicit wildcard), so a caller that omits them must route the
    # same as one passing the canonical defaults — otherwise a routable question
    # silently no_match's. Mirrors intent.Intent's field defaults. (asset_class
    # and periodicity have no sane default, hence they're 'required' above.)
    facets = {"knowledge_time": "latest_known", "event_time": "as_reported",
              **{k: v for k, v in facets.items() if v is not None}}

    # Guard: as_known_on requires an as_of_date (the bitemporal silent-failure trap)
    if facets.get("knowledge_time") == "as_known_on" and not facets.get("as_of_date"):
        return RouteResult("ambiguous",
            reason="Point-in-time (as_known_on) requested without as_of_date. "
                   "Ask the user for the knowledge date before routing.")

    matches = [t for t in REGISTRY.values() if t.facets.matches(facets)]
    if not matches:
        return RouteResult("no_match",
            reason=f"No certified Legend MCP serves facets: {facets}")

    # Most-specific-wins: the tool constraining the most facets takes priority.
    matches.sort(key=lambda t: t.facets.specificity(), reverse=True)
    top = matches[0]
    tied = [t for t in matches if t.facets.specificity() == top.facets.specificity()]
    if len(tied) > 1:
        return RouteResult("ambiguous",
            reason="Multiple equally-specific tools match; registry has a "
                   "routing collision that must be resolved by facet refinement.",
            candidates=tied)

    if top.entitlement not in entitlements:
        return RouteResult("blocked", tool=top,
            reason=f"Entitlement '{top.entitlement}' required for {top.name}.")

    return RouteResult("routed", tool=top,
        reason=f"Matched on {top.facets.specificity()} facets; "
               f"certification={top.certification}.")
