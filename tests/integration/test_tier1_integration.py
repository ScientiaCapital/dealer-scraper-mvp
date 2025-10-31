"""
Integration tests for Tier 1 (BULK) state scrapers.

Tests the complete workflow: Factory → Scraper → parse_file → StandardizedLicensee
"""
import pytest
from pathlib import Path
from scrapers.license.scraper_factory import LicenseScraperFactory
from scrapers.license.models import ScraperMode, StandardizedLicensee

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_factory_creates_all_tier1_scrapers():
    """Test factory creates scrapers for all Tier 1 states"""
    states = ["CA", "FL", "TX"]
    for state in states:
        scraper = LicenseScraperFactory.create(state, mode=ScraperMode.PLAYWRIGHT)
        assert scraper is not None
        assert scraper.get_state_code() == state


def test_california_end_to_end():
    """Test California scraper end-to-end"""
    scraper = LicenseScraperFactory.create("CA", mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(FIXTURES_DIR / "ca_sample.csv"))

    assert len(result) == 5
    assert all(isinstance(l, StandardizedLicensee) for l in result)
    assert all(l.source_state == "CA" for l in result)
    assert all(l.source_tier == "BULK" for l in result)

    # Verify license type mapping worked
    license_types = {l.license_type for l in result}
    assert "Electrical" in license_types
    assert "HVAC" in license_types
    assert "LowVoltage" in license_types


def test_florida_end_to_end():
    """Test Florida scraper end-to-end"""
    scraper = LicenseScraperFactory.create("FL", mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(FIXTURES_DIR / "fl_sample.csv"))

    assert len(result) == 5
    assert all(isinstance(l, StandardizedLicensee) for l in result)
    assert all(l.source_state == "FL" for l in result)
    assert all(l.source_tier == "BULK" for l in result)

    # Verify license type mapping worked
    license_types = {l.license_type for l in result}
    assert "Electrical" in license_types
    assert "HVAC" in license_types
    assert "LowVoltage" in license_types


def test_texas_end_to_end():
    """Test Texas scraper end-to-end"""
    scraper = LicenseScraperFactory.create("TX", mode=ScraperMode.PLAYWRIGHT)
    result = scraper.parse_file(str(FIXTURES_DIR / "tx_sample.csv"))

    assert len(result) == 5
    assert all(isinstance(l, StandardizedLicensee) for l in result)
    assert all(l.source_state == "TX" for l in result)
    assert all(l.source_tier == "BULK" for l in result)

    # Verify license type mapping worked
    license_types = {l.license_type for l in result}
    assert "Electrical" in license_types
    assert "HVAC" in license_types
    assert "LowVoltage" in license_types


def test_all_states_have_required_fields():
    """Test all scrapers populate required fields"""
    states_and_fixtures = [
        ("CA", "ca_sample.csv"),
        ("FL", "fl_sample.csv"),
        ("TX", "tx_sample.csv")
    ]

    for state, fixture in states_and_fixtures:
        scraper = LicenseScraperFactory.create(state, mode=ScraperMode.PLAYWRIGHT)
        result = scraper.parse_file(str(FIXTURES_DIR / fixture))

        for licensee in result:
            # Required fields must be present
            assert licensee.licensee_name
            assert licensee.license_number
            assert licensee.license_type
            assert licensee.license_status
            assert licensee.city
            assert licensee.state
            assert licensee.zip
            assert licensee.source_state == state
            assert licensee.source_tier == "BULK"


def test_date_parsing_works_across_states():
    """Test date parsing works for all states"""
    states_and_fixtures = [
        ("CA", "ca_sample.csv"),
        ("FL", "fl_sample.csv"),
        ("TX", "tx_sample.csv")
    ]

    for state, fixture in states_and_fixtures:
        scraper = LicenseScraperFactory.create(state, mode=ScraperMode.PLAYWRIGHT)
        result = scraper.parse_file(str(FIXTURES_DIR / fixture))

        # At least one licensee should have dates parsed
        has_expiration = any(l.expiration_date is not None for l in result)
        assert has_expiration, f"{state} should have at least one expiration date"
