#!/usr/bin/env python3
"""
WaterFurnace Geothermal Dealer Scraper

Scrapes the WaterFurnace dealer locator to find geothermal contractors.
Target URL: https://www.waterfurnace.com/residential/dealer-locator/

Business Context:
- WaterFurnace is the leading geothermal heat pump manufacturer
- Products: Geothermal heat pumps, ground source systems
- HIGH ICP VALUE: Geothermal installers need HVAC + Plumbing + Electrical
- GeoPro dealers are premium tier (5+ years experience, certified)

Dealer Locator Structure:
- City/State or ZIP code input
- Map-based results with dealer cards
- Shows distance, address, ratings
- "Retrieve more dealers" button for expanded results
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


class WaterFurnaceScraper(BaseDealerScraper):
    """Scraper for WaterFurnace geothermal dealer network."""

    OEM_NAME = "WaterFurnace"
    DEALER_LOCATOR_URL = "https://www.waterfurnace.com/residential/dealer-locator/"
    PRODUCT_LINES = [
        "Geothermal Heat Pumps",
        "Ground Source Heat Pumps",
        "Water Source Heat Pumps",
        "Hybrid Systems",
    ]

    def get_base_url(self) -> str:
        """Return the base URL for WaterFurnace dealer locator."""
        return self.DEALER_LOCATOR_URL

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "WaterFurnace"

    def supports_zip_search(self) -> bool:
        """WaterFurnace dealer locator supports ZIP code search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for WaterFurnace dealers.

        Extracts dealer cards with name, phone, address, ratings, GeoPro status.
        """
        return r"""
