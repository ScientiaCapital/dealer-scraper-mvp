#!/usr/bin/env python3
"""
Trane Detail Page Enrichment Script (SQLite Version)

Enriches existing Trane dealers in SQLite with data from their detail pages:
- Google ratings and review counts
- Certifications (Trane Comfort Specialist, NATE, etc.)
- Business hours
- Emergency service availability
- Financing options

Usage:
    python scripts/trane_enrich_detail_pages.py              # Enrich all unenriched
    python scripts/trane_enrich_detail_pages.py --test 50    # Test with 50 dealers
    python scripts/trane_enrich_detail_pages.py --resume     # Resume from checkpoint
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

# Load environment
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

BROWSERBASE_API_KEY = os.getenv('BROWSERBASE_API_KEY')
BROWSERBASE_PROJECT_ID = os.getenv('BROWSERBASE_PROJECT_ID')

# Database and output paths
DB_PATH = Path(__file__).parent.parent / 'output' / 'pipeline.db'
CHECKPOINT_DIR = Path(__file__).parent.parent / 'output' / 'trane_enrichment'

# Rate limiting (from trane_scraper.py)
DELAY_BETWEEN_REQUESTS = 3.0
CHECKPOINT_INTERVAL = 100


def get_extraction_script():
    """JavaScript extraction for Trane detail pages (from trane_scraper.py)."""
    return r"""
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

    // Google Rating + Review Count
    const googleReviewPattern = /(\d+\.?\d*)\s*\n?\s*(\d+)\s*Google\s*Reviews?/i;
    const combinedMatch = pageText.match(googleReviewPattern);
    if (combinedMatch) {
        const possibleRating = parseFloat(combinedMatch[1]);
        if (possibleRating >= 1 && possibleRating <= 5) {
            result.google_rating = possibleRating;
        }
        result.google_review_count = parseInt(combinedMatch[2]);
    }

    // Fallback: just get review count
    if (!result.google_review_count) {
        const reviewMatch = pageText.match(/(\d+)\s*Google\s*Reviews?/i);
        if (reviewMatch) {
            result.google_review_count = parseInt(reviewMatch[1]);
        }
    }

    // If we have reviews but no rating, look for standalone rating
    if (result.google_review_count && !result.google_rating) {
        const lines = pageText.split('\n').map(l => l.trim());
        for (let i = 0; i < lines.length; i++) {
            if (lines[i].includes('Google Review')) {
                for (let j = 1; j <= 3; j++) {
                    if (i - j >= 0) {
                        const possibleRating = parseFloat(lines[i-j]);
                        if (possibleRating >= 1 && possibleRating <= 5) {
                            result.google_rating = possibleRating;
                            break;
                        }
                    }
                }
                break;
            }
        }
    }

    // Certifications
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
        const tollFreePrefix = ['800', '888', '877', '866', '855', '844', '833'];
        if (phone.length >= 10) {
            const areaCode = phone.slice(-10, -7);
            if (!tollFreePrefix.includes(areaCode)) {
                result.phone = phone.slice(-10);
            }
        }
    });

    // Business Hours
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    days.forEach(day => {
        const dayRegex = new RegExp(day + '[:\\s]+([0-9:APMapm\\s\\-A-Za-z]+?)(?=\\n|Tue|Wed|Thu|Fri|Sat|Sun|$)', 'i');
        const match = pageText.match(dayRegex);
        if (match) {
            let hours = match[1].trim();
            hours = hours.replace(/(Mon|Tue|Wed|Thu|Fri|Sat|Sun).*$/i, '').trim();
            if (hours.length > 0 && hours.length < 50) {
                result.business_hours[day] = hours;
            }
        }
    });

    // Areas of expertise
    const expertiseKeywords = ['HVAC repair', 'AC installation', 'Furnace installation',
                               'Heat pump', 'Ductless', 'Air handler', 'Maintenance',
                               'Emergency service', 'Commercial', 'Residential'];
    expertiseKeywords.forEach(keyword => {
        if (pageText.includes(keyword)) {
            result.areas_of_expertise.push(keyword);
        }
    });

    return result;
}
"""


def init_database():
    """Initialize SQLite database with schema if needed."""
    import sqlite3

    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        print("Run: python -c 'from database import PipelineDB; PipelineDB().initialize()'")
        sys.exit(1)

    # Verify dealer_enrichments table exists
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dealer_enrichments'")
    if not cursor.fetchone():
        print("dealer_enrichments table not found. Initializing schema...")
        from database import PipelineDB
        db = PipelineDB(DB_PATH)
        db.initialize()
    conn.close()


def fetch_trane_dealers_to_enrich(limit=None):
    """Fetch Trane dealers that need enrichment."""
    import sqlite3

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Find contractors with Trane OEM certification that don't have enrichment yet
    query = """
        SELECT DISTINCT
            c.id,
            c.company_name,
            c.city,
            c.state,
            o.certification_tier as tier,
            o.scraped_from_zip
        FROM contractors c
        JOIN oem_certifications o ON c.id = o.contractor_id
        LEFT JOIN dealer_enrichments e ON c.id = e.contractor_id AND e.oem_name = 'Trane'
        WHERE o.oem_name = 'Trane'
          AND e.id IS NULL
          AND c.is_deleted = 0
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    dealers = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return dealers


