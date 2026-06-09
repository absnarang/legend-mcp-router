"""
eval_msci_fund_daily_returns.py — committed in the SAME PR as the MSCI MCP.

Two jobs:
  1. Positive coverage for the new tool (required by ci_check).
  2. Regression: the daily-return question that was no_match under FactSet-only
     must now route to MSCI — AND the FactSet questions must still route to
     FactSet (proving no collision was introduced).
"""
MSCI = "LegendMSCIMCPForFundDailyReturns"
FACTSET = "LegendFactsetMCPForPointInTimeFundamentals"

EVAL_CASES = [
    # --- Positive: the new capability ---
    {"id": "msci_pos_daily_return",
     "question": "What were the daily returns of SPY last week?",
     "facets": {"concept": "daily_return", "entity_id": "SPY",
                "asset_class": "etf", "periodicity": "daily",
                "event_time": "time_series", "knowledge_time": "latest_known"},
     "entitlements": {"msci_etf_prices"},
     "expect": {"status": "routed", "tool": MSCI}},

    {"id": "msci_pos_phrasing_variance",
     "question": "Show me the day-over-day performance of the iShares ETF.",
     "facets": {"concept": "daily_return", "entity_id": "IVV",
                "asset_class": "etf", "periodicity": "daily",
                "event_time": "time_series", "knowledge_time": "latest_known"},
     "entitlements": {"msci_etf_prices"},
     "expect": {"status": "routed", "tool": MSCI}},

    # --- Mutual funds: MSCI covers MF returns too, both open- and closed-ended.
    # "open ended fund" / "closed ended fund" phrasings collapse to mutual_fund. ---
    {"id": "msci_pos_open_ended_mutual_fund",
     "question": "Daily returns of the Vanguard 500 open-ended mutual fund?",
     "facets": {"concept": "daily_return", "entity_id": "VFIAX",
                "asset_class": "mutual_fund", "periodicity": "daily",
                "event_time": "time_series", "knowledge_time": "latest_known"},
     "entitlements": {"msci_etf_prices"},
     "expect": {"status": "routed", "tool": MSCI}},

    {"id": "msci_pos_closed_ended_fund",
     "question": "Day-over-day returns of a closed-ended fund (CEF)?",
     "facets": {"concept": "daily_return", "entity_id": "ADX",
                "asset_class": "mutual_fund", "periodicity": "daily",
                "event_time": "time_series", "knowledge_time": "latest_known"},
     "entitlements": {"msci_etf_prices"},
     "expect": {"status": "routed", "tool": MSCI}},

    # --- Defaults: caller OMITS event_time. Router defaults it to as_reported,
    # but MSCI wildcards event_time (a return series is always a time-series),
    # so the terse "SPY daily returns" still routes. Regression for the
    # default-fill / time-series-only interaction. ---
    {"id": "msci_pos_omitted_event_time",
     "question": "What is SPY daily returns?",
     "facets": {"concept": "daily_return", "entity_id": "SPY",
                "asset_class": "etf", "periodicity": "daily"},
     "entitlements": {"msci_etf_prices"},
     "expect": {"status": "routed", "tool": MSCI}},

    {"id": "msci_blocked_no_entitlement",
     "question": "Daily returns of SPY?",
     "facets": {"concept": "daily_return", "entity_id": "SPY",
                "asset_class": "etf", "periodicity": "daily",
                "event_time": "time_series", "knowledge_time": "latest_known"},
     "entitlements": {"factset_fundamentals"},  # wrong entitlement
     "expect": {"status": "blocked"}},

    # --- Regression: FactSet must STILL route to FactSet (no collision) ---
    {"id": "reg_factset_still_routes",
     "question": "What's Apple's EBITDA?",
     "facets": {"concept": "ebitda", "entity_id": "AAPL",
                "asset_class": "equity", "periodicity": "fundamental",
                "knowledge_time": "latest_known", "event_time": "as_reported"},
     "entitlements": {"factset_fundamentals"},
     "expect": {"status": "routed", "tool": FACTSET}},
]
