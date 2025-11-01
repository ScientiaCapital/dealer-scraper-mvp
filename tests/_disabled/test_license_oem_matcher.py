import pytest
from analysis.license_oem_matcher import LicenseOEMMatcher
from scrapers.license.models import StandardizedLicensee
from scrapers.base_scraper import StandardizedDealer

def test_match_by_phone_exact():
    """Test exact phone number matching"""
    licensee = StandardizedLicensee(
        licensee_name="ABC Electric",
        license_number="12345",
        license_type="Electrical",
        license_status="Active",
        city="Los Angeles",
        state="CA",
        zip="90001",
        source_state="CA",
        source_tier="BULK",
        phone="323-555-1234"
    )

    dealer = StandardizedDealer(
        name="ABC Electrical Services",
        phone="+1 (323) 555-1234",  # Different format, same number
        domain="abcelectrical.com",
        website="https://abcelectrical.com",
        street="123 Main St",
        city="Los Angeles",
        state="CA",
        zip="90001",
        address_full="123 Main St, Los Angeles, CA 90001",
        oem_source="Generac",
        scraped_from_zip="90001"
    )

    matcher = LicenseOEMMatcher()
    matches = matcher.match([licensee], [dealer])

    assert len(matches) == 1
    assert matches[0]["licensee"] == licensee
    assert matches[0]["dealer"] == dealer
    assert matches[0]["match_type"] == "phone"
    assert matches[0]["confidence"] == 100

def test_match_by_domain():
    """Test domain matching when phone missing"""
    licensee = StandardizedLicensee(
        licensee_name="XYZ Solar",
        license_number="67890",
        license_type="Electrical",
        license_status="Active",
        city="San Diego",
        state="CA",
        zip="92101",
        source_state="CA",
        source_tier="BULK",
        website="https://www.xyzsolar.com"
    )

    dealer = StandardizedDealer(
        name="XYZ Solar Inc",
        phone="619-555-0000",
        domain="xyzsolar.com",
        website="https://xyzsolar.com",
        street="456 Solar Way",
        city="San Diego",
        state="CA",
        zip="92101",
        address_full="456 Solar Way, San Diego, CA 92101",
        oem_source="Tesla",
        scraped_from_zip="92101"
    )

    matcher = LicenseOEMMatcher()
    matches = matcher.match([licensee], [dealer])

    assert len(matches) == 1
    assert matches[0]["match_type"] == "domain"
    assert matches[0]["confidence"] == 90

def test_no_match_different_data():
    """Test no match when data doesn't align"""
    licensee = StandardizedLicensee(
        licensee_name="Company A",
        license_number="11111",
        license_type="Electrical",
        license_status="Active",
        city="Austin",
        state="TX",
        zip="78701",
        source_state="TX",
        source_tier="BULK",
        phone="512-555-1111"
    )

    dealer = StandardizedDealer(
        name="Company B",
        phone="512-555-2222",  # Different number
        domain="companyb.com",
        website="https://companyb.com",
        street="789 Oak St",
        city="Austin",
        state="TX",
        zip="78701",
        address_full="789 Oak St, Austin, TX 78701",
        oem_source="Generac",
        scraped_from_zip="78701"
    )

    matcher = LicenseOEMMatcher()
    matches = matcher.match([licensee], [dealer])

    assert len(matches) == 0

def test_match_returns_enriched_dealer():
    """Test matched dealer gets enriched with license metadata"""
    licensee = StandardizedLicensee(
        licensee_name="Test Contractor",
        license_number="99999",
        license_type="HVAC",
        license_status="Active",
        city="Miami",
        state="FL",
        zip="33101",
        source_state="FL",
        source_tier="BULK",
        phone="305-555-9999"
    )

    dealer = StandardizedDealer(
        name="Test HVAC",
        phone="305-555-9999",
        domain="testhvac.com",
        website="https://testhvac.com",
        street="321 Palm Dr",
        city="Miami",
        state="FL",
        zip="33101",
        address_full="321 Palm Dr, Miami, FL 33101",
        oem_source="Carrier",
        scraped_from_zip="33101"
    )

    matcher = LicenseOEMMatcher()
    matches = matcher.match([licensee], [dealer])

    match = matches[0]
    enriched = match["enriched_dealer"]

    # Verify enrichment fields
    assert enriched["license_number"] == "99999"
    assert enriched["license_type"] == "HVAC"
    assert enriched["license_status"] == "Active"
    assert enriched["license_state"] == "FL"
