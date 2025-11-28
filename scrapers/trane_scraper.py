#!/usr/bin/env python3
"""
Trane HVAC Dealer Scraper - Enhanced Version

Scrapes the Trane dealer directory using TWO-PHASE approach:
1. Master Directory Table: Get ALL dealers (name, city, state, zip, detail URL)
2. Detail Pages: Click into each for rich pre-qualification data

Target URLs:
- Directory: https://www.trane.com/residential/en/dealers/
- Detail: https://www.trane.com/residential/en/dealers/{dealer-slug}/

UNIQUE VALUE PROPOSITION:
- Trane detail pages have GOOGLE RATINGS + REVIEW COUNTS (pre-verified by Trane!)
- Also: certifications, expertise areas, business hours, financing
- NAME is the anchor - sales-agent enriches from there via Hunter/Apollo

Business Context:
- Trane is one of the "Big 3" HVAC brands (Carrier, Trane, Lennox)
- Owned by Trane Technologies (parent also owns Carrier brand)
- ~2,800 certified dealers nationwide
- Residential + commercial HVAC contractors

PHONE HANDLING:
- "Call Now" button reveals 1-866-953-1673 = Trane call center (USELESS)
- BUT some dealer cards may show local phones - grab those (exclude 800/888/etc)
- Sales-agent will enrich remaining contacts via Hunter/Apollo

Rate Limiting:
- 3 second delay between detail page requests (user-confirmed)
- ~2,800 pages × 3 sec = ~140 minutes (2.3 hours)
- Checkpoints every 100 dealers for resume capability
"""

import re
import time
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from scrapers.base_scraper import (
    BaseDealerScraper,
    StandardizedDealer,
    DealerCapabilities,
    ScraperMode,
)
from scrapers.scraper_factory import ScraperFactory


