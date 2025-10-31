#!/usr/bin/env python3
"""
Combine all three national OEM datasets into Grand Master List
"""
from scrapers.base_scraper import StandardizedDealer
from datetime import datetime
import json
import csv
import glob

def load_dealers_from_json(filepath):
    """Load dealers from JSON file"""
    print(f"  📂 Loading: {filepath}")
    with open(filepath, 'r') as f:
        dealers_data = json.load(f)

    dealers = []
    for d in dealers_data:
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
            distance=d.get('distance', ''),
            distance_miles=d.get('distance_miles', 0.0),
            oem_source=d.get('oem_source', ''),
            scraped_from_zip=d.get('scraped_from_zip', '')
        )
        dealers.append(dealer)

    print(f"     Loaded {len(dealers):,} dealers")
    return dealers

def deduplicate_by_phone(dealers):
    """Deduplicate dealers by phone number"""
    seen_phones = set()
    unique_dealers = []

    for dealer in dealers:
        # Normalize phone to digits only
        phone_normalized = ''.join(filter(str.isdigit, dealer.phone))

        if not phone_normalized or phone_normalized in seen_phones:
            continue

        seen_phones.add(phone_normalized)
        unique_dealers.append(dealer)

    return unique_dealers

def save_to_csv(dealers, filepath):
    """Save dealers to CSV"""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'name', 'phone', 'domain', 'website',
            'street', 'city', 'state', 'zip', 'address_full',
            'rating', 'review_count', 'tier',
            'distance', 'distance_miles',
            'oem_source', 'scraped_from_zip'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for dealer in dealers:
            d = dealer.to_dict()
            writer.writerow({k: d.get(k, '') for k in fieldnames})

def save_to_json(dealers, filepath):
    """Save dealers to JSON"""
    dealers_dict = [d.to_dict() for d in dealers]
    with open(filepath, 'w') as f:
        json.dump(dealers_dict, f, indent=2)

def main():
    print("=" * 70)
    print("GRAND MASTER LIST - COMBINING ALL NATIONAL OEM DATASETS")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    all_dealers = []
    oem_counts = {}

    # Load Cummins
    print("\n🔧 CUMMINS RESIDENTIAL STANDBY")
    cummins_files = glob.glob("output/cummins_national_*.json")
    if cummins_files:
        latest_cummins = max(cummins_files)
        cummins_dealers = load_dealers_from_json(latest_cummins)
        all_dealers.extend(cummins_dealers)
        oem_counts['Cummins'] = len(cummins_dealers)
    else:
        print("  ⚠️  No Cummins national file found, checking checkpoints...")
        checkpoint_files = glob.glob("output/cummins_national_checkpoint_*.json")
        if checkpoint_files:
            latest_checkpoint = max(checkpoint_files)
            cummins_dealers = load_dealers_from_json(latest_checkpoint)
            all_dealers.extend(cummins_dealers)
            oem_counts['Cummins'] = len(cummins_dealers)
        else:
            print("  ❌ No Cummins data found!")
            oem_counts['Cummins'] = 0

    # Load Briggs & Stratton
    print("\n🔩 BRIGGS & STRATTON STANDBY GENERATORS")
    briggs_files = glob.glob("output/briggs_national_*.json")
    if briggs_files:
        latest_briggs = max(briggs_files)
        briggs_dealers = load_dealers_from_json(latest_briggs)
        all_dealers.extend(briggs_dealers)
        oem_counts['Briggs & Stratton'] = len(briggs_dealers)
    else:
        print("  ⚠️  No Briggs national file found!")
        oem_counts['Briggs & Stratton'] = 0

    # Load Generac
    print("\n⚡ GENERAC BACKUP GENERATORS")
    generac_files = glob.glob("output/generac_national_*.json")
    if generac_files:
        latest_generac = max(generac_files)
        generac_dealers = load_dealers_from_json(latest_generac)
        all_dealers.extend(generac_dealers)
        oem_counts['Generac'] = len(generac_dealers)
    else:
        print("  ⚠️  No Generac national file found!")
        oem_counts['Generac'] = 0

    print(f"\n{'='*70}")
    print("COMBINED DATASET SUMMARY")
    print(f"{'='*70}")
    for oem, count in oem_counts.items():
        print(f"   • {oem}: {count:,} dealers")
    print(f"   • TOTAL: {len(all_dealers):,} dealers (before dedup)")

    # Deduplicate
    print(f"\n{'='*70}")
    print("DEDUPLICATING BY PHONE NUMBER")
    print(f"{'='*70}")
    before_count = len(all_dealers)
    unique_dealers = deduplicate_by_phone(all_dealers)
    after_count = len(unique_dealers)

    duplicate_count = before_count - after_count
    duplicate_pct = (duplicate_count / before_count * 100) if before_count > 0 else 0

    print(f"\n📊 Deduplication Results:")
    print(f"   • Before: {before_count:,} dealers")
    print(f"   • After: {after_count:,} unique dealers")
    print(f"   • Removed: {duplicate_count:,} duplicates ({duplicate_pct:.1f}%)")

    # Save Grand Master List
    timestamp = datetime.now().strftime("%Y%m%d")
    csv_file = f"output/grand_master_national_{timestamp}.csv"
    json_file = f"output/grand_master_national_{timestamp}.json"

    print(f"\n💾 Saving Grand Master List...")
    save_to_csv(unique_dealers, csv_file)
    save_to_json(unique_dealers, json_file)

    print(f"\n{'='*70}")
    print("✅ GRAND MASTER LIST COMPLETE!")
    print(f"{'='*70}")
    print(f"   📁 CSV: {csv_file}")
    print(f"   📁 JSON: {json_file}")
    print(f"   📊 Total unique dealers: {len(unique_dealers):,}")
    print(f"\n   OEM Breakdown:")
    for oem, count in oem_counts.items():
        pct = (count / after_count * 100) if after_count > 0 else 0
        print(f"   • {oem}: {count:,} dealers ({pct:.1f}% of total)")
    print(f"\n   Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

if __name__ == "__main__":
    main()
