#!/usr/bin/env python3
"""
Kohler Single ZIP Scraper with Card Detail Extraction
- Scrapes ONE ZIP code at a time
- Clicks into each dealer card for FULL details
- Outputs JSON + LOG files
"""

import sys
import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
OUTPUT_DIR = Path("output/kohler")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def setup_logging(zip_code: str) -> logging.Logger:
    """Setup logging to file and console."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = OUTPUT_DIR / f"kohler_{zip_code}_{timestamp}.log"

    logger = logging.getLogger(f"kohler_{zip_code}")
    logger.setLevel(logging.DEBUG)

    # File handler
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger, log_file

def scrape_kohler_zip(zip_code: str):
    """Scrape Kohler dealers for a single ZIP with card detail extraction."""
    logger, log_file = setup_logging(zip_code)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    logger.info(f"=" * 60)
    logger.info(f"KOHLER SCRAPER - ZIP: {zip_code}")
    logger.info(f"=" * 60)

    dealers = []

    try:
        from patchright.sync_api import sync_playwright

        with sync_playwright() as p:
            logger.info("Launching Patchright browser (headed mode)...")

            browser = p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )

            page = context.new_page()

            # Navigate to dealer locator
            url = "https://www.kohlerhomeenergy.rehlko.com/find-a-dealer"
            logger.info(f"Navigating to {url}")
            page.goto(url, timeout=60000)
            time.sleep(5)

            # Dismiss cookie consent
            logger.info("Checking for cookie consent...")
            try:
                consent = page.locator('.osano-cm-button--type_accept').first
                if consent.is_visible(timeout=3000):
                    consent.click(force=True)
                    logger.info("Dismissed cookie consent")
                    time.sleep(1)
            except:
                pass

            # Close any modals (Tier Legend, etc.)
            logger.info("Checking for modals...")
            page.evaluate("""() => {
                // Close osano completely
                const osano = document.querySelector('.osano-cm-window');
                if (osano) osano.remove();

                // Close any modal dialogs
                const modals = document.querySelectorAll('[role="dialog"], .modal');
                modals.forEach(m => m.remove());

                // Click close buttons by aria-label
                document.querySelectorAll('button').forEach(b => {
                    const label = b.getAttribute('aria-label') || '';
                    const text = b.textContent || '';
                    if (label.toLowerCase().includes('close') || text.toLowerCase().includes('close')) {
                        b.click();
                    }
                });
            }""")
            time.sleep(1)

            # Fill ZIP code - use query_selector_all to find visible inputs
            logger.info(f"Entering ZIP code: {zip_code}")

            # Try multiple selectors
            zip_selectors = [
                'input[name="zipcode"]',
                'input[placeholder*="ZIP" i]',
                'input[placeholder*="postal" i]',
            ]

            filled = False
            for selector in zip_selectors:
                inputs = page.query_selector_all(selector)
                for inp in inputs:
                    try:
                        box = inp.bounding_box()
                        if box and box['width'] > 0 and box['height'] > 0 and box['y'] > 0:
                            inp.scroll_into_view_if_needed()
                            time.sleep(0.3)
                            inp.click()
                            time.sleep(0.3)
                            inp.fill('')
                            inp.type(zip_code, delay=100)
                            time.sleep(0.5)

                            # Verify
                            val = inp.input_value()
                            if val == zip_code:
                                logger.info(f"Entered ZIP code: {val}")
                                filled = True
                                break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                if filled:
                    break

            if not filled:
                logger.error("Could not fill ZIP input")
                browser.close()
                return []

            # Submit search
            logger.info("Pressing Enter to search...")
            page.keyboard.press('Enter')
            time.sleep(8)

            # Extract dealer data directly from list view
            logger.info("Extracting dealer data from list...")

            raw_dealers = page.evaluate(r"""() => {
                const dealers = [];
                const seen = new Set();
                const lists = document.querySelectorAll('ul');

                for (const ul of lists) {
                    const lis = ul.querySelectorAll('li');
                    if (lis.length >= 3) {
                        const firstText = lis[0]?.innerText || '';
                        if (firstText.includes('miles') || firstText.includes('Dealer')) {
                            lis.forEach((li, idx) => {
                                const fullText = li.innerText || '';
                                if (!fullText.includes('miles')) return;

                                // Extract phone (non-toll-free)
                                const phoneMatch = fullText.match(/\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g) || [];
                                let phone = '';
                                for (const ph of phoneMatch) {
                                    const clean = ph.replace(/\D/g, '');
                                    if (!clean.startsWith('844') && !clean.startsWith('800') && clean.length === 10) {
                                        phone = clean;
                                        break;
                                    }
                                }

                                // Skip duplicates by phone
                                if (phone && seen.has(phone)) return;
                                if (phone) seen.add(phone);

                                // Get name from first <p> tag
                                const paragraphs = li.querySelectorAll('p');
                                const name = paragraphs[0]?.textContent?.trim() || '';
                                if (!name) return;

                                // Distance
                                const distMatch = fullText.match(/([\d.]+)\s*miles/i);
                                const distance = distMatch ? distMatch[1] + ' miles' : '';
                                const distance_miles = distMatch ? parseFloat(distMatch[1]) : 0;

                                // Tier
                                let tier = 'Certified';
                                if (fullText.includes('Titanium Dealer')) tier = 'Titanium';
                                else if (fullText.includes('Platinum Dealer')) tier = 'Platinum';
                                else if (fullText.includes('Gold Dealer')) tier = 'Gold';
                                else if (fullText.includes('Silver Dealer')) tier = 'Silver';
                                else if (fullText.includes('Bronze Dealer')) tier = 'Bronze';

                                // Address - look in paragraphs
                                let street = '', city = '', state = '', zip = '';
                                for (let i = 2; i < paragraphs.length; i++) {
                                    const pText = paragraphs[i]?.textContent?.trim() || '';
                                    const addrMatch = pText.match(/^([^,]+),\s*([^,]+),\s*([A-Z]{2})\s+(\d{5})/);
                                    if (addrMatch) {
                                        street = addrMatch[1].trim();
                                        city = addrMatch[2].trim();
                                        state = addrMatch[3];
                                        zip = addrMatch[4];
                                        break;
                                    }
                                }

                                // Fallback address extraction
                                if (!street) {
                                    const addrMatch = fullText.match(/([A-Z0-9][^,\n]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Way|Lane|Ln|Blvd|Court|Ct|Highway|Hwy)[^,]*),\s*([A-Za-z\s]+),\s*([A-Z]{2})\s+(\d{5})/i);
                                    if (addrMatch) {
                                        street = addrMatch[1].trim();
                                        city = addrMatch[2].trim();
                                        state = addrMatch[3].toUpperCase();
                                        zip = addrMatch[4];
                                    }
                                }

                                // Website
                                let website = '';
                                const links = li.querySelectorAll('a[href^="http"]');
                                for (const link of links) {
                                    if (!link.href.includes('rehlko') && !link.href.includes('kohler')) {
                                        website = link.href;
                                        break;
                                    }
                                }

                                // Certifications
                                const certs = [];
                                if (fullText.includes('Titan Certified')) certs.push('Titan Certified');
                                if (tier !== 'Certified') certs.push(tier + ' Dealer');

                                dealers.push({
                                    name,
                                    phone,
                                    website,
                                    street,
                                    city,
                                    state,
                                    zip,
                                    address_full: street ? `${street}, ${city}, ${state} ${zip}` : '',
                                    tier,
                                    distance,
                                    distance_miles,
                                    certifications: certs
                                });
                            });
                            break;
                        }
                    }
                }
                return dealers;
            }""")

            logger.info(f"Found {len(raw_dealers)} dealers")

            # Convert to dealer format
            for d in raw_dealers:
                dealer = {
                    'name': d.get('name', ''),
                    'phone': d.get('phone', ''),
                    'website': d.get('website', ''),
                    'street': d.get('street', ''),
                    'city': d.get('city', ''),
                    'state': d.get('state', ''),
                    'zip': d.get('zip', ''),
                    'address_full': d.get('address_full', ''),
                    'tier': d.get('tier', 'Certified'),
                    'distance': d.get('distance', ''),
                    'distance_miles': d.get('distance_miles', 0),
                    'certifications': d.get('certifications', []),
                    'scraped_zip': zip_code,
                    'oem': 'Kohler',
                    'scraped_at': datetime.now().isoformat()
                }
                dealers.append(dealer)

                logger.info(f"  {dealer['name']}: {dealer['phone']} | {dealer['tier']} | {dealer['city']}, {dealer['state']}")

            browser.close()
            logger.info("Browser closed")

    except Exception as e:
        logger.error(f"Scraper error: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # Save JSON output
    json_file = OUTPUT_DIR / f"kohler_{zip_code}_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump({
            'zip_code': zip_code,
            'scraped_at': datetime.now().isoformat(),
            'dealer_count': len(dealers),
            'dealers': dealers
        }, f, indent=2)

    logger.info(f"\n{'=' * 60}")
    logger.info(f"RESULTS: {len(dealers)} dealers scraped")
    logger.info(f"JSON: {json_file}")
    logger.info(f"LOG: {log_file}")
    logger.info(f"{'=' * 60}")

    return dealers

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python kohler_single_zip.py <ZIP_CODE>")
        print("Example: python kohler_single_zip.py 94102")
        sys.exit(1)

    zip_code = sys.argv[1]
    dealers = scrape_kohler_zip(zip_code)

    # Print summary
    print(f"\n📊 Summary for ZIP {zip_code}:")
    print(f"   Dealers: {len(dealers)}")
    with_phone = sum(1 for d in dealers if d.get('phone'))
    print(f"   With phone: {with_phone} ({with_phone/len(dealers)*100:.0f}%)" if dealers else "   With phone: 0")
