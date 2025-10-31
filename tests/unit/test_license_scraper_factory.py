import pytest
from scrapers.license.scraper_factory import LicenseScraperFactory
from scrapers.license.models import ScraperMode
from scrapers.license.base_license_scraper import BaseLicenseScraper

def test_factory_creates_bulk_scraper():
    """Test factory creates BulkDownloadScraper for CA"""
    scraper = LicenseScraperFactory.create("CA", mode=ScraperMode.PLAYWRIGHT)
    assert scraper is not None
    assert scraper.get_state_code() == "CA"

def test_factory_raises_for_invalid_state():
    """Test factory raises ValueError for invalid state"""
    with pytest.raises(ValueError):
        LicenseScraperFactory.create("XX", mode=ScraperMode.PLAYWRIGHT)

def test_factory_returns_base_scraper_type():
    """Test factory returns BaseLicenseScraper instance"""
    scraper = LicenseScraperFactory.create("CA", mode=ScraperMode.PLAYWRIGHT)
    assert isinstance(scraper, BaseLicenseScraper)

def test_factory_supports_all_bulk_states():
    """Test factory supports CA, FL, TX"""
    for state in ["CA", "FL", "TX"]:
        scraper = LicenseScraperFactory.create(state, mode=ScraperMode.PLAYWRIGHT)
        assert scraper.get_state_code() == state

def test_factory_get_supported_states():
    """Test factory returns list of supported states"""
    supported = LicenseScraperFactory.get_supported_states()
    assert isinstance(supported, list)
    assert "CA" in supported
    assert "FL" in supported
    assert "TX" in supported
