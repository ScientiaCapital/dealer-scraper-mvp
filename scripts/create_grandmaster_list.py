#!/usr/bin/env python3
"""
Combine all 5 OEM datasets into grandmaster list with multi-OEM overlap detection
"""
import csv
import json
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Set

def normalize_phone(phone: str) -> str:
    """Extract digits only from phone number"""
    if not phone:
        return ""
    return ''.join(c for c in phone if c.isdigit())

def extract_domain(website: str) -> str:
    """Extract root domain from website URL"""
    if not website:
        return ""

    # Remove protocol
    domain = website.replace('http://', '').replace('https://', '')

    # Remove www
    domain = domain.replace('www.', '')

    # Remove path
    domain = domain.split('/')[0]

    # Remove port
    domain = domain.split(':')[0]

    return domain.lower().strip()

def load_oem_csv(filepath: str, oem_name: str) -> List[Dict]:
    """Load OEM CSV and tag each dealer with OEM source"""
    dealers = []

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize phone and extract domain
            phone = normalize_phone(row.get('phone', ''))
            website = row.get('website', '') or row.get('domain', '')
            domain = extract_domain(website)

            # Add normalized fields
            row['phone_normalized'] = phone
            row['domain_normalized'] = domain
            row['oem_source'] = oem_name

            dealers.append(row)

    return dealers

def detect_multi_oem_overlaps(all_dealers: List[Dict]) -> Dict:
    """
    Detect contractors who appear in multiple OEM networks
    Returns dict mapping unique_id -> dealer_info with OEM certifications
    """
    # Group by phone (primary key)
    phone_groups = defaultdict(list)
    for dealer in all_dealers:
        phone = dealer['phone_normalized']
        if phone:  # Only group if phone exists
            phone_groups[phone].append(dealer)

    # Build unique contractor records
    unique_contractors = {}

    for phone, dealers in phone_groups.items():
        # Collect OEM certifications
        oems = set(d['oem_source'] for d in dealers)

        # Use first dealer as base record
        base = dealers[0].copy()

        # Add multi-OEM fields
        base['OEM_Count'] = len(oems)
        base['OEMs_Certified'] = ', '.join(sorted(oems))

        # Create unique ID
        unique_id = f"phone_{phone}"
        unique_contractors[unique_id] = base

    # Handle dealers without phones (use domain as backup)
    domain_groups = defaultdict(list)
    for dealer in all_dealers:
        phone = dealer['phone_normalized']
        domain = dealer['domain_normalized']

        if not phone and domain:  # Only if no phone but has domain
            domain_groups[domain].append(dealer)

    for domain, dealers in domain_groups.items():
        # Collect OEM certifications
        oems = set(d['oem_source'] for d in dealers)

        # Use first dealer as base record
        base = dealers[0].copy()

        # Add multi-OEM fields
        base['OEM_Count'] = len(oems)
        base['OEMs_Certified'] = ', '.join(sorted(oems))

        # Create unique ID
        unique_id = f"domain_{domain}"
        unique_contractors[unique_id] = base

    return unique_contractors

