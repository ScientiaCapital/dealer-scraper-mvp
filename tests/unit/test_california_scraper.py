import pytest
from pathlib import Path
from scrapers.license.scraper_factory import CaliforniaScraper
from scrapers.license.models import ScraperMode

# Test fixture path
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
CA_SAMPLE_CSV = FIXTURES_DIR / "ca_sample.csv"


def test_california_parser_returns_list():
    """Test parse_file returns list of StandardizedLicensee"""
    scraper = CaliforniaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(CA_SAMPLE_CSV))
    assert isinstance(result, list)


def test_california_parser_parses_all_rows():
    """Test parser extracts all 5 sample rows"""
    scraper = CaliforniaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(CA_SAMPLE_CSV))
    assert len(result) == 5


def test_california_parser_maps_license_number():
    """Test license number field mapping"""
    scraper = CaliforniaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(CA_SAMPLE_CSV))
    assert result[0].license_number == "123456"
    assert result[1].license_number == "789012"


def test_california_parser_maps_business_name():
    """Test business name field mapping"""
    scraper = CaliforniaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(CA_SAMPLE_CSV))
    assert result[0].licensee_name == "ABC Electrical Services"
    assert result[1].licensee_name == "XYZ HVAC Corp"


def test_california_parser_maps_license_type():
    """Test license type mapping"""
    scraper = CaliforniaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(CA_SAMPLE_CSV))
    assert result[0].license_type == "Electrical"  # C-10 -> Electrical
    assert result[1].license_type == "HVAC"  # C-20 -> HVAC
    assert result[2].license_type == "LowVoltage"  # C-7 -> LowVoltage


def test_california_parser_maps_status():
    """Test license status mapping"""
    scraper = CaliforniaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(CA_SAMPLE_CSV))
    assert result[0].license_status == "Active"
    assert result[3].license_status == "Inactive"


def test_california_parser_maps_location():
    """Test location field mapping"""
    scraper = CaliforniaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(CA_SAMPLE_CSV))
    first = result[0]
    assert first.street == "1234 Main St"
    assert first.city == "Los Angeles"
    assert first.state == "CA"
    assert first.zip == "90001"


def test_california_parser_sets_source_metadata():
    """Test source_state and source_tier are set correctly"""
    scraper = CaliforniaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(CA_SAMPLE_CSV))
    first = result[0]
    assert first.source_state == "CA"
    assert first.source_tier == "BULK"


def test_california_parser_handles_missing_email():
    """Test parser handles missing optional fields"""
    scraper = CaliforniaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(CA_SAMPLE_CSV))
    # Row 4 has empty email
    assert result[3].email is None or result[3].email == ""


def test_california_parser_parses_dates():
    """Test date parsing for issue and expiration dates"""
    scraper = CaliforniaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(CA_SAMPLE_CSV))
    first = result[0]
    assert first.issue_date is not None
    assert first.expiration_date is not None
