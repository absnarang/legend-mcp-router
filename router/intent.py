"""
intent.py — The structured intent that the LLM skill extracts BEFORE any tool
is chosen. Stage 1 of the two-stage router.

Design note: routing is on FACETS, not keywords. The LLM's only job is to
collapse phrasing variance ("Apple's EBITDA", "AAPL profitability", "how much
does Apple earn before interest and tax") into ONE canonical intent. The
deterministic rules engine (Stage 2) never sees the raw question.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class Concept(str, Enum):
    EBITDA = "ebitda"
    REVENUE = "revenue"
    NET_INCOME = "net_income"
    EPS = "eps"
    DEBT_TO_CAPITAL = "debt_to_capital"
    PE_RATIO = "pe_ratio"
    DAILY_RETURN = "daily_return"
    PRICE = "price"
    ESG_RATING = "esg_rating"
    # extend as capabilities are registered


class AssetClass(str, Enum):
    """Canonical asset class. Stage 1 collapses phrasing variance onto these:
      etf          <- "ETF", "exchange-traded fund(s)", "exchange traded fund"
      mutual_fund  <- "MF", "mutual fund(s)", "open-ended fund(s)",
                      "closed-ended fund(s)", "closed-end fund(s)", "CEF"

    Open- vs closed-ended is a fund *structure* sub-attribute, NOT a separate
    routing facet: MSCI daily returns cover both, so it discriminates no route
    and would be dead weight as a facet. It therefore collapses into mutual_fund.
    Add a structure facet only if a future tool must distinguish the two."""
    EQUITY = "equity"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    BOND = "bond"
    INDEX = "index"


class Periodicity(str, Enum):
    FUNDAMENTAL = "fundamental"   # quarterly/annual reported financials
    DAILY = "daily"
    INTRADAY = "intraday"


# --- Bitemporality split into TWO facets, deliberately. ---
# This is the silent-failure guard. "Point-in-time" collapses two distinct
# axes that a bulge-bracket data consumer must not conflate:
class KnowledgeTime(str, Enum):
    """As-of *knowledge* date: what was KNOWN as of a given date.
    FactSet point-in-time fundamentals reconstruct the world as it was seen
    then (pre-restatement)."""
    AS_KNOWN_ON = "as_known_on"      # bitemporal, pre-restatement
    LATEST_KNOWN = "latest_known"    # whatever we know now


class EventTime(str, Enum):
    """Effective/reporting date: which fiscal period the value pertains to."""
    AS_REPORTED = "as_reported"      # the value for a specific fiscal period
    TIME_SERIES = "time_series"      # a span of periods


@dataclass
class Intent:
    concept: Concept
    entity_raw: str                       # "Apple" — pre-resolution
    entity_id: Optional[str] = None       # "AAPL" / ISIN — post entity-resolution
    asset_class: Optional[AssetClass] = None
    periodicity: Optional[Periodicity] = None
    knowledge_time: KnowledgeTime = KnowledgeTime.LATEST_KNOWN
    event_time: EventTime = EventTime.AS_REPORTED
    as_of_date: Optional[str] = None      # ISO date when knowledge_time=AS_KNOWN_ON
    consequence: str = "Read"             # consequence ladder; routing is read-only here

    def to_facets(self) -> dict:
        d = asdict(self)
        # normalise enums to their values for matching
        return {k: (v.value if isinstance(v, Enum) else v) for k, v in d.items()}
