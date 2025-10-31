import pytest
from pathlib import Path
from scrapers.license.scraper_factory import TexasScraper
from scrapers.license.models import ScraperMode

# Test fixture path (using CSV for testing, production uses Excel)
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
TX_SAMPLE_CSV = FIXTURES_DIR / "tx_sample.csv"


def test_texas_parser_returns_list():
    """Test parse_file returns list of StandardizedLicensee"""
    scraper = TexasScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(TX_SAMPLE_CSV))
    assert isinstance(result, list)


def test_texas_parser_parses_all_rows():
    """Test parser extracts all 5 sample rows"""
    scraper = TexasScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(TX_SAMPLE_CSV))
    assert len(result) == 5


def test_texas_parser_maps_license_number():
    """Test license number field mapping"""
    scraper = TexasScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(TX_SAMPLE_CSV))
    assert result[0].license_number == "EC123456"
    assert result[1].license_number == "LV456789"


def test_texas_parser_maps_business_name():
    """Test business name field mapping"""
    scraper = TexasScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(TX_SAMPLE_CSV))
    assert result[0].licensee_name == "Texas Electric Services LLC"
    assert result[1].licensee_name == "Low Voltage Specialists"


def test_texas_parser_maps_license_type():
    """Test license type mapping"""
    scraper = TexasScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(TX_SAMPLE_CSV))
    assert result[0].license_type == "Electrical"  # Electrical Contractor -> Electrical
    assert result[1].license_type == "LowVoltage"  # Low Voltage Contractor -> LowVoltage
    assert result[2].license_type == "HVAC"  # Air Conditioning Contractor -> HVAC


def test_texas_parser_maps_status():
    """Test license status mapping"""
    scraper = TexasScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(TX_SAMPLE_CSV))
    assert result[0].license_status == "Active"
    assert result[3].license_status == "Inactive"


def test_texas_parser_maps_location():
    """Test location field mapping"""
    scraper = TexasScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(TX_SAMPLE_CSV))
    first = result[0]
    assert first.street == "1234 Longhorn Dr"
    assert first.city == "Austin"
    assert first.state == "TX"
    assert first.zip == "78701"


def test_texas_parser_sets_source_metadata():
    """Test source_state and source_tier are set correctly"""
    scraper = TexasScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(TX_SAMPLE_CSV))
    first = result[0]
    assert first.source_state == "TX"
    assert first.source_tier == "BULK"


def test_texas_parser_handles_missing_email():
    """Test parser handles missing optional fields"""
    scraper = TexasScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(TX_SAMPLE_CSV))
    # Row 4 has empty email
    assert result[3].email is None or result[3].email == ""


def test_texas_parser_parses_dates():
    """Test date parsing for issue and expiration dates"""
    scraper = TexasScraper(mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(TX_SAMPLE_CSV))
    first = result[0]
    assert first.issue_date is not None
    assert first.expiration_date is not None
