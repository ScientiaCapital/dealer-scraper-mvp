import pytest
from pathlib import Path
from scrapers.license.scraper_factory import FloridaScraper
from scrapers.license.models import ScraperMode

# Test fixture path
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
FL_SAMPLE_CSV = FIXTURES_DIR / "fl_sample.csv"


def test_florida_parser_returns_list():
    """Test parse_file returns list of StandardizedLicensee"""
    scraper = FloridaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(FL_SAMPLE_CSV))
    assert isinstance(result, list)


def test_florida_parser_parses_all_rows():
    """Test parser extracts all 5 sample rows"""
    scraper = FloridaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(FL_SAMPLE_CSV))
    assert len(result) == 5


def test_florida_parser_maps_license_number():
    """Test license number field mapping"""
    scraper = FloridaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(FL_SAMPLE_CSV))
    assert result[0].license_number == "ER0012345"
    assert result[1].license_number == "EL0056789"


def test_florida_parser_maps_business_name():
    """Test business name field mapping"""
    scraper = FloridaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(FL_SAMPLE_CSV))
    assert result[0].licensee_name == "Florida Electric Pro LLC"
    assert result[1].licensee_name == "Low Voltage Systems Inc"


def test_florida_parser_maps_license_type():
    """Test license type mapping"""
    scraper = FloridaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(FL_SAMPLE_CSV))
    assert result[0].license_type == "Electrical"  # ER -> Electrical
    assert result[1].license_type == "LowVoltage"  # EL -> LowVoltage
    assert result[2].license_type == "HVAC"  # CAC -> HVAC


def test_florida_parser_maps_status():
    """Test license status mapping"""
    scraper = FloridaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(FL_SAMPLE_CSV))
    assert result[0].license_status == "Active"
    assert result[3].license_status == "Inactive"


def test_florida_parser_maps_location():
    """Test location field mapping"""
    scraper = FloridaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(FL_SAMPLE_CSV))
    first = result[0]
    assert first.street == "123 Palm Ave"
    assert first.city == "Miami"
    assert first.state == "FL"
    assert first.zip == "33101"


def test_florida_parser_sets_source_metadata():
    """Test source_state and source_tier are set correctly"""
    scraper = FloridaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(FL_SAMPLE_CSV))
    first = result[0]
    assert first.source_state == "FL"
    assert first.source_tier == "BULK"


def test_florida_parser_handles_missing_email():
    """Test parser handles missing optional fields"""
    scraper = FloridaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(FL_SAMPLE_CSV))
    # Row 4 has empty email
    assert result[3].email is None or result[3].email == ""


def test_florida_parser_parses_dates():
    """Test date parsing for original and expiration dates"""
    scraper = FloridaScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(FL_SAMPLE_CSV))
    first = result[0]
    assert first.original_issue_date is not None  # Florida has "Original License Date"
    assert first.expiration_date is not None
