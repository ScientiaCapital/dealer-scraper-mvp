#!/usr/bin/env python3
"""
Rinnai Tankless Water Heater Dealer Scraper

Scrapes the Rinnai PRO locator to find plumbing contractors.
Target URL: https://www.rinnai.us/find-pro

Business Context:
- Rinnai is #1 tankless water heater brand in US
- Products: Tankless water heaters, boilers, heating systems
- HIGH ICP VALUE: Tankless installers need Plumbing + Gas trades
- PRO tiers: Rinnai ACE PRO (elite), Rinnai PRO (certified)

Dealer Locator Structure:
- ZIP code input with filters
- Filters: Contractor type, Products, Energy source, Offerings
- Shows PRO type, products served, financing options
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


class RinnaiScraper(BaseDealerScraper):
    """Scraper for Rinnai PRO dealer network."""

    OEM_NAME = "Rinnai"
    DEALER_LOCATOR_URL = "https://www.rinnai.us/find-pro"
    PRODUCT_LINES = [
        "Tankless Water Heaters",
        "Condensing Boilers",
        "Hybrid Water Heaters",
        "Commercial Water Heaters",
        "Wall-Mounted Boilers",
    ]

    def get_base_url(self) -> str:
        """Return the base URL for Rinnai dealer locator."""
        return self.DEALER_LOCATOR_URL

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "Rinnai"

    def supports_zip_search(self) -> bool:
        """Rinnai dealer locator supports ZIP code search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for Rinnai PROs.

        Extracts dealer cards with name, phone, address, PRO type, products.
        """
        return r"""
() => {
    const dealers = [];
    const seen = new Set();

    // Find PRO cards/listings
    const cards = document.querySelectorAll(
        '[class*="pro"], [class*="dealer"], [class*="result"], ' +
        '[class*="listing"], [class*="card"], article, li'
    );

    // Also find by structure
    const allContainers = document.querySelectorAll('div, li, article');
    const dealerContainers = [];

    allContainers.forEach(container => {
        const text = container.textContent;
        const hasPhone = text.match(/\(\d{3}\)\s*\d{3}[-.]\d{4}/) ||
                         container.querySelector('a[href^="tel:"]');
        const hasRinnai = /Rinnai\s*(ACE\s*)?PRO/i.test(text) ||
                          /water\s*heat/i.test(text);

        if (hasPhone && hasRinnai && text.length < 2000 && text.length > 30) {
            dealerContainers.push(container);
        }
    });

    const targetCards = dealerContainers.length > 0 ?
        dealerContainers.sort((a, b) => a.textContent.length - b.textContent.length).slice(0, 50) :
        Array.from(cards);

    targetCards.forEach(card => {
        const text = card.textContent;

        // Extract name
        const nameEl = card.querySelector('h2, h3, h4, h5, strong, [class*="name"], [class*="title"], [class*="company"]');
        let name = nameEl ? nameEl.textContent.trim() : '';
        name = name.replace(/\s+/g, ' ').trim();

        // Skip labels/headers
        if (!name || name.length < 3 || name.length > 100) return;
        if (/^(rinnai|phone|address|find|search|filter|pro type)/i.test(name)) return;

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

        const fullAddr = text.match(/(\d+\s+[A-Za-z0-9\s.]+),\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5})/);
        if (fullAddr) {
            address = fullAddr[1].trim();
            city = fullAddr[2].trim();
            state = fullAddr[3];
            zip_code = fullAddr[4];
        } else {
            const cityStateZip = text.match(/([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5})/);
            if (cityStateZip) {
                city = cityStateZip[1].trim();
                state = cityStateZip[2];
                zip_code = cityStateZip[3];
            }
        }

        // Extract PRO type and certifications
        const certifications = [];
        let tier = 'Rinnai PRO';

        if (/ACE\s*PRO/i.test(text)) {
            certifications.push('Rinnai ACE PRO');
            tier = 'ACE PRO';
        } else if (/Rinnai\s*PRO/i.test(text)) {
            certifications.push('Rinnai PRO');
        }

        // Products offered
        const products = [];
        if (/water\s*heat/i.test(text)) products.push('Water Heating');
        if (/boiler/i.test(text)) products.push('Boiler');
        if (/heat/i.test(text) && !/water/i.test(text)) products.push('Heating');
        if (/commercial/i.test(text)) products.push('Commercial');

        if (products.length > 0) {
            certifications.push(...products);
        }

        // Energy sources
        if (/natural\s*gas/i.test(text)) certifications.push('Natural Gas');
        if (/propane/i.test(text)) certifications.push('Propane');
        if (/electric/i.test(text)) certifications.push('Electric');

        // Special offerings
        if (/financing/i.test(text)) certifications.push('Financing Available');
        if (/showroom/i.test(text)) certifications.push('Has Showroom');
        if (/wi-?fi|monitoring/i.test(text)) certifications.push('Wi-Fi Monitoring');

        // Extract website
        let website = '', domain = '';
        const links = card.querySelectorAll('a[href^="http"]');
        for (const link of links) {
            const href = link.href;
            if (href.includes('rinnai.us') || href.includes('google.com')) continue;
            website = href;
            try { domain = new URL(website).hostname.replace(/^www\./, ''); } catch(e) {}
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
            tier: tier,
            products: products
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
                    tier=data.get("tier", "Rinnai PRO"),
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
        Detect multi-trade capabilities from Rinnai dealer data.

        Tankless water heater installers are HIGH VALUE because:
        - Tankless requires Plumbing + Gas line work
        - Many also do HVAC (boilers, heating)
        """
        caps = DealerCapabilities()
        caps.plumbing = True  # All Rinnai PROs do plumbing

        # Check products and certifications
        certs = " ".join(dealer.certifications).lower()
        name_lower = dealer.name.lower()

        # Gas line work
        if "natural gas" in certs or "propane" in certs or "gas" in name_lower:
            caps.multi_trade_score += 1

        # Boiler/heating = HVAC capability
        if "boiler" in certs or "heating" in certs:
            caps.hvac = True
            caps.multi_trade_score += 1

        # Commercial = larger operation
        if "commercial" in certs:
            caps.multi_trade_score += 1

        # Check name for trade keywords
        if "mechanical" in name_lower:
            caps.hvac = True
            caps.multi_trade_score += 1
        if "electric" in name_lower:
            caps.electrical = True
            caps.multi_trade_score += 1

        # ACE PRO tier bonus
        if dealer.tier == "ACE PRO":
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
                print(f"\n🔍 Scraping Rinnai PROs for ZIP: {zip_code}")

                page.goto(self.DEALER_LOCATOR_URL, timeout=30000)
                time.sleep(2)

                # Find and fill ZIP input
                zip_input = page.locator(
                    'input[type="text"], input[name*="zip"], '
                    'input[placeholder*="zip"], input[placeholder*="ZIP"]'
                ).first

                if zip_input.count() > 0:
                    zip_input.fill(zip_code)
                    time.sleep(0.5)

                    # Submit search
                    search_btn = page.locator(
                        'button:has-text("Find PRO"), button:has-text("Search"), '
                        'button[type="submit"], input[type="submit"]'
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
                        print(f"  ✓ Found {len(dealers)} PROs")
                    else:
                        print("  ✗ No PROs found")
                else:
                    print("  ✗ Could not find ZIP input")

            except Exception as e:
                print(f"  ✗ Error: {e}")

            finally:
                browser.close()

        return dealers


# Register with factory
ScraperFactory.register("rinnai", RinnaiScraper)
ScraperFactory.register("Rinnai", RinnaiScraper)
