"""
Dealer Locator Scraper MVP
Supports: Playwright (local) and Browserbase (cloud)
Easily adaptable for other dealer locator sites
"""

import json
import csv
from typing import List, Dict, Optional
from enum import Enum
from pathlib import Path
import time
import requests
from dotenv import load_dotenv


class ScraperMode(Enum):
    PLAYWRIGHT = "playwright"
    RUNPOD = "runpod"
    BROWSERBASE = "browserbase"


class DealerScraper:
    """Base scraper that can use either Playwright or Browserbase"""

    def __init__(self, mode: ScraperMode = ScraperMode.PLAYWRIGHT, config: Optional[Dict] = None):
        # Load environment variables for API keys
        load_dotenv()

        self.mode = mode
        self.config = config or {}
        self.results = []

    def scrape_zip_code(self, zip_code: str) -> List[Dict]:
        """
        Scrape dealers for a single ZIP code
        Supports multiple backend modes: Playwright (MCP), RunPod (cloud), Browserbase
        """
        if self.mode == ScraperMode.PLAYWRIGHT:
            return self._scrape_with_playwright(zip_code)
        elif self.mode == ScraperMode.RUNPOD:
            return self._scrape_with_runpod(zip_code)
        elif self.mode == ScraperMode.BROWSERBASE:
            return self._scrape_with_browserbase(zip_code)

    def _scrape_with_playwright(self, zip_code: str) -> List[Dict]:
        """
        Scrape using MCP Playwright tools
        Manual execution flow:
        1. mcp__playwright__browser_navigate to dealer locator URL
        2. mcp__playwright__browser_click on "Accept Cookies"
        3. mcp__playwright__browser_type to fill ZIP code
        4. mcp__playwright__browser_click on "Search" button
        5. mcp__playwright__browser_wait_for 3 seconds
        6. mcp__playwright__browser_evaluate to extract data
        """
        print(f"[Playwright Mode] Would scrape ZIP: {zip_code}")
        print("Manual MCP tool calls required:")
        print("  1. browser_navigate to https://www.generac.com/dealer-locator/")
        print("  2. browser_click Accept Cookies button")
        print(f"  3. browser_type ZIP code: {zip_code}")
        print("  4. browser_click Search button")
        print("  5. browser_wait_for 3 seconds")
        print("  6. browser_evaluate with extraction.js")
        return []

    def _scrape_with_runpod(self, zip_code: str) -> List[Dict]:
        """
        Scrape using RunPod serverless Playwright API
        Makes HTTP POST request to cloud-hosted browser automation service
        Returns extracted dealer data or empty list on error
        """
        from config import (
            RUNPOD_API_KEY,
            RUNPOD_API_URL,
            DEALER_LOCATOR_URL,
            EXTRACTION_SCRIPT,
            WAIT_AFTER_SEARCH,
        )

        # Validate configuration
        if not RUNPOD_API_KEY or not RUNPOD_API_URL:
            print("[RunPod Error] Missing RUNPOD_API_KEY or RUNPOD_ENDPOINT_ID in .env")
            print("Set these environment variables to use RunPod mode")
            return []

        # Build the 6-step workflow matching MCP Playwright pattern
        workflow = [
            {"action": "navigate", "url": DEALER_LOCATOR_URL},
            {"action": "click", "selector": "button:has-text('Accept Cookies')"},
            {"action": "fill", "selector": "input[name*='zip' i]", "text": zip_code},
            {"action": "click", "selector": "button:has-text('Search')"},
            {"action": "wait", "timeout": WAIT_AFTER_SEARCH * 1000},  # Convert to ms
            {"action": "evaluate", "script": EXTRACTION_SCRIPT},
        ]

        # Prepare request payload
        payload = {"input": {"workflow": workflow}}

        headers = {
            "Authorization": f"Bearer {RUNPOD_API_KEY}",
            "Content-Type": "application/json",
        }

        try:
            print(f"[RunPod] Scraping ZIP {zip_code} via cloud API...")
            response = requests.post(
                RUNPOD_API_URL,
                json=payload,
                headers=headers,
                timeout=60,  # 60 second timeout
            )
            response.raise_for_status()

            result = response.json()

            # Check for RunPod-level errors
            if "error" in result:
                print(f"[RunPod Error] {result['error']}")
                return []

            # Extract dealers from response
            dealers = result.get("results", [])
            print(f"[RunPod] Extracted {len(dealers)} dealers from ZIP {zip_code}")
            return dealers

        except requests.exceptions.Timeout:
            print(f"[RunPod Error] Request timeout after 60 seconds for ZIP {zip_code}")
            return []
        except requests.exceptions.RequestException as e:
            print(f"[RunPod Error] HTTP request failed: {e}")
            return []
        except Exception as e:
            print(f"[RunPod Error] Unexpected error: {e}")
            return []

    def _scrape_with_browserbase(self, zip_code: str) -> List[Dict]:
        """Scrape using Browserbase cloud browser"""
        print(f"[Browserbase Mode] Would scrape ZIP: {zip_code}")
        print("Browserbase integration not yet implemented")
        return []

    def scrape_multiple(self, zip_codes: List[str], delay: int = 3) -> List[Dict]:
        """Scrape multiple ZIP codes with delay between requests"""
        all_dealers = []

        for i, zip_code in enumerate(zip_codes):
            print(f"\n[{i+1}/{len(zip_codes)}] Scraping ZIP: {zip_code}")
            dealers = self.scrape_zip_code(zip_code)
            all_dealers.extend(dealers)

            if i < len(zip_codes) - 1:
                print(f"Waiting {delay} seconds before next ZIP...")
                time.sleep(delay)

        self.results = all_dealers
        return all_dealers

    def deduplicate(self) -> List[Dict]:
        """Remove duplicate dealers based on phone number"""
        seen_phones = set()
        unique_dealers = []

        for dealer in self.results:
            phone = dealer.get('phone', '')
            if phone and phone not in seen_phones:
                seen_phones.add(phone)
                unique_dealers.append(dealer)

        print(f"Deduplicated: {len(self.results)} -> {len(unique_dealers)} dealers")
        self.results = unique_dealers
        return unique_dealers

    def save_json(self, filepath: str = "dealers.json"):
        """Save results to JSON file"""
        path = Path(filepath)
        with path.open('w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(self.results)} dealers to {filepath}")

    def save_csv(self, filepath: str = "dealers.csv"):
        """Save results to CSV file"""
        if not self.results:
            print("No results to save")
            return

        path = Path(filepath)
        fieldnames = [
            'name', 'rating', 'review_count', 'tier', 'is_power_pro_premier',
            'street', 'city', 'state', 'zip', 'address_full',
            'phone', 'website', 'domain', 'distance', 'distance_miles'
        ]

        with path.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)
        print(f"Saved {len(self.results)} dealers to {filepath}")

    def get_top_rated(self, min_reviews: int = 5, limit: int = 10) -> List[Dict]:
        """Get top-rated dealers with minimum review count"""
        filtered = [d for d in self.results if d.get('review_count', 0) >= min_reviews]
        sorted_dealers = sorted(filtered, key=lambda x: x.get('rating', 0), reverse=True)
        return sorted_dealers[:limit]


def main():
    """Example usage"""
    from config import ZIP_CODES_MILWAUKEE, ZIP_CODES_TEST

    # Initialize scraper in Playwright mode
    scraper = DealerScraper(mode=ScraperMode.PLAYWRIGHT)

    # For now, this shows manual workflow
    # In future, integrate with MCP Playwright automation
    print("=== Dealer Scraper MVP ===")
    print(f"Mode: {scraper.mode.value}")
    print(f"\nTest ZIP codes: {ZIP_CODES_TEST}")
    print("\nTo execute manually:")
    print("1. Use MCP Playwright tools to navigate and extract")
    print("2. Save results to dealers.json")
    print("3. Use scraper.save_csv() to export")


if __name__ == "__main__":
    main()
