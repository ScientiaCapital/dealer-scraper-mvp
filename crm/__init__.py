"""
CRM Integration Modules

Imports enriched contractor data into CRM systems for sales outreach.

Modules:
- close_importer: Close CRM API client for bulk lead import and Smart View creation
"""

from crm.close_importer import CloseImporter

__all__ = [
    "CloseImporter",
]
