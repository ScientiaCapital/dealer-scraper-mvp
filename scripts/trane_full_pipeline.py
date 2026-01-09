#!/usr/bin/env python3
"""
Trane Full Pipeline - Directory Scrape + Detail Page Enrichment

A complete, robust pipeline that:
1. Scrapes the Trane dealer directory (all ~2,800 dealers)
2. Saves to JSON (audit trail) + SQLite (queryable)
3. Enriches each dealer with detail page data
4. Full logging to file + console
5. Checkpoint/resume support
6. BATCH MODE: Fresh browser session every N dealers (prevents timeout)

Output Files:
- output/trane/trane_directory_YYYYMMDD_HHMMSS.json  (raw directory data)
- output/trane/trane_enriched_YYYYMMDD_HHMMSS.json   (enriched data)
- output/pipeline.db                                  (SQLite database)
- logs/trane_pipeline_YYYYMMDD_HHMMSS.log            (full log)

Usage:
    python scripts/trane_full_pipeline.py                    # Full pipeline
    python scripts/trane_full_pipeline.py --step directory   # Only scrape directory
    python scripts/trane_full_pipeline.py --step enrich      # Only enrich (needs directory first)
    python scripts/trane_full_pipeline.py --test 20          # Test with 20 dealers
    python scripts/trane_full_pipeline.py --resume           # Resume from checkpoint
    python scripts/trane_full_pipeline.py --batch-size 300   # Custom batch size
"""

import os
import sys
import json
import time
import logging
import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

# Configuration
BROWSERBASE_API_KEY = os.getenv('BROWSERBASE_API_KEY')
BROWSERBASE_PROJECT_ID = os.getenv('BROWSERBASE_PROJECT_ID')

DB_PATH = PROJECT_ROOT / 'output' / 'pipeline.db'
OUTPUT_DIR = PROJECT_ROOT / 'output' / 'trane'
LOG_DIR = PROJECT_ROOT / 'logs'

# Rate limiting
DELAY_BETWEEN_REQUESTS = 3.0
DEFAULT_BATCH_SIZE = 400  # Fresh session every 400 dealers
MAX_RETRIES = 3
MAX_CONSECUTIVE_FAILURES = 5  # Refresh session after this many consecutive failures

# Special return value to indicate session is dead
SESSION_DEAD = "SESSION_DEAD"

# URLs
TRANE_DIRECTORY_URL = "https://www.trane.com/residential/en/dealers/"


def setup_logging(run_id: str) -> logging.Logger:
    """Set up logging to both file and console."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f'trane_pipeline_{run_id}.log'

    # Create logger
    logger = logging.getLogger('trane_pipeline')
    logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    logger.handlers = []

    # File handler (detailed)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler (summary)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    logger.info(f"Logging to: {log_file}")
    return logger


def get_directory_extraction_script() -> str:
    """JavaScript to extract dealer directory table."""
    return r"""
() => {
    const dealers = [];

    // Find the main dealer table
    const tables = document.querySelectorAll('table');

    for (const table of tables) {
        const rows = table.querySelectorAll('tbody tr');
        if (rows.length < 10) continue;  // Skip small tables

        console.log(`Found table with ${rows.length} rows`);

        rows.forEach((row, idx) => {
            const cells = row.querySelectorAll('td');
            if (cells.length < 4) return;

            // Find dealer detail link
            const link = row.querySelector('a[href*="/dealers/"]');
            const detailUrl = link ? link.href : '';

            // Extract slug from URL for ID
            let slug = '';
            if (detailUrl) {
                const match = detailUrl.match(/\/dealers\/([^\/]+)\/?$/);
                if (match) slug = match[1];
            }

            const dealer = {
                row_index: idx,
                name: cells[0]?.textContent?.trim() || '',
                state: cells[1]?.textContent?.trim() || '',
                city: cells[2]?.textContent?.trim() || '',
                zip: cells[3]?.textContent?.trim() || '',
                country: cells[4]?.textContent?.trim() || 'USA',
                detail_url: detailUrl,
                slug: slug
            };

            // Only add if we have a name
            if (dealer.name && dealer.name.length > 2) {
                dealers.push(dealer);
            }
        });
    }

    return dealers;
}
"""


def get_detail_extraction_script() -> str:
    """JavaScript to extract detail page enrichment data."""
    return r"""
