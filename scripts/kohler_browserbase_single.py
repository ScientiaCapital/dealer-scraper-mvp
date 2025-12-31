#!/usr/bin/env python3
"""
Kohler Single ZIP Scraper with Browserbase + Card Clicking

Features:
- Uses Browserbase cloud browser (more reliable)
- Scrapes ONE ZIP at a time
- Clicks into EACH dealer card for full details
- Outputs JSON + LOG
"""

import sys
import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
OUTPUT_DIR = Path("output/kohler")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def setup_logging(zip_code: str):
    """Setup logging."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = OUTPUT_DIR / f"kohler_bb_{zip_code}_{timestamp}.log"

    logger = logging.getLogger(f"kohler_bb_{zip_code}")
    logger.setLevel(logging.DEBUG)
    logger.handlers = []  # Clear existing handlers

    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger, log_file, timestamp

def scrape_kohler_browserbase(zip_code: str):
    """Scrape Kohler dealers using Browserbase with card clicking."""
    logger, log_file, timestamp = setup_logging(zip_code)

    logger.info("=" * 60)
    logger.info(f"KOHLER BROWSERBASE SCRAPER - ZIP: {zip_code}")
    logger.info("=" * 60)

    dealers = []

    try:
        from browserbase import Browserbase
        from playwright.sync_api import sync_playwright

        # Initialize Browserbase
        bb_api_key = os.getenv("BROWSERBASE_API_KEY")
        bb_project_id = os.getenv("BROWSERBASE_PROJECT_ID")

        if not bb_api_key or not bb_project_id:
            logger.error("Missing BROWSERBASE_API_KEY or BROWSERBASE_PROJECT_ID")
            return []

        logger.info("Creating Browserbase session...")
        bb = Browserbase(api_key=bb_api_key)
        session = bb.sessions.create(project_id=bb_project_id)
        logger.info(f"Session created: {session.id}")

        with sync_playwright() as p:
            logger.info("Connecting to Browserbase...")
            browser = p.chromium.connect_over_cdp(session.connect_url)
            context = browser.contexts[0]
            page = context.pages[0]

            # Navigate to dealer locator
            url = "https://www.kohlerhomeenergy.rehlko.com/find-a-dealer"
            logger.info(f"Navigating to {url}")
            page.goto(url, timeout=60000)
            time.sleep(5)

            # Take screenshot
            page.screenshot(path=str(OUTPUT_DIR / f"kohler_bb_{zip_code}_1_initial.png"))
            logger.info("Screenshot: initial page")

            # Dismiss cookie consent
            logger.info("Checking for cookie consent...")
            try:
                consent = page.locator('.osano-cm-button--type_accept').first
                if consent.is_visible(timeout=5000):
                    consent.click(force=True)
                    logger.info("Dismissed cookie consent")
                    time.sleep(2)
            except Exception as e:
                logger.debug(f"No cookie consent: {e}")

            # Remove any overlays via JS
            page.evaluate("""() => {
                const osano = document.querySelector('.osano-cm-window');
                if (osano) osano.remove();
                document.querySelectorAll('[role="dialog"]').forEach(m => m.remove());
            }""")
            time.sleep(1)

            # Find and fill ZIP input
            logger.info(f"Entering ZIP code: {zip_code}")
            filled = False

            for selector in ['input[name="zipcode"]', 'input[placeholder*="ZIP" i]']:
                try:
                    inputs = page.query_selector_all(selector)
                    for inp in inputs:
                        box = inp.bounding_box()
                        if box and box['width'] > 0 and box['height'] > 0:
                            inp.scroll_into_view_if_needed()
                            time.sleep(0.5)
                            inp.click()
                            time.sleep(0.3)
                            inp.fill('')
                            inp.type(zip_code, delay=150)
                            time.sleep(0.5)

                            val = inp.input_value()
                            if val == zip_code:
                                logger.info(f"Entered ZIP: {val}")
                                filled = True
                                break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                if filled:
                    break

            if not filled:
                logger.error("Could not fill ZIP input")
                page.screenshot(path=str(OUTPUT_DIR / f"kohler_bb_{zip_code}_error.png"))
                browser.close()
                return []

            # Submit search
            logger.info("Pressing Enter to search...")
            page.keyboard.press('Enter')
            time.sleep(10)  # Wait for results

            # Screenshot after search
            page.screenshot(path=str(OUTPUT_DIR / f"kohler_bb_{zip_code}_2_results.png"))
            logger.info("Screenshot: search results")

            # Get list of dealer names first
            logger.info("Finding dealer cards...")
            dealer_names = page.evaluate(r"""() => {
                const names = [];
                const lists = document.querySelectorAll('ul');

                for (const ul of lists) {
                    const lis = ul.querySelectorAll('li');
                    if (lis.length >= 3) {
                        const firstText = lis[0]?.innerText || '';
                        if (firstText.includes('miles') || firstText.includes('Dealer')) {
                            lis.forEach(li => {
                                const text = li.innerText || '';
                                if (text.includes('miles')) {
                                    const name = li.querySelector('p')?.textContent?.trim();
                                    if (name) names.push(name);
                                }
                            });
                            break;
                        }
                    }
                }
                return names;
            }""")

            logger.info(f"Found {len(dealer_names)} dealers: {dealer_names}")

            # Click into EACH dealer card for full details
            for i, name in enumerate(dealer_names):
                logger.info(f"\n--- Dealer {i+1}/{len(dealer_names)}: {name} ---")

                try:
                    # Find and click the dealer name
                    dealer_elem = page.locator(f"text='{name}'").first
                    if dealer_elem.is_visible(timeout=3000):
                        dealer_elem.click()
                        logger.info(f"Clicked on: {name}")
                        time.sleep(3)

                        # Screenshot detail view
                        page.screenshot(path=str(OUTPUT_DIR / f"kohler_bb_{zip_code}_dealer_{i+1}.png"))

                        # Extract ALL details from detail view
                        detail = page.evaluate(r"""() => {
                            const body = document.body.innerText;

                            // Phone
                            let phone = '';
                            const phones = body.match(/\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g) || [];
                            for (const ph of phones) {
                                const clean = ph.replace(/\D/g, '');
                                if (!clean.startsWith('844') && !clean.startsWith('800') && clean.length === 10) {
                                    phone = clean;
                                    break;
                                }
                            }

                            // Website
                            let website = '';
                            document.querySelectorAll('a[href^="http"]').forEach(a => {
                                if (!website && !a.href.includes('rehlko') && !a.href.includes('kohler') &&
                                    !a.href.includes('google') && !a.href.includes('facebook')) {
                                    website = a.href;
                                }
                            });

                            // Email
                            const emailMatch = body.match(/[\w.-]+@[\w.-]+\.\w+/);
                            const email = emailMatch ? emailMatch[0] : '';

                            // Address
                            let street = '', city = '', state = '', zip = '';
                            const addrMatch = body.match(/(\d+[^,\n]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Way|Lane|Ln|Blvd|Court|Ct|Highway|Hwy)[^,]*),\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5})/i);
                            if (addrMatch) {
                                street = addrMatch[1].trim();
                                city = addrMatch[2].trim();
                                state = addrMatch[3].toUpperCase();
                                zip = addrMatch[4];
                            }

                            // Tier
                            let tier = 'Certified';
                            if (body.includes('Titanium Dealer')) tier = 'Titanium';
                            else if (body.includes('Platinum Dealer')) tier = 'Platinum';
                            else if (body.includes('Gold Dealer')) tier = 'Gold';
                            else if (body.includes('Silver Dealer')) tier = 'Silver';
                            else if (body.includes('Bronze Dealer')) tier = 'Bronze';

                            // Distance
                            const distMatch = body.match(/([\d.]+)\s*miles/i);
                            const distance = distMatch ? distMatch[1] + ' miles' : '';

                            // Services/Certifications
                            const services = [];
                            ['Installation', 'Service', 'Maintenance', 'Repair', 'Sales'].forEach(s => {
                                if (body.includes(s)) services.push(s);
                            });

                            const certifications = [];
                            if (body.includes('Titan Certified')) certifications.push('Titan Certified');
                            if (tier !== 'Certified') certifications.push(tier + ' Dealer');

                            return {
                                phone, website, email, street, city, state, zip, tier,
                                distance, services, certifications,
                                raw_text: body.substring(0, 1000)
                            };
                        }""")

                        dealer = {
                            'name': name,
                            'phone': detail.get('phone', ''),
                            'website': detail.get('website', ''),
                            'email': detail.get('email', ''),
                            'street': detail.get('street', ''),
                            'city': detail.get('city', ''),
                            'state': detail.get('state', ''),
                            'zip': detail.get('zip', ''),
                            'address_full': f"{detail.get('street', '')}, {detail.get('city', '')}, {detail.get('state', '')} {detail.get('zip', '')}" if detail.get('street') else '',
                            'tier': detail.get('tier', 'Certified'),
                            'distance': detail.get('distance', ''),
                            'services': detail.get('services', []),
                            'certifications': detail.get('certifications', []),
                            'scraped_zip': zip_code,
                            'oem': 'Kohler',
                            'scraped_at': datetime.now().isoformat()
                        }

                        dealers.append(dealer)

                        logger.info(f"  Phone: {dealer['phone']}")
                        logger.info(f"  Website: {dealer['website']}")
                        logger.info(f"  Address: {dealer['address_full']}")
                        logger.info(f"  Tier: {dealer['tier']}")

                        # Go back to list
                        page.keyboard.press('Escape')
                        time.sleep(2)

                except Exception as e:
                    logger.error(f"Error with {name}: {e}")
                    # Add basic info
                    dealers.append({
                        'name': name,
                        'scraped_zip': zip_code,
                        'oem': 'Kohler',
                        'error': str(e)
                    })

            browser.close()
            logger.info("Browser closed")

    except Exception as e:
        logger.error(f"Scraper error: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # Save JSON
    json_file = OUTPUT_DIR / f"kohler_bb_{zip_code}_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump({
            'zip_code': zip_code,
            'scraped_at': datetime.now().isoformat(),
            'dealer_count': len(dealers),
            'dealers': dealers
        }, f, indent=2)

    logger.info(f"\n{'=' * 60}")
    logger.info(f"RESULTS: {len(dealers)} dealers")
    logger.info(f"JSON: {json_file}")
    logger.info(f"LOG: {log_file}")
    logger.info(f"{'=' * 60}")

    return dealers

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python kohler_browserbase_single.py <ZIP_CODE>")
        print("Example: python kohler_browserbase_single.py 94102")
        sys.exit(1)

    zip_code = sys.argv[1]
    dealers = scrape_kohler_browserbase(zip_code)

    # Summary
    print(f"\n📊 Summary for ZIP {zip_code}:")
    print(f"   Dealers: {len(dealers)}")
    if dealers:
        with_phone = sum(1 for d in dealers if d.get('phone'))
        with_website = sum(1 for d in dealers if d.get('website'))
        print(f"   With phone: {with_phone} ({with_phone/len(dealers)*100:.0f}%)")
        print(f"   With website: {with_website} ({with_website/len(dealers)*100:.0f}%)")
