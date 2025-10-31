from abc import ABC, abstractmethod
from typing import List
from .models import ScraperMode, StandardizedLicensee

class BaseLicenseScraper(ABC):
    """
    Abstract base class for all state license scrapers.

    Similar to BaseDealerScraper for OEM scrapers.
    Each state tier (Bulk, API, Playwright) extends this base.
    """

    def __init__(self, mode: ScraperMode):
        """
        Initialize scraper with execution mode.

        Args:
            mode: PLAYWRIGHT (local), RUNPOD (cloud), or BROWSERBASE (managed)
        """
        self.mode = mode

    @abstractmethod
    def scrape_licenses(self, license_types: List[str]) -> List[StandardizedLicensee]:
        """
        Scrape licenses for specified types.

        Args:
            license_types: List of license types to scrape
                          (e.g., ["Electrical", "HVAC", "LowVoltage"])

        Returns:
            List of StandardizedLicensee objects
        """
        pass

    @abstractmethod
    def get_state_code(self) -> str:
        """
        Return two-letter state code.

        Returns:
            State code (e.g., "CA", "TX", "FL")
        """
        pass
