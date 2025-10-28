#!/usr/bin/env python3
"""Regenerate Cummins final files from checkpoint 130 with fixed CSV fields"""

import json
from pathlib import Path
from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode

print("🔧 REGENERATING CUMMINS FINAL FILES FROM CHECKPOINT")
print("=" * 70)

# Load checkpoint 130 (last checkpoint before completion)
checkpoint_file = "output/cummins_national_checkpoint_130_20251028_063037.json"

print(f"Loading: {checkpoint_file}")
with open(checkpoint_file, 'r') as f:
    dealers_data = json.load(f)

print(f"Loaded {len(dealers_data)} dealers from checkpoint")

# Create scraper and load data
scraper = ScraperFactory.create("Cummins", mode=ScraperMode.PLAYWRIGHT)

# The checkpoint has deduplicated data already
# Just need to reconstruct and re-save with fixed CSV fields
from scrapers.base_scraper import StandardizedDealer, DealerCapabilities

for dealer_dict in dealers_data:
    # Separate capabilities
    caps_dict = dealer_dict.pop('capabilities', {})
    
    # Handle both dict and DealerCapabilities object formats
    if isinstance(caps_dict, dict):
        caps = DealerCapabilities(
            has_generator=caps_dict.get('has_generator', False),
            has_solar=caps_dict.get('has_solar', False),
            has_battery=caps_dict.get('has_battery', False),
            has_microinverters=caps_dict.get('has_microinverters', False),
            has_inverters=caps_dict.get('has_inverters', False),
            has_electrical=caps_dict.get('has_electrical', False),
            has_hvac=caps_dict.get('has_hvac', False),
            has_roofing=caps_dict.get('has_roofing', False),
            has_plumbing=caps_dict.get('has_plumbing', False),
            is_commercial=caps_dict.get('is_commercial', False),
            is_residential=caps_dict.get('is_residential', False),
            is_gc=caps_dict.get('is_gc', False),
            is_sub=caps_dict.get('is_sub', False)
        )
    else:
        caps = caps_dict
    
    # Create dealer object
    dealer = StandardizedDealer(**dealer_dict, capabilities=caps)
    scraper.dealers.append(dealer)

print(f"Reconstructed {len(scraper.dealers)} dealers")
print()

# Save with fixed CSV fields
csv_file = "output/cummins_national_20251028.csv"
json_file = "output/cummins_national_20251028.json"

print("💾 Saving final files with fixed CSV fields...")
scraper.save_csv(csv_file)
scraper.save_json(json_file)

print()
print("✅ REGENERATION COMPLETE!")
print(f"   • Dealers: {len(scraper.dealers):,}")
print(f"   • CSV: {csv_file}")
print(f"   • JSON: {json_file}")