class TraneScraper(BaseDealerScraper):
    """Enhanced Trane scraper with directory table + detail page approach."""

    OEM_NAME = "Trane"
    DIRECTORY_URL = "https://www.trane.com/residential/en/dealers/"
    DEALER_LOCATOR_URL = "https://www.trane.com/residential/en/dealer-locator/"
    PRODUCT_LINES = [
        "HVAC Systems",
        "Air Conditioners",
        "Heat Pumps",
        "Furnaces",
        "Air Handlers",
        "Packaged Systems",
        "Ductless Systems",
    ]

    # Rate limiting (user-confirmed: 3 second delay)
    DELAY_BETWEEN_REQUESTS = 3.0
    CHECKPOINT_INTERVAL = 100

    def get_base_url(self) -> str:
        """Return the base URL for Trane dealer locator."""
        return self.DEALER_LOCATOR_URL

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "Trane"

    def supports_zip_search(self) -> bool:
        """Trane dealer locator supports ZIP code search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for Trane directory table.

        Extracts all rows from the dealer directory table.
        """
        return r"""
() => {
    const dealers = [];

    // Find all table rows in the dealer directory
    const rows = document.querySelectorAll('table tbody tr, .dealer-list tr');

    rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 4) {
            // Extract link to detail page
            const link = row.querySelector('a[href*="/dealers/"]');
            const detailUrl = link ? link.href : '';

            dealers.push({
                name: cells[0]?.textContent?.trim() || '',
                state: cells[1]?.textContent?.trim() || '',
                city: cells[2]?.textContent?.trim() || '',
                zip: cells[3]?.textContent?.trim() || '',
                country: cells[4]?.textContent?.trim() || 'USA',
                detail_url: detailUrl
            });
        }
    });

    return dealers;
}
"""

    def scrape_directory_table(self, page) -> List[Dict[str, Any]]:
        """
        Scrape the master dealer directory table.

        Args:
            page: Playwright page object (already navigated to directory)

        Returns:
            List of dealer dicts with: name, state, city, zip, country, detail_url
        """
        dealers = []

        try:
            # Wait for table to load
            page.wait_for_selector('table, .dealer-list', timeout=30000)
            time.sleep(2)  # Let dynamic content settle

            # Extract using JavaScript
            raw_dealers = page.evaluate(self.get_extraction_script())

            print(f"  → Extracted {len(raw_dealers)} dealers from directory table")

            # Filter valid entries
            for dealer in raw_dealers:
                if dealer.get('name') and len(dealer.get('name', '')) > 2:
                    dealers.append(dealer)

            return dealers

        except Exception as e:
            print(f"  ✗ Error scraping directory table: {e}")
            return []

    def scrape_detail_page(self, page, detail_url: str) -> Dict[str, Any]:
        """
        Extract rich data from a dealer detail page.

        Args:
            page: Playwright page object
            detail_url: URL of dealer detail page

        Returns:
            Dict with enriched dealer data:
            - google_rating, google_review_count
            - business_hours, areas_of_expertise
            - certifications, has_emergency, has_financing
            - phone (if visible and valid - not toll-free)
        """
        enriched = {
            'google_rating': 0.0,
            'google_review_count': 0,
            'business_hours': {},
            'areas_of_expertise': [],
            'certifications': [],
            'has_emergency_service': False,
            'has_financing': False,
            'financing_provider': '',
            'phone': '',
            'detail_page_url': detail_url,
        }

        try:
            page.goto(detail_url, timeout=30000, wait_until='domcontentloaded')
            time.sleep(1.5)  # Let page settle

            # Extract using JavaScript
            data = page.evaluate(r"""
() => {
    const result = {
        google_rating: 0.0,
        google_review_count: 0,
        business_hours: {},
        areas_of_expertise: [],
        certifications: [],
        has_emergency: false,
        has_financing: false,
        financing_provider: '',
        phone: ''
    };

    const pageText = document.body.innerText;

    // Google Rating (e.g., "4.9")
    const ratingMatch = pageText.match(/(\d+\.?\d*)\s*(?:out of 5|\/5|stars?)/i);
    if (ratingMatch) {
        result.google_rating = parseFloat(ratingMatch[1]);
    } else {
        // Try to find rating badge
        const ratingEl = document.querySelector('[class*="rating"], [class*="stars"], [data-rating]');
        if (ratingEl) {
            const ratingText = ratingEl.textContent || ratingEl.getAttribute('data-rating') || '';
            const match = ratingText.match(/(\d+\.?\d*)/);
            if (match) result.google_rating = parseFloat(match[1]);
        }
    }

    // Google Review Count (e.g., "1010 Google Reviews")
    const reviewMatch = pageText.match(/(\d+)\s*(?:Google\s*)?[Rr]eviews?/);
    if (reviewMatch) {
        result.google_review_count = parseInt(reviewMatch[1]);
    }

    // Areas of Expertise (e.g., "HVAC repair, AC installation")
    const expertiseSection = document.querySelector('[class*="expertise"], [class*="services"], [class*="capabilities"]');
    if (expertiseSection) {
        const items = expertiseSection.querySelectorAll('li, span, p');
        items.forEach(item => {
            const text = item.textContent.trim();
            if (text.length > 2 && text.length < 100) {
                result.areas_of_expertise.push(text);
            }
        });
    }

    // Also check for expertise keywords in page text
    const expertiseKeywords = ['HVAC repair', 'AC installation', 'Furnace installation',
                               'Heat pump', 'Ductless', 'Air handler', 'Maintenance',
                               'Emergency service', 'Commercial', 'Residential'];
    expertiseKeywords.forEach(keyword => {
        if (pageText.includes(keyword) && !result.areas_of_expertise.includes(keyword)) {
            result.areas_of_expertise.push(keyword);
        }
    });

    // Certifications (e.g., "Trane Comfort Specialist", "NATE Certified")
    const certKeywords = ['Trane Comfort Specialist', 'NATE Certified', 'NATE',
                          'EPA Certified', 'BBB', 'Accredited', 'Dealer of Excellence',
                          'Premier Dealer', 'Authorized Dealer'];
    certKeywords.forEach(cert => {
        if (pageText.includes(cert)) {
            result.certifications.push(cert);
        }
    });

    // 24/7 Emergency Service
    result.has_emergency = /24\/?7|emergency|after.?hours/i.test(pageText);

    // Financing
    result.has_financing = /financing|finance|payment plan|wells fargo|synchrony/i.test(pageText);
    if (pageText.includes('Wells Fargo')) result.financing_provider = 'Wells Fargo';
    else if (pageText.includes('Synchrony')) result.financing_provider = 'Synchrony';

    // Phone Number (look for local phones, exclude toll-free)
    const phoneLinks = document.querySelectorAll('a[href^="tel:"]');
    phoneLinks.forEach(link => {
        const phone = link.href.replace('tel:', '').replace(/[^0-9]/g, '');
        // Skip toll-free numbers (800, 888, 877, 866, 855, 844, 833)
        const tollFreePrefix = ['800', '888', '877', '866', '855', '844', '833'];
        if (phone.length >= 10) {
            const areaCode = phone.slice(-10, -7);  // Get area code from 10-digit
            if (!tollFreePrefix.includes(areaCode)) {
                result.phone = phone.slice(-10);  // Last 10 digits
            }
        }
    });

    // Business Hours (try to extract)
    const hoursSection = document.querySelector('[class*="hours"], [class*="schedule"]');
    if (hoursSection) {
        const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        days.forEach(day => {
            const dayRegex = new RegExp(day + '[:\\s]+([0-9:APMapm\\s-]+)', 'i');
            const match = hoursSection.textContent.match(dayRegex);
            if (match) {
                result.business_hours[day] = match[1].trim();
            }
        });
    }

    return result;
}
""")

            # Map extracted data to enriched dict
            enriched['google_rating'] = data.get('google_rating', 0.0)
            enriched['google_review_count'] = data.get('google_review_count', 0)
            enriched['business_hours'] = data.get('business_hours', {})
            enriched['areas_of_expertise'] = data.get('areas_of_expertise', [])
            enriched['certifications'] = data.get('certifications', [])
            enriched['has_emergency_service'] = data.get('has_emergency', False)
            enriched['has_financing'] = data.get('has_financing', False)
            enriched['financing_provider'] = data.get('financing_provider', '')

            # Validate and set phone (only if valid non-toll-free)
            phone = data.get('phone', '')
            if phone and self._is_valid_phone(phone):
                enriched['phone'] = self._normalize_phone(phone)

        except Exception as e:
            print(f"    ⚠️ Error on detail page: {e}")

        return enriched

    def _scrape_with_browserbase(self, zip_code: str = None) -> List[StandardizedDealer]:
        """
        BROWSERBASE mode: Cloud browser automation for full directory scrape.

        This is the PRIMARY method for Trane - scrapes ALL dealers from
        the master directory table, then visits each detail page.

        Args:
            zip_code: Ignored - scrapes full directory regardless

        Returns:
            List of StandardizedDealer objects with enriched data
        """
        from browserbase import Browserbase
        from playwright.sync_api import sync_playwright

        dealers = []
        checkpoint_dir = "output/oem_data/trane"
        Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)

        # Load Browserbase credentials
        api_key = os.environ.get("BROWSERBASE_API_KEY")
        project_id = os.environ.get("BROWSERBASE_PROJECT_ID")

        if not api_key or not project_id:
            raise ValueError("BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID required")

        bb = Browserbase(api_key=api_key)

        print(f"\n{'='*60}")
        print(f"  TRANE ENHANCED SCRAPER - FULL DIRECTORY MODE")
        print(f"{'='*60}")
        print(f"  Strategy: Directory Table → Detail Pages")
        print(f"  Rate Limit: {self.DELAY_BETWEEN_REQUESTS}s delay")
        print(f"  Checkpoint: Every {self.CHECKPOINT_INTERVAL} dealers")
        print(f"{'='*60}\n")

        with sync_playwright() as p:
            # Create Browserbase session
            session = bb.sessions.create(project_id=project_id)

            try:
                # Connect to cloud browser
                browser = p.chromium.connect_over_cdp(session.connect_url)
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else context.new_page()

                # Phase 1: Scrape directory table
                print("PHASE 1: Scraping master directory table...")
                page.goto(self.DIRECTORY_URL, timeout=60000, wait_until='domcontentloaded')
                time.sleep(3)

                # Handle cookie banner if present
                try:
                    cookie_btn = page.locator('button:has-text("continue"), button:has-text("accept")').first
                    if cookie_btn.count() > 0:
                        cookie_btn.click(timeout=3000)
                        time.sleep(1)
                except:
                    pass

                directory_dealers = self.scrape_directory_table(page)

                if not directory_dealers:
                    print("  ✗ No dealers found in directory table!")
                    return []

                print(f"  ✓ Found {len(directory_dealers)} dealers in directory")

                # Phase 2: Visit each detail page
                print(f"\nPHASE 2: Visiting {len(directory_dealers)} detail pages...")
                print(f"  Estimated time: ~{len(directory_dealers) * self.DELAY_BETWEEN_REQUESTS / 60:.1f} minutes\n")

                for i, dealer_data in enumerate(directory_dealers, 1):
                    detail_url = dealer_data.get('detail_url', '')

                    if detail_url:
                        print(f"  [{i}/{len(directory_dealers)}] {dealer_data.get('name', 'Unknown')[:40]}...", end=" ")

                        # Scrape detail page
                        enriched = self.scrape_detail_page(page, detail_url)
                        dealer_data.update(enriched)

                        # Show progress
                        rating_info = f"⭐{enriched['google_rating']}" if enriched['google_rating'] > 0 else "No rating"
                        phone_info = f"📞{enriched['phone'][:6]}..." if enriched['phone'] else "No phone"
                        print(f"{rating_info} | {phone_info}")

                    # Parse into StandardizedDealer
                    try:
                        dealer = self.parse_dealer_data(dealer_data, zip_code or "00000")
                        dealers.append(dealer)
                    except Exception as e:
                        print(f"    ⚠️ Parse error: {e}")

                    # Checkpoint every N dealers
                    if i % self.CHECKPOINT_INTERVAL == 0:
                        self._save_trane_checkpoint(
                            checkpoint_dir, i, dealers, len(directory_dealers)
                        )

                    # Rate limiting
                    time.sleep(self.DELAY_BETWEEN_REQUESTS)

                # Final checkpoint
                self._save_trane_checkpoint(
                    checkpoint_dir, len(directory_dealers), dealers, len(directory_dealers), final=True
                )

                print(f"\n{'='*60}")
                print(f"  COMPLETED: {len(dealers)} dealers scraped")
                print(f"  With ratings: {sum(1 for d in dealers if d.google_rating > 0)}")
                print(f"  With phones: {sum(1 for d in dealers if d.phone)}")
                print(f"{'='*60}\n")

            finally:
                browser.close()
                bb.sessions.update(session.id, status="COMPLETED")

        return dealers

    def _save_trane_checkpoint(
        self,
        checkpoint_dir: str,
        count: int,
        dealers: List[StandardizedDealer],
        total: int,
        final: bool = False
    ):
        """Save checkpoint with Trane-specific data."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trane_checkpoint_{count:04d}" if not final else f"trane_final_{timestamp}"
        filepath = f"{checkpoint_dir}/{filename}.json"

        # Calculate stats
        with_rating = sum(1 for d in dealers if d.google_rating > 0)
        with_phone = sum(1 for d in dealers if d.phone)
        with_certs = sum(1 for d in dealers if d.dealer_certifications)

        checkpoint_data = {
            "oem": "Trane",
            "timestamp": datetime.now().isoformat(),
            "progress": f"{count}/{total}",
            "stats": {
                "total_scraped": len(dealers),
                "with_google_rating": with_rating,
                "with_phone": with_phone,
                "with_certifications": with_certs,
                "avg_rating": sum(d.google_rating for d in dealers) / len(dealers) if dealers else 0,
            },
            "dealers": [d.to_dict() for d in dealers]
        }

        with open(filepath, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)

        print(f"\n  💾 Checkpoint saved: {filename} ({len(dealers)} dealers)")

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Local browser for testing.

        Uses the dealer locator (not directory) for ZIP-based search.
        Useful for quick tests but not for full national scrape.
        """
        from playwright.sync_api import sync_playwright

        dealers = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = context.new_page()

            try:
                # Navigate to dealer locator
                print(f"  → Navigating to Trane dealer locator...")
                page.goto(self.DEALER_LOCATOR_URL, timeout=60000, wait_until='domcontentloaded')
                time.sleep(2)

                # Handle cookies
                try:
                    cookie_btn = page.locator('button:has-text("continue")').first
                    if cookie_btn.count() > 0:
                        cookie_btn.click(timeout=2000)
                        time.sleep(1)
                except:
                    pass

                # Search by ZIP
                print(f"  → Searching ZIP: {zip_code}")
                zip_input = page.locator('input[type="text"]').first
                zip_input.fill(zip_code)
                time.sleep(0.5)

                search_btn = page.locator('button:has-text("Search")').first
                search_btn.click()
                time.sleep(4)

                # Extract dealer cards
                raw_dealers = page.evaluate(r"""
() => {
    const dealers = [];
    const cards = document.querySelectorAll('[class*="dealer"], [class*="card"], [class*="result"]');

    cards.forEach(card => {
        const nameEl = card.querySelector('h2, h3, h4, a[class*="name"]');
        const name = nameEl ? nameEl.textContent.trim() : '';
        if (!name || name.length < 3) return;

        // Look for phone (local, not toll-free)
        let phone = '';
        const phoneLink = card.querySelector('a[href^="tel:"]');
        if (phoneLink) {
            const rawPhone = phoneLink.href.replace('tel:', '').replace(/[^0-9]/g, '');
            const tollFree = ['800', '888', '877', '866', '855', '844', '833'];
            if (rawPhone.length >= 10) {
                const areaCode = rawPhone.slice(-10, -7);
                if (!tollFree.includes(areaCode)) {
                    phone = rawPhone.slice(-10);
                }
            }
        }

        // Location
        const text = card.textContent;
        let city = '', state = '';
        const cityStateMatch = text.match(/([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})/);
        if (cityStateMatch) {
            city = cityStateMatch[1];
            state = cityStateMatch[2];
        }

        // Rating
        let rating = 0;
        const ratingMatch = text.match(/(\d+\.?\d*)\s*(?:out|stars?|\()/i);
        if (ratingMatch) rating = parseFloat(ratingMatch[1]);

        dealers.push({
            name: name,
            phone: phone,
            city: city,
            state: state,
            rating: rating,
            certifications: ['Trane Dealer']
        });
    });

    return dealers;
}
""")

                print(f"  → Found {len(raw_dealers)} dealers")

                # Parse results
                for raw in raw_dealers:
                    try:
                        dealer = self.parse_dealer_data(raw, zip_code)
                        dealers.append(dealer)
                    except Exception as e:
                        print(f"    ⚠️ Parse error: {e}")

            finally:
                browser.close()

        return dealers

    def _scrape_with_runpod(self, zip_code: str) -> List[StandardizedDealer]:
        """RunPod mode not implemented for Trane."""
        raise NotImplementedError("Use Browserbase mode for Trane")

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """Patchright mode not implemented for Trane."""
        raise NotImplementedError("Use Browserbase mode for Trane")

    def parse_dealer_data(
        self, raw_dealer_data: Dict[str, Any], zip_code: str
    ) -> StandardizedDealer:
        """
        Convert raw Trane dealer data to StandardizedDealer format.

        Handles both directory table data and enriched detail page data.
        """
        # Detect capabilities from name, certifications, expertise
        caps = self.detect_capabilities(raw_dealer_data)

        # Get phone (already validated in extraction)
        phone = raw_dealer_data.get('phone', '')
        if phone and not self._is_valid_phone(phone):
            phone = ''

        # Create StandardizedDealer
        dealer = StandardizedDealer(
            name=raw_dealer_data.get('name', ''),
            phone=phone,
            domain='',
            website='',
            street='',
            city=raw_dealer_data.get('city', ''),
            state=raw_dealer_data.get('state', ''),
            zip=raw_dealer_data.get('zip', ''),
            address_full=f"{raw_dealer_data.get('city', '')}, {raw_dealer_data.get('state', '')}",
            rating=raw_dealer_data.get('rating', 0.0),
            review_count=raw_dealer_data.get('review_count', 0),
            tier=self._determine_tier(raw_dealer_data.get('certifications', [])),
            certifications=raw_dealer_data.get('certifications', []),
            distance='',
            distance_miles=0,
            capabilities=caps,
            oem_source="Trane",
            scraped_from_zip=zip_code,
            # Enrichment fields
            google_rating=raw_dealer_data.get('google_rating', 0.0),
            google_review_count=raw_dealer_data.get('google_review_count', 0),
            business_hours=raw_dealer_data.get('business_hours', {}),
            areas_of_expertise=raw_dealer_data.get('areas_of_expertise', []),
            dealer_certifications=raw_dealer_data.get('certifications', []),
            has_emergency_service=raw_dealer_data.get('has_emergency_service', False),
            has_financing=raw_dealer_data.get('has_financing', False),
            financing_provider=raw_dealer_data.get('financing_provider', ''),
            detail_page_url=raw_dealer_data.get('detail_page_url', ''),
        )

        return dealer

    def _determine_tier(self, certifications: List[str]) -> str:
        """Determine dealer tier from certifications."""
        certs_lower = [c.lower() for c in certifications]

        if any('comfort specialist' in c for c in certs_lower):
            return "Comfort Specialist"
        elif any('excellence' in c for c in certs_lower):
            return "Dealer of Excellence"
        elif any('premier' in c for c in certs_lower):
            return "Premier Dealer"
        else:
            return "Authorized Dealer"

    def detect_capabilities(self, raw_dealer: Dict[str, Any]) -> DealerCapabilities:
        """
        Detect dealer capabilities from raw data.

        Uses name, certifications, AND areas of expertise for detection.
        This is where we flag multi-trade GOLD signals!
        """
        caps = DealerCapabilities()

        # HVAC capability (all Trane dealers)
        caps.has_hvac = True
        caps.oem_certifications.add("Trane")

        # Combine all text for searching
        name = raw_dealer.get('name', '').lower()
        certs = [c.lower() for c in raw_dealer.get('certifications', [])]
        expertise = [e.lower() for e in raw_dealer.get('areas_of_expertise', [])]
        all_text = f"{name} {' '.join(certs)} {' '.join(expertise)}"

        # Trade detection from expertise areas
        # Electrical signals
        if any(kw in all_text for kw in ['electric', 'electrical', 'wiring', 'panel']):
            caps.has_electrical = True

        # Plumbing signals
        if any(kw in all_text for kw in ['plumb', 'plumbing', 'pipe', 'water heater']):
            caps.has_plumbing = True

        # Fire/Security signals (GOLD when combined with HVAC!)
        if any(kw in all_text for kw in ['fire', 'alarm', 'security', 'sprinkler', 'low voltage']):
            caps.has_fire_security = True

        # Solar/Energy signals
        if any(kw in all_text for kw in ['solar', 'energy', 'renewable', 'photovoltaic']):
            caps.has_solar = True

        # Roofing signals
        if any(kw in all_text for kw in ['roof', 'roofing']):
            caps.has_roofing = True

        # Commercial signals (high value)
        commercial_signals = ['commercial', 'industrial', 'mechanical', 'inc', 'corp', 'llc']
        caps.is_commercial = any(sig in name for sig in commercial_signals)

        # Residential (most Trane dealers)
        caps.is_residential = any(kw in all_text for kw in ['residential', 'home', 'house']) or not caps.is_commercial

        # Resimercial (does BOTH - highest value!)
        if caps.is_commercial and caps.is_residential:
            # This is handled in StandardizedDealer.is_resimercial
            pass

        # O&M Detection
        if any(kw in all_text for kw in ['maintenance', 'service', 'repair', 'o&m', 'operations']):
            caps.has_om_capability = True

        # High ratings = likely larger operations
        rating = raw_dealer.get('google_rating', 0.0) or raw_dealer.get('rating', 0.0)
        review_count = raw_dealer.get('google_review_count', 0) or raw_dealer.get('review_count', 0)
        if rating >= 4.5 and review_count >= 50:
            caps.is_commercial = True

        # Calculate multi-trade score (GOLD detection!)
        caps.detect_high_value_contractor_types(
            dealer_name=raw_dealer.get('name', ''),
            certifications=raw_dealer.get('certifications', []),
            tier=raw_dealer.get('tier', '')
        )

        return caps

    def parse_results(
        self, raw_results: List[Dict[str, Any]], zip_code: str
    ) -> List[StandardizedDealer]:
        """Convert raw results to StandardizedDealer objects."""
        return [self.parse_dealer_data(raw, zip_code) for raw in raw_results]


# Register with factory
ScraperFactory.register("Trane", TraneScraper)
