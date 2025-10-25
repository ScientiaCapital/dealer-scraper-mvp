"""
Simple Interactive Generac Scraper - MVP
Supports: Playwright MCP (manual) + Browserbase (automated)

Usage: python scripts/run_scraper.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.generac_scraper import GeneracScraper
from scrapers.base_scraper import ScraperMode
from targeting.coperniq_lead_scorer import CoperniqLeadScorer
from analysis.multi_oem_detector import MultiOEMMatch
from datetime import datetime
import config
import csv

print("\n" + "="*60)
print(" "*15 + "Generac Installer Scraper")
print("="*60 + "\n")

# Step 1: Select mode
print("Select scraping mode:")
print("  [1] Browserbase (Automated cloud scraping)")
print("  [2] Playwright MCP (Manual workflow for testing)")
mode_choice = input("\n→ ").strip()

if mode_choice == "2":
    mode = ScraperMode.PLAYWRIGHT
    print("\n✓ Using Playwright MCP (manual workflow)\n")
else:
    mode = ScraperMode.BROWSERBASE
    print("\n✓ Using Browserbase (automated)\n")

# Step 2: Show wealthy ZIPs
print("Top 20 Wealthy ZIP Codes by State:")
print("-" * 60)
for state, zips in sorted(config.WEALTHY_ZIPS.items()):
    preview = ", ".join(zips[:5])
    remaining = len(zips) - 5
    print(f"  {state}: {preview}... (+{remaining} more)")

# Step 3: Get ZIPs from user
print("\n" + "-" * 60)
print("Enter ZIP codes:")
print("  • Manual entry:  94027,76092,19035")
print("  • All state:     all-CA, all-TX, all-PA, all-MA, all-NJ, all-FL")
print("  • Multiple states: all-CA,all-TX")
print("-" * 60)
zip_input = input("\n→ ").strip()

# Parse input
zip_codes = []
if "all-" in zip_input:
    # Handle "all-CA,all-TX" or "all-CA"
    for part in zip_input.split(","):
        part = part.strip()
        if part.startswith("all-"):
            state = part.split("-")[1].upper()
            state_zips = config.WEALTHY_ZIPS.get(state, [])
            zip_codes.extend(state_zips)
            print(f"  ✓ Added {len(state_zips)} {state} ZIPs")
else:
    zip_codes = [z.strip() for z in zip_input.split(",")]

print(f"\n→ Total: {len(zip_codes)} ZIP codes to scrape\n")

# Step 4: Scrape
scraper = GeneracScraper(mode=mode)

if mode == ScraperMode.PLAYWRIGHT:
    print("="*60)
    print(" "*10 + "⚠️  MANUAL PLAYWRIGHT MODE")
    print("="*60)
    print("\nThe scraper will print MCP Playwright workflow instructions.")
    print("Execute each step manually in Claude Code, then proceed.\n")
    print("After completing all steps:")
    print("  1. Parse results with: scraper.parse_results(json, zip)")
    print("  2. Export with: scraper.save_csv('output/file.csv')")
    print("\nOR rerun this script in Browserbase mode for automation.\n")
    print("="*60 + "\n")

    for zip_code in zip_codes:
        scraper.scrape_zip_code(zip_code)

    print("\n⚠️  Manual workflow complete. Exiting.")
    print("    Rerun with Browserbase mode for automated scraping.\n")
    sys.exit(0)

# Browserbase automated flow
print("="*60)
print(f" Scraping {len(zip_codes)} ZIPs with Browserbase")
print("="*60 + "\n")

for i, zip_code in enumerate(zip_codes, 1):
    try:
        print(f"[{i:3d}/{len(zip_codes)}] {zip_code}...", end=" ", flush=True)
        dealers = scraper.scrape_zip_code(zip_code)
        print(f"✓ {len(dealers):2d} dealers")
    except Exception as e:
        print(f"✗ Error: {str(e)[:50]}")

# Step 5: Deduplicate & Score
print("\n" + "="*60)
print(" Processing Results")
print("="*60 + "\n")

print(f"Total dealers found:     {len(scraper.dealers)}")
scraper.deduplicate()
print(f"After deduplication:     {len(scraper.dealers)} unique dealers")

# Convert to scoring format
matches = [MultiOEMMatch.from_single_dealer(d) for d in scraper.dealers]
scorer = CoperniqLeadScorer()
scored = [scorer.score_match(m) for m in matches]

# Step 6: Export CSV
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"output/generac_leads_{timestamp}.csv"
Path("output").mkdir(exist_ok=True)

with open(filename, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=[
        'score', 'priority', 'name', 'phone', 'domain', 'website',
        'city', 'state', 'zip', 'tier', 'rating', 'review_count',
        'distance_miles', 'address_full', 'multi_oem_score'
    ])
    writer.writeheader()

    for match in sorted(scored, key=lambda x: x.coperniq_score, reverse=True):
        dealer = match.dealer_data[0] if match.dealer_data else None
        writer.writerow({
            'score': match.coperniq_score,
            'priority': match.priority_tier,
            'name': match.name,
            'phone': match.phone,
            'domain': match.domain,
            'website': match.website,
            'city': match.city,
            'state': match.state,
            'zip': match.zip,
            'tier': dealer.tier if dealer else '',
            'rating': dealer.rating if dealer else 0,
            'review_count': dealer.review_count if dealer else 0,
            'distance_miles': round(dealer.distance_miles, 1) if dealer else 0,
            'address_full': dealer.address_full if dealer else '',
            'multi_oem_score': match.multi_oem_score,
        })

# Summary
high = sum(1 for m in scored if m.priority_tier == "HIGH")
med = sum(1 for m in scored if m.priority_tier == "MEDIUM")
low = sum(1 for m in scored if m.priority_tier == "LOW")

print(f"\n✓ CSV exported: {filename}")
print("\n" + "="*60)
print(" Priority Breakdown (Sorted by Score)")
print("="*60)
print(f"\n  HIGH (80-100):   {high:4d} installers  ← Call first!")
print(f"  MEDIUM (50-79):  {med:4d} installers  ← Call second")
print(f"  LOW (<50):       {low:4d} installers  ← Nurture/Email")
print(f"\n  TOTAL:           {len(scored):4d} unique installers")
print("\n" + "="*60)
print(" Next Steps")
print("="*60)
print("\n  1. Open CSV and review HIGH priority installers")
print("  2. Enrich with Apollo (employee count, revenue)")
print("  3. Import to Close CRM for outbound campaigns")
print("  4. Begin calling HIGH priority installers\n")
print("="*60 + "\n")
