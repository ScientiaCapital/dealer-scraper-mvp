#!/usr/bin/env python3
"""
Navien Tankless/Boiler Dealer Scraper

Scrapes the Navien installer locator to find plumbing/HVAC contractors.
Target URL: https://www.navieninc.com/installers

Business Context:
- Navien is a leading tankless water heater and boiler manufacturer
- Products: Tankless water heaters, condensing boilers, combi-boilers
- HIGH ICP VALUE: Navien installers need Plumbing + HVAC trades
- Hydronic heating = complex multi-trade work

Dealer Locator Structure:
- ZIP/radius search for installers
- Separate section for distributors
- Shows installer contact info and specialties
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


class NavienScraper(BaseDealerScraper):
    """Scraper for Navien installer network."""

    OEM_NAME = "Navien"
    DEALER_LOCATOR_URL = "https://www.navieninc.com/installers"
    PRODUCT_LINES = [
        "Tankless Water Heaters",
        "Condensing Boilers",
        "Combi-Boilers",
        "Hydro-Furnaces",
        "Commercial Water Heaters",
    ]

    def get_base_url(self) -> str:
        """Return the base URL for Navien installer locator."""
        return self.DEALER_LOCATOR_URL

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "Navien"

    def supports_zip_search(self) -> bool:
        """Navien installer locator supports ZIP code search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for Navien installers.

        Extracts installer cards with name, phone, address, specialties.
        """
        return r"""
() => {
    const dealers = [];
    const seen = new Set();

    // Find installer listings
    const containers = document.querySelectorAll(
        '[class*="installer"], [class*="dealer"], [class*="result"], ' +
        '[class*="listing"], [class*="card"], article, li'
    );

    // Also search by content structure
    const allElements = document.querySelectorAll('div, li, article, section');
    const installerElements = [];

    allElements.forEach(el => {
        const text = el.textContent;
        const hasPhone = text.match(/\(\d{3}\)\s*\d{3}[-.]\d{4}/) ||
                         el.querySelector('a[href^="tel:"]');
        const hasAddress = text.match(/[A-Z]{2}\s*\d{5}/) ||
                           text.match(/,\s*[A-Z]{2}\s*$/m);

        if (hasPhone && hasAddress && text.length > 50 && text.length < 1500) {
            installerElements.push(el);
        }
    });

    const targetElements = installerElements.length > 0 ?
        installerElements.sort((a, b) => a.textContent.length - b.textContent.length).slice(0, 50) :
        Array.from(containers);

    targetElements.forEach(el => {
        const text = el.textContent;

        // Extract name
        const nameEl = el.querySelector('h2, h3, h4, h5, strong, [class*="name"], [class*="title"], [class*="company"]');
        let name = nameEl ? nameEl.textContent.trim() : '';
        name = name.replace(/\s+/g, ' ').trim();

        if (!name || name.length < 3 || name.length > 100) return;
        if (/^(navien|phone|address|find|search|installer|service)/i.test(name)) return;

        // Extract phone
        let phone = '';
        const phoneLink = el.querySelector('a[href^="tel:"]');
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

        // Extract certifications and specialties
        const certifications = [];
        let tier = 'Installer';

        if (/certified/i.test(text)) certifications.push('Navien Certified');
        if (/authorized/i.test(text)) certifications.push('Authorized Installer');
        if (/service\s*specialist/i.test(text)) {
            certifications.push('Service Specialist');
            tier = 'Service Specialist';
        }

        // Products
        if (/tankless/i.test(text)) certifications.push('Tankless');
        if (/boiler/i.test(text)) certifications.push('Boiler');
        if (/combi/i.test(text)) certifications.push('Combi-Boiler');
        if (/hydro.?furnace/i.test(text)) certifications.push('Hydro-Furnace');
        if (/commercial/i.test(text)) certifications.push('Commercial');

        // Extract website
        let website = '', domain = '';
        const links = el.querySelectorAll('a[href^="http"]');
        for (const link of links) {
            const href = link.href;
            if (href.includes('navien') || href.includes('google.com')) continue;
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
            tier: tier
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
                    tier=data.get("tier", "Installer"),
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
        Detect multi-trade capabilities from Navien installer data.

        Navien installers are HIGH VALUE because:
        - Tankless = Plumbing trade
        - Boilers/Hydro-Furnace = HVAC trade
        - Many do both = multi-trade contractors
        """
        caps = DealerCapabilities()
        caps.plumbing = True  # All Navien installers do plumbing

        certs = " ".join(dealer.certifications).lower()
        name_lower = dealer.name.lower()

        # Boiler/HVAC work
        if any(kw in certs for kw in ["boiler", "hydro-furnace", "heating"]):
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
        if "hvac" in name_lower or "heating" in name_lower:
            caps.hvac = True
            caps.multi_trade_score += 1

        # Service Specialist tier bonus
        if dealer.tier == "Service Specialist":
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
                print(f"\n🔍 Scraping Navien installers for ZIP: {zip_code}")

                page.goto(self.DEALER_LOCATOR_URL, timeout=30000)
                time.sleep(2)

                # Find and fill ZIP input
                zip_input = page.locator(
                    'input[type="text"], input[name*="zip"], '
                    'input[placeholder*="zip"], input[id*="zip"]'
                ).first

                if zip_input.count() > 0:
                    zip_input.fill(zip_code)
                    time.sleep(0.5)

                    # Submit search
                    search_btn = page.locator(
                        'button:has-text("Find"), button:has-text("Search"), '
                        'button[type="submit"], input[type="submit"], '
                        'input[value*="Find"], input[value*="Search"]'
                    ).first

                    if search_btn.count() > 0:
                        search_btn.click()
                    else:
                        zip_input.press("Enter")

                    time.sleep(3)

                    # Extract installers
                    raw_data = page.evaluate(self.get_extraction_script())

                    if raw_data:
                        dealers = self.parse_dealer_data(raw_data)
                        print(f"  ✓ Found {len(dealers)} installers")
                    else:
                        print("  ✗ No installers found")
                else:
                    print("  ✗ Could not find ZIP input")

            except Exception as e:
                print(f"  ✗ Error: {e}")

            finally:
                browser.close()

        return dealers


# Register with factory
ScraperFactory.register("navien", NavienScraper)
ScraperFactory.register("Navien", NavienScraper)
