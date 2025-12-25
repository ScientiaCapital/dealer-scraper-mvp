"""
Unit tests for SimpliPhi Power Battery Installer Scraper

Tests for the SimpliPhiScraper class which scrapes the SimpliPhi Power
(now Briggs & Stratton Energy Solutions) installer network.

No network calls - uses mock data only.
"""

import pytest
from scrapers.simpliphi_scraper import SimpliPhiScraper
from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import StandardizedDealer, DealerCapabilities, ScraperMode


class TestSimpliphiScraperFactoryRegistration:
    """Test that SimpliPhi scraper is properly registered with the factory."""

    def test_factory_has_simpliphi_registered(self):
        """Test 'SimpliPhi' is registered in ScraperFactory."""
        available_oems = ScraperFactory.list_available_oems()
        assert "simpliphi" in available_oems

    def test_factory_has_simpliphi_power_alias(self):
        """Test 'SimpliPhi Power' alias is also registered."""
        available_oems = ScraperFactory.list_available_oems()
        assert "simpliphi power" in available_oems

    def test_factory_creates_simpliphi_scraper(self):
        """Test factory creates SimpliPhiScraper instance."""
        scraper = ScraperFactory.create("SimpliPhi", mode=ScraperMode.PLAYWRIGHT)
        assert isinstance(scraper, SimpliPhiScraper)

    def test_factory_create_case_insensitive(self):
        """Test factory lookup is case-insensitive."""
        scraper = ScraperFactory.create("simpliphi", mode=ScraperMode.PLAYWRIGHT)
        assert isinstance(scraper, SimpliPhiScraper)


class TestSimpliphiScraperRequiredMethods:
    """Test that all required abstract methods are implemented."""

    @pytest.fixture
    def scraper(self):
        """Create a SimpliPhiScraper instance for testing."""
        return SimpliPhiScraper(mode=ScraperMode.PLAYWRIGHT)

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
        assert scraper.OEM_NAME == "SimpliPhi"

    def test_has_dealer_locator_url(self, scraper):
        """Test DEALER_LOCATOR_URL class constant is set."""
        assert "briggsandstratton.com" in scraper.DEALER_LOCATOR_URL

    def test_has_product_lines(self, scraper):
        """Test PRODUCT_LINES class constant is set."""
        assert len(scraper.PRODUCT_LINES) > 0
        assert "Battery Storage" in scraper.PRODUCT_LINES
        assert "LFP Batteries" in scraper.PRODUCT_LINES


class TestSimpliphiExtractionScript:
    """Test the JavaScript extraction script is valid."""

    @pytest.fixture
    def scraper(self):
        """Create a SimpliPhiScraper instance for testing."""
        return SimpliPhiScraper(mode=ScraperMode.PLAYWRIGHT)

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


class TestSimpliphiParseDealerData:
    """Test parse_dealer_data returns StandardizedDealer with correct fields."""

    @pytest.fixture
    def scraper(self):
        """Create a SimpliPhiScraper instance for testing."""
        return SimpliPhiScraper(mode=ScraperMode.PLAYWRIGHT)

    @pytest.fixture
    def mock_raw_dealer(self):
        """Create mock raw dealer data as returned from JS extraction."""
        return {
            "name": "Battery Storage Experts",
            "phone": "5557891234",
            "email": "info@batteryexperts.com",
            "website": "https://www.batteryexperts.com",
            "street": "321 Power Lane",
            "city": "San Diego",
            "state": "CA",
            "zip": "92101",
            "address_full": "321 Power Lane, San Diego, CA 92101",
            "rating": 4.7,
            "review_count": 156,
            "tier": "SimpliPhi Authorized Installer",
            "certifications": ["SimpliPhi Authorized", "Solar Installation"],
            "capabilities": ["Battery Storage", "Energy Storage Systems", "Solar"],
            "distance": "6.2 mi",
            "distance_miles": 6.2,
            "has_commercial": False,
            "has_generators": True,
            "has_solar": True,
            "is_multi_product": True,
            "is_resimercial": False
        }

    def test_parse_dealer_data_returns_standardized_dealer(self, scraper, mock_raw_dealer):
        """Test parse_dealer_data returns StandardizedDealer object."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "92101")
        assert isinstance(dealer, StandardizedDealer)

    def test_parse_dealer_data_maps_name(self, scraper, mock_raw_dealer):
        """Test dealer name is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "92101")
        assert dealer.name == "Battery Storage Experts"

    def test_parse_dealer_data_maps_phone(self, scraper, mock_raw_dealer):
        """Test dealer phone is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "92101")
        assert dealer.phone == "5557891234"

    def test_parse_dealer_data_maps_website(self, scraper, mock_raw_dealer):
        """Test dealer website is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "92101")
        assert dealer.website == "https://www.batteryexperts.com"

    def test_parse_dealer_data_extracts_domain(self, scraper, mock_raw_dealer):
        """Test dealer domain is extracted from website."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "92101")
        assert dealer.domain == "batteryexperts.com"

    def test_parse_dealer_data_maps_address(self, scraper, mock_raw_dealer):
        """Test dealer address fields are correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "92101")
        assert dealer.street == "321 Power Lane"
        assert dealer.city == "San Diego"
        assert dealer.state == "CA"
        assert dealer.zip == "92101"

    def test_parse_dealer_data_maps_tier(self, scraper, mock_raw_dealer):
        """Test dealer tier is correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "92101")
        assert dealer.tier == "SimpliPhi Authorized Installer"

    def test_parse_dealer_data_maps_certifications(self, scraper, mock_raw_dealer):
        """Test dealer certifications are correctly mapped."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "92101")
        assert "SimpliPhi Authorized" in dealer.certifications

    def test_parse_dealer_data_sets_oem_source(self, scraper, mock_raw_dealer):
        """Test oem_source is set to SimpliPhi."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "92101")
        assert dealer.oem_source == "SimpliPhi"

    def test_parse_dealer_data_sets_scraped_from_zip(self, scraper, mock_raw_dealer):
        """Test scraped_from_zip is set correctly."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "92101")
        assert dealer.scraped_from_zip == "92101"

    def test_parse_dealer_data_has_capabilities(self, scraper, mock_raw_dealer):
        """Test dealer has DealerCapabilities object."""
        dealer = scraper.parse_dealer_data(mock_raw_dealer, "92101")
        assert isinstance(dealer.capabilities, DealerCapabilities)