() => {
    const dealers = [];
    const seen = new Set();

    // Find dealer cards in the dealer list
    const cards = document.querySelectorAll(
        '#dealerList .card, [class*="dealer"], [class*="result"], ' +
        '[class*="listing"], .card, article'
    );

    // Also look for structured containers with dealer info
    const allContainers = document.querySelectorAll('div, li, article');
    const dealerContainers = [];

    allContainers.forEach(container => {
        const text = container.textContent;
        const hasPhone = text.match(/\(\d{3}\)\s*\d{3}[-.]\d{4}/) ||
                         container.querySelector('a[href^="tel:"]');
        const hasAddress = text.match(/\d+\s+[A-Za-z].*,\s*[A-Z]{2}\s*\d{5}/);

        if (hasPhone && hasAddress && text.length < 1500 && text.length > 50) {
            dealerContainers.push(container);
        }
    });

    const targetCards = dealerContainers.length > 0 ?
        dealerContainers.sort((a, b) => a.textContent.length - b.textContent.length).slice(0, 50) :
        Array.from(cards);

    targetCards.forEach(card => {
        const text = card.textContent;

        // Extract name - usually first heading or strong text
        const nameEl = card.querySelector('h2, h3, h4, h5, strong, [class*="name"], [class*="title"]');
        let name = nameEl ? nameEl.textContent.trim() : '';
        name = name.replace(/\s+/g, ' ').trim();

        if (!name || name.length < 3 || name.length > 100) return;
        if (/^(phone|address|email|dealer|view|select|contact)/i.test(name)) return;

        // Extract phone
        let phone = '';
        const phoneLink = card.querySelector('a[href^="tel:"]');
        if (phoneLink) {
            phone = phoneLink.href.replace('tel:', '').replace(/[^0-9]/g, '');
        } else {
            const phoneMatch = text.match(/\(?(\d{3})\)?[.\s-]*(\d{3})[.\s-]*(\d{4})/);
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

        // Extract address
        let address = '', city = '', state = '', zip_code = '';

        // Full address pattern: 123 Main St, City, ST 12345
        const fullAddr = text.match(/(\d+\s+[A-Za-z0-9\s.]+),\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5})/);
        if (fullAddr) {
            address = fullAddr[1].trim();
            city = fullAddr[2].trim();
            state = fullAddr[3];
            zip_code = fullAddr[4];
        } else {
            // Just city, state, zip
            const cityStateZip = text.match(/([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5})/);
            if (cityStateZip) {
                city = cityStateZip[1].trim();
                state = cityStateZip[2];
                zip_code = cityStateZip[3];
            }
        }

        // Extract GeoPro status and certifications
        const certifications = [];
        let tier = 'Dealer';

        if (/GeoPro/i.test(text)) {
            certifications.push('GeoPro');
            tier = 'GeoPro';
        }
        if (/5.?star/i.test(text) || /★★★★★/.test(text)) {
            certifications.push('5-Star');
            tier = 'GeoPro 5-Star';
        }
        if (/authorized/i.test(text)) certifications.push('Authorized Dealer');
        if (/certified/i.test(text)) certifications.push('Certified');

        // Extract rating if present
        let rating = 0;
        const stars = card.querySelectorAll('.stars, [class*="star"], [class*="rating"]');
        if (stars.length > 0) {
            // Count filled stars or parse rating number
            const starText = stars[0].textContent || stars[0].getAttribute('aria-label') || '';
            const ratingMatch = starText.match(/(\d+\.?\d*)/);
            if (ratingMatch) {
                rating = parseFloat(ratingMatch[1]);
            }
        }

        // Extract website
        let website = '', domain = '';
        const links = card.querySelectorAll('a[href^="http"]');
        for (const link of links) {
            const href = link.href;
            if (href.includes('waterfurnace.com') || href.includes('google.com')) continue;
            if (href.includes('maps') || href.includes('direction')) continue;
            website = href;
            try { domain = new URL(website).hostname.replace(/^www\./, ''); } catch(e) {}
            break;
        }

        // Extract distance if shown
        let distance = '';
        const distMatch = text.match(/(\d+\.?\d*)\s*(miles?|mi)/i);
        if (distMatch) {
            distance = distMatch[1] + ' miles';
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
            certifications: certifications,
            tier: tier,
            rating: rating,
            distance: distance
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
                    tier=data.get("tier", "Dealer"),
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
        Detect multi-trade capabilities from WaterFurnace dealer data.

        Geothermal contractors are EXTREMELY HIGH VALUE because:
        - Geothermal requires HVAC + Plumbing + Electrical
        - Ground loop installation = heavy equipment/excavation
        - These are true multi-trade contractors
        """
        caps = DealerCapabilities()

        # ALL geothermal installers need these trades
        caps.hvac = True
        caps.plumbing = True  # Ground loop piping
        caps.electrical = True  # Heat pump electrical
        caps.multi_trade_score = 3  # Base score for geothermal

        # Check name for additional signals
        name_lower = dealer.name.lower()

        if "mechanical" in name_lower:
            caps.multi_trade_score += 1
        if "solar" in name_lower or "energy" in name_lower:
            caps.solar = True
            caps.multi_trade_score += 1
        if "generator" in name_lower:
            caps.generators = True
            caps.multi_trade_score += 1

        # GeoPro tier bonus
        if dealer.tier in ["GeoPro", "GeoPro 5-Star"]:
            caps.multi_trade_score += 1

        return caps

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """PLAYWRIGHT mode: Local browser automation for testing."""
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
                print(f"\n🔍 Scraping WaterFurnace dealers for ZIP: {zip_code}")

                page.goto(self.DEALER_LOCATOR_URL, timeout=30000)
                time.sleep(2)

                # Find and fill search input (city/state or ZIP)
                search_input = page.locator(
                    'input[type="text"], input[type="search"], '
                    'input[placeholder*="zip"], input[placeholder*="city"], '
                    'input[id*="search"], input[name*="search"]'
                ).first

                if search_input.count() > 0:
                    search_input.fill(zip_code)
                    time.sleep(0.5)

                    # Submit search
                    search_btn = page.locator(
                        'button[type="submit"], button:has-text("Search"), '
                        'button:has-text("Find"), input[type="submit"]'
                    ).first

                    if search_btn.count() > 0:
                        search_btn.click()
                    else:
                        search_input.press("Enter")

                    time.sleep(3)

                    # Try clicking "Retrieve more dealers" if available
                    try:
                        more_btn = page.locator('button:has-text("Retrieve more"), button:has-text("Load more")').first
                        if more_btn.count() > 0:
                            more_btn.click()
                            time.sleep(2)
                    except:
                        pass

                    # Extract dealers
                    raw_data = page.evaluate(self.get_extraction_script())

                    if raw_data:
                        dealers = self.parse_dealer_data(raw_data)
                        print(f"  ✓ Found {len(dealers)} dealers")
                    else:
                        print("  ✗ No dealers found")
                else:
                    print("  ✗ Could not find search input")

            except Exception as e:
                print(f"  ✗ Error: {e}")

            finally:
                browser.close()

        return dealers


# Register with factory
ScraperFactory.register("waterfurnace", WaterFurnaceScraper)
ScraperFactory.register("WaterFurnace", WaterFurnaceScraper)
