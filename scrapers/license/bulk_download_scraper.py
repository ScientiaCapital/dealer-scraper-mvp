from abc import abstractmethod
from typing import List
import requests
from pathlib import Path
from .base_license_scraper import BaseLicenseScraper
from .models import StandardizedLicensee

class BulkDownloadScraper(BaseLicenseScraper):
    """
    Base class for Tier 1 states with bulk download portals.

    States: CA, FL, TX
    """

    @abstractmethod
    def get_download_url(self) -> str:
        """Return the CSV/Excel download URL"""
        pass

    @abstractmethod
    def parse_file(self, file_path: str) -> List[StandardizedLicensee]:
        """Parse downloaded file into StandardizedLicensee objects"""
        pass

    def download_file(self, output_dir: str = "output/state_licenses") -> str:
        """
        Download file from state portal.

        Returns:
            Path to downloaded file
        """
        url = self.get_download_url()
        state_code = self.get_state_code()

        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Determine file extension
        ext = ".csv" if url.endswith(".csv") else ".xlsx"
        output_path = f"{output_dir}/{state_code}_licenses{ext}"

        # Download file
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            f.write(response.content)

        return output_path

    def scrape_licenses(self, license_types: List[str]) -> List[StandardizedLicensee]:
        """
        Download and parse state license file.

        Args:
            license_types: Filter to these license types (e.g., ["Electrical", "HVAC"])

        Returns:
            List of StandardizedLicensee objects
        """
        # Download file
        file_path = self.download_file()

        # Parse file
        all_licensees = self.parse_file(file_path)

        # Filter to requested license types
        if license_types:
            filtered = [l for l in all_licensees if l.license_type in license_types]
            return filtered

        return all_licensees
