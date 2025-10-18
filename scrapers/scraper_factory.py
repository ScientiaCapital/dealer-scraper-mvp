"""
Scraper Factory for Multi-OEM Dealer Networks

Factory pattern to instantiate the correct OEM scraper based on OEM name.
Supports dynamic addition of new OEM scrapers without modifying core code.
"""

from typing import Dict, Type, Optional
from scrapers.base_scraper import BaseDealerScraper, ScraperMode


class ScraperFactory:
    """
    Factory for creating OEM-specific scraper instances.
    
    Usage:
        scraper = ScraperFactory.create("Generac", mode=ScraperMode.RUNPOD)
        dealers = scraper.scrape_zip_code("53202")
    """
    
    # Registry of available OEM scrapers
    _scrapers: Dict[str, Type[BaseDealerScraper]] = {}
    
    @classmethod
    def register(cls, oem_name: str, scraper_class: Type[BaseDealerScraper]) -> None:
        """
        Register a new OEM scraper class.
        
        This allows OEM scrapers to self-register when their modules are imported.
        
        Args:
            oem_name: OEM identifier (e.g., "Generac", "Tesla", "Enphase")
            scraper_class: Scraper class that inherits from BaseDealerScraper
        """
        cls._scrapers[oem_name.lower()] = scraper_class
    
    @classmethod
    def create(cls, oem_name: str, mode: ScraperMode = ScraperMode.PLAYWRIGHT) -> BaseDealerScraper:
        """
        Create an instance of the requested OEM scraper.
        
        Args:
            oem_name: OEM identifier (case-insensitive)
            mode: ScraperMode enum (PLAYWRIGHT, RUNPOD, BROWSERBASE)
        
        Returns:
            Instantiated scraper object
        
        Raises:
            ValueError: If OEM scraper not found in registry
        """
        oem_key = oem_name.lower()
        
        if oem_key not in cls._scrapers:
            available = ", ".join(cls._scrapers.keys())
            raise ValueError(
                f"No scraper registered for OEM '{oem_name}'. "
                f"Available scrapers: {available}"
            )
        
        scraper_class = cls._scrapers[oem_key]
        return scraper_class(mode=mode)
    
    @classmethod
    def list_available_oems(cls) -> list:
        """
        Get list of all registered OEM scrapers.
        
        Returns:
            List of OEM names
        """
        return list(cls._scrapers.keys())
    
    @classmethod
    def create_all(cls, mode: ScraperMode = ScraperMode.PLAYWRIGHT) -> Dict[str, BaseDealerScraper]:
        """
        Create instances of all registered OEM scrapers.
        
        Useful for scraping across all OEM networks in a single operation.
        
        Args:
            mode: ScraperMode enum for all scrapers
        
        Returns:
            Dict mapping OEM names to scraper instances
        """
        return {
            oem_name: scraper_class(mode=mode)
            for oem_name, scraper_class in cls._scrapers.items()
        }


# Convenience function for common use case
def get_scraper(oem_name: str, mode: ScraperMode = ScraperMode.PLAYWRIGHT) -> Optional[BaseDealerScraper]:
    """
    Get a scraper instance for the specified OEM.
    
    Args:
        oem_name: OEM identifier (case-insensitive)
        mode: ScraperMode enum
    
    Returns:
        Scraper instance or None if not found
    """
    try:
        return ScraperFactory.create(oem_name, mode=mode)
    except ValueError:
        return None
