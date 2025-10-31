from typing import Dict, Type, List
from .base_license_scraper import BaseLicenseScraper
from .bulk_download_scraper import BulkDownloadScraper
from .models import ScraperMode, StandardizedLicensee
from config.state_license_configs import STATE_CONFIGS

# ==================== Concrete State Scrapers ====================

class CaliforniaScraper(BulkDownloadScraper):
    """California CSLB scraper"""
    def get_state_code(self) -> str:
        return "CA"

    def get_download_url(self) -> str:
        return STATE_CONFIGS["CA"]["download_url"]

    def parse_file(self, file_path: str) -> List[StandardizedLicensee]:
        """
        Parse California CSLB CSV file.

        TODO: Implement CSV parsing with pandas
        - Expected columns: License Number, Business Name, License Type, Status, etc.
        - Map to StandardizedLicensee fields
        - Filter by license_types from config (C-10, C-7, C-20)
        """
        # Placeholder until we implement CSV parsing
        return []


class FloridaScraper(BulkDownloadScraper):
    """Florida MyFloridaLicense scraper"""
    def get_state_code(self) -> str:
        return "FL"

    def get_download_url(self) -> str:
        return STATE_CONFIGS["FL"]["download_url"]

    def parse_file(self, file_path: str) -> List[StandardizedLicensee]:
        """
        Parse Florida MyFloridaLicense CSV file.

        TODO: Implement CSV parsing with pandas
        - Expected columns: License Number, Name, License Type, Status, etc.
        - Map to StandardizedLicensee fields
        - Filter by license_types from config (ER, EL, CAC)
        """
        # Placeholder until we implement CSV parsing
        return []


class TexasScraper(BulkDownloadScraper):
    """Texas TDLR scraper"""
    def get_state_code(self) -> str:
        return "TX"

    def get_download_url(self) -> str:
        return STATE_CONFIGS["TX"]["download_url"]

    def parse_file(self, file_path: str) -> List[StandardizedLicensee]:
        """
        Parse Texas TDLR Excel file.

        TODO: Implement Excel parsing with openpyxl
        - Expected columns: License Number, Business Name, License Type, Status, etc.
        - Map to StandardizedLicensee fields
        - Filter by license_types from config (Electrical, Low Voltage, Air Conditioning)
        """
        # Placeholder until we implement Excel parsing
        return []


# ==================== Factory ====================

class LicenseScraperFactory:
    """
    Factory for creating state-specific license scrapers.

    Currently supports Tier 1 (BULK) states:
    - CA: California CSLB
    - FL: Florida MyFloridaLicense
    - TX: Texas TDLR

    Future: Will support Tier 2 (API) and Tier 3 (SCRAPER) states
    """

    _scrapers: Dict[str, Type[BaseLicenseScraper]] = {
        "CA": CaliforniaScraper,
        "FL": FloridaScraper,
        "TX": TexasScraper,
    }

    @classmethod
    def create(cls, state_code: str, mode: ScraperMode) -> BaseLicenseScraper:
        """
        Create scraper for given state.

        Args:
            state_code: Two-letter state code (e.g., "CA", "FL", "TX")
            mode: Execution mode (PLAYWRIGHT, RUNPOD, BROWSERBASE)

        Returns:
            State-specific scraper instance

        Raises:
            ValueError: If state not supported yet

        Example:
            >>> factory = LicenseScraperFactory()
            >>> scraper = factory.create("CA", ScraperMode.PLAYWRIGHT)
            >>> licenses = scraper.scrape_licenses(["Electrical", "HVAC"])
        """
        if state_code not in cls._scrapers:
            supported = ", ".join(cls.get_supported_states())
            raise ValueError(
                f"No scraper available for state: {state_code}. "
                f"Supported states: {supported}"
            )

        scraper_class = cls._scrapers[state_code]
        return scraper_class(mode=mode)

    @classmethod
    def get_supported_states(cls) -> List[str]:
        """
        Return list of supported state codes.

        Returns:
            List of two-letter state codes (e.g., ["CA", "FL", "TX"])
        """
        return list(cls._scrapers.keys())

    @classmethod
    def register(cls, state_code: str, scraper_class: Type[BaseLicenseScraper]) -> None:
        """
        Register a new state scraper (for future extensibility).

        Args:
            state_code: Two-letter state code
            scraper_class: Scraper class implementing BaseLicenseScraper

        Example:
            >>> class MassachusettsScraper(ApiLicenseScraper):
            ...     pass
            >>> LicenseScraperFactory.register("MA", MassachusettsScraper)
        """
        cls._scrapers[state_code] = scraper_class
