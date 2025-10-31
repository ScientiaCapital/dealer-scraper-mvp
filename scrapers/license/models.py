from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List
from enum import Enum

class ScraperMode(Enum):
    """Execution modes for scrapers"""
    PLAYWRIGHT = "playwright"  # Local browser automation
    RUNPOD = "runpod"          # Cloud serverless (pay-per-second)
    BROWSERBASE = "browserbase"  # Cloud managed browsers (residential IPs)

@dataclass
class StandardizedLicensee:
    """
    Standardized contractor license data model.

    Parallel to StandardizedDealer for OEM contractors.
    Keeps license data architecturally separate while enabling cross-reference.
    """
    # Core identity (required)
    licensee_name: str
    license_number: str
    license_type: str  # "C-10 Electrical", "HVAC Contractor", etc.
    license_status: str  # "Active", "Expired", "Suspended", "Revoked"
    city: str
    state: str  # Two-letter code
    zip: str
    source_state: str
    source_tier: str  # "BULK", "API", "SCRAPER"

    # Optional identity fields
    business_name: Optional[str]

    # License metadata (optional dates)
    issue_date: Optional[date]
    expiration_date: Optional[date]
    original_issue_date: Optional[date]  # First licensed (growth signal)

    # Contact information (optional)
    phone: Optional[str]
    email: Optional[str]
    website: Optional[str]

    # Location (optional)
    street: Optional[str]
    county: Optional[str]

    # Business details (optional - rich states only: CA, TX, FL)
    insurance_info: Optional[str] = None
    worker_count: Optional[int] = None
    business_type: Optional[str] = None

    # Lists with defaults
    trade_classifications: List[str] = field(default_factory=list)
    matched_oem_contractors: List[str] = field(default_factory=list)

    # Datetime with default
    scraped_date: datetime = field(default_factory=datetime.now)

    # Optional cross-reference
    match_confidence: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for CSV export"""
        return {
            'licensee_name': self.licensee_name,
            'business_name': self.business_name,
            'license_number': self.license_number,
            'license_type': self.license_type,
            'license_status': self.license_status,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'original_issue_date': self.original_issue_date.isoformat() if self.original_issue_date else None,
            'phone': self.phone,
            'email': self.email,
            'website': self.website,
            'street': self.street,
            'city': self.city,
            'state': self.state,
            'zip': self.zip,
            'county': self.county,
            'trade_classifications': '|'.join(self.trade_classifications),
            'insurance_info': self.insurance_info,
            'worker_count': self.worker_count,
            'business_type': self.business_type,
            'source_state': self.source_state,
            'source_tier': self.source_tier,
            'scraped_date': self.scraped_date.isoformat(),
            'matched_oem_contractors': '|'.join(self.matched_oem_contractors),
            'match_confidence': self.match_confidence
        }
