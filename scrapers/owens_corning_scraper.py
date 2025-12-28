#!/usr/bin/env python3
"""
Owens Corning Roofing Contractor Scraper

Scrapes the Owens Corning contractor locator to find certified roofing contractors.
Target URL: https://www.owenscorning.com/en-us/roofing/contractors

Business Context:
- Owens Corning is a major roofing materials manufacturer
- Products: Duration, TruDefinition, Oakridge shingles
- HIGH ICP VALUE: Roofing contractors often do solar installations too
- Contractor tiers: Preferred → Platinum Preferred (highest)

Dealer Locator Structure:
- Geolocation-based or ZIP search
- Contractor cards with ratings, reviews
- Shows phone, email, website links
- Filter by contractor type
"""

import re
import time
from typing import List, Dict, Any, Optional

from scrapers.base_scraper import (
    BaseDealerScraper,
    StandardizedDealer,
    DealerCapabilities,
    ScraperMode,
)
from scrapers.scraper_factory import ScraperFactory


class OwensCorningScrap(BaseDealerScraper):
    """Scraper for Owens Corning certified roofing contractor network."""

    OEM_NAME = "Owens Corning"
    DEALER_LOCATOR_URL = "https://www.owenscorning.com/en-us/roofing/contractors"
    PRODUCT_LINES = [
        "Duration Shingles",
        "TruDefinition Duration",
        "Oakridge Shingles",
        "Supreme Shingles",
        "Roofing Accessories",
    ]

    def get_base_url(self) -> str:
        """Return the base URL for Owens Corning contractor locator."""
        return self.DEALER_LOCATOR_URL

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "Owens Corning"

    def supports_zip_search(self) -> bool:
        """Owens Corning uses geolocation or ZIP search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for Owens Corning contractors.

        Extracts contractor cards with name, phone, address, ratings, tier.
        """
        return r"""
() => {
    const dealers = [];
    const seen = new Set();

    // Find contractor listings - they show as cards with phone and location
    const allDivs = document.querySelectorAll('div, article, section');
    const contractorDivs = [];

    allDivs.forEach(div => {
        const text = div.textContent;
        // Look for patterns with phone numbers and locations
        const hasPhone = text.match(/\(\d{3}\)\s*\d{3}[-.]?\d{4}/);
        const hasLocation = text.match(/[A-Za-z\s]+,\s*[A-Z]{2}/);

        if (hasPhone && hasLocation && text.length > 50 && text.length < 600) {
            contractorDivs.push(div);
        }
    });

    // Sort by size to get most specific containers
    const targetDivs = contractorDivs
        .sort((a, b) => a.textContent.length - b.textContent.length)
        .slice(0, 100);

    targetDivs.forEach(div => {
        const text = div.textContent;

        // Extract name - usually heading element
        const nameEl = div.querySelector('h3, h4, h5, strong, [class*="name"], [class*="title"]');
        let name = nameEl ? nameEl.textContent.trim() : '';

        // Clean up name - remove location/phone that might be attached
        name = name.replace(/[A-Za-z\s]+,\s*[A-Z]{2}.*$/, '').trim();
        name = name.replace(/\(\d{3}\).*$/, '').trim();
        name = name.replace(/\s+/g, ' ').trim();

        if (!name || name.length < 3 || name.length > 100) return;
        if (/^(phone|address|email|filters|roofers|independent)/i.test(name)) return;

        // Extract phone
        let phone = '';
        const phoneLink = div.querySelector('a[href^="tel:"]');
        if (phoneLink) {
            phone = phoneLink.href.replace('tel:', '').replace(/[^0-9]/g, '');
        } else {
            const phoneMatch = text.match(/\((\d{3})\)\s*(\d{3})[-.]?(\d{4})/);
            if (phoneMatch) {
                phone = phoneMatch[1] + phoneMatch[2] + phoneMatch[3];
            }
        }

        if (phone.length === 11 && phone.startsWith('1')) {
            phone = phone.substring(1);
        }

        if (!phone || phone.length !== 10) return;
        if (seen.has(phone)) return;
        seen.add(phone);

        // Extract location
        let city = '', state = '';
        const locationMatch = text.match(/([A-Za-z\s]+),\s*([A-Z]{2})/);
        if (locationMatch) {
            city = locationMatch[1].trim();
            state = locationMatch[2];
        }

        // Extract rating and reviews
        let rating = 0, reviewCount = 0;
        const ratingMatch = text.match(/★\s*([\d.]+)\s*(\d+)\s*reviews?/i);
        if (ratingMatch) {
            rating = parseFloat(ratingMatch[1]);
            reviewCount = parseInt(ratingMatch[2]);
        } else {
            // Try alternate pattern
            const altRating = text.match(/([\d.]+)\s*(\d+)\s*reviews?/i);
            if (altRating) {
                rating = parseFloat(altRating[1]);
                reviewCount = parseInt(altRating[2]);
            }
        }

        // Extract certification tier
        const certifications = [];
        let tier = 'Preferred';

        if (/Platinum\s*Preferred/i.test(text)) {
            certifications.push('Owens Corning Platinum Preferred');
            tier = 'Platinum Preferred';
        } else if (/Preferred/i.test(text)) {
            certifications.push('Owens Corning Preferred');
        }

        // Extract website
        let website = '', domain = '';
        const websiteLink = div.querySelector('a[href^="http"]');
        if (websiteLink) {
            const href = websiteLink.href;
            if (!href.includes('owenscorning.com') && !href.includes('google.com')) {
                website = href;
                try { domain = new URL(website).hostname.replace(/^www\./, ''); } catch(e) {}
            }
        }

        // Check for email
        let email = '';
        const emailLink = div.querySelector('a[href^="mailto:"]');
        if (emailLink) {
            email = emailLink.href.replace('mailto:', '');
        }

        dealers.push({
            name: name,
            phone: phone,
            address: '',
            city: city,
            state: state,
            zip_code: '',
            website: website,
            domain: domain,
            email: email,
            certifications: [...new Set(certifications)],
            tier: tier,
            rating: rating,
            review_count: reviewCount
        });
    });

    return dealers;
}
"""

    def parse_dealer_data(self, raw_data: List[Dict]) -> List[StandardizedDealer]:
        """Convert raw extraction data to StandardizedDealer format."""
        dealers = []

        for data in raw_data:
            try:
                if not data.get("name") or not data.get("phone"):
                    continue

                dealer = StandardizedDealer(
                    name=data.get("name", ""),
                    phone=self._normalize_phone(data.get("phone", "")),
                    address=data.get("address", ""),
                    city=data.get("city", ""),
                    state=data.get("state", ""),
                    zip_code=data.get("zip_code", ""),
                    website=data.get("website", ""),
                    domain=data.get("domain", ""),
                    oem_certified=True,
                    oem_name=self.OEM_NAME,
                    certifications=data.get("certifications", []),
                    tier=data.get("tier", "Preferred"),
                    source_url=self.DEALER_LOCATOR_URL,
                    raw_data=data,
                )
                dealers.append(dealer)

            except Exception as e:
                print(f"  Warning: Error parsing contractor: {e}")
                continue

        return dealers

    def detect_capabilities(self, dealer: StandardizedDealer) -> DealerCapabilities:
        """
        Detect multi-trade capabilities from Owens Corning contractor data.

        Roofing contractors are valuable because:
        - Many also do solar roof installations
        - Platinum Preferred = highest tier, established contractors
        """
        caps = DealerCapabilities()
        caps.roofing = True  # All OC contractors do roofing
        caps.multi_trade_score = 1  # Base score

        certs = " ".join(dealer.certifications).lower()
        name_lower = dealer.name.lower()

        # Tier bonuses
        if dealer.tier == "Platinum Preferred":
            caps.multi_trade_score += 2

        # Check name for multi-trade signals
        if "solar" in name_lower:
            caps.solar = True
            caps.multi_trade_score += 2
        if "construction" in name_lower or "renovation" in name_lower:
            caps.multi_trade_score += 1
        if "hvac" in name_lower or "heating" in name_lower:
            caps.hvac = True
            caps.multi_trade_score += 1
        if "electric" in name_lower:
            caps.electrical = True
            caps.multi_trade_score += 1
        if "plumb" in name_lower:
            caps.plumbing = True
            caps.multi_trade_score += 1
        if "waterproof" in name_lower:
            caps.multi_trade_score += 1

        # High ratings bonus
        raw_data = dealer.raw_data or {}
        if raw_data.get("rating", 0) >= 4.5 and raw_data.get("review_count", 0) >= 50:
            caps.multi_trade_score += 1

        return caps

    def _scrape_with_playwright(self, zip_code: str = None) -> List[StandardizedDealer]:
        """PLAYWRIGHT mode: Local browser automation for testing."""
        from playwright.sync_api import sync_playwright

        dealers = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                geolocation={"latitude": 37.3382, "longitude": -121.8863},  # San Jose
                permissions=["geolocation"],
            )
            page = context.new_page()

            try:
                print(f"\n🔍 Scraping Owens Corning contractors")
                if zip_code:
                    print(f"    ZIP: {zip_code}")

                page.goto(self.DEALER_LOCATOR_URL, timeout=30000)
                time.sleep(3)

                # The page loads contractors based on geolocation
                # Scroll to load more results
                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1)

                # Extract contractors
                raw_data = page.evaluate(self.get_extraction_script())

                if raw_data:
                    dealers = self.parse_dealer_data(raw_data)
                    print(f"  ✓ Found {len(dealers)} contractors")
                else:
                    print("  ✗ No contractors found")

            except Exception as e:
                print(f"  ✗ Error: {e}")

            finally:
                browser.close()

        return dealers


# Register with factory
ScraperFactory.register("owens_corning", OwensCorningScrap)
ScraperFactory.register("OwensCorning", OwensCorningScrap)
ScraperFactory.register("owenscorning", OwensCorningScrap)
