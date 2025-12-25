"""
Unit tests for Schneider Electric EcoXpert System Integrator Scraper

Tests for the SchneiderElectricScraper class which scrapes the Schneider Electric
EcoXpert system integrator network at se.com.

No network calls - uses mock data only.
"""

import pytest
from scrapers.schneider_scraper import SchneiderElectricScraper
from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import StandardizedDealer, DealerCapabilities, ScraperMode


class TestSchneiderScraperFactoryRegistration:
    """Test that Schneider scraper is properly registered with the factory."""

    def test_factory_has_schneider_electric_registered(self):
        """Test 'Schneider Electric' is registered in ScraperFactory."""
        available_oems = ScraperFactory.list_available_oems()
        assert "schneider electric" in available_oems

    def test_factory_creates_schneider_scraper(self):
        """Test factory creates SchneiderElectricScraper instance."""
        scraper = ScraperFactory.create("Schneider Electric", mode=ScraperMode.PLAYWRIGHT)
        assert isinstance(scraper, SchneiderElectricScraper)

    def test_factory_create_case_insensitive(self):
        """Test factory lookup is case-insensitive."""
        scraper = ScraperFactory.create("schneider electric", mode=ScraperMode.PLAYWRIGHT)
        assert isinstance(scraper, SchneiderElectricScraper)


class TestSchneiderScraperRequiredMethods:
    """Test that all required abstract methods are implemented."""

    @pytest.fixture
    def scraper(self):
        """Create a SchneiderElectricScraper instance for testing."""
        return SchneiderElectricScraper(mode=ScraperMode.PLAYWRIGHT)

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
        assert scraper.OEM_NAME == "Schneider Electric"

    def test_has_dealer_locator_url(self, scraper):
        """Test DEALER_LOCATOR_URL class constant is set."""
        assert "se.com" in scraper.DEALER_LOCATOR_URL
        assert "ecoxpert" in scraper.DEALER_LOCATOR_URL.lower()

    def test_has_product_lines(self, scraper):
        """Test PRODUCT_LINES class constant is set."""
        assert len(scraper.PRODUCT_LINES) > 0
        assert "Building Automation Systems" in scraper.PRODUCT_LINES
        assert "Power Distribution" in scraper.PRODUCT_LINES


class TestSchneiderExtractionScript:
    """Test the JavaScript extraction script is valid."""

    @pytest.fixture
    def scraper(self):
        """Create a SchneiderElectricScraper instance for testing."""
        return SchneiderElectricScraper(mode=ScraperMode.PLAYWRIGHT)

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

    def test_extraction_script_sets_oem_source(self, scraper):
        """Test extraction script sets oem_source to Schneider Electric."""
        script = scraper.get_extraction_script()
        assert "Schneider Electric" in script


