#!/usr/bin/env python3
"""
Deduplicate Tesla Premier Installers by Phone Number
Removes duplicate entries while preserving first occurrence
Generates comprehensive deduplication report
"""

import csv
from collections import defaultdict
from datetime import datetime

INPUT_FILE = "output/tesla_premier_installers.csv"
OUTPUT_FILE = f"output/tesla_premier_deduped_{datetime.now().strftime('%Y%m%d')}.csv"
REPORT_FILE = f"output/deduplication_report_{datetime.now().strftime('%Y%m%d')}.txt"

def deduplicate_installers():
    """Deduplicate installers by phone number"""

    # Read all installers
    with open(INPUT_FILE, 'r') as f:
        reader = csv.DictReader(f)
        all_installers = list(reader)

    print(f"📊 Original dataset: {len(all_installers)} installer records")

    # Track unique phone numbers
    seen_phones = set()
    unique_installers = []
    duplicates = []

    # Track stats
    phone_counts = defaultdict(list)

    # Process each installer
    for installer in all_installers:
        phone = installer['phone']

        # Track all occurrences for reporting
        phone_counts[phone].append({
            'name': installer['name'],
            'state': installer['state'],
            'zip': installer['scraped_from_zip'],
            'tier': installer['tier']
        })

        # Keep first occurrence only
        if phone not in seen_phones:
            seen_phones.add(phone)
            unique_installers.append(installer)
        else:
            duplicates.append(installer)

    # Write deduplicated CSV
    with open(OUTPUT_FILE, 'w', newline='') as f:
        fieldnames = all_installers[0].keys()
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique_installers)

    print(f"✅ Deduplicated dataset: {len(unique_installers)} unique installers")
    print(f"🗑️  Duplicates removed: {len(duplicates)} records")
    print(f"📁 Output: {OUTPUT_FILE}")

    # Generate detailed report
    generate_report(all_installers, unique_installers, duplicates, phone_counts)


def generate_report(all_installers, unique_installers, duplicates, phone_counts):
    """Generate comprehensive deduplication report"""

    # Calculate stats
    state_stats = defaultdict(lambda: {'original': 0, 'unique': 0, 'duplicates': 0})
    tier_stats = defaultdict(lambda: {'original': 0, 'unique': 0, 'duplicates': 0})

    for installer in all_installers:
        state = installer['state']
        tier = installer['tier']
        state_stats[state]['original'] += 1
        tier_stats[tier]['original'] += 1

    for installer in unique_installers:
        state = installer['state']
        tier = installer['tier']
        state_stats[state]['unique'] += 1
        tier_stats[tier]['unique'] += 1

    for installer in duplicates:
        state = installer['state']
        tier = installer['tier']
        state_stats[state]['duplicates'] += 1
        tier_stats[tier]['duplicates'] += 1

    # Find installers with most duplicates
    top_duplicates = sorted(
        [(phone, occurrences) for phone, occurrences in phone_counts.items() if len(occurrences) > 1],
        key=lambda x: len(x[1]),
        reverse=True
    )[:20]

    # Write report
    with open(REPORT_FILE, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("TESLA PREMIER INSTALLER DEDUPLICATION REPORT\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Input: {INPUT_FILE}\n")
        f.write(f"Output: {OUTPUT_FILE}\n\n")

        f.write("SUMMARY\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Original Records: {len(all_installers)}\n")
        f.write(f"Unique Installers: {len(unique_installers)}\n")
        f.write(f"Duplicates Removed: {len(duplicates)}\n")
        f.write(f"Deduplication Rate: {len(duplicates)/len(all_installers)*100:.1f}%\n\n")

        f.write("BREAKDOWN BY STATE\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'State':<8} {'Original':<10} {'Unique':<10} {'Duplicates':<12} {'Dup %':<8}\n")
        f.write("-" * 80 + "\n")
        for state in sorted(state_stats.keys()):
            stats = state_stats[state]
            dup_pct = stats['duplicates']/stats['original']*100 if stats['original'] > 0 else 0
            f.write(f"{state:<8} {stats['original']:<10} {stats['unique']:<10} {stats['duplicates']:<12} {dup_pct:>6.1f}%\n")
        f.write("-" * 80 + "\n\n")

        f.write("BREAKDOWN BY TIER\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Tier':<25} {'Original':<10} {'Unique':<10} {'Duplicates':<12} {'Dup %':<8}\n")
        f.write("-" * 80 + "\n")
        for tier in sorted(tier_stats.keys()):
            stats = tier_stats[tier]
            dup_pct = stats['duplicates']/stats['original']*100 if stats['original'] > 0 else 0
            f.write(f"{tier:<25} {stats['original']:<10} {stats['unique']:<10} {stats['duplicates']:<12} {dup_pct:>6.1f}%\n")
        f.write("-" * 80 + "\n\n")

        f.write("TOP 20 INSTALLERS WITH MOST DUPLICATES\n")
        f.write("-" * 80 + "\n")
        for i, (phone, occurrences) in enumerate(top_duplicates, 1):
            f.write(f"\n{i}. {occurrences[0]['name']} - {phone}\n")
            f.write(f"   Appears in {len(occurrences)} ZIPs: ")
            zip_list = [f"{occ['zip']} ({occ['state']})" for occ in occurrences]
            f.write(", ".join(zip_list[:5]))
            if len(zip_list) > 5:
                f.write(f", ... and {len(zip_list)-5} more")
            f.write("\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("END REPORT\n")
        f.write("=" * 80 + "\n")

    print(f"📄 Detailed report: {REPORT_FILE}")

    # Print summary to console
    print("\n" + "=" * 80)
    print("DEDUPLICATION SUMMARY BY STATE")
    print("=" * 80)
    print(f"{'State':<8} {'Original':<10} {'Unique':<10} {'Duplicates':<12} {'Dup %':<8}")
    print("-" * 80)
    for state in sorted(state_stats.keys()):
        stats = state_stats[state]
        dup_pct = stats['duplicates']/stats['original']*100 if stats['original'] > 0 else 0
        print(f"{state:<8} {stats['original']:<10} {stats['unique']:<10} {stats['duplicates']:<12} {dup_pct:>6.1f}%")
    print("=" * 80)


if __name__ == "__main__":
    deduplicate_installers()
