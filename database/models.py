"""
Data Models for Pipeline Database

Dataclasses that mirror the SQLite schema, plus helper methods for
normalization and matching.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Set
import re
from difflib import SequenceMatcher


# Common webmail domains to exclude from domain matching
WEBMAIL_DOMAINS = frozenset({
    'gmail.com', 'yahoo.com', 'hotmail.com', 'aol.com',
    'outlook.com', 'icloud.com', 'comcast.net', 'att.net',
    'bellsouth.net', 'verizon.net', 'msn.com', 'live.com',
    'me.com', 'mac.com', 'sbcglobal.net', 'cox.net',
    'earthlink.net', 'charter.net', 'optonline.net'
})

# FL License Type to Category Mapping
FL_LICENSE_CATEGORIES = {
    "CAC": "HVAC",      # Class A Air Conditioning
    "CMC": "HVAC",      # Certified Mechanical Contractor
    "CPC": "PLUMBING",  # Certified Plumbing Contractor
    "CFC": "FIRE",      # Certified Fire Contractor
    "FRO": "ROOFING",   # Florida Registered Roofing
    "CCC": "ROOFING",   # Certified Roofing Contractor
    "CGC": "GENERAL",   # Certified General Contractor
    "CBC": "BUILDING",  # Certified Building Contractor
    "CUC": "UTILITY",   # Certified Utility Contractor
    "SCC": "SPECIALTY", # Specialty Contractor
    "EC":  "ELECTRICAL",# Electrical Contractor
    "ER":  "ELECTRICAL",# Electrical Registered
}

# CA License Type to Category Mapping
# Note: CA uses both formats (C10 and C-10) - we normalize without hyphen
# EXCLUDED per ICP Framework: A (Engineering), B (General) - not self-performing
CA_LICENSE_CATEGORIES = {
    # Electrical / Solar (primary ICP targets)
    "C10": "ELECTRICAL",
    "C-10": "ELECTRICAL",
    "C46": "SOLAR",
    "C-46": "SOLAR",
    "C-7": "LOW_VOLTAGE",  # Fire alarm, security, data

    # HVAC / Mechanical
    "C20": "HVAC",
    "C-20": "HVAC",
    "C38": "REFRIGERATION",
    "C-38": "REFRIGERATION",
    "C-4": "BOILER",
    "C4": "BOILER",

    # Plumbing / Fire
    "C36": "PLUMBING",
    "C-36": "PLUMBING",
    "C16": "FIRE",
    "C-16": "FIRE",

    # EXCLUDED - Not Coperniq ICP targets:
    # "A": "ENGINEERING"  - Infrastructure/civil (roads, bridges) - no asset mgmt
    # "B": "GENERAL"      - GCs who sub out MEP work - not self-performing

    # Other relevant
    "HAZ": "HAZMAT",
    "ASB": "ASBESTOS",
}

# TX License Type to Category Mapping (TDLR)
# EXCLUDED per ICP Framework: Journeyman Electrician (employees, not owners)
TX_LICENSE_CATEGORIES = {
    # HVAC / A-C (highest count in TX)
    "A/C Contractor": "HVAC",
    "A/C Technician": "HVAC",

    # Electrical (self-performing contractors and master electricians)
    "Electrical Contractor": "ELECTRICAL",
    "Master Electrician": "ELECTRICAL",
    "Residential Wireman": "ELECTRICAL",

    # Appliance (HVAC-adjacent)
    "Appliance Installation Contractor": "APPLIANCE",
    "Appliance Installer": "APPLIANCE",

    # EXCLUDED - Not Coperniq ICP targets:
    # "Journeyman Electrician" - Employees, not business owners/decision-makers
    # "Apprentice Electrician" - Employees in training
}


def normalize_phone(phone: str) -> str:
    """
    Normalize phone to 10 digits.

    Examples:
        '(555) 123-4567' -> '5551234567'
        '+1 555-123-4567' -> '5551234567'
        '1-555-123-4567' -> '5551234567'
    """
    if not phone:
        return ""
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    return digits if len(digits) == 10 else ""


def normalize_email(email: str) -> str:
    """Normalize email to lowercase, stripped."""
    if not email:
        return ""
    return email.lower().strip()


def extract_domain(email: str) -> str:
    """
    Extract domain from email, excluding webmail.

    Returns empty string for webmail domains (gmail, yahoo, etc.)
    since those don't identify a company.
    """
    if not email or '@' not in email:
        return ""
    domain = email.split('@')[1].lower().strip()
    return "" if domain in WEBMAIL_DOMAINS else domain


def normalize_company_name(name: str) -> str:
    """
    Normalize company name for fuzzy matching.

    Removes common suffixes (LLC, Inc, Corp, etc.),
    punctuation, and extra whitespace.
    """
    if not name:
        return ""
    name = name.lower().strip()
    # Remove common suffixes (sorted by length, longest first to avoid partial matches)
    suffixes = [
        ', llc', ', inc.', ', inc', ', corp', ', ltd',  # With comma first
        ' incorporated', ' corporation', ' contracting', ' construction',
        ' contractors', ' enterprises', ' solutions', ' holdings',
        ' associates', ' services', ' systems', ' company', ' limited',
        ' l.l.c.', ' group', ' corp.', ' corp', ' inc.', ' inc',
        ' ltd.', ' ltd', ' llc', ' co.', ' co',  # Short suffixes last
    ]
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    # Remove punctuation
    name = re.sub(r'[^\w\s]', '', name)
    # Collapse whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def fuzzy_match_ratio(name1: str, name2: str) -> float:
    """
    Calculate fuzzy match ratio between two company names.

    Uses normalized names and SequenceMatcher.
    Returns 0.0-1.0 ratio.
    """
    n1 = normalize_company_name(name1)
    n2 = normalize_company_name(name2)
    if not n1 or not n2:
        return 0.0
    return SequenceMatcher(None, n1, n2).ratio()


@dataclass
class Contractor:
    """
    Master contractor record (deduplicated).

    This is the canonical record for a company, merged from
    potentially many source records.
    """
    id: Optional[int] = None
    company_name: str = ""
    normalized_name: str = ""
    street: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""
    primary_phone: str = ""
    primary_email: str = ""
    primary_domain: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Transient fields (not stored in DB directly)
    contacts: List['Contact'] = field(default_factory=list)
    licenses: List['License'] = field(default_factory=list)
    oem_certifications: List['OEMCertification'] = field(default_factory=list)

    def __post_init__(self):
        """Auto-compute normalized fields."""
        if self.company_name and not self.normalized_name:
            self.normalized_name = normalize_company_name(self.company_name)
        if self.primary_phone:
            self.primary_phone = normalize_phone(self.primary_phone)
        if self.primary_email:
            self.primary_email = normalize_email(self.primary_email)
            if not self.primary_domain:
                self.primary_domain = extract_domain(self.primary_email)

    @property
    def category_count(self) -> int:
        """Count unique license categories."""
        return len(set(lic.license_category for lic in self.licenses if lic.license_category))

    @property
    def is_multi_license(self) -> bool:
        """True if contractor has 2+ license categories."""
        return self.category_count >= 2

    @property
    def is_unicorn(self) -> bool:
        """True if contractor has 3+ license categories (highest ICP)."""
        return self.category_count >= 3

    @property
    def categories(self) -> Set[str]:
        """Unique license categories."""
        return set(lic.license_category for lic in self.licenses if lic.license_category)

    @property
    def has_email(self) -> bool:
        """True if contractor has any email."""
        return bool(self.primary_email) or any(c.email for c in self.contacts)

    def to_dict(self) -> dict:
        """Convert to dictionary for CSV export."""
        return {
            'id': self.id,
            'company_name': self.company_name,
            'city': self.city,
            'state': self.state,
            'zip': self.zip,
            'primary_phone': self.primary_phone,
            'primary_email': self.primary_email,
            'categories': '|'.join(sorted(self.categories)),
            'category_count': self.category_count,
            'is_unicorn': self.is_unicorn,
        }


@dataclass
class Contact:
    """
    Contact information for a contractor.

    A contractor can have multiple contacts (owner, manager, etc.)
    from different sources (state license, SPW, Hunter, Apollo).
    """
    id: Optional[int] = None
    contractor_id: Optional[int] = None
    name: str = ""
    email: str = ""
    phone: str = ""
    title: str = ""
    source: str = ""  # 'FL_License', 'SPW', 'Hunter', 'Apollo'
    confidence: int = 50
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """Normalize fields."""
        if self.email:
            self.email = normalize_email(self.email)
        if self.phone:
            self.phone = normalize_phone(self.phone)


@dataclass
class License:
    """
    State license record for a contractor.

    A contractor can hold multiple licenses in multiple states.
    Multi-license contractors (2+ categories) are highest ICP value.
    """
    id: Optional[int] = None
    contractor_id: Optional[int] = None
    state: str = ""
    license_type: str = ""      # 'CAC', 'CPC', 'C-10', etc.
    license_category: str = ""  # 'HVAC', 'PLUMBING', etc.
    license_number: str = ""
    license_status: str = "active"
    source_file: str = ""
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """Auto-map license type to category if not provided."""
        if self.license_type and not self.license_category:
            lt = self.license_type.upper().strip()
            if self.state == 'FL':
                self.license_category = FL_LICENSE_CATEGORIES.get(lt, "")
            elif self.state == 'CA':
                self.license_category = CA_LICENSE_CATEGORIES.get(lt, "")


@dataclass
class OEMCertification:
    """
    OEM certification from dealer locator scraping.

    Links a contractor to their OEM certifications
    (Generac, Tesla, Enphase, etc.)
    """
    id: Optional[int] = None
    contractor_id: Optional[int] = None
    oem_name: str = ""
    certification_tier: str = ""
    scraped_from_zip: str = ""
    source_url: str = ""
    created_at: Optional[datetime] = None


@dataclass
class PipelineRun:
    """
    Pipeline run history for auditing.

    Tracks each ingestion run: what was loaded, how many records,
    how many duplicates, timing, errors.
    """
    id: Optional[int] = None
    state: str = ""
    source_file: str = ""
    records_input: int = 0
    records_new: int = 0
    records_merged: int = 0
    multi_license_found: int = 0
    unicorns_found: int = 0
    run_timestamp: Optional[datetime] = None
    run_duration_seconds: float = 0.0
    status: str = "in_progress"
    error_message: str = ""


@dataclass
class DedupMatch:
    """
    Deduplication match record for debugging.

    Tracks WHY two records were considered duplicates:
    - 'phone': Same normalized phone number
    - 'email': Same email address
    - 'domain': Same company domain (not webmail)
    - 'fuzzy_name': 85%+ name similarity + same state
    """
    id: Optional[int] = None
    master_contractor_id: int = 0
    duplicate_record_hash: str = ""
    match_type: str = ""  # 'phone', 'email', 'domain', 'fuzzy_name'
    match_value: str = ""
    match_confidence: float = 1.0
    source_file: str = ""
    created_at: Optional[datetime] = None


@dataclass
class SPWRanking:
    """
    Solar Power World ranking entry.

    Links SPW list entries to contractors after matching.
    """
    id: Optional[int] = None
    contractor_id: Optional[int] = None
    company_name: str = ""
    list_name: str = ""  # 'Top Commercial', 'Top Residential', 'Top EPCs'
    rank_position: int = 0
    kw_installed: int = 0
    year: int = 2024
    headquarters_state: str = ""
    created_at: Optional[datetime] = None
