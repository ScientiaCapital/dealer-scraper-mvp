"""
Domain extraction for cross-reference matching.

Extracts and normalizes domains from URLs and website strings.
"""
import re
from typing import Optional
from urllib.parse import urlparse


def extract_domain(url: Optional[str]) -> Optional[str]:
    """
    Extract domain from URL or website string.

    Removes protocol, www prefix, and paths. Preserves non-www subdomains.
    Normalizes to lowercase.

    Args:
        url: URL or website string

    Returns:
        Normalized domain or None if invalid

    Examples:
        >>> extract_domain("https://www.example.com/about")
        "example.com"
        >>> extract_domain("shop.example.com")
        "shop.example.com"
    """
    if not url:
        return None

    url = str(url).strip().lower()

    # Add protocol if missing (for urlparse)
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url

    # Parse URL
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0]
    except:
        return None

    if not domain or '.' not in domain:
        return None

    # Remove www prefix
    if domain.startswith('www.'):
        domain = domain[4:]

    return domain
