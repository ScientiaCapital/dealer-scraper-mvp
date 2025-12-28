#!/usr/bin/env python3
"""
Daikin HVAC Dealer Scraper

Scrapes the Daikin Comfort dealer locator to find HVAC contractors.
Target URL: https://daikincomfort.com/find-dealer/locator

Business Context:
- Daikin is the world's largest HVAC manufacturer (acquired Goodman in 2012)
- Products: Heat pumps, mini-splits, VRV systems, air handlers
- HIGH ICP VALUE: Mini-split installers need HVAC + Electrical trades
- Contractor tiers: Daikin Comfort Pro, Design Pro (Ductless), Design Pro (VRV)

Dealer Locator Structure:
- ZIP code input field
- Contractor cards with name, phone, certifications
- Filters by contractor type (Comfort Pro, Design Pro)
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


class DaikinScraper(BaseDealerScraper):
    """Scraper for Daikin HVAC dealer network."""

    OEM_NAME = "Daikin"
    DEALER_LOCATOR_URL = "https://daikincomfort.com/find-dealer/locator"
    PRODUCT_LINES = [
        "Heat Pumps",
        "Mini-Splits",
        "Ductless Systems",
        "VRV Systems",
        "Air Handlers",
        "Air Conditioners",
        "Furnaces",
    ]

    def get_base_url(self) -> str:
        """Return the base URL for Daikin dealer locator."""
        return self.DEALER_LOCATOR_URL

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "Daikin"

    def supports_zip_search(self) -> bool:
        """Daikin dealer locator supports ZIP code search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for Daikin dealers.

        Extracts contractor cards with name, phone, address, certifications.
        """
        return r"""