() => {
    const result = {
        google_rating: null,
        google_review_count: null,
        business_hours: {},
        certifications: [],
        has_emergency_service: false,
        has_financing: false,
        financing_provider: null,
        phone: null,
        address: null,
        website: null
    };

    const pageText = document.body.innerText;
    const pageHtml = document.body.innerHTML;

    // Google Rating + Review Count
    // Pattern: "4.9\n347 Google Reviews" or "4.9 347 Google Reviews"
    const googlePattern = /(\d+\.?\d*)\s*\n?\s*(\d+)\s*Google\s*Reviews?/i;
    const match = pageText.match(googlePattern);
    if (match) {
        const rating = parseFloat(match[1]);
        if (rating >= 1 && rating <= 5) {
            result.google_rating = rating;
        }
        result.google_review_count = parseInt(match[2]);
    }

    // Fallback for review count only
    if (!result.google_review_count) {
        const reviewMatch = pageText.match(/(\d+)\s*Google\s*Reviews?/i);
        if (reviewMatch) {
            result.google_review_count = parseInt(reviewMatch[1]);
        }
    }

    // Certifications
    const certs = [
        'Trane Comfort Specialist', 'NATE Certified', 'NATE',
        'EPA Certified', 'BBB Accredited', 'Dealer of Excellence',
        'Premier Dealer', 'Authorized Dealer', 'TCS'
    ];
    certs.forEach(cert => {
        if (pageText.includes(cert) && !result.certifications.includes(cert)) {
            result.certifications.push(cert);
        }
    });

    // Emergency Service
    result.has_emergency_service = /24\/?7|emergency|after.?hours/i.test(pageText);

    // Financing
    result.has_financing = /financing|finance|payment plan/i.test(pageText);
    if (pageText.includes('Wells Fargo')) result.financing_provider = 'Wells Fargo';
    else if (pageText.includes('Synchrony')) result.financing_provider = 'Synchrony';

    // Phone (exclude toll-free)
    const phoneLinks = document.querySelectorAll('a[href^="tel:"]');
    const tollFree = ['800', '888', '877', '866', '855', '844', '833'];
    for (const link of phoneLinks) {
        const phone = link.href.replace('tel:', '').replace(/[^0-9]/g, '');
        if (phone.length >= 10) {
            const areaCode = phone.slice(-10, -7);
            if (!tollFree.includes(areaCode)) {
                result.phone = phone.slice(-10);
                break;
            }
        }
    }

    // Address - look for structured address
    const addressEl = document.querySelector('[class*="address"], [itemprop="address"]');
    if (addressEl) {
        result.address = addressEl.textContent.trim().replace(/\s+/g, ' ');
    }

    // Website
    const websiteLinks = document.querySelectorAll('a[href^="http"]:not([href*="trane.com"]):not([href*="google"])');
    for (const link of websiteLinks) {
        const href = link.href;
        if (href.includes('.com') || href.includes('.net') || href.includes('.org')) {
            result.website = href;
            break;
        }
    }

    // Business Hours
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    days.forEach(day => {
        const pattern = new RegExp(day + '[:\\s]+([0-9:APMapm\\s\\-]+?)(?=\\s*(?:Tue|Wed|Thu|Fri|Sat|Sun|$))', 'i');
        const match = pageText.match(pattern);
        if (match) {
            let hours = match[1].trim();
            if (hours.length > 0 && hours.length < 30) {
                result.business_hours[day] = hours;
            }
        }
    });

    return result;
}
"""


class TranePipeline:
    """Complete Trane scraping and enrichment pipeline with batch mode."""

    def __init__(self, run_id: str, logger: logging.Logger, batch_size: int = DEFAULT_BATCH_SIZE):
        self.run_id = run_id
        self.logger = logger
        self.batch_size = batch_size
        self.stats = {
            'directory_scraped': 0,
            'enriched': 0,
            'with_rating': 0,
            'with_phone': 0,
            'failed': 0,
            'skipped_404': 0,
            'batches_completed': 0
        }
        self.checkpoint_file = OUTPUT_DIR / f'checkpoint_{run_id}.json'
        self.enriched_dealers = []

    def save_checkpoint(self, processed_ids: Set[int], step: str):
        """Save checkpoint for resume - called after EVERY dealer."""
        data = {
            'run_id': self.run_id,
            'step': step,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'stats': self.stats,
            'processed_ids': list(processed_ids),
            'batch_size': self.batch_size
        }
        with open(self.checkpoint_file, 'w') as f:
            json.dump(data, f, indent=2)
        self.logger.debug(f"Checkpoint saved: {len(processed_ids)} processed")

    def load_checkpoint(self) -> tuple:
        """Load most recent checkpoint from any run."""
        # Look for any checkpoint file
        checkpoint_files = sorted(OUTPUT_DIR.glob('checkpoint_*.json'), reverse=True)
        if checkpoint_files:
            with open(checkpoint_files[0]) as f:
                data = json.load(f)
            self.stats = data.get('stats', self.stats)
            processed = set(data.get('processed_ids', []))
            self.logger.info(f"Loaded checkpoint: {len(processed)} already processed")
            return processed, data.get('step', '')
        return set(), ''

    def scrape_directory(self, page) -> List[Dict[str, Any]]:
        """Scrape the full Trane dealer directory."""
        self.logger.info("=" * 60)
        self.logger.info("STEP 1: Scraping Trane Dealer Directory")
        self.logger.info("=" * 60)

        self.logger.info(f"Navigating to: {TRANE_DIRECTORY_URL}")
        page.goto(TRANE_DIRECTORY_URL, timeout=90000, wait_until='domcontentloaded')
        time.sleep(5)  # Let page fully load

        # Handle cookie banner
        try:
            cookie_btn = page.locator('button:has-text("Continue"), button:has-text("Accept")').first
            if cookie_btn.count() > 0:
                cookie_btn.click(timeout=3000)
                self.logger.debug("Clicked cookie banner")
                time.sleep(1)
        except:
            pass

        # Try to show all entries
        try:
            select = page.locator('select[name*="length"]').first
            if select.count() > 0:
                select.select_option('-1')
                self.logger.info("Selected 'Show All' in table")
                time.sleep(5)
        except Exception as e:
            self.logger.debug(f"No 'Show All' dropdown: {e}")

        # Wait for table
        page.wait_for_selector('table tbody tr', timeout=60000)

        # Extract dealers
        dealers = page.evaluate(get_directory_extraction_script())

        self.stats['directory_scraped'] = len(dealers)
        self.logger.info(f"Extracted {len(dealers)} dealers from directory")

        # Save raw directory data
        output_file = OUTPUT_DIR / f'trane_directory_{self.run_id}.json'
        with open(output_file, 'w') as f:
            json.dump({
                'scraped_at': datetime.now(timezone.utc).isoformat(),
                'source_url': TRANE_DIRECTORY_URL,
                'total_count': len(dealers),
                'dealers': dealers
            }, f, indent=2)
        self.logger.info(f"Saved directory to: {output_file}")

        return dealers

    def save_to_sqlite(self, dealers: List[Dict[str, Any]]):
        """Save dealers to SQLite with proper structure."""
        self.logger.info("Saving dealers to SQLite...")

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Ensure schema is initialized
        from database import PipelineDB
        db = PipelineDB(DB_PATH)
        db.initialize()

        new_count = 0
        updated_count = 0

        for dealer in dealers:
            name = dealer.get('name', '').strip()
            if not name:
                continue

            # Normalize name for dedup
            normalized = name.lower().strip()
            normalized = ' '.join(normalized.split())  # Normalize whitespace

            state = dealer.get('state', '').upper().strip()
            city = dealer.get('city', '').strip()
            zip_code = dealer.get('zip', '').strip()

            # Check if exists
            cursor.execute("""
                SELECT id FROM contractors
                WHERE normalized_name = ? AND state = ?
            """, (normalized, state))

            existing = cursor.fetchone()

            if existing:
                contractor_id = existing[0]
                updated_count += 1
            else:
                # Insert new contractor
                cursor.execute("""
                    INSERT INTO contractors (
                        company_name, normalized_name, city, state, zip, source_type
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (name, normalized, city, state, zip_code, 'oem_dealer'))
                contractor_id = cursor.lastrowid
                new_count += 1

            # Add OEM certification
            cursor.execute("""
                INSERT OR IGNORE INTO oem_certifications (
                    contractor_id, oem_name, certification_tier, source_url
                ) VALUES (?, ?, ?, ?)
            """, (
                contractor_id,
                'Trane',
                'Authorized Dealer',
                dealer.get('detail_url', '')
            ))

        conn.commit()
        conn.close()

        self.logger.info(f"SQLite: {new_count} new, {updated_count} existing")

    def _is_session_dead_error(self, error: Exception) -> bool:
        """Check if error indicates the browser session has died."""
        error_str = str(error).lower()
        dead_indicators = [
            'browser has been closed',
            'target page, context or browser',
            'session closed',
            'connection closed',
            'target closed',
            'page closed'
        ]
        return any(indicator in error_str for indicator in dead_indicators)

    def _enrich_single_dealer(self, page, dealer: Dict, idx: int, total: int):
        """Enrich a single dealer with retry logic.

        Returns:
            - Dict: Enriched dealer data on success
            - None: On regular failure (404, timeout, etc.)
            - SESSION_DEAD: If browser session has died (caller should create new session)
        """
        name = dealer.get('name', 'Unknown')[:35]
        detail_url = dealer.get('detail_url', '')

        if not detail_url:
            self.logger.warning(f"[{idx}/{total}] {name} - No detail URL")
            self.stats['skipped_404'] += 1
            return None

        self.logger.info(f"[{idx}/{total}] {name}...")

        for attempt in range(MAX_RETRIES):
            try:
                page.goto(detail_url, timeout=30000, wait_until='domcontentloaded')
                time.sleep(1.5)

                # Check for 404
                if "Page Not Found" in page.content() or "404" in page.title():
                    self.logger.warning(f"  -> 404 Not Found")
                    self.stats['skipped_404'] += 1
                    return None

                # Extract enrichment
                enrichment = page.evaluate(get_detail_extraction_script())

                # Merge with original data
                enriched = {**dealer, **enrichment, 'enriched_at': datetime.now(timezone.utc).isoformat()}

                # Update stats
                self.stats['enriched'] += 1
                if enrichment.get('google_rating'):
                    self.stats['with_rating'] += 1
                if enrichment.get('phone'):
                    self.stats['with_phone'] += 1

                # Log result
                rating = enrichment.get('google_rating', '-')
                reviews = enrichment.get('google_review_count', '-')
                phone = enrichment.get('phone', '')[:6] + '...' if enrichment.get('phone') else '-'
                self.logger.info(f"  -> Rating: {rating} | Reviews: {reviews} | Phone: {phone}")

                # Save enrichment to SQLite
                self._save_enrichment_to_sqlite(dealer, enrichment)

                return enriched

            except Exception as e:
                # Check if session is dead - no point in retrying
                if self._is_session_dead_error(e):
                    self.logger.error(f"  -> SESSION DEAD: {str(e)[:50]}")
                    return SESSION_DEAD

                if attempt < MAX_RETRIES - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    self.logger.warning(f"  -> Retry {attempt + 1}/{MAX_RETRIES}: {str(e)[:40]}... (waiting {wait_time}s)")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"  -> FAILED after {MAX_RETRIES} attempts: {str(e)[:60]}")
                    self.stats['failed'] += 1
                    return None

        return None

    def _create_new_session(self, bb, p):
        """Create a new Browserbase session and return browser, page."""
        session = bb.sessions.create(project_id=BROWSERBASE_PROJECT_ID)
        self.logger.info(f"  >> New session created: {session.id}")
        browser = p.chromium.connect_over_cdp(session.connect_url)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        return session, browser, page

    def _release_session(self, bb, session):
        """Release a Browserbase session."""
        try:
            bb.sessions.update(session.id, project_id=BROWSERBASE_PROJECT_ID, status="REQUEST_RELEASE")
            self.logger.debug(f"Session {session.id} released")
        except:
            pass

    def enrich_dealers_batch(self, dealers: List[Dict[str, Any]],
                             processed_ids: Set[int], limit: Optional[int] = None):
        """Enrich dealers in batches with fresh browser sessions and session recovery."""
        from browserbase import Browserbase
        from playwright.sync_api import sync_playwright

        self.logger.info("=" * 60)
        self.logger.info("STEP 2: Enriching Dealer Detail Pages (BATCH MODE + RECOVERY)")
        self.logger.info("=" * 60)

        # Filter to unprocessed
        to_process = [(i, d) for i, d in enumerate(dealers) if i not in processed_ids]
        if limit:
            to_process = to_process[:limit]

        total = len(to_process)
        if total == 0:
            self.logger.info("All dealers already processed!")
            return

        num_batches = (total + self.batch_size - 1) // self.batch_size
        self.logger.info(f"Dealers to enrich: {total}")
        self.logger.info(f"Batch size: {self.batch_size}")
        self.logger.info(f"Number of batches: {num_batches}")
        self.logger.info(f"Rate limit: {DELAY_BETWEEN_REQUESTS}s between requests")
        self.logger.info(f"Estimated time: ~{total * DELAY_BETWEEN_REQUESTS / 60:.1f} minutes")
        self.logger.info("-" * 60)

        bb = Browserbase(api_key=BROWSERBASE_API_KEY)
        batch_num = 0

        while to_process:
            batch_num += 1
            batch = to_process[:self.batch_size]
            to_process = to_process[self.batch_size:]

            self.logger.info("")
            self.logger.info(f"{'='*60}")
            self.logger.info(f"  BATCH {batch_num}/{num_batches}: {len(batch)} dealers")
            self.logger.info(f"{'='*60}")

            # Create fresh Browserbase session for this batch
            session = bb.sessions.create(project_id=BROWSERBASE_PROJECT_ID)
            self.logger.info(f"New session: {session.id}")

            try:
                with sync_playwright() as p:
                    browser = p.chromium.connect_over_cdp(session.connect_url)
                    context = browser.contexts[0]
                    page = context.pages[0] if context.pages else context.new_page()

                    consecutive_failures = 0
                    batch_idx = 0

                    while batch_idx < len(batch):
                        global_idx, dealer = batch[batch_idx]

                        # Calculate display numbers correctly
                        processed_so_far = self.stats['enriched'] + self.stats['skipped_404'] + self.stats['failed']
                        display_num = processed_so_far + 1

                        result = self._enrich_single_dealer(page, dealer, display_num, total)

                        # Handle session death
                        if result == SESSION_DEAD:
                            self.logger.warning(f"  >> Session died, creating new session...")
                            # Close old browser (may already be closed)
                            try:
                                browser.close()
                            except:
                                pass
                            self._release_session(bb, session)

                            # Create new session
                            session, browser, page = self._create_new_session(bb, p)
                            consecutive_failures = 0

                            # Retry this dealer with new session
                            result = self._enrich_single_dealer(page, dealer, display_num, total)

                        # Track consecutive failures
                        if result is None or result == SESSION_DEAD:
                            consecutive_failures += 1
                            # Preemptively refresh if too many failures
                            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                                self.logger.warning(f"  >> {consecutive_failures} consecutive failures, refreshing session...")
                                try:
                                    browser.close()
                                except:
                                    pass
                                self._release_session(bb, session)
                                session, browser, page = self._create_new_session(bb, p)
                                consecutive_failures = 0
                        else:
                            consecutive_failures = 0

                        # Success - add to enriched list
                        if result and result != SESSION_DEAD:
                            self.enriched_dealers.append(result)

                        # Mark as processed regardless of success
                        processed_ids.add(global_idx)

                        # Save checkpoint after EVERY dealer
                        self.save_checkpoint(processed_ids, 'enrich')

                        # Rate limit
                        time.sleep(DELAY_BETWEEN_REQUESTS)

                        batch_idx += 1

                    browser.close()

            except Exception as e:
                self.logger.error(f"Batch {batch_num} error: {str(e)[:80]}")
                # Don't lose progress - checkpoint already saved per dealer

            finally:
                # Release session
                self._release_session(bb, session)

            self.stats['batches_completed'] = batch_num

            # Save intermediate enriched data after each batch
            interim_file = OUTPUT_DIR / f'trane_enriched_interim_{self.run_id}.json'
            with open(interim_file, 'w') as f:
                json.dump({
                    'saved_at': datetime.now(timezone.utc).isoformat(),
                    'count': len(self.enriched_dealers),
                    'stats': self.stats,
                    'dealers': self.enriched_dealers
                }, f, indent=2)
            self.logger.info(f"Batch {batch_num} complete. Total enriched: {len(self.enriched_dealers)}")

        # Save final enriched data
        output_file = OUTPUT_DIR / f'trane_enriched_{self.run_id}.json'
        with open(output_file, 'w') as f:
            json.dump({
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'total_enriched': len(self.enriched_dealers),
                'stats': self.stats,
                'dealers': self.enriched_dealers
            }, f, indent=2)
        self.logger.info(f"Saved final enriched data to: {output_file}")

    def _save_enrichment_to_sqlite(self, dealer: Dict, enrichment: Dict):
        """Save enrichment data to dealer_enrichments table."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Find contractor by name + state
        name = dealer.get('name', '').strip()
        normalized = name.lower().strip()
        normalized = ' '.join(normalized.split())
        state = dealer.get('state', '').upper().strip()

        cursor.execute("""
            SELECT id FROM contractors
            WHERE normalized_name = ? AND state = ?
        """, (normalized, state))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return

        contractor_id = row[0]

        # Insert/update enrichment
        cursor.execute("""
            INSERT OR REPLACE INTO dealer_enrichments (
                contractor_id, oem_name, google_rating, google_review_count,
                business_hours, dealer_certifications,
                has_emergency_service, has_financing, financing_provider,
                detail_url, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            contractor_id,
            'Trane',
            enrichment.get('google_rating'),
            enrichment.get('google_review_count'),
            json.dumps(enrichment.get('business_hours', {})),
            json.dumps(enrichment.get('certifications', [])),
            1 if enrichment.get('has_emergency_service') else 0,
            1 if enrichment.get('has_financing') else 0,
            enrichment.get('financing_provider'),
            dealer.get('detail_url', ''),
            datetime.now(timezone.utc).isoformat()
        ))

        # Update phone if found
        phone = enrichment.get('phone')
        if phone:
            cursor.execute("""
                UPDATE contractors SET primary_phone = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND (primary_phone IS NULL OR primary_phone = '')
            """, (phone, contractor_id))

        conn.commit()
        conn.close()

    def print_summary(self):
        """Print final summary."""
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("PIPELINE COMPLETE")
        self.logger.info("=" * 60)
        self.logger.info(f"Directory scraped:   {self.stats['directory_scraped']}")
        self.logger.info(f"Dealers enriched:    {self.stats['enriched']}")
        self.logger.info(f"With Google rating:  {self.stats['with_rating']}")
        self.logger.info(f"With local phone:    {self.stats['with_phone']}")
        self.logger.info(f"404/Not found:       {self.stats['skipped_404']}")
        self.logger.info(f"Failed:              {self.stats['failed']}")
        self.logger.info(f"Batches completed:   {self.stats['batches_completed']}")
        self.logger.info("=" * 60)
        self.logger.info(f"Output files in: {OUTPUT_DIR}")
        self.logger.info(f"Logs in: {LOG_DIR}")


