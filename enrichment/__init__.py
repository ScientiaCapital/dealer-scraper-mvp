"""
Contractor Enrichment Modules

Enhances contractor data with company and contact information from third-party APIs.
Used to improve lead scoring and enable personalized outreach.

Modules:
- apollo_enricher: Apollo.io API client for company data (employees, revenue, contacts, LinkedIn)
- clay_enricher: Clay.com webhook integration for waterfall enrichment
"""

from enrichment.apollo_enricher import ApolloEnricher
from enrichment.clay_enricher import ClayEnricher

__all__ = [
    "ApolloEnricher",
    "ClayEnricher",
]
