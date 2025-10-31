"""
Shared pytest fixtures and configuration for dealer-scraper-mvp tests
"""
import pytest
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
TEST_ZIP_CODES = {
    "generac": "53202",  # Milwaukee
    "tesla": "94102",    # San Francisco
    "enphase": "94102",  # San Francisco
    "briggs": "02101",   # Boston
    "cummins": "77002",  # Houston
    "mitsubishi": "10001",  # New York
    "carrier": "10001",
    "trane": "10001",
    "york": "10001",
    "lennox": "10001",
    "sma": "10001",
}


@pytest.fixture
def sample_dealer_data():
    """Sample dealer data for testing"""
    return {
        "name": "Test Dealer",
        "phone": "(555) 123-4567",
        "domain": "testdealer.com",
        "website": "https://www.testdealer.com",
        "street": "123 Main St",
        "city": "San Francisco",
        "state": "CA",
        "zip": "94102",
        "address_full": "123 Main St, San Francisco, CA 94102",
        "rating": 4.5,
        "review_count": 25,
        "tier": "Premier",
        "distance": "2.5 mi",
        "distance_miles": 2.5,
        "oem_source": "Generac",
        "scraped_from_zip": "94102",
    }


@pytest.fixture
def sample_multi_oem_dealer():
    """Sample dealer with multiple OEM certifications"""
    return {
        "name": "Multi-OEM Dealer",
        "phone": "(555) 987-6543",
        "domain": "multioem.com",
        "website": "https://www.multioem.com",
        "city": "Houston",
        "state": "TX",
        "zip": "77002",
        "oem_certifications": ["Generac", "Tesla", "Enphase"],
        "has_generator": True,
        "has_solar": True,
        "has_battery": True,
    }


@pytest.fixture
def test_zip_codes():
    """Test ZIP codes for different OEMs"""
    return TEST_ZIP_CODES


@pytest.fixture(scope="session")
def mock_playwright():
    """Mock Playwright browser for testing"""
    # This would be implemented with unittest.mock or pytest-mock
    # For now, return a placeholder
    return None

