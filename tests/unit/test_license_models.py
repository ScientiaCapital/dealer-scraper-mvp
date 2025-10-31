from datetime import datetime, date
from scrapers.license.models import StandardizedLicensee

def test_standardized_licensee_creation():
    """Test creating a StandardizedLicensee with all required fields"""
    licensee = StandardizedLicensee(
        licensee_name="John Smith",
        business_name="Smith Electric LLC",
        license_number="C-10-123456",
        license_type="Electrical Contractor",
        license_status="Active",
        issue_date=date(2015, 1, 15),
        expiration_date=date(2027, 1, 15),
        original_issue_date=date(2010, 3, 1),
        phone="4155551234",
        email="john@smithelectric.com",
        website="https://smithelectric.com",
        street="123 Main St",
        city="San Francisco",
        state="CA",
        zip="94102",
        county="San Francisco",
        trade_classifications=["Electrical", "Low Voltage"],
        insurance_info="GL-1M-2M",
        worker_count=15,
        business_type="LLC",
        source_state="CA",
        source_tier="BULK",
        scraped_date=datetime.now(),
        matched_oem_contractors=[],
        match_confidence=None
    )

    assert licensee.licensee_name == "John Smith"
    assert licensee.license_status == "Active"
    assert len(licensee.trade_classifications) == 2

def test_standardized_licensee_with_optional_fields_none():
    """Test creating licensee with minimal required fields"""
    licensee = StandardizedLicensee(
        licensee_name="Jane Doe",
        business_name=None,
        license_number="TX-E-98765",
        license_type="Electrical Contractor",
        license_status="Active",
        issue_date=None,
        expiration_date=None,
        original_issue_date=None,
        phone=None,
        email=None,
        website=None,
        street=None,
        city="Austin",
        state="TX",
        zip="78701",
        county=None,
        trade_classifications=[],
        insurance_info=None,
        worker_count=None,
        business_type=None,
        source_state="TX",
        source_tier="API",
        scraped_date=datetime.now(),
        matched_oem_contractors=[],
        match_confidence=None
    )

    assert licensee.phone is None
    assert licensee.email is None
    assert len(licensee.trade_classifications) == 0
