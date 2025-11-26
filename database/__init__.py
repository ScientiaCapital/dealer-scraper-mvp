"""
Pipeline Database Module

SQLite-backed contractor data pipeline for multi-state license tracking.

Usage:
    from database import PipelineDB, Contractor, License

    # Initialize database
    db = PipelineDB()
    db.initialize()

    # Add contractor with automatic deduplication
    contractor_id, is_new = db.add_contractor({
        'company_name': 'ABC Solar LLC',
        'email': 'info@abcsolar.com',
        'phone': '555-123-4567',
        'state': 'FL',
        'license_type': 'CAC',
        'license_category': 'HVAC'
    })

    # Get statistics
    stats = db.get_stats(state='FL')
    print(f"Multi-license contractors: {stats['multi_license']}")

    # Export multi-license to CSV
    db.export_multi_license('output/fl_multi_license.csv', state='FL')
"""

from database.pipeline_db import PipelineDB, get_db
from database.models import (
    Contractor,
    Contact,
    License,
    OEMCertification,
    PipelineRun,
    DedupMatch,
    SPWRanking,
    normalize_phone,
    normalize_email,
    extract_domain,
    normalize_company_name,
    fuzzy_match_ratio,
    FL_LICENSE_CATEGORIES,
    CA_LICENSE_CATEGORIES,
    TX_LICENSE_CATEGORIES,
    WEBMAIL_DOMAINS
)
from database.audit import (
    FileFingerprint,
    ImportLock,
    AuditTrail
)

__all__ = [
    # Main database class
    'PipelineDB',
    'get_db',

    # Data models
    'Contractor',
    'Contact',
    'License',
    'OEMCertification',
    'PipelineRun',
    'DedupMatch',
    'SPWRanking',

    # Audit classes
    'FileFingerprint',
    'ImportLock',
    'AuditTrail',

    # Utility functions
    'normalize_phone',
    'normalize_email',
    'extract_domain',
    'normalize_company_name',
    'fuzzy_match_ratio',

    # Constants
    'FL_LICENSE_CATEGORIES',
    'CA_LICENSE_CATEGORIES',
    'TX_LICENSE_CATEGORIES',
    'WEBMAIL_DOMAINS',
]
