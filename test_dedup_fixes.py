#!/usr/bin/env python3
"""
Test deduplication pipeline fixes.
"""

import sys
sys.path.insert(0, '/Users/tmkipper/Desktop/tk_projects/dealer-scraper-mvp/.worktrees/22-oem-sequential')

from scripts.run_22_oem_sequential import deduplicate_dealers

# Test data with duplicates across all three phases
test_dealers = [
    # Phone duplicates (should keep only first)
    {"name": "ABC Heating", "phone": "555-1234", "domain": "abcheating.com", "state": "CA"},
    {"name": "ABC Heating Inc", "phone": "(555) 123-4567", "domain": "abcheating.com", "state": "CA"},  # Different phone
    {"name": "ABC Heating LLC", "phone": "555-1234", "domain": "abcheating2.com", "state": "CA"},  # DUPLICATE PHONE

    # Domain duplicates (should keep only first after phone dedup)
    {"name": "XYZ Solar", "phone": "555-5678", "domain": "www.xyzsolar.com", "state": "TX"},
    {"name": "XYZ Solar Power", "phone": "555-9999", "domain": "xyzsolar.com", "state": "TX"},  # DUPLICATE DOMAIN (www. stripped)

    # Fuzzy name matches (should keep only first)
    {"name": "Smith HVAC Services LLC", "phone": "555-1111", "domain": "smithhvac.com", "state": "FL"},
    {"name": "Smith HVAC Service", "phone": "555-2222", "domain": "smith-hvac.com", "state": "FL"},  # FUZZY MATCH 89% (≥85%)

    # Empty fields (should keep all - can't deduplicate)
    {"name": "No Phone Co", "phone": "", "domain": "nophone.com", "state": "NY"},
    {"name": "No Domain Inc", "phone": "555-3333", "domain": "", "state": "NY"},
    {"name": "No Name", "phone": "555-4444", "domain": "noname.com", "state": "NY"},

    # No matches (should keep all)
    {"name": "Unique Solar", "phone": "555-7777", "domain": "uniquesolar.com", "state": "MA"},
    {"name": "Different HVAC", "phone": "555-8888", "domain": "differenthvac.com", "state": "PA"},
]

print("=" * 80)
print("DEDUPLICATION PIPELINE TEST")
print("=" * 80)
print(f"\nInput: {len(test_dealers)} dealers\n")

# Expected results:
# - Phone dedup: Remove dealer[2] (duplicate phone "555-1234") → 11 dealers
# - Domain dedup: Remove dealer[1] (duplicate "abcheating.com" with dealer[0])
#                 Remove dealer[4] (duplicate "xyzsolar.com" with dealer[3]) → 9 dealers
# - Fuzzy dedup: Remove dealer[6] (fuzzy match 88% with dealer[5]) → 8 dealers
# - Keep all dealers with empty fields (dealers[7-9])
# - Keep all unique dealers (dealers[10-11])
# Expected output: 12 - 4 = 8 dealers

deduped_dealers, stats = deduplicate_dealers(test_dealers, "TestOEM")

print(f"\n{'=' * 80}")
print("RESULTS")
print("=" * 80)
print(f"Initial: {stats['initial']}")
print(f"Phone duplicates removed: {stats['phone_dupes']}")
print(f"Domain duplicates removed: {stats['domain_dupes']}")
print(f"Fuzzy name duplicates removed: {stats['fuzzy_dupes']}")
print(f"Final unique dealers: {stats['final']}")
print(f"\nExpected: 8 unique dealers (removed 4 duplicates)")
print(f"Actual: {len(deduped_dealers)} unique dealers")
print(f"Test {'✅ PASSED' if len(deduped_dealers) == 8 else '❌ FAILED'}")

if stats['fuzzy_matches']:
    print(f"\n{'=' * 80}")
    print("FUZZY MATCHES DETECTED")
    print("=" * 80)
    for match in stats['fuzzy_matches']:
        print(f"  - '{match['name1']}' ↔ '{match['name2']}' ({match['similarity']}%, {match['state']})")