def save_enrichment(contractor_id, enrichment_data, detail_url):
    """Save enrichment data to dealer_enrichments table."""
    import sqlite3

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO dealer_enrichments (
            contractor_id, oem_name, google_rating, google_review_count,
            business_hours, areas_of_expertise, dealer_certifications,
            has_emergency_service, has_financing, financing_provider,
            detail_url, scraped_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        contractor_id,
        'Trane',
        enrichment_data.get('google_rating', 0.0),
        enrichment_data.get('google_review_count', 0),
        json.dumps(enrichment_data.get('business_hours', {})),
        json.dumps(enrichment_data.get('areas_of_expertise', [])),
        json.dumps(enrichment_data.get('certifications', [])),
        1 if enrichment_data.get('has_emergency', False) else 0,
        1 if enrichment_data.get('has_financing', False) else 0,
        enrichment_data.get('financing_provider', ''),
        detail_url,
        datetime.utcnow().isoformat()
    ))

    # If we found a valid local phone, update contractor
    phone = enrichment_data.get('phone', '')
    if phone and len(phone) == 10:
        cursor.execute("""
            UPDATE contractors SET primary_phone = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND (primary_phone IS NULL OR primary_phone = '')
        """, (phone, contractor_id))

    conn.commit()
    conn.close()


def build_detail_url(company_name, city, state):
    """Build Trane detail page URL from dealer info."""
    # Trane uses slug format: /dealers/company-name-city-state/
    slug = f"{company_name} {city} {state}".lower()
    slug = slug.replace(' ', '-').replace(',', '').replace('.', '')
    slug = ''.join(c for c in slug if c.isalnum() or c == '-')
    slug = '-'.join(filter(None, slug.split('-')))  # Remove consecutive dashes
    return f"https://www.trane.com/residential/en/dealers/{slug}/"


