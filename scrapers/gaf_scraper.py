#!/usr/bin/env python3
"""
GAF Roofing Contractor Scraper

Scrapes the GAF contractor locator to find certified roofing contractors.
Target URL: https://www.gaf.com/en-us/roofing-contractors/residential

Business Context:
- GAF is North America's largest roofing manufacturer
- Products: Shingles, roofing systems, ventilation
- HIGH ICP VALUE: Roofing contractors often do solar installations too
- Contractor tiers: Certified → Certified Plus → Master Elite (only 2%)
- President's Club = highest recognition

Dealer Locator Structure:
- ZIP/address search input
- Contractor cards with ratings, certifications
- Shows distance, phone, warranties offered
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


class GAFScraper(BaseDealerScraper):
    """Scraper for GAF certified roofing contractor network."""

    OEM_NAME = "GAF"
    DEALER_LOCATOR_URL = "https://www.gaf.com/en-us/roofing-contractors/residential"
    PRODUCT_LINES = [
        "Timberline Shingles",
        "Designer Shingles",
        "3-Tab Shingles",
        "Roofing Systems",
        "Ventilation",
        "Accessories",
    ]

    def get_base_url(self) -> str:
        """Return the base URL for GAF contractor locator."""
        return self.DEALER_LOCATOR_URL

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "GAF"

    def supports_zip_search(self) -> bool:
        """GAF contractor locator supports ZIP code search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for GAF contractors.

        Extracts contractor cards with name, phone, address, ratings, certifications.
        """
        return r"""
() => {
    const dealers = [];
    const seen = new Set();

    // Find contractor cards - GAF uses certification-card__wrapper class
    const cards = document.querySelectorAll('.certification-card__wrapper, [class*="contractor"], [class*="card"]');

    // Also search by content pattern
    const allDivs = document.querySelectorAll('div');
    const contractorDivs = [];

    allDivs.forEach(div => {
        const text = div.textContent;
        // Look for contractor patterns with certification tiers
        if ((text.match(/Master Elite|Certified Plus|Certified/i)) &&
            text.match(/\(\d{3}\)\s*\d{3}[-.]?\d{4}/) &&
            text.length > 80 && text.length < 800) {
            contractorDivs.push(div);
        }
    });

    const targetCards = contractorDivs.length > 0 ?
        contractorDivs.sort((a, b) => a.textContent.length - b.textContent.length).slice(0, 100) :
        Array.from(cards);

    targetCards.forEach(card => {
        const text = card.textContent;

        // Extract name - usually first heading element
        const nameEl = card.querySelector('h3, h4, h5, strong, [class*="name"], [class*="title"]');
        let name = nameEl ? nameEl.textContent.trim() : '';
        name = name.replace(/\s+/g, ' ').trim();

        // Clean up name - remove ratings that might be attached
        name = name.replace(/\d+\.\d+\(\d+\).*$/, '').trim();

        if (!name || name.length < 3 || name.length > 100) return;
        if (/^(phone|address|email|gaf|looking|help|connect)/i.test(name)) return;

        // Extract phone
        let phone = '';
        const phoneLink = card.querySelector('a[href^="tel:"]');
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

        // Extract location - usually City, ST format
        let city = '', state = '';
        const locationMatch = text.match(/([A-Za-z\s]+),\s*([A-Z]{2})\s*-?\s*[\d.]+\s*mi/i);
        if (locationMatch) {
            city = locationMatch[1].trim();
            state = locationMatch[2];
        } else {
            const simpleLocation = text.match(/([A-Za-z\s]+),\s*([A-Z]{2})/);
            if (simpleLocation) {
                city = simpleLocation[1].trim();
                state = simpleLocation[2];
            }
        }

        // Extract rating
        let rating = 0;
        const ratingMatch = text.match(/(\d+\.\d+)\s*\((\d+)\)/);
        if (ratingMatch) {
            rating = parseFloat(ratingMatch[1]);
        }

        // Extract review count
        let reviewCount = 0;
        if (ratingMatch) {
            reviewCount = parseInt(ratingMatch[2]);
        }

        // Extract certification tier
        const certifications = [];
        let tier = 'Certified';

        if (/President'?s?\s*Club/i.test(text)) {
            certifications.push("President's Club Award");
            tier = "President's Club";
        }
        if (/Master\s*Elite/i.test(text)) {
            certifications.push('GAF Master Elite');
            if (tier === 'Certified') tier = 'Master Elite';
        }
        if (/Certified\s*Plus/i.test(text)) {
            certifications.push('GAF Certified Plus');
            if (tier === 'Certified') tier = 'Certified Plus';
        }
        if (/\bCertified\b/i.test(text) && !certifications.some(c => c.includes('Certified'))) {
            certifications.push('GAF Certified');
        }

        // Extract distance
        let distance = '';
        const distMatch = text.match(/([\d.]+)\s*mi/i);
        if (distMatch) {
            distance = distMatch[1] + ' miles';
        }

        // Extract website if available
        let website = '', domain = '';
        const links = card.querySelectorAll('a[href^="http"]');
        for (const link of links) {
            const href = link.href;
            if (href.includes('gaf.com') || href.includes('google.com')) continue;
            website = href;
            try { domain = new URL(website).hostname.replace(/^www\./, ''); } catch(e) {}
            break;
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
            certifications: [...new Set(certifications)],
            tier: tier,
            rating: rating,
            review_count: reviewCount,
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
                    tier=data.get("tier", "Certified"),
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
        Detect multi-trade capabilities from GAF contractor data.

        Roofing contractors are valuable because:
        - Many also do solar roof installations
        - Some expand into general contracting
        - Master Elite = top 2% quality signal
        """
        caps = DealerCapabilities()
        caps.roofing = True  # All GAF contractors do roofing
        caps.multi_trade_score = 1  # Base score

        certs = " ".join(dealer.certifications).lower()
        name_lower = dealer.name.lower()

        # Tier bonuses - higher tier = more established
        if dealer.tier == "President's Club":
            caps.multi_trade_score += 3
        elif dealer.tier == "Master Elite":
            caps.multi_trade_score += 2
        elif dealer.tier == "Certified Plus":
            caps.multi_trade_score += 1

        # Check name for multi-trade signals
        if "solar" in name_lower:
            caps.solar = True
            caps.multi_trade_score += 2
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

        # High ratings bonus
        raw_data = dealer.raw_data or {}
        if raw_data.get("rating", 0) >= 4.5 and raw_data.get("review_count", 0) >= 20:
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
                print(f"\n🔍 Scraping GAF contractors for ZIP: {zip_code}")

                page.goto(self.DEALER_LOCATOR_URL, timeout=30000)
                time.sleep(2)

                # Find and fill ZIP input
                zip_input = page.locator('#unique-id-residential-us').first
                if zip_input.count() == 0:
                    zip_input = page.locator('input[placeholder*="address"], input[placeholder*="zip"]').first

                if zip_input.count() > 0:
                    zip_input.fill(zip_code)
                    time.sleep(0.5)

                    # Submit search
                    search_btn = page.locator('button:has-text("Search")').first
                    if search_btn.count() > 0:
                        search_btn.click()
                    else:
                        zip_input.press("Enter")

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
                    print("  ✗ Could not find ZIP input")

            except Exception as e:
                print(f"  ✗ Error: {e}")

            finally:
                browser.close()

        return dealers


# Register with factory
ScraperFactory.register("gaf", GAFScraper)
ScraperFactory.register("GAF", GAFScraper)