class TestSimpliphiDetectCapabilities:
    """Test detect_capabilities returns DealerCapabilities object."""

    @pytest.fixture
    def scraper(self):
        """Create a SimpliPhiScraper instance for testing."""
        return SimpliPhiScraper(mode=ScraperMode.PLAYWRIGHT)

    @pytest.fixture
    def mock_raw_dealer(self):
        """Create mock raw dealer data."""
        return {
            "name": "Battery Storage Experts",
            "capabilities": ["Battery Storage", "Energy Storage Systems"],
            "has_solar": False,
            "has_generators": False,
            "has_commercial": False,
            "is_multi_product": False
        }

    def test_detect_capabilities_returns_capabilities_object(self, scraper, mock_raw_dealer):
        """Test detect_capabilities returns DealerCapabilities instance."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert isinstance(caps, DealerCapabilities)

    def test_detect_capabilities_sets_battery_true(self, scraper, mock_raw_dealer):
        """Test battery capability is set for SimpliPhi installers (core product)."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert caps.has_battery is True

    def test_detect_capabilities_sets_electrical_true(self, scraper, mock_raw_dealer):
        """Test electrical capability is set (battery installation requires it)."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert caps.has_electrical is True

    def test_detect_capabilities_adds_oem_certification(self, scraper, mock_raw_dealer):
        """Test SimpliPhi is added to OEM certifications."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert "SimpliPhi" in caps.oem_certifications

    def test_detect_capabilities_adds_battery_oem(self, scraper, mock_raw_dealer):
        """Test SimpliPhi is added to battery OEMs."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert "SimpliPhi" in caps.battery_oems

    def test_detect_capabilities_solar_from_has_solar(self, scraper):
        """Test solar capability is set from has_solar flag."""
        raw = {"name": "Solar Battery Co", "capabilities": ["Solar"], "has_solar": True}
        caps = scraper.detect_capabilities(raw)
        assert caps.has_solar is True
        assert caps.has_inverters is True
        assert caps.has_roofing is True

    def test_detect_capabilities_generator_from_has_generators(self, scraper):
        """Test generator capability is set from has_generators flag."""
        raw = {"name": "Power Systems LLC", "capabilities": ["Generators"], "has_generators": True}
        caps = scraper.detect_capabilities(raw)
        assert caps.has_generator is True
        assert "Briggs & Stratton" in caps.oem_certifications

    def test_detect_capabilities_commercial_signals(self, scraper):
        """Test commercial signals are detected."""
        raw = {"name": "Commercial Energy Solutions", "capabilities": ["Commercial"], "has_commercial": True}
        caps = scraper.detect_capabilities(raw)
        assert caps.is_commercial is True

    def test_detect_capabilities_default_residential(self, scraper, mock_raw_dealer):
        """Test default is residential when not commercial."""
        caps = scraper.detect_capabilities(mock_raw_dealer)
        assert caps.is_residential is True

    def test_detect_capabilities_multi_product_sets_both(self, scraper):
        """Test multi-product installers set both residential and commercial."""
        raw = {"name": "Full Service Energy", "capabilities": [], "is_multi_product": True}
        caps = scraper.detect_capabilities(raw)
        assert caps.is_residential is True
        assert caps.is_commercial is True


class TestSimpliphiScraperHelperMethods:
    """Test additional helper methods and properties."""

    @pytest.fixture
    def scraper(self):
        """Create a SimpliPhiScraper instance for testing."""
        return SimpliPhiScraper(mode=ScraperMode.PLAYWRIGHT)

    def test_parse_results_empty_list(self, scraper):
        """Test parse_results handles empty list."""
        result = scraper.parse_results([], "92101")
        assert result == []

    def test_parse_results_multiple_dealers(self, scraper):
        """Test parse_results handles multiple dealers."""
        raw_results = [
            {"name": "Dealer A", "phone": "1111111111", "capabilities": [], "website": ""},
            {"name": "Dealer B", "phone": "2222222222", "capabilities": [], "website": ""},
        ]
        result = scraper.parse_results(raw_results, "92101")
        assert len(result) == 2
        assert all(isinstance(d, StandardizedDealer) for d in result)

    def test_scraper_mode_default(self, scraper):
        """Test default mode is PLAYWRIGHT."""
        assert scraper.mode == ScraperMode.PLAYWRIGHT

    def test_scraper_mode_runpod(self):
        """Test RUNPOD mode can be set."""
        scraper = SimpliPhiScraper(mode=ScraperMode.RUNPOD)
        assert scraper.mode == ScraperMode.RUNPOD

    def test_patchright_mode_not_implemented(self, scraper):
        """Test Patchright mode raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            scraper._scrape_with_patchright("92101")