def save_checkpoint(processed_ids, stats, checkpoint_num):
    """Save checkpoint for resume capability."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint_file = CHECKPOINT_DIR / f'checkpoint_{checkpoint_num:04d}.json'

    checkpoint_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'processed_count': len(processed_ids),
        'stats': stats,
        'processed_ids': list(processed_ids)
    }

    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f, indent=2)

    print(f"  [Checkpoint saved: {len(processed_ids)} processed]")


def load_checkpoint():
    """Load most recent checkpoint."""
    if not CHECKPOINT_DIR.exists():
        return set(), {}

    checkpoints = sorted(CHECKPOINT_DIR.glob('checkpoint_*.json'))
    if not checkpoints:
        return set(), {}

    with open(checkpoints[-1]) as f:
        data = json.load(f)

    print(f"  Resuming from checkpoint: {len(data['processed_ids'])} already processed")
    return set(data['processed_ids']), data.get('stats', {})


def main():
    parser = argparse.ArgumentParser(description='Enrich Trane dealers with detail page data')
    parser.add_argument('--test', type=int, help='Test with N dealers')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    args = parser.parse_args()

    # Validate env
    if not all([BROWSERBASE_API_KEY, BROWSERBASE_PROJECT_ID]):
        print("ERROR: Missing required environment variables:")
        print("  - BROWSERBASE_API_KEY, BROWSERBASE_PROJECT_ID")
        sys.exit(1)

    # Initialize database
    init_database()

    # Initialize Browserbase
    from browserbase import Browserbase
    from playwright.sync_api import sync_playwright

    bb = Browserbase(api_key=BROWSERBASE_API_KEY)

    # Load checkpoint if resuming
    processed_ids = set()
    stats = {'enriched': 0, 'with_rating': 0, 'with_phone': 0, 'failed': 0, 'no_url': 0}
    if args.resume:
        processed_ids, stats = load_checkpoint()

    # Fetch dealers to enrich
    limit = args.test if args.test else None
    dealers = fetch_trane_dealers_to_enrich(limit)

    # Filter out already processed (if resuming)
    dealers = [d for d in dealers if d['id'] not in processed_ids]

    if not dealers:
        print("No unenriched Trane dealers found in SQLite.")
        print("\nTo import Trane dealers first, run:")
        print("  python scripts/run_oem_scraper.py --oem trane --mode browserbase")
        return

    print(f"\n{'='*60}")
    print(f"  TRANE DETAIL PAGE ENRICHMENT (SQLite)")
    print(f"{'='*60}")
    print(f"  Database: {DB_PATH}")
    print(f"  Dealers to enrich: {len(dealers)}")
    print(f"  Rate limit: {DELAY_BETWEEN_REQUESTS}s between requests")
    print(f"  Estimated time: ~{len(dealers) * DELAY_BETWEEN_REQUESTS / 60:.1f} minutes")
    print(f"{'='*60}\n")

    # Create Browserbase session
    session = bb.sessions.create(project_id=BROWSERBASE_PROJECT_ID)
    print(f"Browserbase session: {session.id}")

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(session.connect_url)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()

        try:
            for i, dealer in enumerate(dealers, 1):
                contractor_id = dealer['id']
                name = dealer.get('company_name', 'Unknown')[:40]
                city = dealer.get('city', '')
                state = dealer.get('state', '')

                # Build detail URL
                detail_url = build_detail_url(name, city, state)

                print(f"  [{i}/{len(dealers)}] {name}...", end=" ", flush=True)

                try:
                    # Navigate to detail page
                    page.goto(detail_url, timeout=30000, wait_until='domcontentloaded')
                    time.sleep(1.5)

                    # Check if page exists (not 404)
                    if "Page Not Found" in page.content() or "404" in page.title():
                        print("404 - skipping")
                        stats['no_url'] += 1
                        continue

                    # Extract enrichment data
                    enrichment = page.evaluate(get_extraction_script())

                    # Save to SQLite
                    save_enrichment(contractor_id, enrichment, detail_url)

                    # Track stats
                    stats['enriched'] += 1
                    if enrichment.get('google_rating', 0) > 0:
                        stats['with_rating'] += 1
                    if enrichment.get('phone'):
                        stats['with_phone'] += 1

                    processed_ids.add(contractor_id)

                    # Show progress
                    rating_info = f"R:{enrichment['google_rating']}" if enrichment.get('google_rating') else "No rating"
                    phone_info = f"P:{enrichment['phone'][:6]}..." if enrichment.get('phone') else "No phone"
                    print(f"{rating_info} | {phone_info}")

                except Exception as e:
                    print(f"ERROR: {str(e)[:50]}")
                    stats['failed'] += 1

                # Checkpoint
                if i % CHECKPOINT_INTERVAL == 0:
                    save_checkpoint(processed_ids, stats, i)

                # Rate limit
                time.sleep(DELAY_BETWEEN_REQUESTS)

        finally:
            browser.close()
            bb.sessions.update(session.id, status="COMPLETED")

    # Final checkpoint
    save_checkpoint(processed_ids, stats, len(dealers))

    # Summary
    print(f"\n{'='*60}")
    print(f"  ENRICHMENT COMPLETE")
    print(f"{'='*60}")
    print(f"  Total enriched: {stats['enriched']}")
    print(f"  With Google rating: {stats['with_rating']}")
    print(f"  With local phone: {stats['with_phone']}")
    print(f"  404/No page: {stats['no_url']}")
    print(f"  Failed: {stats['failed']}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
