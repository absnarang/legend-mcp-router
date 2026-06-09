"""
mcp_msci_fund_daily_returns.py — NEW capability added in this commit.

Same hosting pattern: LegendLambda, .project() with a window op for the daily
return calc, decorated with #LegendMCP. Note what facets it claims vs FactSet —
no concept overlap, so no routing collision.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from registry.legend_mcp import LegendMCP, FacetMatch

# Pure (illustrative):
#
#   #LegendMCP
#   LegendMSCIMCPForFundDailyReturns(fundId: String[1], fromDate: StrictDate[1],
#                                    toDate: StrictDate[1]): TabularDataSet[1]
#   {
#     MSCIFundPrice.all()
#       ->filter(p | $p.fundId == $fundId
#                 && $p.priceDate >= $fromDate && $p.priceDate <= $toDate)
#       ->extend(window(over: $p.fundId, order: $p.priceDate asc),
#                lag($p.closePrice)->as('prevClose'))    // window op
#       ->project([
#           col(p | $p.fundId,    'fund'),
#           col(p | $p.priceDate, 'date'),
#           col(p | ($p.closePrice / $p.prevClose) - 1.0, 'dailyReturn')
#         ]);
#   }


@LegendMCP(
    name="LegendMSCIMCPForFundDailyReturns",
    vendor="MSCI",
    certification="Tier1-Gold",
    entitlement="msci_etf_prices",
    facets=FacetMatch(
        concept=("daily_return",),
        # MSCI serves daily returns for BOTH exchange-traded funds and mutual
        # funds (open- and closed-ended alike collapse into mutual_fund; the
        # structure is not a routing discriminator here).
        asset_class=("etf", "mutual_fund"),
        periodicity=("daily",),
        # A daily-return series is inherently a time-series of latest-known
        # prices, so NEITHER bitemporal axis discriminates this tool: knowledge
        # time has no as-known-on dimension, and the result is always a
        # time-series (never a single as-reported period). Both -> wildcard, so
        # the route holds even when Stage 1 omits event_time (router defaults it
        # to as_reported, which must not block an inherently time-series tool).
        knowledge_time=None,
        event_time=None,
    ),
)
def msci_fund_daily_returns(fund_id, from_date, to_date):
    return [{"fund": fund_id, "date": from_date, "dailyReturn": 0.0123}]
