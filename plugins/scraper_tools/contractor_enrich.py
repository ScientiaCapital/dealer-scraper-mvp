"""ContractorEnrichTool - Enrich contractor data with company info.

Wraps Apollo/Clay/Hunter enrichers to add company and contact data
to contractor records.

Usage:
    tool = ContractorEnrichTool()
    result = await tool.run({
        "company_name": "ABC Solar",
        "domain": "abcsolar.com",  # optional
        "enricher": "apollo",  # optional, default
    })
"""

from plugins.scraper_tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult
from enrichment import ApolloEnricher, ClayEnricher, HunterEnricher


class ContractorEnrichTool(BaseTool):
    """Enrich contractor data with company and contact information.

    Uses Apollo, Clay, or Hunter APIs to add:
    - Company info (employee count, revenue, industry)
    - Contact info (emails, phone numbers, LinkedIn)
    - Decision makers (owners, managers)
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="contractor_enrich",
            description=(
                "Enrich contractor/company data with employee count, revenue, "
                "contacts, and LinkedIn profiles. Uses Apollo, Clay, or Hunter APIs."
            ),
            category=ToolCategory.DATA,
            parameters={
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "Company name to enrich",
                    },
                    "domain": {
                        "type": "string",
                        "description": "Company domain (e.g., 'example.com'). Improves match accuracy.",
                    },
                    "enricher": {
                        "type": "string",
                        "enum": ["apollo", "clay", "hunter"],
                        "description": "Which enrichment service to use (default: apollo)",
                        "default": "apollo",
                    },
                },
                "required": ["company_name"],
            },
            requires_approval=False,
        )

    async def run(self, arguments: dict) -> ToolResult:
        """Execute enrichment.

        Args:
            arguments: Must contain 'company_name', optionally 'domain' and 'enricher'

        Returns:
            ToolResult with enriched company data
        """
        company_name = arguments.get("company_name", "")
        domain = arguments.get("domain")
        enricher_type = arguments.get("enricher", "apollo")

        try:
            # Select enricher
            if enricher_type == "apollo":
                enricher = ApolloEnricher()
            elif enricher_type == "clay":
                enricher = ClayEnricher()
            elif enricher_type == "hunter":
                enricher = HunterEnricher()
            else:
                return ToolResult(
                    tool_name="contractor_enrich",
                    success=False,
                    result=None,
                    execution_time_ms=0,
                    error=f"Unknown enricher: {enricher_type}. Use: apollo, clay, hunter",
                )

            # Execute enrichment
            enriched = enricher.enrich_company(company_name, domain=domain)

            if enriched is None:
                # Not finding is not an error, just empty result
                return ToolResult(
                    tool_name="contractor_enrich",
                    success=True,
                    result={},
                    execution_time_ms=0,
                )

            return ToolResult(
                tool_name="contractor_enrich",
                success=True,
                result=enriched,
                execution_time_ms=0,
            )

        except Exception as e:
            return ToolResult(
                tool_name="contractor_enrich",
                success=False,
                result=None,
                execution_time_ms=0,
                error=f"Enrichment failed: {str(e)}",
            )
