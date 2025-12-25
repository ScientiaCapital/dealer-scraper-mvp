"""
Unit tests for Honeywell Home Pro Installer Scraper

Tests for the HoneywellHomeScraper class which scrapes the Honeywell Home Pro
installer directory at honeywellhome.com.

No network calls - uses mock data only.
"""

import pytest
from scrapers.honeywell_scraper import HoneywellHomeScraper
from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import StandardizedDealer, DealerCapabilities, ScraperMode


class TestHoneywellScraperFactoryRegistration:
    """Test that Honeywell scraper is properly registered with the factory."""

    def test_factory_has_honeywell_home_registered(self):
        """Test 'Honeywell Home' is registered in ScraperFactory."""
        available_oems = ScraperFactory.list_available_oems()
        assert "honeywell home" in available_oems

    def test_factory_creates_honeywell_scraper(self):
        """Test factory creates HoneywellHomeScraper instance."""
        scraper = ScraperFactory.create("Honeywell Home", mode=ScraperMode.PLAYWRIGHT)
        assert isinstance(scraper, HoneywellHomeScraper)

    def test_factory_create_case_insensitive(self):
        """Test factory lookup is case-insensitive."""
        scraper = ScraperFactory.create("honeywell home", mode=ScraperMode.PLAYWRIGHT)
        assert isinstance(scraper, HoneywellHomeScraper)


class TestHoneywellScraperRequiredMethods:
    """Test that all required abstract methods are implemented."""

    @pytest.fixture
    def scraper(self):
        """Create a HoneywellHomeScraper instance for testing."""
        return HoneywellHomeScraper(mode=ScraperMode.PLAYWRIGHT)

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
        assert scraper.OEM_NAME == "Honeywell Home"

    def test_has_dealer_locator_url(self, scraper):
        """Test DEALER_LOCATOR_URL class constant is set."""
        assert scraper.DEALER_LOCATOR_URL == "https://www.honeywellhome.com/us/en/find-a-pro/"

    def test_has_product_lines(self, scraper):
        """Test PRODUCT_LINES class constant is set."""
        assert len(scraper.PRODUCT_LINES) > 0
        assert "Smart Thermostats" in scraper.PRODUCT_LINES


class TestHoneywellExtractionScript:
    """Test the JavaScript extraction script is valid."""

    @pytest.fixture
    def scraper(self):
        """Create a HoneywellHomeScraper instance for testing."""
        return HoneywellHomeScraper(mode=ScraperMode.PLAYWRIGHT)

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
        """Test extraction script sets oem_source to Honeywell Home."""
        script = scraper.get_extraction_script()
        assert "Honeywell Home" in script


