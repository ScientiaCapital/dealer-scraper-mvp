"""
Multi-OEM Dealer Network Scraper Framework

Supports scraping installer/dealer networks across multiple OEM brands:
- Generac (generators) - PRODUCTION READY ✅
- Tesla Powerwall (batteries + solar) - PRODUCTION READY ✅
- Enphase (microinverters + batteries) - PRODUCTION READY ✅
- Briggs & Stratton (generators + battery storage) - PRODUCTION READY
- Cummins (generators) - PRODUCTION READY ✅
- Kohler (generators) - NEEDS DOM INSPECTION
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
from scrapers import tesla_scraper
from scrapers import enphase_scraper
from scrapers import briggs_scraper
from scrapers import cummins_scraper
from scrapers import kohler_scraper
from scrapers import fronius_scraper
from scrapers import solark_scraper
from scrapers import simpliphi_scraper
from scrapers import mitsubishi_scraper
from scrapers import sma_scraper
from scrapers import lennox_scraper
from scrapers import carrier_scraper
from scrapers import rheem_scraper
from scrapers import trane_scraper
from scrapers import york_scraper

__all__ = [
    "BaseDealerScraper",
    "DealerCapabilities",
    "ScraperFactory",
]
