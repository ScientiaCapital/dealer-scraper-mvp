import pytest
from utils.phone_normalizer import normalize_phone

def test_normalize_removes_country_code():
    """Test US country code removal"""
    assert normalize_phone("+1-323-555-1234") == "3235551234"
    assert normalize_phone("1-323-555-1234") == "3235551234"

def test_normalize_removes_formatting():
    """Test formatting removal"""
    assert normalize_phone("(323) 555-1234") == "3235551234"
    assert normalize_phone("323-555-1234") == "3235551234"
    assert normalize_phone("323.555.1234") == "3235551234"

def test_normalize_handles_extensions():
    """Test extension stripping"""
    assert normalize_phone("323-555-1234 ext 123") == "3235551234"
    assert normalize_phone("323-555-1234x456") == "3235551234"

def test_normalize_handles_invalid():
    """Test invalid phone handling"""
    assert normalize_phone("") is None
    assert normalize_phone(None) is None
    assert normalize_phone("abc") is None
    assert normalize_phone("123") is None  # Too short

def test_normalize_returns_10_digits():
    """Test all valid outputs are 10 digits"""
    result = normalize_phone("323-555-1234")
    assert result is not None
    assert len(result) == 10
    assert result.isdigit()