class TestHoneywellParseDealerData:
    """Test parse_dealer_data returns StandardizedDealer with correct fields."""

    @pytest.fixture
    def scraper(self):
        """Create a HoneywellHomeScraper instance for testing."""
        return HoneywellHomeScraper(mode=ScraperMode.PLAYWRIGHT)

    @pytest.fixture
    def mock_raw_dealer(self):
        """Create mock raw dealer data as returned from JS extraction."""
        return {
            "name": "ABC Heating & Cooling Inc",
            "phone": "5551234567",
            "domain": "abchvac.com",
            "website": "https://www.abchvac.com",
            "street": "123 Main Street",
            "city": "Houston",
            "state": "TX",
            "zip": "77001",
            "address_full": "123 Main Street, Houston, TX 77001",
            "rating": 4.8,
            "review_count": 125,
            "tier": "Pro Installer",
            "certifications": ["HVAC", "Smart Controls"],
            "distance": "5.2 mi",
            "distance_miles": 5.2,
            "oem_source": "Honeywell Home"
        }

    def test_parse_dealer_data_returns_standardized_dealer(self, scraper, mock_raw_dealer):
        """Test parse_dealer_data returns StandardizedDealer object."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "77001")
        assert isinstance(dealer, StandardizedDealer)

    def test_parse_dealer_data_maps_name(self, scraper, mock_raw_dealer):
        """Test dealer name is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "77001")
        assert dealer.name == "ABC Heating & Cooling Inc"

    def test_parse_dealer_data_maps_phone(self, scraper, mock_raw_dealer):
        """Test dealer phone is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "77001")
        assert dealer.phone == "5551234567"

    def test_parse_dealer_data_maps_website(self, scraper, mock_raw_dealer):
        """Test dealer website is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "77001")
        assert dealer.website == "https://www.abchvac.com"

    def test_parse_dealer_data_maps_domain(self, scraper, mock_raw_dealer):
        """Test dealer domain is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "77001")
        assert dealer.domain == "abchvac.com"

    def test_parse_dealer_data_maps_address(self, scraper, mock_raw_dealer):
        """Test dealer address fields are correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "77001")
        assert dealer.street == "123 Main Street"
        assert dealer.city == "Houston"
        assert dealer.state == "TX"
        assert dealer.zip == "77001"

    def test_parse_dealer_data_maps_tier(self, scraper, mock_raw_dealer):
        """Test dealer tier is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "77001")
        assert dealer.tier == "Pro Installer"

    def test_parse_dealer_data_maps_certifications(self, scraper, mock_raw_dealer):
        """Test dealer certifications are correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "77001")
        assert "HVAC" in dealer.certifications
        assert "Smart Controls" in dealer.certifications

    def test_parse_dealer_data_sets_oem_source(self, scraper, mock_raw_dealer):
        """Test oem_source is set to Honeywell Home."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "77001")
        assert dealer.oem_source == "Honeywell Home"

    def test_parse_dealer_data_sets_scraped_from_zip(self, scraper, mock_raw_dealer):
        """Test scraped_from_zip is set correctly."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "77001")
        assert dealer.scraped_from_zip == "77001"

    def test_parse_dealer_data_has_capabilities(self, scraper, mock_raw_dealer):
        """Test dealer has DealerCapabilities object."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "77001")
        assert isinstance(dealer.capabilities, DealerCapabilities)


class TestHoneywellDetectCapabilities:
    """Test detect_capabilities returns DealerCapabilities object."""

    @pytest.fixture
    def scraper(self):
        """Create a HoneywellHomeScraper instance for testing."""
        return HoneywellHomeScraper(mode=ScraperMode.PLAYWRIGHT)

    @pytest.fixture
    def mock_raw_dealer(self):
        """Create mock raw dealer data."""
        return {
            "name": "ABC Heating & Cooling Inc",
            "certifications": ["HVAC", "Smart Controls"],
        }

    def test_detect_capabilities_returns_capabilities_object(self, scraper, mock_raw_dealer):
        """Test detect_capabilities returns DealerCapabilities instance."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert isinstance(caps, DealerCapabilities)

    def test_detect_capabilities_sets_hvac_true(self, scraper, mock_raw_dealer):
        """Test HVAC capability is set for Honeywell contractors."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert caps.has_hvac is True

    def test_detect_capabilities_sets_electrical_true(self, scraper, mock_raw_dealer):
        """Test electrical capability is set (smart thermostats = low-voltage)."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert caps.has_electrical is True

    def test_detect_capabilities_adds_oem_certification(self, scraper, mock_raw_dealer):
        """Test Honeywell Home is added to OEM certifications."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert "Honeywell Home" in caps.oem_certifications

    def test_detect_capabilities_commercial_signals(self, scraper):
        """Test commercial signals are detected from name."""
        raw = {"name": "Commercial HVAC Systems Inc", "certifications": []}
        caps = scraper.detect_capabilities(raw)
        assert caps.is_commercial is True

    def test_detect_capabilities_residential_signals(self, scraper):
        """Test residential signals are detected from name."""
        raw = {"name": "Home Comfort Solutions", "certifications": []}
        caps = scraper.detect_capabilities(raw)
        assert caps.is_residential is True

    def test_detect_capabilities_default_residential(self, scraper):
        """Test default is residential when no commercial signals."""
        raw = {"name": "Cool Air Experts", "certifications": []}
        caps = scraper.detect_capabilities(raw)
        assert caps.is_residential is True


class TestHoneywellScraperHelperMethods:
    """Test additional helper methods and properties."""

    @pytest.fixture
    def scraper(self):
        """Create a HoneywellHomeScraper instance for testing."""
        return HoneywellHomeScraper(mode=ScraperMode.PLAYWRIGHT)

    def test_get_base_url(self, scraper):
        """Test get_base_url returns correct URL."""
        assert scraper.get_base_url() == "https://www.honeywellhome.com/us/en/find-a-pro/"

    def test_get_brand_name(self, scraper):
        """Test get_brand_name returns correct name."""
        assert scraper.get_brand_name() == "Honeywell Home"

    def test_supports_zip_search(self, scraper):
        """Test supports_zip_search returns True."""
        assert scraper.supports_zip_search() is True

    def test_parse_results_empty_list(self, scraper):
        """Test parse_results handles empty list."""
        result = scraper.parse_results([], "77001")
        assert result == []

    def test_parse_results_multiple_dealers(self, scraper):
        """Test parse_results handles multiple dealers."""
        raw_results = [
            {"name": "Dealer A", "phone": "1111111111", "certifications": []},
            {"name": "Dealer B", "phone": "2222222222", "certifications": []},
        ]
        result = scraper.parse_results(raw_results, "77001")
        assert len(result) == 2
        assert all(isinstance(d, StandardizedDealer) for d in result)
