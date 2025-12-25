"""
Unit tests for Sol-Ark Distributor Scraper

Tests for the SolArkScraper class which scrapes the Sol-Ark distributor network
for hybrid inverter installations at sol-ark.com.

No network calls - uses mock data only.
"""

import pytest
from scrapers.solark_scraper import SolArkScraper
from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import StandardizedDealer, DealerCapabilities, ScraperMode


class TestSolArkScraperFactoryRegistration:
    """Test that Sol-Ark scraper is properly registered with the factory."""

    def test_factory_has_solark_registered(self):
        """Test 'Sol-Ark' is registered in ScraperFactory."""
        available_oems = ScraperFactory.list_available_oems()
        assert "sol-ark" in available_oems

    def test_factory_has_solark_alias(self):
        """Test 'solark' alias is also registered."""
        available_oems = ScraperFactory.list_available_oems()
        assert "solark" in available_oems

    def test_factory_creates_solark_scraper(self):
        """Test factory creates SolArkScraper instance."""
        scraper = ScraperFactory.create("Sol-Ark", mode=ScraperMode.PLAYWRIGHT)
        assert isinstance(scraper, SolArkScraper)

    def test_factory_create_case_insensitive(self):
        """Test factory lookup is case-insensitive."""
        scraper = ScraperFactory.create("solark", mode=ScraperMode.PLAYWRIGHT)
        assert isinstance(scraper, SolArkScraper)


class TestSolArkScraperRequiredMethods:
    """Test that all required abstract methods are implemented."""

    @pytest.fixture
    def scraper(self):
        """Create a SolArkScraper instance for testing."""
        return SolArkScraper(mode=ScraperMode.PLAYWRIGHT)

    def test_has_get_extraction_script_method(self, scraper):
        """Test get_extraction_script method exists and is callable."""
        assert hasattr(scraper, "get_extraction_script")
        assert callable(scraper.get_extraction_script)

    def test_has_detect_capabilities_method(self, scraper):
        """Test detect_capabilities method exists and is callable."""
        assert hasattr(scraper, "detect_capabilities")
        assert callable(scraper.detect_capabilities)

    def test_has_parse_dealer_data_method(self, scraper):
        """Test parse_dealer_data method exists and is callable."""
        assert hasattr(scraper, "parse_dealer_data")
        assert callable(scraper.parse_dealer_data)

    def test_has_oem_name_constant(self, scraper):
        """Test OEM_NAME class constant is set."""
        assert scraper.OEM_NAME == "Sol-Ark"

    def test_has_dealer_locator_url(self, scraper):
        """Test DEALER_LOCATOR_URL class constant is set."""
        assert scraper.DEALER_LOCATOR_URL == "https://www.sol-ark.com/solar-installers/distributor-map/"

    def test_has_product_lines(self, scraper):
        """Test PRODUCT_LINES class constant is set."""
        assert len(scraper.PRODUCT_LINES) > 0
        assert "Hybrid Inverters" in scraper.PRODUCT_LINES
        assert "Battery Storage" in scraper.PRODUCT_LINES


class TestSolArkExtractionScript:
    """Test the JavaScript extraction script is valid."""

    @pytest.fixture
    def scraper(self):
        """Create a SolArkScraper instance for testing."""
        return SolArkScraper(mode=ScraperMode.PLAYWRIGHT)

    def test_extraction_script_is_non_empty(self, scraper):
        """Test extraction script returns non-empty string."""
        script = scraper.get_extraction_script()
        assert isinstance(script, str)
        assert len(script) > 100

    def test_extraction_script_has_function(self, scraper):
        """Test extraction script contains a JavaScript function."""
        script = scraper.get_extraction_script()
        # Check for arrow function or regular function syntax
        assert "() =>" in script or "function" in script

    def test_extraction_script_has_return(self, scraper):
        """Test extraction script contains a return statement."""
        script = scraper.get_extraction_script()
        assert "return" in script

    def test_extraction_script_returns_dealers_array(self, scraper):
        """Test extraction script initializes and returns dealers array."""
        script = scraper.get_extraction_script()
        assert "dealers" in script
        assert "return dealers" in script

    def test_extraction_script_extracts_name(self, scraper):
        """Test extraction script extracts dealer name."""
        script = scraper.get_extraction_script()
        assert "name" in script

    def test_extraction_script_extracts_phone(self, scraper):
        """Test extraction script extracts phone number."""
        script = scraper.get_extraction_script()
        assert "phone" in script or "tel:" in script


