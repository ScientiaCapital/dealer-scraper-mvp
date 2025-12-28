#!/usr/bin/env python3
"""
Sonnen Battery Storage Dealer Scraper

Scrapes the Sonnen installer directory to find solar/battery contractors.
Target URL: https://www.sonnenusa.com/find-installer

Business Context:
- Sonnen is a premium German battery storage manufacturer
- Products: sonnenCore, sonnenBatterie, sonnenConnect
- HIGH ICP VALUE: Battery installers need Electrical + Solar trades
- Flagship tier = premier partners, Select = certified

Dealer Locator Structure:
- Static directory organized by state
- Flagship Installers section (premium partners)
- Select Partners by state with contact info
- Shows specialties (solar, sonnenConnect, etc.)
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


class SonnenScraper(BaseDealerScraper):
    """Scraper for Sonnen battery installer network."""

    OEM_NAME = "Sonnen"
    DEALER_LOCATOR_URL = "https://www.sonnenusa.com/find-installer"
    PRODUCT_LINES = [
        "sonnenCore",
        "sonnenBatterie",
        "sonnenConnect",
        "Battery Storage",
        "Solar Integration",
    ]

    def get_base_url(self) -> str:
        """Return the base URL for Sonnen installer directory."""
        return self.DEALER_LOCATOR_URL

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "Sonnen"

    def supports_zip_search(self) -> bool:
        """Sonnen uses a static directory, not ZIP search."""
        return False

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for Sonnen installers.

        Extracts installer cards with name, phone, address, website, tier.
        """
        return r"""
() => {
    const dealers = [];
    const seen = new Set();

    // Track which section we're in
    let currentSection = 'Select';
    let currentState = '';

    // Find all sections and installer entries
    const allElements = document.querySelectorAll('h2, h3, h4, h5, div, article, section, li');

    // Look for structured installer data
    const containers = document.querySelectorAll('div, article, li, section');
    const installerContainers = [];

    containers.forEach(container => {
        const text = container.textContent;
        const hasPhone = text.match(/\(\d{3}\)\s*\d{3}[-.]?\d{4}/) ||
                         container.querySelector('a[href^="tel:"]');
        const hasAddress = text.match(/[A-Z]{2}\s*\d{5}/) ||
                           text.match(/,\s*[A-Z]{2}\s*$/m);

        // Must have phone and reasonable size
        if (hasPhone && text.length > 30 && text.length < 1500) {
            installerContainers.push(container);
        }
    });

    // Sort by size to get most specific containers
    const targetContainers = installerContainers
        .sort((a, b) => a.textContent.length - b.textContent.length)
        .slice(0, 100);

    // Check for Flagship section
    const pageText = document.body.textContent;
    const isFlagship = (el) => {
        let parent = el;
        for (let i = 0; i < 10; i++) {
            if (!parent) break;
            if (/flagship/i.test(parent.textContent) && parent.textContent.length < 3000) {
                return true;
            }
            parent = parent.parentElement;
        }
        return false;
    };

    // Detect state from nearby headings
    const getState = (el) => {
        let parent = el;
        for (let i = 0; i < 10; i++) {
            if (!parent) break;
            // Look for state headings
            const headings = parent.querySelectorAll('h2, h3, h4');
            for (const h of headings) {
                const states = ['California', 'Texas', 'Nevada', 'Idaho', 'Massachusetts',
                               'Rhode Island', 'Utah', 'Puerto Rico', 'Arizona', 'Florida',
                               'Colorado', 'New York', 'Hawaii'];
                for (const state of states) {
                    if (h.textContent.includes(state)) {
                        return state;
                    }
                }
            }
            parent = parent.parentElement;
        }
        return '';
    };

    targetContainers.forEach(container => {
        const text = container.textContent;

        // Extract name - usually first strong text or heading
        const nameEl = container.querySelector('h3, h4, h5, strong, [class*="name"], [class*="title"], [class*="company"]');
        let name = nameEl ? nameEl.textContent.trim() : '';
        name = name.replace(/\s+/g, ' ').trim();

        if (!name || name.length < 3 || name.length > 100) return;
        if (/^(phone|address|email|find|search|installer|partner)/i.test(name)) return;

        // Extract phone
        let phone = '';
        const phoneLink = container.querySelector('a[href^="tel:"]');
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

        // Determine tier
        const certifications = [];
        let tier = 'Select Partner';

        if (isFlagship(container)) {
            certifications.push('Flagship Installer');
            tier = 'Flagship';
        } else {
            certifications.push('Select Partner');
        }

        // Check specialties
        if (/solar/i.test(text)) certifications.push('Solar');
        if (/sonnenConnect/i.test(text)) certifications.push('sonnenConnect');
        if (/sonnenBatterie/i.test(text)) certifications.push('sonnenBatterie');
        if (/commercial/i.test(text)) certifications.push('Commercial');
        if (/certified/i.test(text)) certifications.push('Sonnen Certified');

        // Extract website
        let website = '', domain = '';
        const links = container.querySelectorAll('a[href^="http"]');
        for (const link of links) {
            const href = link.href;
            if (href.includes('sonnen') || href.includes('google.com')) continue;
            if (href.includes('facebook') || href.includes('twitter')) continue;
            website = href;
            try { domain = new URL(website).hostname.replace(/^www\./, ''); } catch(e) {}
            break;
        }

        // Get state from section context
        const detectedState = getState(container);
        if (!state && detectedState) {
            // Map full state name to abbreviation
            const stateMap = {
                'California': 'CA', 'Texas': 'TX', 'Nevada': 'NV', 'Idaho': 'ID',
                'Massachusetts': 'MA', 'Rhode Island': 'RI', 'Utah': 'UT',
                'Puerto Rico': 'PR', 'Arizona': 'AZ', 'Florida': 'FL',
                'Colorado': 'CO', 'New York': 'NY', 'Hawaii': 'HI'
            };
            state = stateMap[detectedState] || '';
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
                    tier=data.get("tier", "Select Partner"),
                    source_url=self.DEALER_LOCATOR_URL,
                    raw_data=data,
                )
                dealers.append(dealer)

            except Exception as e:
                print(f"  Warning: Error parsing dealer: {e}")
                continue

        return dealers

    def detect_capabilities(self, dealer: StandardizedDealer) -> DealerCapabilities:
        """
        Detect multi-trade capabilities from Sonnen installer data.

        Battery storage installers are HIGH VALUE because:
        - Battery systems require Electrical expertise
        - Most also do Solar installation
        - Premium German brand = sophisticated contractors
        """
        caps = DealerCapabilities()
        caps.electrical = True  # All battery installers need electrical
        caps.solar = True  # Most Sonnen installers also do solar
        caps.multi_trade_score = 2  # Base score for battery+solar

        certs = " ".join(dealer.certifications).lower()
        name_lower = dealer.name.lower()

        # Flagship tier bonus
        if dealer.tier == "Flagship":
            caps.multi_trade_score += 2

        # Solar signal
        if "solar" in certs or "solar" in name_lower:
            caps.multi_trade_score += 1

        # Commercial capability
        if "commercial" in certs or "commercial" in name_lower:
            caps.multi_trade_score += 1

        # Check name for additional trade keywords
        if "hvac" in name_lower or "heating" in name_lower:
            caps.hvac = True
            caps.multi_trade_score += 1
        if "plumb" in name_lower:
            caps.plumbing = True
            caps.multi_trade_score += 1
        if "generator" in name_lower:
            caps.generators = True
            caps.multi_trade_score += 1
        if "energy" in name_lower or "power" in name_lower:
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
            )
            page = context.new_page()

            try:
                print(f"\n🔍 Scraping Sonnen installer directory")

                page.goto(self.DEALER_LOCATOR_URL, timeout=30000)
                time.sleep(3)

                # Scroll to load all content (static page)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)

                # Extract installers
                raw_data = page.evaluate(self.get_extraction_script())

                if raw_data:
                    dealers = self.parse_dealer_data(raw_data)
                    print(f"  ✓ Found {len(dealers)} installers")
                else:
                    print("  ✗ No installers found")

            except Exception as e:
                print(f"  ✗ Error: {e}")

            finally:
                browser.close()

        return dealers


# Register with factory
ScraperFactory.register("sonnen", SonnenScraper)
ScraperFactory.register("Sonnen", SonnenScraper)
