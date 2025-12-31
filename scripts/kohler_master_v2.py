#!/usr/bin/env python3
"""
Kohler Master Scraper v2 - Card Clicking with Master Tracking

Features:
- Clicks into EACH dealer card for accurate data (like detail scraper)
- One master JSON file tracking all dealers
- Resumable (skip already-scraped ZIPs)
- Clean as we go (no temp file buildup)
"""

import sys
import os
import json
import time
import random
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ZIP_CODES_SREC_ALL

# Configuration
OUTPUT_DIR = Path("output/kohler")
MASTER_JSON = OUTPUT_DIR / "kohler_master.json"
MASTER_LOG = OUTPUT_DIR / "kohler_master.log"
DELAY_BETWEEN_ZIPS = (3, 6)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(MASTER_LOG),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_master_data():
    """Load existing master data or create new."""
    if MASTER_JSON.exists():
        with open(MASTER_JSON) as f:
            return json.load(f)
    return {
        'oem': 'Kohler',
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'completed_zips': [],
        'failed_zips': [],
        'total_dealers': 0,
        'dealers': []
    }

def save_master_data(data):
    """Save master data to JSON."""
    data['updated_at'] = datetime.now().isoformat()
    data['total_dealers'] = len(data['dealers'])
    with open(MASTER_JSON, 'w') as f:
        json.dump(data, f, indent=2)

def get_all_zips():
    """Get all SREC state ZIP codes."""
    zips = []
    for state, state_zips in ZIP_CODES_SREC_ALL.items():
        zips.extend(state_zips)
    return zips