class TestSchneiderParseDealerData:
    """Test parse_dealer_data returns StandardizedDealer with correct fields."""

    @pytest.fixture
    def scraper(self):
        """Create a SchneiderElectricScraper instance for testing."""
        return SchneiderElectricScraper(mode=ScraperMode.PLAYWRIGHT)

    @pytest.fixture
    def mock_raw_dealer(self):
        """Create mock raw dealer data as returned from JS extraction."""
        return {
            "name": "Advanced Building Systems Inc",
            "phone": "5551112233",
            "domain": "advancedbuildingsystems.com",
            "website": "https://www.advancedbuildingsystems.com",
            "street": "100 Corporate Drive",
            "city": "Chicago",
            "state": "IL",
            "zip": "60601",
            "address_full": "Chicago",
            "rating": 4.6,
            "review_count": 45,
            "tier": "EcoXpert",
            "certifications": ["EcoXpert Certified", "Building Automation"],
            "distance": "12.5 mi",
            "distance_miles": 12.5,
            "oem_source": "Schneider Electric"
        }

    def test_parse_dealer_data_returns_standardized_dealer(self, scraper, mock_raw_dealer):
        """Test parse_dealer_data returns StandardizedDealer object."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "60601")
        assert isinstance(dealer, StandardizedDealer)

    def test_parse_dealer_data_maps_name(self, scraper, mock_raw_dealer):
        """Test dealer name is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "60601")
        assert dealer.name == "Advanced Building Systems Inc"

    def test_parse_dealer_data_maps_phone(self, scraper, mock_raw_dealer):
        """Test dealer phone is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "60601")
        assert dealer.phone == "5551112233"

    def test_parse_dealer_data_maps_website(self, scraper, mock_raw_dealer):
        """Test dealer website is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "60601")
        assert dealer.website == "https://www.advancedbuildingsystems.com"

    def test_parse_dealer_data_maps_domain(self, scraper, mock_raw_dealer):
        """Test dealer domain is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "60601")
        assert dealer.domain == "advancedbuildingsystems.com"

    def test_parse_dealer_data_maps_address(self, scraper, mock_raw_dealer):
        """Test dealer address fields are correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "60601")
        assert dealer.city == "Chicago"
        assert dealer.state == "IL"
        assert dealer.zip == "60601"

    def test_parse_dealer_data_maps_tier(self, scraper, mock_raw_dealer):
        """Test dealer tier is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "60601")
        assert dealer.tier == "EcoXpert"

    def test_parse_dealer_data_maps_certifications(self, scraper, mock_raw_dealer):
        """Test dealer certifications are correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "60601")
        assert "EcoXpert Certified" in dealer.certifications

    def test_parse_dealer_data_sets_oem_source(self, scraper, mock_raw_dealer):
        """Test oem_source is set to Schneider Electric."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "60601")
        assert dealer.oem_source == "Schneider Electric"

    def test_parse_dealer_data_sets_scraped_from_zip(self, scraper, mock_raw_dealer):
        """Test scraped_from_zip is set correctly."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "60601")
        assert dealer.scraped_from_zip == "60601"

    def test_parse_dealer_data_has_capabilities(self, scraper, mock_raw_dealer):
        """Test dealer has DealerCapabilities object."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "60601")
        assert isinstance(dealer.capabilities, DealerCapabilities)

    def test_parse_dealer_data_maps_distance(self, scraper, mock_raw_dealer):
        """Test distance fields are correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "60601")
        assert dealer.distance == "12.5 mi"
        assert dealer.distance_miles == 12.5


class TestSchneiderDetectCapabilities:
    """Test detect_capabilities returns DealerCapabilities object."""

    @pytest.fixture
    def scraper(self):
        """Create a SchneiderElectricScraper instance for testing."""
        return SchneiderElectricScraper(mode=ScraperMode.PLAYWRIGHT)

    @pytest.fixture
    def mock_raw_dealer(self):
        """Create mock raw dealer data."""
        return {
            "name": "Advanced Building Systems Inc",
            "certifications": ["EcoXpert Certified"],
        }

    def test_detect_capabilities_returns_capabilities_object(self, scraper, mock_raw_dealer):
        """Test detect_capabilities returns DealerCapabilities instance."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert isinstance(caps, DealerCapabilities)

    def test_detect_capabilities_sets_solar_true(self, scraper, mock_raw_dealer):
        """Test solar capability is set for Schneider installers."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert caps.has_solar is True

    def test_detect_capabilities_sets_inverters_true(self, scraper, mock_raw_dealer):
        """Test inverter capability is set."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert caps.has_inverters is True

    def test_detect_capabilities_adds_oem_certification(self, scraper, mock_raw_dealer):
        """Test Schneider Electric is added to OEM certifications."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert "Schneider Electric" in caps.oem_certifications

    def test_detect_capabilities_commercial_signals(self, scraper):
        """Test commercial signals are detected from name."""
        raw = {"name": "Commercial Energy Systems Corp", "certifications": []}
        caps = scraper.detect_capabilities(raw)
        assert caps.is_commercial is True

    def test_detect_capabilities_residential_signals(self, scraper):
        """Test residential signals are detected from name."""
        raw = {"name": "Home Energy Solutions", "certifications": []}
        caps = scraper.detect_capabilities(raw)
        assert caps.is_residential is True

    def test_detect_capabilities_electrical_from_name(self, scraper):
        """Test electrical capability is detected from name keywords."""
        raw = {"name": "Solar Electric Contractors", "certifications": []}
        caps = scraper.detect_capabilities(raw)
        assert caps.has_electrical is True

    def test_detect_capabilities_battery_from_name(self, scraper):
        """Test battery capability is detected from name keywords."""
        raw = {"name": "Battery Storage Systems LLC", "certifications": []}
        caps = scraper.detect_capabilities(raw)
        assert caps.has_battery is True

    def test_detect_capabilities_battery_from_certifications(self, scraper):
        """Test battery capability is detected from certifications."""
        raw = {"name": "Energy Systems Inc", "certifications": ["Battery Storage Certified"]}
        caps = scraper.detect_capabilities(raw)
        assert caps.has_battery is True

    def test_detect_capabilities_commercial_from_certifications(self, scraper):
        """Test commercial capability is detected from certifications."""
        raw = {"name": "Power Systems LLC", "certifications": ["Commercial Industrial Certified"]}
        caps = scraper.detect_capabilities(raw)
        assert caps.is_commercial is True


