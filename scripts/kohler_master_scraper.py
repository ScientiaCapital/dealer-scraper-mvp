#!/usr/bin/env python3
"""
Kohler Master Scraper - Single JSON Output with Tracking

Features:
- One master JSON file with all dealers
- Tracks which ZIPs are completed
- Resumable (skip already-scraped ZIPs)
- Cleans up temp files
- Batch size control (default: 5)
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
BATCH_SIZE = 5
DELAY_BETWEEN_ZIPS = (2, 4)

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
    logger.info(f"Saved master JSON: {len(data['dealers'])} dealers from {len(data['completed_zips'])} ZIPs")

def get_all_zips():
    """Get all SREC state ZIP codes."""
    zips = []
    for state, state_zips in ZIP_CODES_SREC_ALL.items():
        zips.extend(state_zips)
    return zips

def scrape_single_zip(zip_code: str):
    """Scrape a single ZIP code and return dealers."""
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

            # Close modals
            page.evaluate("""() => {
                const osano = document.querySelector('.osano-cm-window');
                if (osano) osano.remove();
                const modals = document.querySelectorAll('[role="dialog"], .modal');
                modals.forEach(m => m.remove());
            }""")
            time.sleep(1)

            # Fill ZIP code
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

            # Extract dealers
            raw_dealers = page.evaluate(r"""() => {
                const dealers = [];
                const seen = new Set();
                const lists = document.querySelectorAll('ul');

                for (const ul of lists) {
                    const lis = ul.querySelectorAll('li');
                    if (lis.length >= 3) {
                        const firstText = lis[0]?.innerText || '';
                        if (firstText.includes('miles') || firstText.includes('Dealer')) {
                            lis.forEach((li) => {
                                const fullText = li.innerText || '';
                                if (!fullText.includes('miles')) return;

                                const phoneMatch = fullText.match(/\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g) || [];
                                let phone = '';
                                for (const ph of phoneMatch) {
                                    const clean = ph.replace(/\D/g, '');
                                    if (!clean.startsWith('844') && !clean.startsWith('800') && clean.length === 10) {
                                        phone = clean;
                                        break;
                                    }
                                }

                                if (phone && seen.has(phone)) return;
                                if (phone) seen.add(phone);

                                const paragraphs = li.querySelectorAll('p');
                                const name = paragraphs[0]?.textContent?.trim() || '';
                                if (!name) return;

                                const distMatch = fullText.match(/([\d.]+)\s*miles/i);
                                const distance = distMatch ? distMatch[1] + ' miles' : '';
                                const distance_miles = distMatch ? parseFloat(distMatch[1]) : 0;

                                let tier = 'Certified';
                                if (fullText.includes('Titanium Dealer')) tier = 'Titanium';
                                else if (fullText.includes('Platinum Dealer')) tier = 'Platinum';
                                else if (fullText.includes('Gold Dealer')) tier = 'Gold';
                                else if (fullText.includes('Silver Dealer')) tier = 'Silver';
                                else if (fullText.includes('Bronze Dealer')) tier = 'Bronze';

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

                                let website = '';
                                const links = li.querySelectorAll('a[href^="http"]');
                                for (const link of links) {
                                    if (!link.href.includes('rehlko') && !link.href.includes('kohler')) {
                                        website = link.href;
                                        break;
                                    }
                                }

                                const certs = [];
                                if (fullText.includes('Titan Certified')) certs.push('Titan Certified');
                                if (tier !== 'Certified') certs.push(tier + ' Dealer');

                                dealers.push({
                                    name, phone, website, street, city, state, zip,
                                    address_full: street ? `${street}, ${city}, ${state} ${zip}` : '',
                                    tier, distance, distance_miles, certifications: certs
                                });
                            });
                            break;
                        }
                    }
                }
                return dealers;
            }""")

            browser.close()

            # Add metadata
            for d in raw_dealers:
                d['scraped_zip'] = zip_code
                d['oem'] = 'Kohler'
                d['scraped_at'] = datetime.now().isoformat()
                dealers.append(d)

            return dealers

    except Exception as e:
        logger.error(f"Error scraping {zip_code}: {e}")
        return []

def run_batch(start_idx=0, batch_size=BATCH_SIZE):
    """Run a batch of ZIP codes."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_zips = get_all_zips()
    master_data = load_master_data()

    # Filter out already completed ZIPs
    pending_zips = [z for z in all_zips if z not in master_data['completed_zips']]

    if not pending_zips:
        logger.info("All ZIPs already scraped!")
        return

    # Select batch
    batch = pending_zips[start_idx:start_idx + batch_size]

    logger.info("=" * 60)
    logger.info(f"KOHLER BATCH: {len(batch)} ZIPs (starting at index {start_idx})")
    logger.info(f"Total pending: {len(pending_zips)} | Completed: {len(master_data['completed_zips'])}")
    logger.info("=" * 60)

    for i, zip_code in enumerate(batch, 1):
        logger.info(f"\n[{i}/{len(batch)}] Scraping ZIP: {zip_code}")

        dealers = scrape_single_zip(zip_code)

        if dealers:
            # Add unique dealers (by phone)
            existing_phones = {d.get('phone') for d in master_data['dealers'] if d.get('phone')}
            new_dealers = [d for d in dealers if d.get('phone') not in existing_phones]
            master_data['dealers'].extend(new_dealers)
            master_data['completed_zips'].append(zip_code)

            logger.info(f"  ✓ {len(dealers)} dealers found, {len(new_dealers)} new (Total: {len(master_data['dealers'])})")
        else:
            master_data['failed_zips'].append(zip_code)
            logger.warning(f"  ✗ No dealers found")

        # Save after each ZIP
        save_master_data(master_data)

        # Delay
        if i < len(batch):
            delay = random.uniform(*DELAY_BETWEEN_ZIPS)
            logger.info(f"  ⏳ Waiting {delay:.1f}s...")
            time.sleep(delay)

    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("BATCH COMPLETE")
    logger.info("=" * 60)
    logger.info(f"ZIPs completed: {len(master_data['completed_zips'])}/{len(all_zips)}")
    logger.info(f"ZIPs failed: {len(master_data['failed_zips'])}")
    logger.info(f"Total unique dealers: {len(master_data['dealers'])}")

    with_phone = sum(1 for d in master_data['dealers'] if d.get('phone'))
    logger.info(f"Phone coverage: {with_phone}/{len(master_data['dealers'])} ({with_phone/len(master_data['dealers'])*100:.0f}%)" if master_data['dealers'] else "Phone coverage: N/A")

    # Next batch hint
    next_idx = start_idx + batch_size
    remaining = len(pending_zips) - next_idx
    if remaining > 0:
        logger.info(f"\n📍 Next batch: python3 scripts/kohler_master_scraper.py {next_idx}")
    else:
        logger.info("\n✅ All ZIPs processed!")

def cleanup_temp_files():
    """Remove individual ZIP JSON/LOG files after merging to master."""
    count = 0
    for f in OUTPUT_DIR.glob("kohler_[0-9]*_*.json"):
        if f.name != "kohler_master.json":
            f.unlink()
            count += 1
    for f in OUTPUT_DIR.glob("kohler_[0-9]*_*.log"):
        if f.name != "kohler_master.log":
            f.unlink()
            count += 1
    if count > 0:
        logger.info(f"Cleaned up {count} temp files")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "clean":
            cleanup_temp_files()
        elif sys.argv[1] == "status":
            data = load_master_data()
            print(f"Completed ZIPs: {len(data['completed_zips'])}")
            print(f"Failed ZIPs: {len(data['failed_zips'])}")
            print(f"Total dealers: {len(data['dealers'])}")
        else:
            start_idx = int(sys.argv[1])
            batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else BATCH_SIZE
            run_batch(start_idx, batch_size)
    else:
        run_batch(0, BATCH_SIZE)
