"""DealerLocatorTool - Scrape OEM dealer locator pages.

Wraps the existing ScraperFactory to expose dealer scraping
to conductor-ai agents.

Usage:
    tool = DealerLocatorTool()
    result = await tool.run({
        "oem": "generac",
        "zip_code": "53202",
        "radius_miles": 50,  # optional
    })
"""

from plugins.scraper_tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult
from scrapers.scraper_factory import ScraperFactory


class DealerLocatorTool(BaseTool):
    """Scrape OEM dealer locator pages to find certified installers.

    Supports 25+ OEM brands including:
    - Generators: Generac, Kohler, Cummins, Briggs
    - Solar: Tesla, Enphase, SolarEdge, SMA, Fronius
    - HVAC: Carrier, Trane, Lennox, York, Rheem
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="dealer_locator",
            description=(
                "Scrape OEM dealer locator pages to find certified installers/dealers. "
                "Supports 25+ OEM brands for generators, solar, HVAC, and battery systems. "
                "Returns list of dealers with name, address, phone, and capabilities."
            ),
            category=ToolCategory.WEB,
            parameters={
                "type": "object",
                "properties": {
                    "oem": {
                        "type": "string",
                        "description": (
                            "OEM brand name (e.g., 'generac', 'tesla', 'enphase', 'carrier'). "
                            "Case-insensitive."
                        ),
                    },
                    "zip_code": {
                        "type": "string",
                        "description": "US ZIP code to search around",
                    },
                    "radius_miles": {
                        "type": "integer",
                        "description": "Search radius in miles (default: 50)",
                        "default": 50,
                    },
                },
                "required": ["oem", "zip_code"],
            },
            requires_approval=False,
        )

    async def run(self, arguments: dict) -> ToolResult:
        """Execute dealer locator scrape.

        Args:
            arguments: Must contain 'oem' and 'zip_code'

        Returns:
            ToolResult with list of dealer dictionaries
        """
        oem = arguments.get("oem", "")
        zip_code = arguments.get("zip_code", "")
        radius = arguments.get("radius_miles", 50)

        try:
            # Create scraper for the OEM
            scraper = ScraperFactory.create(oem)

            # Execute scrape
            dealers = scraper.scrape_zip_code(zip_code)

            return ToolResult(
                tool_name="dealer_locator",
                success=True,
                result=dealers,
                execution_time_ms=0,  # Will be filled by execute()
            )

        except ValueError as e:
            # OEM not found
            available = ScraperFactory.list_available_oems()
            return ToolResult(
                tool_name="dealer_locator",
                success=False,
                result=None,
                execution_time_ms=0,
                error=f"OEM '{oem}' not found. Available: {', '.join(available)}",
            )

        except Exception as e:
            return ToolResult(
                tool_name="dealer_locator",
                success=False,
                result=None,
                execution_time_ms=0,
                error=f"Scrape failed: {str(e)}",
            )
