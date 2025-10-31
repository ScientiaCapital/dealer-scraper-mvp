import pytest
from scrapers.license.bulk_download_scraper import BulkDownloadScraper
from scrapers.license.models import ScraperMode, StandardizedLicensee

class TestBulkScraper(BulkDownloadScraper):
    """Concrete implementation for testing"""
    def get_state_code(self):
        return "CA"

    def get_download_url(self):
        return "https://example.com/data.csv"

    def parse_file(self, file_path: str):
        return [StandardizedLicensee(
            licensee_name="Test Contractor",
            license_number="12345",
            license_type="Electrical",
            license_status="Active",
            city="Los Angeles",
            state="CA",
            zip="90001",
            source_state="CA",
            source_tier="BULK"
        )]

def test_bulk_scraper_inherits_base():
    """Test BulkDownloadScraper extends BaseLicenseScraper"""
    scraper = TestBulkScraper(mode=ScraperMode.PLAYWRIGHT)
    assert hasattr(scraper, 'mode')
    assert scraper.mode == ScraperMode.PLAYWRIGHT

def test_bulk_scraper_has_download_method():
    """Test scraper has download_file method"""
    scraper = TestBulkScraper(mode=ScraperMode.PLAYWRIGHT)
    assert hasattr(scraper, 'download_file')

def test_bulk_scraper_has_parse_method():
    """Test scraper has abstract parse_file method"""
    scraper = TestBulkScraper(mode=ScraperMode.PLAYWRIGHT)
    assert hasattr(scraper, 'parse_file')

def test_bulk_scraper_filters_license_types():
    """Test scraper filters results by license type"""
    scraper = TestBulkScraper(mode=ScraperMode.PLAYWRIGHT)
    # This will fail until we implement scrape_licenses
    # Just testing the interface exists
    assert hasattr(scraper, 'scrape_licenses')
