"""
Unit tests for Emerson Sensi Thermostat Installer Scraper

Tests for the SensiScraper class which scrapes the Sensi (Copeland Climate Technologies)
installer directory at sensi.copeland.com.

No network calls - uses mock data only.
"""

import pytest
from scrapers.sensi_scraper import SensiScraper
from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import StandardizedDealer, DealerCapabilities, ScraperMode


class TestSensiScraperFactoryRegistration:
    """Test that Sensi scraper is properly registered with the factory."""

    def test_factory_has_sensi_registered(self):
        """Test 'Sensi' is registered in ScraperFactory."""
        available_oems = ScraperFactory.list_available_oems()
        assert "sensi" in available_oems

    def test_factory_creates_sensi_scraper(self):
        """Test factory creates SensiScraper instance."""
        scraper = ScraperFactory.create("Sensi", mode=ScraperMode.PLAYWRIGHT)
        assert isinstance(scraper, SensiScraper)

    def test_factory_create_case_insensitive(self):
        """Test factory lookup is case-insensitive."""
        scraper = ScraperFactory.create("sensi", mode=ScraperMode.PLAYWRIGHT)
        assert isinstance(scraper, SensiScraper)


class TestSensiScraperRequiredMethods:
    """Test that all required abstract methods are implemented."""

    @pytest.fixture
    def scraper(self):
        """Create a SensiScraper instance for testing."""
        return SensiScraper(mode=ScraperMode.PLAYWRIGHT)

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
        assert scraper.OEM_NAME == "Sensi"

    def test_has_dealer_locator_url(self, scraper):
        """Test DEALER_LOCATOR_URL class constant is set."""
        assert scraper.DEALER_LOCATOR_URL == "https://sensi.copeland.com/en-us/find-a-pro"

    def test_has_product_lines(self, scraper):
        """Test PRODUCT_LINES class constant is set."""
        assert len(scraper.PRODUCT_LINES) > 0
        assert "Sensi Touch 2 Smart Thermostat" in scraper.PRODUCT_LINES


class TestSensiExtractionScript:
    """Test the JavaScript extraction script is valid."""

    @pytest.fixture
    def scraper(self):
        """Create a SensiScraper instance for testing."""
        return SensiScraper(mode=ScraperMode.PLAYWRIGHT)

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

    def test_extraction_script_sets_oem_source(self, scraper):
        """Test extraction script sets oem_source to Sensi."""
        script = scraper.get_extraction_script()
        assert "Sensi" in script


