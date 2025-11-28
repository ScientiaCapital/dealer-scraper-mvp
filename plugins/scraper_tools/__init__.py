"""Scraper tools plugin for conductor-ai.

Exposes dealer-scraper-mvp capabilities as conductor-ai tools:
- DealerLocatorTool: Scrape OEM dealer locator pages
- ContractorEnrichTool: Enrich contractor data with Apollo/Clay/Hunter
- LicenseValidateTool: Validate state contractor licenses

Usage:
    from plugins.scraper_tools import register

    # Register with conductor-ai
    register(global_registry)
"""

from plugins.scraper_tools.dealer_locator import DealerLocatorTool
from plugins.scraper_tools.contractor_enrich import ContractorEnrichTool
from plugins.scraper_tools.license_validate import LicenseValidateTool


def register(global_registry) -> None:
    """Register all scraper tools with conductor-ai registry.

    Args:
        global_registry: The conductor-ai ToolRegistry instance
    """
    global_registry.register(DealerLocatorTool())
    global_registry.register(ContractorEnrichTool())
    global_registry.register(LicenseValidateTool())


__all__ = [
    "DealerLocatorTool",
    "ContractorEnrichTool",
    "LicenseValidateTool",
    "register",
]
