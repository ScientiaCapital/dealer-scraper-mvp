"""
Multi-OEM Dealer Network Scraper Framework

Supports scraping installer/dealer networks across multiple OEM brands:
- HVAC Systems: Carrier, Trane, Lennox, York, Rheem, Mitsubishi
- Generators: Briggs & Stratton, Cummins, Kohler
- Solar Inverters: Fronius, SMA, Sol-Ark, GoodWe, Growatt, Sungrow, ABB, Delta, Tigo, SolarEdge
- Battery Storage: SimpliPhi
- Future: Generac, Tesla, Enphase (need conversion to unified framework)

Used for Coperniq's partner prospecting system to identify
multi-brand contractors who need brand-agnostic monitoring.
"""

from scrapers.base_scraper import BaseDealerScraper, DealerCapabilities
from scrapers.scraper_factory import ScraperFactory

# Auto-import all OEM scrapers to self-register with factory
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
from scrapers import abb_scraper
from scrapers import delta_scraper
from scrapers import goodwe_scraper
from scrapers import growatt_scraper
from scrapers import sungrow_scraper
from scrapers import tigo_scraper
from scrapers import solaredge_scraper

__all__ = [
    "BaseDealerScraper",
    "DealerCapabilities",
    "ScraperFactory",
]
