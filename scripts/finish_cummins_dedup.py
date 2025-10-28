#!/usr/bin/env python3
"""
Load Cummins checkpoint and finish deduplication
"""
import json
import csv
from datetime import datetime
from scrapers.cummins_scraper import CumminsScraper
from scrapers.base_scraper import ScraperMode, StandardizedDealer

# Load checkpoint
print("Loading Cummins checkpoint...")
with open("output/cummins_checkpoint_140_20251027_170457.json", 'r') as f:
    dealers_dict = json.load(f)

# Convert to StandardizedDealer objects
print(f"Loaded {len(dealers_dict)} dealers from checkpoint")
dealers = [StandardizedDealer(**d) for d in dealers_dict]

# Create scraper and deduplicate
scraper = CumminsScraper(mode=ScraperMode.PLAYWRIGHT)
scraper.dealers = dealers

print("\n🔄 Deduplicating by phone number...")
scraper.deduplicate(key="phone")
deduped_dealers = scraper.dealers

print(f"   Unique dealers: {len(deduped_dealers)}")
print(f"   Duplicates removed: {len(dealers) - len(deduped_dealers)}")

# Save FINAL results
final_timestamp = datetime.now().strftime("%Y%m%d")

# Save JSON
json_file = f"output/cummins_dealers_{final_timestamp}.json"
dealers_dict = [d.to_dict() for d in deduped_dealers]
with open(json_file, 'w') as f:
    json.dump(dealers_dict, f, indent=2)
print(f"\n💾 Saved FINAL JSON: {json_file}")

# Save CSV
csv_file = f"output/cummins_dealers_{final_timestamp}.csv"
with open(csv_file, 'w', newline='', encoding='utf-8') as f:
    if deduped_dealers:
        fieldnames = [
            'name', 'phone', 'domain', 'website',
            'street', 'city', 'state', 'zip', 'address_full',
            'rating', 'review_count', 'tier',
            'distance', 'distance_miles',
            'oem_source', 'scraped_from_zip'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for dealer in deduped_dealers:
            d = dealer.to_dict()
            writer.writerow({k: d.get(k, '') for k in fieldnames})

print(f"💾 Saved FINAL CSV: {csv_file}")

# Summary stats
print(f"\n📊 Summary Statistics:")
print(f"   Total dealers scraped: {len(dealers)}")
print(f"   Unique dealers: {len(deduped_dealers)}")
print(f"   ZIP codes processed: 140")
print(f"   Avg dealers per ZIP: {len(dealers) / 140:.1f}")

# Count by state
states = {}
for dealer in deduped_dealers:
    state = dealer.state or 'Unknown'
    states[state] = states.get(state, 0) + 1

print(f"\n   Dealers by state:")
for state in sorted(states.keys(), key=lambda s: states[s], reverse=True)[:10]:
    print(f"      {state}: {states[state]}")

print(f"\n✅ Cummins deduplication complete!")
print(f"   Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)