class TestSensiParseDealerData:
    """Test parse_dealer_data returns StandardizedDealer with correct fields."""

    @pytest.fixture
    def scraper(self):
        """Create a SensiScraper instance for testing."""
        return SensiScraper(mode=ScraperMode.PLAYWRIGHT)

    @pytest.fixture
    def mock_raw_dealer(self):
        """Create mock raw dealer data as returned from JS extraction."""
        return {
            "name": "Smart Climate Pros",
            "phone": "5559876543",
            "domain": "smartclimate.com",
            "website": "https://www.smartclimate.com",
            "street": "456 Oak Avenue",
            "city": "Dallas",
            "state": "TX",
            "zip": "75201",
            "address_full": "456 Oak Avenue, Dallas, TX 75201",
            "rating": 4.5,
            "review_count": 89,
            "tier": "Sensi Pro",
            "certifications": ["Smart Thermostats", "HVAC Installation"],
            "distance": "8.3 mi",
            "distance_miles": 8.3,
            "oem_source": "Sensi"
        }

    def test_parse_dealer_data_returns_standardized_dealer(self, scraper, mock_raw_dealer):
        """Test parse_dealer_data returns StandardizedDealer object."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "75201")
        assert isinstance(dealer, StandardizedDealer)

    def test_parse_dealer_data_maps_name(self, scraper, mock_raw_dealer):
        """Test dealer name is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "75201")
        assert dealer.name == "Smart Climate Pros"

    def test_parse_dealer_data_maps_phone(self, scraper, mock_raw_dealer):
        """Test dealer phone is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "75201")
        assert dealer.phone == "5559876543"

    def test_parse_dealer_data_maps_website(self, scraper, mock_raw_dealer):
        """Test dealer website is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "75201")
        assert dealer.website == "https://www.smartclimate.com"

    def test_parse_dealer_data_maps_domain(self, scraper, mock_raw_dealer):
        """Test dealer domain is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "75201")
        assert dealer.domain == "smartclimate.com"

    def test_parse_dealer_data_maps_address(self, scraper, mock_raw_dealer):
        """Test dealer address fields are correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "75201")
        assert dealer.street == "456 Oak Avenue"
        assert dealer.city == "Dallas"
        assert dealer.state == "TX"
        assert dealer.zip == "75201"

    def test_parse_dealer_data_maps_tier(self, scraper, mock_raw_dealer):
        """Test dealer tier is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "75201")
        assert dealer.tier == "Sensi Pro"

    def test_parse_dealer_data_maps_certifications(self, scraper, mock_raw_dealer):
        """Test dealer certifications are correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "75201")
        assert "Smart Thermostats" in dealer.certifications

    def test_parse_dealer_data_sets_oem_source(self, scraper, mock_raw_dealer):
        """Test oem_source is set to Sensi."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "75201")
        assert dealer.oem_source == "Sensi"

    def test_parse_dealer_data_sets_scraped_from_zip(self, scraper, mock_raw_dealer):
        """Test scraped_from_zip is set correctly."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "75201")
        assert dealer.scraped_from_zip == "75201"

    def test_parse_dealer_data_has_capabilities(self, scraper, mock_raw_dealer):
        """Test dealer has DealerCapabilities object."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "75201")
        assert isinstance(dealer.capabilities, DealerCapabilities)


class TestSensiDetectCapabilities:
    """Test detect_capabilities returns DealerCapabilities object."""

    @pytest.fixture
    def scraper(self):
        """Create a SensiScraper instance for testing."""
        return SensiScraper(mode=ScraperMode.PLAYWRIGHT)

    @pytest.fixture
    def mock_raw_dealer(self):
        """Create mock raw dealer data."""
        return {
            "name": "Smart Climate Pros",
            "certifications": ["Smart Thermostats", "HVAC Installation"],
        }

    def test_detect_capabilities_returns_capabilities_object(self, scraper, mock_raw_dealer):
        """Test detect_capabilities returns DealerCapabilities instance."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert isinstance(caps, DealerCapabilities)

    def test_detect_capabilities_sets_hvac_true(self, scraper, mock_raw_dealer):
        """Test HVAC capability is set for Sensi contractors."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert caps.has_hvac is True

    def test_detect_capabilities_sets_electrical_true(self, scraper, mock_raw_dealer):
        """Test electrical capability is set (smart thermostats = low-voltage)."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert caps.has_electrical is True

    def test_detect_capabilities_adds_oem_certification(self, scraper, mock_raw_dealer):
        """Test Sensi is added to OEM certifications."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert "Sensi" in caps.oem_certifications

    def test_detect_capabilities_commercial_signals(self, scraper):
        """Test commercial signals are detected from name."""
        raw = {"name": "Commercial HVAC Solutions LLC", "certifications": []}
        caps = scraper.detect_capabilities(raw)
        assert caps.is_commercial is True

    def test_detect_capabilities_residential_signals(self, scraper):
        """Test residential signals are detected from name."""
        raw = {"name": "Home Comfort Experts", "certifications": []}
        caps = scraper.detect_capabilities(raw)
        assert caps.is_residential is True

    def test_detect_capabilities_default_residential(self, scraper):
        """Test default is residential when no commercial signals."""
        raw = {"name": "Cool Air Technicians", "certifications": []}
        caps = scraper.detect_capabilities(raw)
        assert caps.is_residential is True

    def test_detect_capabilities_plumbing_signals(self, scraper):
        """Test plumbing signals are detected from certifications."""
        raw = {"name": "Full Service HVAC", "certifications": ["plumbing", "water heaters"]}
        caps = scraper.detect_capabilities(raw)
        assert caps.has_plumbing is True


class TestSensiScraperHelperMethods:
    """Test additional helper methods and properties."""

    @pytest.fixture
    def scraper(self):
        """Create a SensiScraper instance for testing."""
        return SensiScraper(mode=ScraperMode.PLAYWRIGHT)

    def test_get_base_url(self, scraper):
        """Test get_base_url returns correct URL."""
        assert scraper.get_base_url() == "https://sensi.copeland.com/en-us/find-a-pro"

    def test_get_brand_name(self, scraper):
        """Test get_brand_name returns correct name."""
        assert scraper.get_brand_name() == "Sensi"

    def test_supports_zip_search(self, scraper):
        """Test supports_zip_search returns True."""
        assert scraper.supports_zip_search() is True

    def test_parse_results_empty_list(self, scraper):
        """Test parse_results handles empty list."""
        result = scraper.parse_results([], "75201")
        assert result == []

    def test_parse_results_multiple_dealers(self, scraper):
        """Test parse_results handles multiple dealers."""
        raw_results = [
            {"name": "Dealer A", "phone": "1111111111", "certifications": []},
            {"name": "Dealer B", "phone": "2222222222", "certifications": []},
        ]
        result = scraper.parse_results(raw_results, "75201")
        assert len(result) == 2
        assert all(isinstance(d, StandardizedDealer) for d in result)