class TestSchneiderScraperHelperMethods:
    """Test additional helper methods and properties."""

    @pytest.fixture
    def scraper(self):
        """Create a SchneiderElectricScraper instance for testing."""
        return SchneiderElectricScraper(mode=ScraperMode.PLAYWRIGHT)

    def test_get_base_url(self, scraper):
        """Test get_base_url returns correct URL."""
        url = scraper.get_base_url()
        assert "se.com" in url
        assert "ecoxpert" in url.lower()

    def test_get_brand_name(self, scraper):
        """Test get_brand_name returns correct name."""
        assert scraper.get_brand_name() == "Schneider Electric"

    def test_supports_zip_search(self, scraper):
        """Test supports_zip_search returns True."""
        assert scraper.supports_zip_search() is True

    def test_parse_results_empty_list(self, scraper):
        """Test parse_results handles empty list."""
        result = scraper.parse_results([], "60601")
        assert result == []

    def test_parse_results_multiple_dealers(self, scraper):
        """Test parse_results handles multiple dealers."""
        raw_results = [
            {"name": "Dealer A", "phone": "1111111111", "certifications": []},
            {"name": "Dealer B", "phone": "2222222222", "certifications": []},
        ]
        result = scraper.parse_results(raw_results, "60601")
        assert len(result) == 2
        assert all(isinstance(d, StandardizedDealer) for d in result)

    def test_runpod_mode_not_implemented(self, scraper):
        """Test RunPod mode raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            scraper._scrape_with_runpod("60601")

    def test_patchright_mode_not_implemented(self, scraper):
        """Test Patchright mode raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            scraper._scrape_with_patchright("60601")


class TestSchneiderScraperEcoXpertSpecific:
    """Test EcoXpert-specific functionality."""

    @pytest.fixture
    def scraper(self):
        """Create a SchneiderElectricScraper instance for testing."""
        return SchneiderElectricScraper(mode=ScraperMode.PLAYWRIGHT)

    def test_extraction_script_handles_results_section(self, scraper):
        """Test extraction script looks for Results section."""
        script = scraper.get_extraction_script()
        # EcoXpert page shows "X Results" after search
        assert "Results" in script

    def test_extraction_script_parses_company_patterns(self, scraper):
        """Test extraction script recognizes company name patterns."""
        script = scraper.get_extraction_script()
        # Should recognize common company suffixes
        assert "Inc" in script or "LLC" in script or "Corp" in script

    def test_ecoxpert_tier_in_certifications(self, scraper):
        """Test EcoXpert tier is recognized in mock data."""
        raw = {
            "name": "EcoXpert Systems Integration",
            "certifications": ["EcoXpert Certified"],
            "tier": "EcoXpert"
        }
        dealer = scraper.parse_dealer_data(raw, "60601")
        assert dealer.tier == "EcoXpert"
        assert "EcoXpert Certified" in dealer.certifications
