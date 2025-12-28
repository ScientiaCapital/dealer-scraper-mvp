#!/usr/bin/env python3
"""
CertainTeed Roofing Contractor Scraper

Scrapes the CertainTeed contractor locator to find certified roofing contractors.
Target URL: https://www.certainteed.com/find-a-pro

Business Context:
- CertainTeed is a premium roofing manufacturer (Saint-Gobain subsidiary)
- Products: Landmark, Presidential, Grand Manor shingles
- HIGH ICP VALUE: Roofing contractors often do solar installations too
- Contractor tiers: ShingleMaster → SELECT ShingleMaster (highest)
- SELECT ShingleMaster = 5+ years business, 50%+ Master Craftsman certified crew

Dealer Locator Structure:
- Form-based search with product category selection
- Location input (city, ZIP, address)
- Returns contractor cards with contact info and certifications
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


class CertainTeedScraper(BaseDealerScraper):
    """Scraper for CertainTeed certified roofing contractor network."""

    OEM_NAME = "CertainTeed"
    DEALER_LOCATOR_URL = "https://www.certainteed.com/find-a-pro"
    PRODUCT_LINES = [
        "Landmark Shingles",
        "Presidential Shake",
        "Grand Manor Shingles",
        "Northgate Shingles",
        "Solar Roofing",
        "Commercial Roofing",
    ]

    def get_base_url(self) -> str:
        """Return the base URL for CertainTeed contractor locator."""
        return self.DEALER_LOCATOR_URL

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "CertainTeed"

    def supports_zip_search(self) -> bool:
        """CertainTeed contractor locator supports location search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for CertainTeed contractors.

        Extracts contractor cards with name, phone, address, certifications, tier.
        """
        return r"""
