#!/usr/bin/env python3
"""
Recover Lennox data from checkpoint and regenerate CSV files.
"""
import json
import csv
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.base_scraper import StandardizedDealer, DealerCapabilities

# Load checkpoint
checkpoint_path = PROJECT_ROOT / "output/oem_data/lennox/lennox_checkpoint_0264.json"
print(f"Loading checkpoint: {checkpoint_path}")

with open(checkpoint_path, 'r') as f:
    data = json.load(f)

dealers = data['dealers']
print(f"Loaded {len(dealers)} dealers")

# Convert dict dealers back to StandardizedDealer objects
dealer_objects = []
for d in dealers:
    # Reconstruct capabilities
    caps_data = d.get('capabilities', {})
    caps = DealerCapabilities()
    for key, value in caps_data.items():
        if hasattr(caps, key):
            if key in ('oem_certifications', 'generator_oems', 'battery_oems', 'microinverter_oems', 'inverter_oems'):
                setattr(caps, key, set(value) if isinstance(value, list) else value)
            else:
                setattr(caps, key, value)

    # Create StandardizedDealer
    dealer = StandardizedDealer(
        name=d.get('name', ''),
        phone=d.get('phone', ''),
        domain=d.get('domain', ''),
        website=d.get('website', ''),
        street=d.get('street', ''),
        city=d.get('city', ''),
        state=d.get('state', ''),
        zip=d.get('zip', ''),
        address_full=d.get('address_full', ''),
        rating=d.get('rating', 0.0),
        review_count=d.get('review_count', 0),
        tier=d.get('tier', 'Standard'),
        certifications=d.get('certifications', []),
        distance=d.get('distance', ''),
        distance_miles=d.get('distance_miles', 0.0),
        capabilities=caps,
        oem_source=d.get('oem_source', 'Lennox'),
        scraped_from_zip=d.get('scraped_from_zip', ''),
    )
    dealer_objects.append(dealer)

print(f"Reconstructed {len(dealer_objects)} dealer objects")

# Deduplicate (phone → domain → fuzzy name)
from collections import defaultdict

# Phase 1: Phone deduplication
phone_map = {}
for dealer in dealer_objects:
    phone = dealer.phone.strip()
    if phone and phone not in phone_map:
        phone_map[phone] = dealer

print(f"After phone dedup: {len(phone_map)} dealers")

# Phase 2: Domain deduplication
domain_map = {}
for dealer in phone_map.values():
    domain = dealer.domain.strip().lower()
    if domain:
        if domain not in domain_map:
            domain_map[domain] = dealer
    else:
        # No domain, keep the dealer
        domain_map[dealer.phone] = dealer

print(f"After domain dedup: {len(domain_map)} dealers")

# Phase 3: Fuzzy name deduplication (same state only)
from fuzzywuzzy import fuzz

final_dealers = []
seen_names = defaultdict(list)

for dealer in domain_map.values():
    # Normalize name
    name_key = dealer.name.lower().strip()
    name_key = name_key.replace('inc.', '').replace('llc', '').replace('corp', '').strip()

    # Check for fuzzy matches in same state
    found_match = False
    for prev_dealer in seen_names[dealer.state]:
        prev_name = prev_dealer.name.lower().strip()
        prev_name = prev_name.replace('inc.', '').replace('llc', '').replace('corp', '').strip()

        similarity = fuzz.ratio(name_key, prev_name)
        if similarity >= 85:  # 85% similarity threshold
            found_match = True
            break

    if not found_match:
        final_dealers.append(dealer)
        seen_names[dealer.state].append(dealer)

print(f"After fuzzy name dedup: {len(final_dealers)} dealers")

# Generate CSV
output_dir = PROJECT_ROOT / "output/oem_data/lennox"
output_dir.mkdir(parents=True, exist_ok=True)

csv_path = output_dir / f"lennox_deduped_{datetime.now().strftime('%Y%m%d')}.csv"

# Get all dealer dict representations
dealer_dicts = [d.to_dict() for d in final_dealers]

# Flatten capabilities
flattened = []
for d in dealer_dicts:
    caps = d.pop('capabilities', {})
    d.update({f"cap_{k}": v for k, v in caps.items()})
    flattened.append(d)

# Write CSV
if flattened:
    fieldnames = list(flattened[0].keys())

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flattened)

    print(f"\n✅ CSV saved: {csv_path}")
    print(f"   Total dealers: {len(flattened)}")
else:
    print("\n❌ No dealers to export")

# Also generate JSON
json_path = output_dir / f"lennox_raw_{datetime.now().strftime('%Y%m%d')}.json"
with open(json_path, 'w') as f:
    json.dump(dealer_dicts, f, indent=2)

print(f"✅ JSON saved: {json_path}")