def main():
    print("=" * 70)
    print("CREATING GRANDMASTER LIST - 5 OEM NETWORKS")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Load all 5 OEM datasets
    oem_files = [
        ('output/tesla_premier_deduped_20251026.csv', 'Tesla'),
        ('output/enphase_platinum_gold_deduped_20251026.csv', 'Enphase'),
        ('output/generac_national_20251028.csv', 'Generac'),
        ('output/cummins_dealers_20251028.csv', 'Cummins'),
        ('output/briggs_national_20251028.csv', 'Briggs & Stratton'),
    ]

    all_dealers = []
    oem_counts = {}

    print("\n📂 Loading OEM datasets...\n")
    for filepath, oem_name in oem_files:
        dealers = load_oem_csv(filepath, oem_name)
        all_dealers.extend(dealers)
        oem_counts[oem_name] = len(dealers)
        print(f"   ✓ {oem_name}: {len(dealers)} unique dealers")

    print(f"\n   Total dealer records loaded: {len(all_dealers)}")

    # Detect multi-OEM overlaps
    print(f"\n🔍 Detecting multi-OEM overlaps...")
    unique_contractors = detect_multi_oem_overlaps(all_dealers)

    print(f"   Unique contractors identified: {len(unique_contractors)}")

    # Count by OEM certification count
    oem_count_distribution = defaultdict(int)
    for contractor in unique_contractors.values():
        count = contractor['OEM_Count']
        oem_count_distribution[count] += 1

    print(f"\n📊 Multi-OEM Distribution:")
    for count in sorted(oem_count_distribution.keys(), reverse=True):
        contractors_count = oem_count_distribution[count]
        percentage = (contractors_count / len(unique_contractors)) * 100

        if count == 1:
            label = "Single-OEM contractors"
        elif count == 2:
            label = "🥈 Dual-OEM contractors (GOLD tier potential)"
        elif count == 3:
            label = "🥇 Triple-OEM contractors (PLATINUM tier!)"
        elif count >= 4:
            label = "💎 Quad+ OEM contractors (UNICORNS!)"
        else:
            label = f"{count}-OEM contractors"

        print(f"   {label}: {contractors_count} ({percentage:.1f}%)")

    # Save grandmaster list
    timestamp = datetime.now().strftime("%Y%m%d")

    # Save as CSV
    csv_file = f"output/grandmaster_list_{timestamp}.csv"

    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        # Get all fieldnames from first contractor
        if unique_contractors:
            sample = list(unique_contractors.values())[0]

            # Define output field order
            priority_fields = [
                'name', 'phone', 'domain', 'website',
                'OEM_Count', 'OEMs_Certified',
                'street', 'city', 'state', 'zip', 'address_full',
                'rating', 'review_count', 'tier',
                'distance', 'distance_miles',
                'oem_source', 'scraped_from_zip'
            ]

            # Get all unique fields from ALL contractors (not just the first one)
            all_fields = set()
            for contractor in unique_contractors.values():
                all_fields.update(contractor.keys())

            # Add any remaining fields (exclude empty fieldnames)
            remaining = [f for f in all_fields if f not in priority_fields
                        and not f.endswith('_normalized')
                        and f.strip() != '']  # Exclude empty fieldnames

            fieldnames = [f for f in priority_fields + remaining if f.strip() != '']

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            # Sort by OEM_Count (descending) then name
            sorted_contractors = sorted(
                unique_contractors.values(),
                key=lambda x: (-x['OEM_Count'], x.get('name', ''))
            )

            for contractor in sorted_contractors:
                # Remove normalized fields and empty keys from output
                clean_contractor = {k: v for k, v in contractor.items()
                                  if not k.endswith('_normalized') and k.strip() != ''}
                writer.writerow(clean_contractor)

    print(f"\n💾 Saved grandmaster list: {csv_file}")

    # Save multi-OEM crossovers only (2+ OEMs)
    multi_oem = [c for c in unique_contractors.values() if c['OEM_Count'] >= 2]

    if multi_oem:
        crossover_file = f"output/multi_oem_crossovers_{timestamp}.csv"

        with open(crossover_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            # Sort by OEM_Count descending
            sorted_multi = sorted(multi_oem, key=lambda x: (-x['OEM_Count'], x.get('name', '')))

            for contractor in sorted_multi:
                clean_contractor = {k: v for k, v in contractor.items()
                                  if not k.endswith('_normalized') and k.strip() != ''}
                writer.writerow(clean_contractor)

        print(f"💾 Saved multi-OEM crossovers: {crossover_file}")
        print(f"   ({len(multi_oem)} contractors certified with 2+ OEMs)")

    # Summary statistics
    print(f"\n📊 Final Summary:")
    print(f"   Total OEM records processed: {len(all_dealers)}")
    print(f"   Unique contractors: {len(unique_contractors)}")
    print(f"   Deduplication rate: {((len(all_dealers) - len(unique_contractors)) / len(all_dealers)) * 100:.1f}%")

    print(f"\n   OEM Network Sizes:")
    for oem_name, count in sorted(oem_counts.items(), key=lambda x: -x[1]):
        print(f"      {oem_name}: {count}")

    # Geographic distribution
    states = defaultdict(int)
    for contractor in unique_contractors.values():
        state = contractor.get('state', 'Unknown')
        if state:
            states[state] += 1

    print(f"\n   Top 10 States:")
    for state, count in sorted(states.items(), key=lambda x: -x[1])[:10]:
        print(f"      {state}: {count}")

    print(f"\n✅ Grandmaster list creation complete!")
    print(f"   Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

if __name__ == "__main__":
    main()