() => {
    const dealers = [];
    const seen = new Set();

    // Find contractor result containers
    const containers = document.querySelectorAll(
        '[class*="contractor"], [class*="result"], [class*="card"], ' +
        '[class*="listing"], [class*="pro-"], article, li'
    );

    // Also search by content pattern - look for contractor data
    const allElements = document.querySelectorAll('div, article, section, li');
    const contractorElements = [];

    allElements.forEach(el => {
        const text = el.textContent;
        // Look for contractor patterns with phone and location
        const hasPhone = text.match(/\(\d{3}\)\s*\d{3}[-.]?\d{4}/) ||
                         el.querySelector('a[href^="tel:"]');
        const hasLocation = text.match(/[A-Z]{2}\s*\d{5}/) ||
                            text.match(/,\s*[A-Z]{2}\s*$/m);

        // ShingleMaster or contractor signals
        const hasContractor = /ShingleMaster|SELECT|Certified|Contractor/i.test(text);

        if (hasPhone && (hasLocation || hasContractor) &&
            text.length > 60 && text.length < 1200) {
            contractorElements.push(el);
        }
    });

    const targetElements = contractorElements.length > 0 ?
        contractorElements.sort((a, b) => a.textContent.length - b.textContent.length).slice(0, 80) :
        Array.from(containers);

    targetElements.forEach(el => {
        const text = el.textContent;

        // Extract name - usually first heading or strong element
        const nameEl = el.querySelector('h2, h3, h4, h5, strong, [class*="name"], [class*="title"], [class*="company"]');
        let name = nameEl ? nameEl.textContent.trim() : '';
        name = name.replace(/\s+/g, ' ').trim();

        // Clean up name - remove certifications that might be attached
        name = name.replace(/SELECT\s*ShingleMaster.*/i, '').trim();
        name = name.replace(/ShingleMaster.*/i, '').trim();
        name = name.replace(/Certified.*/i, '').trim();

        if (!name || name.length < 3 || name.length > 100) return;
        if (/^(certainteed|phone|address|find|search|contractor|select|shingle)/i.test(name)) return;

        // Extract phone
        let phone = '';
        const phoneLink = el.querySelector('a[href^="tel:"]');
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

        // Extract address components
        let address = '', city = '', state = '', zip_code = '';

        const fullAddr = text.match(/(\d+\s+[A-Za-z0-9\s.,]+),\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5})/);
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
            } else {
                const cityState = text.match(/([A-Za-z\s]+),\s*([A-Z]{2})\b/);
                if (cityState) {
                    city = cityState[1].trim();
                    state = cityState[2];
                }
            }
        }

        // Extract certification tier
        const certifications = [];
        let tier = 'ShingleMaster';

        if (/SELECT\s*ShingleMaster/i.test(text)) {
            certifications.push('SELECT ShingleMaster');
            tier = 'SELECT ShingleMaster';
        } else if (/ShingleMaster/i.test(text)) {
            certifications.push('ShingleMaster');
        }

        // Additional certifications
        if (/Master\s*Craftsman/i.test(text)) {
            certifications.push('Master Craftsman');
        }
        if (/5\s*Star/i.test(text)) {
            certifications.push('5-Star Contractor');
        }
        if (/Integrity\s*Roof\s*System/i.test(text)) {
            certifications.push('Integrity Roof System');
        }
        if (/SureStart\s*PLUS/i.test(text)) {
            certifications.push('SureStart PLUS Warranty');
        }

        // Product specialties
        if (/solar/i.test(text)) certifications.push('Solar Roofing');
        if (/commercial/i.test(text)) certifications.push('Commercial');
        if (/siding/i.test(text)) certifications.push('Siding');

        // Extract website
        let website = '', domain = '';
        const links = el.querySelectorAll('a[href^="http"]');
        for (const link of links) {
            const href = link.href;
            if (href.includes('certainteed') || href.includes('google.com')) continue;
            if (href.includes('facebook') || href.includes('twitter')) continue;
            website = href;
            try { domain = new URL(website).hostname.replace(/^www\./, ''); } catch(e) {}
            break;
        }

        // Extract email if available
        let email = '';
        const emailLink = el.querySelector('a[href^="mailto:"]');
        if (emailLink) {
            email = emailLink.href.replace('mailto:', '').split('?')[0];
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
            email: email,
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
                    tier=data.get("tier", "ShingleMaster"),
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
        Detect multi-trade capabilities from CertainTeed contractor data.

        Roofing contractors are valuable because:
        - Many also do solar roof installations
        - SELECT ShingleMaster = highest tier, premium contractors
        - 5+ years in business + certified crew requirements
        """
        caps = DealerCapabilities()
        caps.roofing = True  # All CertainTeed contractors do roofing
        caps.multi_trade_score = 1  # Base score

        certs = " ".join(dealer.certifications).lower()
        name_lower = dealer.name.lower()

        # Tier bonuses - SELECT ShingleMaster is highest
        if dealer.tier == "SELECT ShingleMaster":
            caps.multi_trade_score += 2

        # Solar capability - big value signal
        if "solar" in certs or "solar" in name_lower:
            caps.solar = True
            caps.multi_trade_score += 2

        # Siding = additional trade
        if "siding" in certs or "siding" in name_lower:
            caps.multi_trade_score += 1

        # Check name for multi-trade signals
        if "construction" in name_lower or "renovations" in name_lower:
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
        if "exterior" in name_lower or "home improvement" in name_lower:
            caps.multi_trade_score += 1

        # Master Craftsman certification = quality signal
        if "master craftsman" in certs:
            caps.multi_trade_score += 1

        # Commercial = larger operation
        if "commercial" in certs:
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
                print(f"\n🔍 Scraping CertainTeed contractors for ZIP: {zip_code}")

                page.goto(self.DEALER_LOCATOR_URL, timeout=30000)
                time.sleep(2)

                # Handle cookie consent if present
                try:
                    cookie_btn = page.locator('button:has-text("Accept"), button:has-text("OK"), [class*="cookie"] button').first
                    if cookie_btn.count() > 0:
                        cookie_btn.click()
                        time.sleep(0.5)
                except:
                    pass

                # Select Residential Roofing product category
                # Radio button value="601" for Residential Roofing
                try:
                    roofing_radio = page.locator('input[value="601"], input[type="radio"][id*="residential"]').first
                    if roofing_radio.count() > 0:
                        roofing_radio.click()
                        time.sleep(0.5)
                except:
                    pass

                # Find and fill location input
                location_input = page.locator(
                    'input[id*="google-geo"], input[id*="location"], '
                    'input[placeholder*="location"], input[placeholder*="zip"], '
                    'input[placeholder*="city"], input[name*="location"]'
                ).first

                if location_input.count() > 0:
                    location_input.fill(zip_code)
                    time.sleep(1)

                    # Select "Find a contractor myself" option if present
                    try:
                        find_myself = page.locator('input[value*="find"], label:has-text("Find a contractor myself")').first
                        if find_myself.count() > 0:
                            find_myself.click()
                            time.sleep(0.5)
                    except:
                        pass

                    # Submit search
                    search_btn = page.locator(
                        'button:has-text("Search"), button:has-text("Find"), '
                        'button[type="submit"], input[type="submit"]'
                    ).first

                    if search_btn.count() > 0:
                        search_btn.click()
                    else:
                        location_input.press("Enter")

                    time.sleep(4)

                    # Scroll to load results
                    page.evaluate("window.scrollTo(0, 1000)")
                    time.sleep(1)

                    # Extract contractors
                    raw_data = page.evaluate(self.get_extraction_script())

                    if raw_data:
                        dealers = self.parse_dealer_data(raw_data)
                        print(f"  ✓ Found {len(dealers)} contractors")
                    else:
                        print("  ✗ No contractors found")
                else:
                    print("  ✗ Could not find location input")

            except Exception as e:
                print(f"  ✗ Error: {e}")

            finally:
                browser.close()

        return dealers


# Register with factory
ScraperFactory.register("certainteed", CertainTeedScraper)
ScraperFactory.register("CertainTeed", CertainTeedScraper)
ScraperFactory.register("certain_teed", CertainTeedScraper)
