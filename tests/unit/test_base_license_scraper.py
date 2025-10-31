import pytest
from scrapers.license.base_license_scraper import BaseLicenseScraper
from scrapers.license.models import ScraperMode, StandardizedLicensee

class ConcreteScraper(BaseLicenseScraper):
    """Concrete implementation for testing"""
    def scrape_licenses(self, license_types):
        return []

    def get_state_code(self):
        return "CA"

def test_base_scraper_has_mode():
    """Test BaseLicenseScraper initializes with mode"""
    scraper = ConcreteScraper(mode=ScraperMode.PLAYWRIGHT)
    assert scraper.mode == ScraperMode.PLAYWRIGHT

def test_base_scraper_requires_scrape_licenses():
    """Test abstract method scrape_licenses must be implemented"""
    with pytest.raises(TypeError):
        BaseLicenseScraper(mode=ScraperMode.PLAYWRIGHT)

def test_concrete_scraper_returns_list():
    """Test concrete scraper returns list of StandardizedLicensee"""
    scraper = ConcreteScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.scrape_licenses(["Electrical"])
    assert isinstance(result, list)
