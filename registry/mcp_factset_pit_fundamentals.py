"""
mcp_factset_pit_fundamentals.py — The ONLY LegendMCP that exists at first.

Models your premise: a LegendLambda doing .project() over Legend classes with
filter/window ops, decorated with #LegendMCP. The Pure-ish body is illustrative
pseudocode in a docstring; the Python fn is the executable stand-in.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from registry.legend_mcp import LegendMCP, FacetMatch

# Pure (illustrative):
#
#   #LegendMCP
#   LegendFactsetMCPForPointInTimeFundamentals(
#       entityId: String[1], asOfDate: StrictDate[1], concept: String[1]): TabularDataSet[1]
#   {
#     FactsetFundamental.all()
#       ->filter(f | $f.entityId == $entityId
#                 && $f.knowledgeDate <= $asOfDate)   // bitemporal: as-known-on
#       ->groupBy([$f.fiscalPeriod],
#                 window(over: $f.fiscalPeriod, order: $f.knowledgeDate desc),
#                 row_number()->as('rn'))             // latest known <= asOfDate
#       ->filter(r | $r.rn == 1)
#       ->project([
#           col(f | $f.entityId,      'entity'),
#           col(f | $f.fiscalPeriod,  'period'),
#           col(f | $f.ebitda,        'ebitda'),
#           col(f | $f.knowledgeDate, 'asKnownOn')
#         ]);
#   }


@LegendMCP(
    name="LegendFactsetMCPForPointInTimeFundamentals",
    vendor="FactSet",
    certification="Tier1-Gold",
    entitlement="factset_fundamentals",
    facets=FacetMatch(
        concept=("ebitda", "revenue", "net_income",
                 "eps", "debt_to_capital", "pe_ratio"),
        asset_class=("equity",),
        periodicity=("fundamental",),
        knowledge_time=("as_known_on", "latest_known"),
        event_time=("as_reported", "time_series"),
    ),
)
def factset_pit_fundamentals(entity_id, as_of_date, concept):
    # Executable stand-in for the compiled Legend lambda result.
    return {"entity": entity_id, "period": "FY2024", concept: 123456.0,
            "asKnownOn": as_of_date}