def main():
    parser = argparse.ArgumentParser(description='Trane Full Pipeline')
    parser.add_argument('--step', choices=['directory', 'enrich', 'all'],
                        default='all', help='Which step to run')
    parser.add_argument('--test', type=int, help='Test with N dealers')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE,
                        help=f'Dealers per batch (default: {DEFAULT_BATCH_SIZE})')
    args = parser.parse_args()

    # Validate env
    if not all([BROWSERBASE_API_KEY, BROWSERBASE_PROJECT_ID]):
        print("ERROR: Missing BROWSERBASE_API_KEY or BROWSERBASE_PROJECT_ID")
        print("Set these in .env file")
        sys.exit(1)

    # Create output dirs
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate run ID
    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Setup logging
    logger = setup_logging(run_id)

    logger.info("")
    logger.info("=" * 60)
    logger.info("  TRANE FULL PIPELINE (BATCH MODE)")
    logger.info("=" * 60)
    logger.info(f"  Run ID: {run_id}")
    logger.info(f"  Step: {args.step}")
    logger.info(f"  Batch size: {args.batch_size}")
    logger.info(f"  Test mode: {args.test if args.test else 'No (full run)'}")
    logger.info(f"  Resume: {args.resume}")
    logger.info("=" * 60)

    # Initialize pipeline
    pipeline = TranePipeline(run_id, logger, batch_size=args.batch_size)

    # Load checkpoint if resuming
    processed_ids = set()
    if args.resume:
        processed_ids, last_step = pipeline.load_checkpoint()

    dealers = []

    # Step 1: Directory scrape (requires single session)
    if args.step in ['directory', 'all']:
        from browserbase import Browserbase
        from playwright.sync_api import sync_playwright

        bb = Browserbase(api_key=BROWSERBASE_API_KEY)
        session = bb.sessions.create(project_id=BROWSERBASE_PROJECT_ID)
        logger.info(f"Directory scrape session: {session.id}")

        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(session.connect_url)
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else context.new_page()

                dealers = pipeline.scrape_directory(page)
                pipeline.save_to_sqlite(dealers)

                browser.close()
        finally:
            try:
                bb.sessions.update(session.id, project_id=BROWSERBASE_PROJECT_ID, status="REQUEST_RELEASE")
            except:
                pass

    # Load existing directory if only enriching
    if args.step == 'enrich':
        # Find most recent directory file
        dir_files = sorted(OUTPUT_DIR.glob('trane_directory_*.json'), reverse=True)
        if not dir_files:
            logger.error("No directory file found. Run --step directory first.")
            sys.exit(1)
        with open(dir_files[0]) as f:
            data = json.load(f)
        dealers = data.get('dealers', [])
        logger.info(f"Loaded {len(dealers)} dealers from {dir_files[0].name}")

    # Step 2: Enrichment (uses batch mode with fresh sessions)
    if args.step in ['enrich', 'all'] and dealers:
        limit = args.test if args.test else None
        pipeline.enrich_dealers_batch(dealers, processed_ids, limit)

    pipeline.print_summary()


if __name__ == '__main__':
    main()
