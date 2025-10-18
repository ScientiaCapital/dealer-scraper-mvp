"""
Multi-OEM Dealer Network Scraper Framework

Supports scraping installer/dealer networks across multiple OEM brands:
- Generac (generators)
- Tesla Powerwall (batteries + solar)
- Enphase (microinverters + batteries)
- Future: SolarEdge, Kohler, Cummins, Carrier, Trane, etc.

Used for Coperniq's partner prospecting system to identify
multi-brand contractors who need brand-agnostic monitoring.
"""

from scrapers.base_scraper import BaseDealerScraper, DealerCapabilities
from scrapers.scraper_factory import ScraperFactory

__all__ = [
    "BaseDealerScraper",
    "DealerCapabilities",
    "ScraperFactory",
]
