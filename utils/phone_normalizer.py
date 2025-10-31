"""
Phone number normalization for cross-reference matching.

Normalizes US phone numbers to 10-digit strings (area code + number).
Based on successful OEM deduplication pattern (96.5% accuracy).
"""
import re
from typing import Optional


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    """
    Normalize phone number to 10-digit string.

    Args:
        phone: Raw phone number in any format

    Returns:
        10-digit string or None if invalid

    Examples:
        >>> normalize_phone("+1-323-555-1234")
        "3235551234"
        >>> normalize_phone("(323) 555-1234")
        "3235551234"
        >>> normalize_phone("invalid")
        None
    """
    if not phone:
        return None

    # Convert to string and strip whitespace
    phone = str(phone).strip()

    # Remove extensions (ext, x, followed by digits)
    phone = re.sub(r'\s*(ext|x)\s*\d+', '', phone, flags=re.IGNORECASE)

    # Extract only digits
    digits = re.sub(r'\D', '', phone)

    # Handle US country code (1 + 10 digits)
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]

    # Validate 10-digit US number
    if len(digits) != 10:
        return None

    return digits
