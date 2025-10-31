import pytest
from utils.domain_extractor import extract_domain

def test_extract_removes_www():
    """Test www prefix removal"""
    assert extract_domain("www.example.com") == "example.com"
    assert extract_domain("www.subdomain.example.com") == "subdomain.example.com"

def test_extract_removes_protocol():
    """Test protocol removal"""
    assert extract_domain("https://example.com") == "example.com"
    assert extract_domain("http://www.example.com") == "example.com"
    assert extract_domain("https://www.example.com/path") == "example.com"

def test_extract_removes_path():
    """Test path removal"""
    assert extract_domain("example.com/about") == "example.com"
    assert extract_domain("example.com/about/team") == "example.com"

def test_extract_keeps_subdomain():
    """Test subdomain preservation"""
    assert extract_domain("shop.example.com") == "shop.example.com"
    assert extract_domain("blog.shop.example.com") == "blog.shop.example.com"

def test_extract_handles_invalid():
    """Test invalid domain handling"""
    assert extract_domain("") is None
    assert extract_domain(None) is None
    assert extract_domain("not a domain") is None

def test_extract_lowercases():
    """Test case normalization"""
    assert extract_domain("EXAMPLE.COM") == "example.com"
    assert extract_domain("Example.COM") == "example.com"