class TestSolArkParseDealerData:
    """Test parse_dealer_data returns StandardizedDealer with correct fields."""

    @pytest.fixture
    def scraper(self):
        """Create a SolArkScraper instance for testing."""
        return SolArkScraper(mode=ScraperMode.PLAYWRIGHT)

    @pytest.fixture
    def mock_raw_dealer(self):
        """Create mock raw dealer data as returned from JS extraction."""
        return {
            "name": "Solar Energy Systems LLC",
            "phone": "5554567890",
            "email": "info@solarenergy.com",
            "website": "https://www.solarenergy.com",
            "street": "789 Solar Drive",
            "city": "Phoenix",
            "state": "AZ",
            "zip": "85001",
            "address_full": "789 Solar Drive, Phoenix, AZ 85001",
            "rating": 4.9,
            "review_count": 200,
            "tier": "Sol-Ark Top Distributor",
            "certifications": ["Sol-Ark Authorized", "Commercial Systems"],
            "capabilities": ["Solar", "Hybrid Inverters", "Battery Storage", "Commercial"],
            "distance": "3.5 mi",
            "distance_miles": 3.5,
            "has_commercial": True,
            "has_ops_maintenance": False,
            "is_resimercial": True,
            "is_top_distributor": True
        }

    def test_parse_dealer_data_returns_standardized_dealer(self, scraper, mock_raw_dealer):
        """Test parse_dealer_data returns StandardizedDealer object."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "85001")
        assert isinstance(dealer, StandardizedDealer)

    def test_parse_dealer_data_maps_name(self, scraper, mock_raw_dealer):
        """Test dealer name is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "85001")
        assert dealer.name == "Solar Energy Systems LLC"

    def test_parse_dealer_data_maps_phone(self, scraper, mock_raw_dealer):
        """Test dealer phone is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "85001")
        assert dealer.phone == "5554567890"

    def test_parse_dealer_data_maps_website(self, scraper, mock_raw_dealer):
        """Test dealer website is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "85001")
        assert dealer.website == "https://www.solarenergy.com"

    def test_parse_dealer_data_extracts_domain(self, scraper, mock_raw_dealer):
        """Test dealer domain is extracted from website."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "85001")
        assert dealer.domain == "solarenergy.com"

    def test_parse_dealer_data_maps_address(self, scraper, mock_raw_dealer):
        """Test dealer address fields are correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "85001")
        assert dealer.street == "789 Solar Drive"
        assert dealer.city == "Phoenix"
        assert dealer.state == "AZ"
        assert dealer.zip == "85001"

    def test_parse_dealer_data_maps_tier(self, scraper, mock_raw_dealer):
        """Test dealer tier is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "85001")
        assert dealer.tier == "Sol-Ark Top Distributor"

    def test_parse_dealer_data_maps_certifications(self, scraper, mock_raw_dealer):
        """Test dealer certifications are correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "85001")
        assert "Sol-Ark Authorized" in dealer.certifications

    def test_parse_dealer_data_sets_oem_source(self, scraper, mock_raw_dealer):
        """Test oem_source is set to Sol-Ark."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "85001")
        assert dealer.oem_source == "Sol-Ark"

    def test_parse_dealer_data_sets_scraped_from_zip(self, scraper, mock_raw_dealer):
        """Test scraped_from_zip is set correctly."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "85001")
        assert dealer.scraped_from_zip == "85001"

    def test_parse_dealer_data_has_capabilities(self, scraper, mock_raw_dealer):
        """Test dealer has DealerCapabilities object."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "85001")
        assert isinstance(dealer.capabilities, DealerCapabilities)

    def test_parse_dealer_data_sets_resimercial(self, scraper, mock_raw_dealer):
        """Test is_resimercial is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "85001")
        assert dealer.is_resimercial is True


