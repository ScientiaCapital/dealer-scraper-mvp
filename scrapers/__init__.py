"""
Multi-OEM Dealer Network Scraper Framework

Supports scraping installer/dealer networks across multiple OEM brands:
- HVAC Systems: Carrier, Trane, Lennox, York, Rheem, Mitsubishi
- Generators: Generac, Briggs & Stratton, Cummins, Kohler
- Solar Inverters: Tesla, Enphase, Fronius, SMA, Sol-Ark, SolarEdge, GoodWe, Growatt, Sungrow, ABB, Delta, Tigo
- Battery Storage: Tesla Powerwall, SimpliPhi

Used for Coperniq's partner prospecting system to identify
multi-brand contractors who need brand-agnostic monitoring.
"""

from scrapers.base_scraper import BaseDealerScraper, DealerCapabilities
from scrapers.scraper_factory import ScraperFactory

# Auto-import all OEM scrapers to self-register with factory
from scrapers import tesla_scraper
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
from scrapers import generac_scraper
from scrapers import enphase_scraper
from scrapers import honeywell_scraper
from scrapers import johnson_controls_scraper
from scrapers import schneider_scraper
from scrapers import sensi_scraper

__all__ = [
    "BaseDealerScraper",
    "DealerCapabilities",
    "ScraperFactory",
]
