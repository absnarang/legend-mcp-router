"""
legend_mcp.py — Hosting model.

Your premise: a Legend MCP is just a LegendLambda doing .project() over Legend
classes with filter/window ops, decorated with a #LegendMCP sentinel. We model
the sentinel as a decorator that, at import time, registers the lambda as a
governed Capability Product (an MCPToolProduct) into the registry.

So "hosting" == "decorating + the CI that validates it". The decorator captures
the routing facets the registry needs; the rules engine never hardcodes tool
names, it queries the registry by facet.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional

# ---- The registry (in-memory here; in prod this is the Legend registry) ----
REGISTRY: dict[str, "MCPToolProduct"] = {}


@dataclass(frozen=True)
class FacetMatch:
    """Which intent facets this tool serves. None = wildcard (don't constrain)."""
    concept: tuple[str, ...]
    asset_class: Optional[tuple[str, ...]] = None
    periodicity: Optional[tuple[str, ...]] = None
    knowledge_time: Optional[tuple[str, ...]] = None
    event_time: Optional[tuple[str, ...]] = None

    def matches(self, facets: dict) -> bool:
        def ok(field_name, allowed):
            if allowed is None:
                return True
            return facets.get(field_name) in allowed
        return (
            ok("concept", self.concept)
            and ok("asset_class", self.asset_class)
            and ok("periodicity", self.periodicity)
            and ok("knowledge_time", self.knowledge_time)
            and ok("event_time", self.event_time)
        )

    def specificity(self) -> int:
        """How many facets this match constrains. Higher = more specific =
        wins a tie. Prevents a wildcard tool from shadowing a precise one."""
        return sum(x is not None for x in
                   (self.concept, self.asset_class, self.periodicity,
                    self.knowledge_time, self.event_time))


@dataclass
class MCPToolProduct:
    name: str
    vendor: str
    facets: FacetMatch
    certification: str          # certification tier from Legend governance
    fn: Callable                # the underlying LegendLambda
    entitlement: str            # entitlement group required to call it


def LegendMCP(*, name: str, vendor: str, facets: FacetMatch,
              certification: str, entitlement: str):
    """The #LegendMCP sentinel. Decorating a LegendLambda registers it as a
    governed MCPToolProduct. In CI, a hook asserts every #LegendMCP-decorated
    lambda ships with (a) a FacetMatch and (b) an eval file (see ci_check.py)."""
    def deco(fn: Callable) -> Callable:
        REGISTRY[name] = MCPToolProduct(
            name=name, vendor=vendor, facets=facets,
            certification=certification, fn=fn, entitlement=entitlement,
        )
        fn._legend_mcp_name = name  # marker the CI hook greps for
        return fn
    return deco