class TestSolArkDetectCapabilities:
    """Test detect_capabilities returns DealerCapabilities object."""

    @pytest.fixture
    def scraper(self):
        """Create a SolArkScraper instance for testing."""
        return SolArkScraper(mode=ScraperMode.PLAYWRIGHT)

    @pytest.fixture
    def mock_raw_dealer(self):
        """Create mock raw dealer data."""
        return {
            "name": "Solar Energy Systems LLC",
            "capabilities": ["Solar", "Hybrid Inverters", "Battery Storage"],
            "has_commercial": False,
            "is_resimercial": False
        }

    def test_detect_capabilities_returns_capabilities_object(self, scraper, mock_raw_dealer):
        """Test detect_capabilities returns DealerCapabilities instance."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert isinstance(caps, DealerCapabilities)

    def test_detect_capabilities_sets_solar_true(self, scraper, mock_raw_dealer):
        """Test solar capability is set for Sol-Ark distributors."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert caps.has_solar is True

    def test_detect_capabilities_sets_inverters_true(self, scraper, mock_raw_dealer):
        """Test inverter capability is set (hybrid inverters)."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert caps.has_inverters is True

    def test_detect_capabilities_sets_battery_true(self, scraper, mock_raw_dealer):
        """Test battery capability is set (100% battery-ready)."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert caps.has_battery is True

    def test_detect_capabilities_sets_electrical_true(self, scraper, mock_raw_dealer):
        """Test electrical capability is set (inverter installation requires it)."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert caps.has_electrical is True

    def test_detect_capabilities_sets_roofing_true(self, scraper, mock_raw_dealer):
        """Test roofing capability is set (solar requires roof work)."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert caps.has_roofing is True

    def test_detect_capabilities_sets_generator_true(self, scraper, mock_raw_dealer):
        """Test generator capability is set (Sol-Ark supports generator inputs)."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert caps.has_generator is True

    def test_detect_capabilities_adds_oem_certification(self, scraper, mock_raw_dealer):
        """Test Sol-Ark is added to OEM certifications."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert "Sol-Ark" in caps.oem_certifications

    def test_detect_capabilities_adds_inverter_oem(self, scraper, mock_raw_dealer):
        """Test Sol-Ark is added to inverter OEMs."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert "Sol-Ark" in caps.inverter_oems

    def test_detect_capabilities_adds_battery_oem(self, scraper, mock_raw_dealer):
        """Test Sol-Ark is added to battery OEMs."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert "Sol-Ark" in caps.battery_oems

    def test_detect_capabilities_commercial_signals(self, scraper):
        """Test commercial signals are detected."""
        raw = {"name": "Commercial Solar Systems", "capabilities": ["Commercial"], "has_commercial": True}
        caps = scraper.detect_capabilities(raw)
        assert caps.is_commercial is True

    def test_detect_capabilities_default_residential(self, scraper, mock_raw_dealer):
        """Test default is residential when not commercial."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert caps.is_residential is True


class TestSolArkScraperHelperMethods:
    """Test additional helper methods and properties."""

    @pytest.fixture
    def scraper(self):
        """Create a SolArkScraper instance for testing."""
        return SolArkScraper(mode=ScraperMode.PLAYWRIGHT)

    def test_parse_results_empty_list(self, scraper):
        """Test parse_results handles empty list."""
        result = scraper.parse_results([], "85001")
        assert result == []

    def test_parse_results_multiple_dealers(self, scraper):
        """Test parse_results handles multiple dealers."""
        raw_results = [
            {"name": "Dealer A", "phone": "1111111111", "capabilities": [], "website": ""},
            {"name": "Dealer B", "phone": "2222222222", "capabilities": [], "website": ""},
        ]
        result = scraper.parse_results(raw_results, "85001")
        assert len(result) == 2
        assert all(isinstance(d, StandardizedDealer) for d in result)

    def test_scraper_mode_default(self, scraper):
        """Test default mode is PLAYWRIGHT."""
        assert scraper.mode == ScraperMode.PLAYWRIGHT

    def test_scraper_mode_runpod(self):
        """Test RUNPOD mode can be set."""
        scraper = SolArkScraper(mode=ScraperMode.RUNPOD)
        assert scraper.mode == ScraperMode.RUNPOD