def scrape_single_zip_with_clicks(zip_code: str):
    """Scrape a single ZIP with card clicking for full details."""
    try:
        from patchright.sync_api import sync_playwright

        dealers = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )

            page = context.new_page()
            page.goto("https://www.kohlerhomeenergy.rehlko.com/find-a-dealer", timeout=60000)
            time.sleep(5)

            # Dismiss cookie consent
            try:
                consent = page.locator('.osano-cm-button--type_accept').first
                if consent.is_visible(timeout=3000):
                    consent.click(force=True)
                    time.sleep(1)
            except:
                pass

            # Remove overlays
            page.evaluate("""() => {
                document.querySelectorAll('.osano-cm-window, [role="dialog"]').forEach(e => e.remove());
            }""")
            time.sleep(1)

            # Fill ZIP
            filled = False
            for selector in ['input[name="zipcode"]', 'input[placeholder*="ZIP" i]']:
                inputs = page.query_selector_all(selector)
                for inp in inputs:
                    try:
                        box = inp.bounding_box()
                        if box and box['width'] > 0 and box['height'] > 0 and box['y'] > 0:
                            inp.scroll_into_view_if_needed()
                            inp.click()
                            inp.fill('')
                            inp.type(zip_code, delay=100)
                            time.sleep(0.5)
                            if inp.input_value() == zip_code:
                                filled = True
                                break
                    except:
                        continue
                if filled:
                    break

            if not filled:
                logger.warning(f"Could not fill ZIP input for {zip_code}")
                browser.close()
                return []

            # Submit and wait
            page.keyboard.press('Enter')
            time.sleep(8)

            # Get dealer names from list
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
                                    if (name) items.push({ index: idx, name: name });
                                }
                            });
                            break;
                        }
                    }
                }
                return items;
            }""")

            logger.info(f"  Found {len(dealer_items)} dealers")

            # Click into each dealer for full details
            for i, item in enumerate(dealer_items):
                name = item['name']

                try:
                    # Click on dealer name
                    paragraphs = page.query_selector_all('p')
                    clicked = False
                    for p in paragraphs:
                        try:
                            if p.text_content() and p.text_content().strip() == name:
                                box = p.bounding_box()
                                if box and box['y'] > 0:
                                    p.click()
                                    clicked = True
                                    break
                        except:
                            continue

                    if not clicked:
                        continue

                    time.sleep(1.5)

                    # Extract from popup
                    detail = page.evaluate(r"""(dealerName) => {
                        let popup = null;
                        const allElements = document.querySelectorAll('div, section, article');

                        for (const el of allElements) {
                            const rect = el.getBoundingClientRect();
                            if (rect.x > 300 && rect.width > 200 && rect.width < 500 && rect.height > 150) {
                                const text = el.innerText || '';
                                if (text.includes(dealerName) && text.includes('miles')) {
                                    if (text.match(/\d{3}[-.\s]?\d{3}[-.\s]?\d{4}/)) {
                                        popup = el;
                                        break;
                                    }
                                }
                            }
                        }

                        if (!popup) {
                            for (const el of allElements) {
                                const text = el.innerText || '';
                                const rect = el.getBoundingClientRect();
                                if (rect.x > 250 && rect.width > 150 && rect.height > 100 && rect.height < 400) {
                                    if (text.startsWith(dealerName) || (text.includes(dealerName) && text.indexOf(dealerName) < 100)) {
                                        if (text.match(/\d{3}[-.\s]?\d{3}[-.\s]?\d{4}/) && text.includes('miles')) {
                                            popup = el;
                                            break;
                                        }
                                    }
                                }
                            }
                        }

                        const text = popup ? popup.innerText : '';
                        if (!text) return { phone: '', website: '', email: '', street: '', city: '', state: '', zip: '', tier: 'Certified', distance: '', certs: [] };

                        // Phone
                        let phone = '';
                        const phones = text.match(/\d{3}[-.\s]?\d{3}[-.\s]?\d{4}/g) || [];
                        for (const ph of phones) {
                            const clean = ph.replace(/\D/g, '');
                            if (!clean.startsWith('844') && !clean.startsWith('800') && !clean.startsWith('888') && !clean.startsWith('877') && clean.length === 10) {
                                phone = clean;
                                break;
                            }
                        }

                        // Website
                        let website = '';
                        if (popup) {
                            popup.querySelectorAll('a[href^="http"]').forEach(a => {
                                const href = a.href.toLowerCase();
                                const linkText = (a.innerText || '').toLowerCase();
                                if (!website && linkText.includes('website') && !href.includes('rehlko') && !href.includes('kohler') && !href.includes('azure') && !href.includes('aka.ms')) {
                                    website = a.href;
                                }
                            });
                        }

                        // Address
                        let street = '', city = '', state = '', zip = '';
                        let addrMatch = text.match(/(\d+[^,\n]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Way|Lane|Ln|Blvd|Court|Ct|Highway|Hwy|Circle|Cir|Place|Pl|Village)[^,\n]*),?\s*([A-Z][A-Za-z\s]+),?\s*([A-Z]{2})\s*(\d{5})/i);
                        if (!addrMatch) addrMatch = text.match(/(\d+\s+[A-Z][^,\n]{3,40}),?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),?\s*([A-Z]{2})\s*(\d{5})/);
                        if (addrMatch) {
                            street = addrMatch[1].trim().replace(/,\s*$/, '');
                            city = addrMatch[2].trim().replace(/,\s*$/, '');
                            state = addrMatch[3].toUpperCase();
                            zip = addrMatch[4];
                        }

                        // Tier
                        let tier = 'Certified';
                        if (text.includes('Titanium Dealer')) tier = 'Titanium';
                        else if (text.includes('Platinum Dealer')) tier = 'Platinum';
                        else if (text.includes('Gold Dealer')) tier = 'Gold';
                        else if (text.includes('Silver Dealer')) tier = 'Silver';
                        else if (text.includes('Bronze Dealer')) tier = 'Bronze';

                        const distMatch = text.match(/([\d.]+)\s*miles/i);
                        const distance = distMatch ? distMatch[1] + ' miles' : '';

                        const certs = [];
                        if (text.includes('Titan Certified')) certs.push('Titan Certified');
                        if (tier !== 'Certified') certs.push(tier + ' Dealer');

                        return { phone, website, street, city, state, zip, tier, distance, certs };
                    }""", name)

                    dealer = {
                        'name': name,
                        'phone': detail.get('phone', ''),
                        'website': detail.get('website', ''),
                        'street': detail.get('street', ''),
                        'city': detail.get('city', ''),
                        'state': detail.get('state', ''),
                        'zip': detail.get('zip', ''),
                        'address_full': f"{detail.get('street', '')}, {detail.get('city', '')}, {detail.get('state', '')} {detail.get('zip', '')}".strip(', ') if detail.get('street') else '',
                        'tier': detail.get('tier', 'Certified'),
                        'distance': detail.get('distance', ''),
                        'certifications': detail.get('certs', []),
                        'scraped_zip': zip_code,
                        'oem': 'Kohler',
                        'scraped_at': datetime.now().isoformat()
                    }
                    dealers.append(dealer)

                    # Close popup
                    page.keyboard.press('Escape')
                    time.sleep(1)

                except Exception as e:
                    logger.debug(f"Error with {name}: {e}")

            browser.close()
            return dealers

    except Exception as e:
        logger.error(f"Error scraping {zip_code}: {e}")
        return []

def run_batch(batch_size=5):
    """Run a batch of ZIP codes."""
    all_zips = get_all_zips()
    master_data = load_master_data()

    pending_zips = [z for z in all_zips if z not in master_data['completed_zips']]

    if not pending_zips:
        logger.info("All ZIPs already scraped!")
        return

    batch = pending_zips[:batch_size]

    logger.info("=" * 60)
    logger.info(f"KOHLER MASTER v2: {len(batch)} ZIPs")
    logger.info(f"Pending: {len(pending_zips)} | Completed: {len(master_data['completed_zips'])}")
    logger.info("=" * 60)

    for i, zip_code in enumerate(batch, 1):
        logger.info(f"\n[{i}/{len(batch)}] ZIP: {zip_code}")

        dealers = scrape_single_zip_with_clicks(zip_code)

        if dealers:
            existing_phones = {d.get('phone') for d in master_data['dealers'] if d.get('phone')}
            new_dealers = [d for d in dealers if d.get('phone') and d.get('phone') not in existing_phones]
            master_data['dealers'].extend(new_dealers)
            master_data['completed_zips'].append(zip_code)
            logger.info(f"  ✓ {len(dealers)} found, {len(new_dealers)} new (Total: {len(master_data['dealers'])})")
        else:
            master_data['failed_zips'].append(zip_code)
            logger.warning(f"  ✗ No dealers")

        save_master_data(master_data)

        if i < len(batch):
            delay = random.uniform(*DELAY_BETWEEN_ZIPS)
            logger.info(f"  ⏳ {delay:.1f}s...")
            time.sleep(delay)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("BATCH COMPLETE")
    logger.info(f"ZIPs: {len(master_data['completed_zips'])}/{len(all_zips)}")
    logger.info(f"Dealers: {len(master_data['dealers'])}")
    if master_data['dealers']:
        with_phone = sum(1 for d in master_data['dealers'] if d.get('phone'))
        logger.info(f"Phone coverage: {with_phone}/{len(master_data['dealers'])} ({with_phone/len(master_data['dealers'])*100:.0f}%)")
    logger.info("=" * 60)

if __name__ == "__main__":
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    run_batch(batch_size)