() => {
    const dealers = [];

    // Find all contractor/dealer cards
    // Daikin uses card-based layout with contractor info
    const cards = document.querySelectorAll(
        '[class*="dealer"], [class*="contractor"], [class*="result"], ' +
        '[class*="card"], [class*="listing"], article'
    );

    // Also try finding by content structure
    const allContainers = document.querySelectorAll('div, article, section');
    const dealerContainers = [];

    allContainers.forEach(container => {
        const hasPhone = container.querySelector('a[href^="tel:"]') ||
                         container.textContent.match(/\(\d{3}\)\s*\d{3}[-.]\d{4}/);
        const hasName = container.querySelector('h2, h3, h4, h5, strong, [class*="name"], [class*="title"]');

        // Must have both phone and name, and be reasonably sized
        if (hasPhone && hasName && container.textContent.length < 2000) {
            dealerContainers.push(container);
        }
    });

    // Use the smaller containers (more specific)
    const targetCards = dealerContainers.length > 0 ?
        dealerContainers.sort((a, b) => a.textContent.length - b.textContent.length).slice(0, 50) :
        Array.from(cards);

    const seen = new Set();

    targetCards.forEach(card => {
        const text = card.textContent;

        // Extract name from heading
        const nameEl = card.querySelector('h2, h3, h4, h5, strong, [class*="name"], [class*="title"]');
        let name = nameEl ? nameEl.textContent.trim() : '';

        // Clean up name - remove extra whitespace
        name = name.replace(/\s+/g, ' ').trim();

        if (!name || name.length < 3 || name.length > 100) return;

        // Skip if name looks like a label or header
        if (/^(phone|address|email|contact|dealer|contractor|select)/i.test(name)) return;

        // Extract phone
        let phone = '';
        const phoneLink = card.querySelector('a[href^="tel:"]');
        if (phoneLink) {
            phone = phoneLink.href.replace('tel:', '').replace(/[^0-9]/g, '');
        } else {
            // Try regex in text
            const phoneMatch = text.match(/\(?(\d{3})\)?[.\s-]*(\d{3})[.\s-]*(\d{4})/);
            if (phoneMatch) {
                phone = phoneMatch[1] + phoneMatch[2] + phoneMatch[3];
            }
        }

        // Normalize phone
        if (phone.length === 11 && phone.startsWith('1')) {
            phone = phone.substring(1);
        }

        if (!phone || phone.length !== 10) return;

        // Skip duplicates
        if (seen.has(phone)) return;
        seen.add(phone);

        // Extract address components
        let city = '', state = '', zip_code = '', address = '';

        // Look for address patterns
        const addressEl = card.querySelector('[class*="address"], address, [class*="location"]');
        const addressText = addressEl ? addressEl.textContent : text;

        // City, ST ZIP pattern
        const cityStateZip = addressText.match(/([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5})/);
        if (cityStateZip) {
            city = cityStateZip[1].trim();
            state = cityStateZip[2];
            zip_code = cityStateZip[3];
        } else {
            // Just City, ST
            const cityState = addressText.match(/([A-Za-z\s]+),\s*([A-Z]{2})/);
            if (cityState) {
                city = cityState[1].trim();
                state = cityState[2];
            }
        }

        // Street address
        const streetMatch = addressText.match(/(\d+\s+[A-Za-z0-9\s.]+(?:St|Ave|Blvd|Rd|Dr|Ln|Way|Ct|Pkwy|Hwy)[^,]*)/i);
        if (streetMatch) {
            address = streetMatch[1].trim();
        }

        // Extract certifications
        const certifications = [];
        const certPatterns = [
            /Daikin Comfort Pro/i,
            /Design Pro/i,
            /Ductless/i,
            /VRV/i,
            /Experience Center/i,
            /Authorized/i,
            /Certified/i,
        ];

        certPatterns.forEach(pattern => {
            const match = text.match(pattern);
            if (match) {
                certifications.push(match[0]);
            }
        });

        // Also check img alt text
        card.querySelectorAll('img[alt]').forEach(img => {
            const alt = img.alt.trim();
            if (alt && alt.length > 2 && alt.length < 50) {
                if (/pro|certified|authorized|daikin/i.test(alt)) {
                    certifications.push(alt);
                }
            }
        });

        // Extract website
        let website = '', domain = '';
        const links = card.querySelectorAll('a[href^="http"]');
        for (const link of links) {
            const href = link.href;
            if (href.includes('daikin') || href.includes('google.com')) continue;
            if (link.textContent.includes('Review') || link.textContent.includes('Direction')) continue;

            website = href;
            try {
                domain = new URL(website).hostname.replace(/^www\./, '');
            } catch(e) {}
            break;
        }

        dealers.push({
            name: name,
            phone: phone,
            address: address,
            city: city,
            state: state,
            zip_code: zip_code,
            website: website,
            domain: domain,
            certifications: [...new Set(certifications)],
            tier: certifications.some(c => /Design Pro|VRV/i.test(c)) ? 'Premier' :
                  certifications.some(c => /Comfort Pro/i.test(c)) ? 'Comfort Pro' : 'Authorized'
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
                # Skip invalid entries
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
                    tier=data.get("tier", "Authorized"),
                    source_url=self.DEALER_LOCATOR_URL,
                    raw_data=data,
                )
                dealers.append(dealer)

            except Exception as e:
                print(f"  ⚠️ Error parsing dealer: {e}")
                continue

        return dealers

    def detect_capabilities(self, dealer: StandardizedDealer) -> DealerCapabilities:
        """
        Detect multi-trade capabilities from Daikin dealer data.

        Daikin mini-split installers are HIGH VALUE because:
        - Mini-splits require HVAC + Electrical expertise
        - VRV systems require advanced training
        """
        caps = DealerCapabilities()
        caps.hvac = True  # All Daikin dealers do HVAC

        # Check for electrical capability signals
        name_lower = dealer.name.lower()
        certs = [c.lower() for c in dealer.certifications]
        cert_text = " ".join(certs)

        # Mini-split/ductless = likely electrical capability
        if any(
            kw in cert_text or kw in name_lower
            for kw in ["ductless", "mini-split", "mini split", "vrv", "vrf"]
        ):
            caps.electrical = True
            caps.multi_trade_score += 2

        # Check name for trade keywords
        if any(
            kw in name_lower
            for kw in ["electric", "mechanical", "plumb", "solar", "energy"]
        ):
            if "electric" in name_lower:
                caps.electrical = True
                caps.multi_trade_score += 1
            if "plumb" in name_lower:
                caps.plumbing = True
                caps.multi_trade_score += 1
            if "solar" in name_lower or "energy" in name_lower:
                caps.solar = True
                caps.multi_trade_score += 1

        # Tier bonuses
        if dealer.tier == "Premier" or "Design Pro" in cert_text:
            caps.multi_trade_score += 1

        return caps

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Local browser automation for testing.
        """
        from playwright.sync_api import sync_playwright

        dealers = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            )
            page = context.new_page()

            try:
                print(f"\n🔍 Scraping Daikin dealers for ZIP: {zip_code}")

                # Navigate to dealer locator
                page.goto(self.DEALER_LOCATOR_URL, timeout=30000)
                time.sleep(2)

                # Find and fill ZIP input
                zip_input = page.locator(
                    'input[type="text"], input[name*="zip"], input[placeholder*="zip"], '
                    'input[id*="zip"], input[aria-label*="zip"]'
                ).first

                if zip_input.count() > 0:
                    zip_input.fill(zip_code)
                    time.sleep(0.5)

                    # Try to submit - look for search button or press Enter
                    search_btn = page.locator(
                        'button[type="submit"], button:has-text("Search"), '
                        'button:has-text("Find"), input[type="submit"]'
                    ).first

                    if search_btn.count() > 0:
                        search_btn.click()
                    else:
                        zip_input.press("Enter")

                    time.sleep(3)

                    # Extract dealers
                    raw_data = page.evaluate(self.get_extraction_script())

                    if raw_data:
                        dealers = self.parse_dealer_data(raw_data)
                        print(f"  ✓ Found {len(dealers)} dealers")
                    else:
                        print("  ✗ No dealers found")

                else:
                    print("  ✗ Could not find ZIP input field")

            except Exception as e:
                print(f"  ✗ Error: {e}")

            finally:
                browser.close()

        return dealers


# Register with factory
ScraperFactory.register("daikin", DaikinScraper)
ScraperFactory.register("Daikin", DaikinScraper)
