"""
eval_factset_pit_fundamentals.py — MUST be committed in the same PR that adds
the FactSet MCP. CI fails if a #LegendMCP lambda has no co-committed eval file.

The rubric is not just "does it route to FactSet". It encodes the failure modes
a bulge-bracket data consumer cares about:
  1. Phrasing variance collapses to the right intent  (positive routes)
  2. The bitemporal trap is caught                     (ambiguous, not silent)
  3. Entitlement is enforced                           (blocked)
  4. Out-of-scope concepts do NOT route here           (no_match / other tool)
"""
FACTSET = "LegendFactsetMCPForPointInTimeFundamentals"

EVAL_CASES = [
    # --- 1. Positive: phrasing variance -> same intent -> FactSet ---
    {"id": "fs_pos_ebitda_plain",
     "question": "What's Apple's EBITDA?",
     "facets": {"concept": "ebitda", "entity_id": "AAPL",
                "asset_class": "equity", "periodicity": "fundamental",
                "knowledge_time": "latest_known", "event_time": "as_reported"},
     "entitlements": {"factset_fundamentals"},
     "expect": {"status": "routed", "tool": FACTSET}},

    {"id": "fs_pos_revenue_synonym",
     "question": "How much top-line did AAPL report last fiscal year?",
     "facets": {"concept": "revenue", "entity_id": "AAPL",
                "asset_class": "equity", "periodicity": "fundamental",
                "knowledge_time": "latest_known", "event_time": "as_reported"},
     "entitlements": {"factset_fundamentals"},
     "expect": {"status": "routed", "tool": FACTSET}},

    # --- 1a. Newly-registered FactSet concepts (eps, debt_to_capital, pe_ratio).
    # Each must route to FactSet; "TSLA EPS" in particular was no_match before. ---
    {"id": "fs_pos_eps",
     "question": "What is Tesla's EPS as of Dec 2021?",
     "facets": {"concept": "eps", "entity_id": "TSLA",
                "asset_class": "equity", "periodicity": "fundamental",
                "knowledge_time": "latest_known", "event_time": "as_reported"},
     "entitlements": {"factset_fundamentals"},
     "expect": {"status": "routed", "tool": FACTSET}},

    {"id": "fs_pos_debt_to_capital",
     "question": "What is Apple's debt-to-capital ratio?",
     "facets": {"concept": "debt_to_capital", "entity_id": "AAPL",
                "asset_class": "equity", "periodicity": "fundamental",
                "knowledge_time": "latest_known", "event_time": "as_reported"},
     "entitlements": {"factset_fundamentals"},
     "expect": {"status": "routed", "tool": FACTSET}},

    {"id": "fs_pos_pe_ratio",
     "question": "What is Microsoft's P/E ratio?",
     "facets": {"concept": "pe_ratio", "entity_id": "MSFT",
                "asset_class": "equity", "periodicity": "fundamental",
                "knowledge_time": "latest_known", "event_time": "as_reported"},
     "entitlements": {"factset_fundamentals"},
     "expect": {"status": "routed", "tool": FACTSET}},

    # --- 1b. Defaults: caller OMITS the optional bitemporal facets. The router
    # must fill knowledge_time=latest_known / event_time=as_reported and still
    # route, NOT no_match. (Regression for the tool-spec/router defaults gap.) ---
    {"id": "fs_pos_omitted_bitemporal_facets",
     "question": "What's Apple's EBITDA?",
     "facets": {"concept": "ebitda", "entity_id": "AAPL",
                "asset_class": "equity", "periodicity": "fundamental"},
     "entitlements": {"factset_fundamentals"},
     "expect": {"status": "routed", "tool": FACTSET}},

    # --- 2. Bitemporal trap: PIT requested with NO as_of_date -> ambiguous ---
    {"id": "fs_neg_pit_no_date",
     "question": "What did we think Apple's EBITDA was back in 2021, "
                 "before restatements?",
     "facets": {"concept": "ebitda", "entity_id": "AAPL",
                "asset_class": "equity", "periodicity": "fundamental",
                "knowledge_time": "as_known_on", "event_time": "as_reported"},
     "entitlements": {"factset_fundamentals"},
     "expect": {"status": "ambiguous"}},  # must ASK for the knowledge date

    {"id": "fs_pos_pit_with_date",
     "question": "What was Apple's EBITDA as known on 2021-06-30?",
     "facets": {"concept": "ebitda", "entity_id": "AAPL",
                "asset_class": "equity", "periodicity": "fundamental",
                "knowledge_time": "as_known_on", "event_time": "as_reported",
                "as_of_date": "2021-06-30"},
     "entitlements": {"factset_fundamentals"},
     "expect": {"status": "routed", "tool": FACTSET}},

    # --- 3. Entitlement enforcement ---
    {"id": "fs_blocked_no_entitlement",
     "question": "What's Apple's EBITDA?",
     "facets": {"concept": "ebitda", "entity_id": "AAPL",
                "asset_class": "equity", "periodicity": "fundamental",
                "knowledge_time": "latest_known", "event_time": "as_reported"},
     "entitlements": set(),  # user lacks the entitlement
     "expect": {"status": "blocked"}},

    # --- 4. Out-of-scope FOR FACTSET: a returns question must NEVER route here.
    # NOTE (updated in the MSCI PR): once MSCI is registered this is no longer
    # no_match — it must route to MSCI, NOT FactSet. The assertion that matters
    # for FactSet's contract is "tool != FactSet", which we encode as routed-to-MSCI.
    {"id": "fs_neg_returns_not_factset",
     "question": "What were the daily returns of an ETF last week?",
     "facets": {"concept": "daily_return", "entity_id": "SPY",
                "asset_class": "etf", "periodicity": "daily",
                "knowledge_time": "latest_known", "event_time": "time_series"},
     "entitlements": {"factset_fundamentals", "msci_etf_prices"},
     "expect": {"status": "routed", "tool": "LegendMSCIMCPForFundDailyReturns"}},
]
