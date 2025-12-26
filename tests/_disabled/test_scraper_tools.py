"""Tests for scraper tools plugin - TDD RED phase.

These tests verify the conductor-ai plugin tools wrap existing scrapers correctly.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Plugin imports
from plugins.scraper_tools import (
    DealerLocatorTool,
    ContractorEnrichTool,
    LicenseValidateTool,
    register,
)
from plugins.scraper_tools.dealer_locator import DealerLocatorTool as DLT
from plugins.scraper_tools.contractor_enrich import ContractorEnrichTool as CET
from plugins.scraper_tools.license_validate import LicenseValidateTool as LVT


class TestDealerLocatorTool:
    """Tests for DealerLocatorTool."""

    def test_tool_definition(self):
        """Tool has correct definition."""
        tool = DealerLocatorTool()
        defn = tool.definition

        assert defn.name == "dealer_locator"
        assert "OEM" in defn.description or "dealer" in defn.description.lower()
        assert "oem" in defn.parameters.get("properties", {})
        assert "zip_code" in defn.parameters.get("properties", {})

    def test_tool_requires_oem_and_zip(self):
        """Tool requires oem and zip_code parameters."""
        tool = DealerLocatorTool()
        defn = tool.definition

        required = defn.parameters.get("required", [])
        assert "oem" in required
        assert "zip_code" in required

    @pytest.mark.asyncio
    async def test_run_returns_dealers(self):
        """Tool returns list of dealers on success."""
        tool = DealerLocatorTool()

        # Mock the ScraperFactory
        with patch("plugins.scraper_tools.dealer_locator.ScraperFactory") as mock_factory:
            mock_scraper = MagicMock()
            mock_scraper.scrape_zip_code.return_value = [
                {
                    "name": "ABC Solar",
                    "address": "123 Main St",
                    "city": "Austin",
                    "state": "TX",
                    "phone": "512-555-1234",
                }
            ]
            mock_factory.create.return_value = mock_scraper

            result = await tool.run({"oem": "enphase", "zip_code": "78701"})

            assert result.success is True
            assert len(result.result) == 1
            assert result.result[0]["name"] == "ABC Solar"
            mock_factory.create.assert_called_once_with("enphase")
            mock_scraper.scrape_zip_code.assert_called_once_with("78701")

    @pytest.mark.asyncio
    async def test_run_with_invalid_oem(self):
        """Tool returns error for unknown OEM."""
        tool = DealerLocatorTool()

        with patch("plugins.scraper_tools.dealer_locator.ScraperFactory") as mock_factory:
            mock_factory.create.side_effect = ValueError("No scraper for 'fake_oem'")

            result = await tool.run({"oem": "fake_oem", "zip_code": "12345"})

            assert result.success is False
            assert "fake_oem" in result.error or "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_run_lists_available_oems(self):
        """Tool provides available OEMs in error message."""
        tool = DealerLocatorTool()

        with patch("plugins.scraper_tools.dealer_locator.ScraperFactory") as mock_factory:
            mock_factory.create.side_effect = ValueError("No scraper")
            mock_factory.list_available_oems.return_value = ["generac", "tesla", "enphase"]

            result = await tool.run({"oem": "unknown", "zip_code": "12345"})

            assert result.success is False


class TestContractorEnrichTool:
    """Tests for ContractorEnrichTool."""

    def test_tool_definition(self):
        """Tool has correct definition."""
        tool = ContractorEnrichTool()
        defn = tool.definition

        assert defn.name == "contractor_enrich"
        assert "company_name" in defn.parameters.get("properties", {})

    @pytest.mark.asyncio
    async def test_run_enriches_company(self):
        """Tool enriches company data using Apollo."""
        tool = ContractorEnrichTool()

        with patch("plugins.scraper_tools.contractor_enrich.ApolloEnricher") as mock_enricher_cls:
            mock_enricher = MagicMock()
            mock_enricher.enrich_company.return_value = {
                "company_name": "ABC Solar",
                "domain": "abcsolar.com",
                "employee_count": 25,
                "revenue_range": "$5M-$10M",
                "contacts": [
                    {"name": "John Doe", "email": "john@abcsolar.com", "title": "Owner"}
                ],
            }
            mock_enricher_cls.return_value = mock_enricher

            result = await tool.run({
                "company_name": "ABC Solar",
                "domain": "abcsolar.com",
            })

            assert result.success is True
            assert result.result["employee_count"] == 25
            assert len(result.result["contacts"]) == 1

    @pytest.mark.asyncio
    async def test_run_handles_not_found(self):
        """Tool handles company not found gracefully."""
        tool = ContractorEnrichTool()

        with patch("plugins.scraper_tools.contractor_enrich.ApolloEnricher") as mock_enricher_cls:
            mock_enricher = MagicMock()
            mock_enricher.enrich_company.return_value = None
            mock_enricher_cls.return_value = mock_enricher

            result = await tool.run({
                "company_name": "Unknown Corp",
            })

            assert result.success is True  # Not finding is not an error
            assert result.result is None or result.result == {}


class TestLicenseValidateTool:
    """Tests for LicenseValidateTool."""

    def test_tool_definition(self):
        """Tool has correct definition."""
        tool = LicenseValidateTool()
        defn = tool.definition

        assert defn.name == "license_validate"
        assert "contractor_name" in defn.parameters.get("properties", {})
        assert "state" in defn.parameters.get("properties", {})

    @pytest.mark.asyncio
    async def test_run_validates_license(self):
        """Tool validates contractor license."""
        tool = LicenseValidateTool()

        # Mock the license lookup
        with patch("plugins.scraper_tools.license_validate.lookup_license") as mock_lookup:
            mock_lookup.return_value = {
                "license_number": "TECL-12345",
                "license_status": "Active",
                "expiration_date": "2026-03-15",
                "license_type": "Electrical",
                "violations": [],
            }

            result = await tool.run({
                "contractor_name": "ABC Solar",
                "state": "TX",
            })

            assert result.success is True
            assert result.result["license_status"] == "Active"
            assert result.result["license_number"] == "TECL-12345"

    @pytest.mark.asyncio
    async def test_run_reports_invalid_license(self):
        """Tool reports invalid/expired licenses."""
        tool = LicenseValidateTool()

        with patch("plugins.scraper_tools.license_validate.lookup_license") as mock_lookup:
            mock_lookup.return_value = {
                "license_number": "TECL-12345",
                "license_status": "Expired",
                "expiration_date": "2023-01-15",
                "violations": ["Late renewal"],
            }

            result = await tool.run({
                "contractor_name": "Old Corp",
                "state": "TX",
            })

            assert result.success is True  # Finding expired is still a successful lookup
            assert result.result["license_status"] == "Expired"


class TestPluginRegistration:
    """Tests for plugin registration."""

    def test_register_adds_tools(self):
        """register() adds all tools to global registry."""
        mock_registry = MagicMock()

        register(mock_registry)

        # Should register 3 tools
        assert mock_registry.register.call_count == 3

    def test_module_exports_all_tools(self):
        """Module exports all tool classes."""
        from plugins import scraper_tools

        assert hasattr(scraper_tools, "DealerLocatorTool")
        assert hasattr(scraper_tools, "ContractorEnrichTool")
        assert hasattr(scraper_tools, "LicenseValidateTool")
        assert hasattr(scraper_tools, "register")
