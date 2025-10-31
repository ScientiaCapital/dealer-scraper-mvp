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

        Expected columns: License Number, Business Name, License Type, License Status,
                         Issue Date, Expiration Date, Business Address, City, State,
                         ZIP Code, County, Business Phone, Email
        """
        import pandas as pd

        # License type mapping: CA codes -> StandardizedLicensee types
        LICENSE_TYPE_MAP = {
            "C-10": "Electrical",
            "C-7": "LowVoltage",
            "C-20": "HVAC"
        }

        # Read CSV
        df = pd.read_csv(file_path)

        licensees = []
        for _, row in df.iterrows():
            # Map license type
            ca_license_type = row.get("License Type", "")
            license_type = LICENSE_TYPE_MAP.get(ca_license_type, ca_license_type)

            # Parse dates
            issue_date = None
            if pd.notna(row.get("Issue Date")):
                try:
                    issue_date = pd.to_datetime(row["Issue Date"]).date()
                except:
                    pass

            expiration_date = None
            if pd.notna(row.get("Expiration Date")):
                try:
                    expiration_date = pd.to_datetime(row["Expiration Date"]).date()
                except:
                    pass

            # Handle optional fields
            email = row.get("Email")
            if pd.isna(email) or email == "":
                email = None

            phone = row.get("Business Phone")
            if pd.isna(phone):
                phone = None

            # Create StandardizedLicensee
            licensee = StandardizedLicensee(
                licensee_name=row.get("Business Name", ""),
                license_number=str(row.get("License Number", "")),
                license_type=license_type,
                license_status=row.get("License Status", ""),
                city=row.get("City", ""),
                state=row.get("State", "CA"),
                zip=str(row.get("ZIP Code", "")),
                source_state="CA",
                source_tier="BULK",
                business_name=row.get("Business Name", ""),
                issue_date=issue_date,
                expiration_date=expiration_date,
                phone=phone,
                email=email,
                street=row.get("Business Address"),
                county=row.get("County")
            )

            licensees.append(licensee)

        return licensees


class FloridaScraper(BulkDownloadScraper):
    """Florida MyFloridaLicense scraper"""
    def get_state_code(self) -> str:
        return "FL"

    def get_download_url(self) -> str:
        return STATE_CONFIGS["FL"]["download_url"]

    def parse_file(self, file_path: str) -> List[StandardizedLicensee]:
        """
        Parse Florida MyFloridaLicense CSV file.

        Expected columns: License Number, Name, License Type, Primary Status,
                         Original License Date, Expiration Date, Address Line 1,
                         City, State, Zip Code, County, Phone, Email
        """
        import pandas as pd

        # License type mapping: FL codes -> StandardizedLicensee types
        LICENSE_TYPE_MAP = {
            "ER": "Electrical",
            "EL": "LowVoltage",
            "CAC": "HVAC"
        }

        # Read CSV
        df = pd.read_csv(file_path)

        licensees = []
        for _, row in df.iterrows():
            # Map license type
            fl_license_type = row.get("License Type", "")
            license_type = LICENSE_TYPE_MAP.get(fl_license_type, fl_license_type)

            # Parse dates
            original_issue_date = None
            if pd.notna(row.get("Original License Date")):
                try:
                    original_issue_date = pd.to_datetime(row["Original License Date"]).date()
                except:
                    pass

            expiration_date = None
            if pd.notna(row.get("Expiration Date")):
                try:
                    expiration_date = pd.to_datetime(row["Expiration Date"]).date()
                except:
                    pass

            # Handle optional fields
            email = row.get("Email")
            if pd.isna(email) or email == "":
                email = None

            phone = row.get("Phone")
            if pd.isna(phone):
                phone = None

            # Create StandardizedLicensee
            licensee = StandardizedLicensee(
                licensee_name=row.get("Name", ""),
                license_number=str(row.get("License Number", "")),
                license_type=license_type,
                license_status=row.get("Primary Status", ""),
                city=row.get("City", ""),
                state=row.get("State", "FL"),
                zip=str(row.get("Zip Code", "")),
                source_state="FL",
                source_tier="BULK",
                business_name=row.get("Name", ""),
                original_issue_date=original_issue_date,
                expiration_date=expiration_date,
                phone=phone,
                email=email,
                street=row.get("Address Line 1"),
                county=row.get("County")
            )

            licensees.append(licensee)

        return licensees


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
