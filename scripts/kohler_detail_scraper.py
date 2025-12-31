#!/usr/bin/env python3
"""
Kohler Detail Scraper - Single ZIP with Card Clicking (Patchright)

Features:
- Uses Patchright (local stealth browser)
- Scrapes ONE ZIP at a time
- Clicks into EACH dealer card for full details
- Takes screenshots for audit
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
    log_file = OUTPUT_DIR / f"kohler_detail_{zip_code}_{timestamp}.log"

    logger = logging.getLogger(f"kohler_detail_{zip_code}")
    logger.setLevel(logging.DEBUG)
    logger.handlers = []

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

def scrape_kohler_detail(zip_code: str):
    """Scrape Kohler dealers with card clicking for full details."""
    logger, log_file, timestamp = setup_logging(zip_code)

    logger.info("=" * 60)
    logger.info(f"KOHLER DETAIL SCRAPER - ZIP: {zip_code}")
    logger.info("=" * 60)

    dealers = []

    try:
        from patchright.sync_api import sync_playwright

        with sync_playwright() as p:
            logger.info("Launching Patchright browser (headed)...")

            browser = p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )

            page = context.new_page()

            # Navigate
            url = "https://www.kohlerhomeenergy.rehlko.com/find-a-dealer"
            logger.info(f"Navigating to {url}")
            page.goto(url, timeout=60000)
            time.sleep(5)

            # Screenshot initial
            page.screenshot(path=str(OUTPUT_DIR / f"kohler_{zip_code}_1_initial.png"))
            logger.info("Screenshot: initial page")

            # Dismiss cookie consent
            logger.info("Dismissing cookie consent...")
            try:
                consent = page.locator('.osano-cm-button--type_accept').first
                if consent.is_visible(timeout=5000):
                    consent.click(force=True)
                    time.sleep(2)
                    logger.info("Cookie consent dismissed")
            except:
                pass

            # Remove overlays
            page.evaluate("""() => {
                document.querySelectorAll('.osano-cm-window, [role="dialog"]').forEach(e => e.remove());
            }""")
            time.sleep(1)

            # Fill ZIP
            logger.info(f"Entering ZIP: {zip_code}")
            filled = False
            for selector in ['input[name="zipcode"]', 'input[placeholder*="ZIP" i]']:
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
                            if inp.input_value() == zip_code:
                                filled = True
                                logger.info(f"ZIP entered: {zip_code}")
                                break
                    except:
                        continue
                if filled:
                    break

            if not filled:
                logger.error("Could not fill ZIP")
                page.screenshot(path=str(OUTPUT_DIR / f"kohler_{zip_code}_error.png"))
                browser.close()
                return []

            # Submit
            logger.info("Pressing Enter...")
            page.keyboard.press('Enter')
            time.sleep(10)

            # Screenshot results
            page.screenshot(path=str(OUTPUT_DIR / f"kohler_{zip_code}_2_results.png"))
            logger.info("Screenshot: results")

            # Find all dealer LI elements
            logger.info("Finding dealer cards...")

            # Get dealer list items with their indexes
            dealer_items = page.evaluate(r"""() => {
                const items = [];
                const lists = document.querySelectorAll('ul');

                for (const ul of lists) {
                    const lis = ul.querySelectorAll('li');
                    if (lis.length >= 3) {
                        const firstText = lis[0]?.innerText || '';
                        if (firstText.includes('miles') || firstText.includes('Dealer')) {
                            lis.forEach((li, idx) => {
                                const text = li.innerText || '';
                                if (text.includes('miles')) {
                                    const name = li.querySelector('p')?.textContent?.trim();
                                    if (name) {
                                        items.push({
                                            index: idx,
                                            name: name
                                        });
                                    }
                                }
                            });
                            break;
                        }
                    }
                }
                return items;
            }""")

            logger.info(f"Found {len(dealer_items)} dealer cards")

            # Process each dealer
            for i, item in enumerate(dealer_items):
                name = item['name']
                logger.info(f"\n--- [{i+1}/{len(dealer_items)}] {name} ---")

                try:
                    # Click on the dealer name/card
                    # Use a more reliable click - find by paragraph text
                    clicked = False

                    # Try clicking on the paragraph with the name
                    paragraphs = page.query_selector_all('p')
                    for p in paragraphs:
                        try:
                            if p.text_content() and p.text_content().strip() == name:
                                box = p.bounding_box()
                                if box and box['y'] > 0:
                                    p.click()
                                    clicked = True
                                    logger.info(f"Clicked on: {name}")
                                    break
                        except:
                            continue

                    if not clicked:
                        logger.warning(f"Could not click on {name}")
                        continue

                    time.sleep(3)

                    # Screenshot detail view
                    page.screenshot(path=str(OUTPUT_DIR / f"kohler_{zip_code}_dealer_{i+1}.png"))
                    logger.info(f"Screenshot: dealer {i+1}")

                    # Wait for detail popup to appear over the map
                    time.sleep(1.5)

                    # Extract from the POPUP PANEL on the right side (over the map)
                    # The popup shows: dealer name, badges, address, phone, website
                    detail = page.evaluate(r"""(dealerName) => {
                        // The popup panel appears over the map area (right side of screen)
                        // It contains the dealer name at the top, followed by details
                        // We need to find this specific popup, not the list on the left

                        // Strategy: Find elements positioned on the RIGHT side of the page (x > 400)
                        // that contain the dealer name
                        let popup = null;

                        // Look for the popup - it's a card/panel that appears over the map
                        // Check for elements that contain the dealer name and are positioned right
                        const allElements = document.querySelectorAll('div, section, article');
                        for (const el of allElements) {
                            const rect = el.getBoundingClientRect();
                            // Popup is on the right side (x > 300) and is a reasonable size
                            if (rect.x > 300 && rect.width > 200 && rect.width < 500 && rect.height > 150) {
                                const text = el.innerText || '';
                                // Check if this element starts with or contains the dealer name prominently
                                if (text.includes(dealerName) && text.includes('miles')) {
                                    // Check if this is the popup (has phone number and address)
                                    if (text.match(/\d{3}[-.\s]?\d{3}[-.\s]?\d{4}/)) {
                                        popup = el;
                                        break;
                                    }
                                }
                            }
                        }

                        // If no popup found, try a different approach - find by content structure
                        if (!popup) {
                            // Look for elements containing miles + phone near the dealer name
                            for (const el of allElements) {
                                const text = el.innerText || '';
                                const rect = el.getBoundingClientRect();
                                // Must be visible and on right side
                                if (rect.x > 250 && rect.width > 150 && rect.height > 100 && rect.height < 400) {
                                    // Must contain the dealer name AND a phone AND miles
                                    if (text.startsWith(dealerName) ||
                                        (text.includes(dealerName) && text.indexOf(dealerName) < 100)) {
                                        if (text.match(/\d{3}[-.\s]?\d{3}[-.\s]?\d{4}/) && text.includes('miles')) {
                                            popup = el;
                                            break;
                                        }
                                    }
                                }
                            }
                        }

                        // Extract from popup (or fallback to body)
                        const text = popup ? popup.innerText : '';

                        if (!text) {
                            return { phone: '', website: '', email: '', street: '', city: '', state: '', zip: '', tier: 'Certified', distance: '', certs: [], debug: 'no popup found' };
                        }

                        // Phone - from the popup text
                        let phone = '';
                        const phones = text.match(/\d{3}[-.\s]?\d{3}[-.\s]?\d{4}/g) || [];
                        for (const ph of phones) {
                            const clean = ph.replace(/\D/g, '');
                            if (!clean.startsWith('844') && !clean.startsWith('800') &&
                                !clean.startsWith('888') && !clean.startsWith('877') &&
                                clean.length === 10) {
                                phone = clean;
                                break;
                            }
                        }

                        // Website - look for links in the popup
                        let website = '';
                        if (popup) {
                            popup.querySelectorAll('a[href^="http"]').forEach(a => {
                                const href = a.href.toLowerCase();
                                const linkText = (a.innerText || '').toLowerCase();
                                if (!website && linkText.includes('website') &&
                                    !href.includes('rehlko') && !href.includes('kohler') &&
                                    !href.includes('google') && !href.includes('azure') &&
                                    !href.includes('aka.ms') && !href.includes('microsoft')) {
                                    website = a.href;
                                }
                            });
                        }

                        // Email
                        const emailMatch = text.match(/[\w.-]+@[\w.-]+\.\w+/);
                        const email = emailMatch ? emailMatch[0] : '';

                        // Address - look for pattern in popup text
                        let street = '', city = '', state = '', zip = '';

                        // Pattern: number + street, City, ST ZIP (or ST\nZIP)
                        let addrMatch = text.match(/(\d+[^,\n]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Way|Lane|Ln|Blvd|Court|Ct|Highway|Hwy|Circle|Cir|Place|Pl|Village)[^,\n]*),?\s*([A-Z][A-Za-z\s]+),?\s*([A-Z]{2})\s*(\d{5})/i);

                        if (!addrMatch) {
                            // Try simpler pattern
                            addrMatch = text.match(/(\d+\s+[A-Z][^,\n]{3,40}),?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),?\s*([A-Z]{2})\s*(\d{5})/);
                        }

                        if (addrMatch) {
                            street = addrMatch[1].trim().replace(/,\s*$/, '');
                            city = addrMatch[2].trim().replace(/,\s*$/, '');
                            state = addrMatch[3].toUpperCase();
                            zip = addrMatch[4];
                        }

                        // Tier - from popup badges
                        let tier = 'Certified';
                        if (text.includes('Titanium Dealer')) tier = 'Titanium';
                        else if (text.includes('Platinum Dealer')) tier = 'Platinum';
                        else if (text.includes('Gold Dealer')) tier = 'Gold';
                        else if (text.includes('Silver Dealer')) tier = 'Silver';
                        else if (text.includes('Bronze Dealer')) tier = 'Bronze';

                        // Distance
                        const distMatch = text.match(/([\d.]+)\s*miles/i);
                        const distance = distMatch ? distMatch[1] + ' miles' : '';

                        // Certifications
                        const certs = [];
                        if (text.includes('Titan Certified')) certs.push('Titan Certified');
                        if (tier !== 'Certified') certs.push(tier + ' Dealer');

                        return { phone, website, email, street, city, state, zip, tier, distance, certs, debug: text.substring(0, 200) };
                    }""", name)

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
                        'certifications': detail.get('certs', []),
                        'scraped_zip': zip_code,
                        'oem': 'Kohler',
                        'scraped_at': datetime.now().isoformat()
                    }

                    dealers.append(dealer)

                    logger.info(f"  Phone: {dealer['phone']}")
                    logger.info(f"  Website: {dealer['website']}")
                    logger.info(f"  Address: {dealer['address_full']}")
                    logger.info(f"  Tier: {dealer['tier']}")

                    # Go back - try multiple methods to close the detail panel
                    closed = False

                    # Method 1: Click a close/back button
                    try:
                        close_btns = page.query_selector_all('button, [role="button"]')
                        for btn in close_btns:
                            try:
                                text = btn.inner_text() or ''
                                aria = btn.get_attribute('aria-label') or ''
                                if any(x in text.lower() for x in ['close', 'back', '×', 'x']) or \
                                   any(x in aria.lower() for x in ['close', 'back', 'dismiss']):
                                    btn.click()
                                    closed = True
                                    logger.debug("Closed via button")
                                    break
                            except:
                                continue
                    except:
                        pass

                    if not closed:
                        # Method 2: Press Escape
                        page.keyboard.press('Escape')
                        time.sleep(0.5)

                        # Method 3: Click on the list area (left side of page)
                        try:
                            page.mouse.click(100, 400)  # Click near left side
                        except:
                            pass

                    time.sleep(1.5)

                except Exception as e:
                    logger.error(f"Error with {name}: {e}")

            browser.close()
            logger.info("Browser closed")

    except Exception as e:
        logger.error(f"Scraper error: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # Save JSON
    json_file = OUTPUT_DIR / f"kohler_detail_{zip_code}_{timestamp}.json"
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
        print("Usage: python kohler_detail_scraper.py <ZIP>")
        sys.exit(1)

    zip_code = sys.argv[1]
    dealers = scrape_kohler_detail(zip_code)

    print(f"\n📊 ZIP {zip_code}: {len(dealers)} dealers")
    if dealers:
        with_phone = sum(1 for d in dealers if d.get('phone'))
        print(f"   Phone: {with_phone}/{len(dealers)} ({with_phone/len(dealers)*100:.0f}%)")
