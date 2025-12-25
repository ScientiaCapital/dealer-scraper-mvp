"""
Multi-OEM Dealer Network Scraper Framework

Supports scraping installer/dealer networks across multiple OEM brands:
- HVAC Systems: Carrier, Trane, Lennox, York, Rheem, Mitsubishi, Honeywell, Sensi
- Generators: Generac, Briggs & Stratton, Cummins, Kohler
- Solar Inverters: Tesla, Enphase, Fronius, SMA, Sol-Ark, SolarEdge
- Battery Storage: Tesla Powerwall, SimpliPhi
- Building Automation: Schneider Electric (EcoXpert system integrators)

Used for Coperniq's partner prospecting system to identify
multi-brand contractors who need brand-agnostic monitoring.

ARCHIVED (not viable for bulk scraping - see scrapers/_archived/):
- ABB: Divested residential solar 2020
- Delta, GoodWe, Growatt, Sungrow, Tigo: No public ZIP-searchable dealer locator
- Johnson Controls: Returns corporate offices only (not contractor ICPs)
"""

from scrapers.base_scraper import BaseDealerScraper, DealerCapabilities
from scrapers.scraper_factory import ScraperFactory

# Auto-import all OEM scrapers to self-register with factory
# HVAC Systems
from scrapers import carrier_scraper
from scrapers import trane_scraper
from scrapers import lennox_scraper
from scrapers import york_scraper
from scrapers import rheem_scraper
from scrapers import mitsubishi_scraper
from scrapers import honeywell_scraper
from scrapers import sensi_scraper

# Generators
from scrapers import generac_scraper
from scrapers import briggs_scraper
from scrapers import cummins_scraper
from scrapers import kohler_scraper

# Solar Inverters
from scrapers import tesla_scraper
from scrapers import enphase_scraper
from scrapers import fronius_scraper
from scrapers import sma_scraper
from scrapers import solark_scraper
from scrapers import solaredge_scraper

# Battery Storage
from scrapers import simpliphi_scraper

# Building Automation
from scrapers import schneider_scraper

__all__ = [
    "BaseDealerScraper",
    "DealerCapabilities",
    "ScraperFactory",
]
