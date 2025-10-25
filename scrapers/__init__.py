"""
Multi-OEM Dealer Network Scraper Framework

Supports scraping installer/dealer networks across multiple OEM brands:
- Generac (generators) - PRODUCTION READY
- Briggs & Stratton (generators + battery storage) - PRODUCTION READY
- Cummins (generators) - NEEDS DOM INSPECTION
- Kohler (generators) - NEEDS DOM INSPECTION
- Tesla Powerwall (batteries + solar) - STRUCTURE READY
- Enphase (microinverters + batteries) - STRUCTURE READY
- Fronius (string inverters + hybrid systems) - PRODUCTION READY
- Sol-Ark (hybrid inverters + battery storage) - PRODUCTION READY
- SimpliPhi (LFP batteries + energy storage) - PRODUCTION READY
- Future: SolarEdge, Carrier, Trane, etc.

Used for Coperniq's partner prospecting system to identify
multi-brand contractors who need brand-agnostic monitoring.
"""

from scrapers.base_scraper import BaseDealerScraper, DealerCapabilities
from scrapers.scraper_factory import ScraperFactory

# Auto-import all OEM scrapers to self-register with factory
from scrapers import generac_scraper
from scrapers import briggs_scraper
from scrapers import cummins_scraper
from scrapers import kohler_scraper
from scrapers import fronius_scraper
from scrapers import solark_scraper
from scrapers import simpliphi_scraper

__all__ = [
    "BaseDealerScraper",
    "DealerCapabilities",
    "ScraperFactory",
]
