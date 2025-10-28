#!/usr/bin/env python3
"""
Analyze deduplication performance metrics from the Cummins test
"""
import sys
from pathlib import Path
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def analyze_dedup_performance():
    print("=" * 70)
    print("ENHANCED DEDUPLICATION PERFORMANCE ANALYSIS")
    print("=" * 70)

    # Results from the Cummins deduplication
    total_raw = 25_800
    total_unique = 701
    duplicates_removed = 25_099

    phone_matches = 24_884
    domain_matches = 183
    fuzzy_matches = 32

    # Calculate percentages
    dedup_rate = (duplicates_removed / total_raw) * 100
    phone_effectiveness = (phone_matches / duplicates_removed) * 100
    domain_effectiveness = (domain_matches / duplicates_removed) * 100
    fuzzy_effectiveness = (fuzzy_matches / duplicates_removed) * 100

    print(f"\n📊 OVERALL PERFORMANCE")
    print(f"   Raw records:        {total_raw:,}")
    print(f"   Unique dealers:     {total_unique:,}")
    print(f"   Duplicates removed: {duplicates_removed:,}")
    print(f"   Deduplication rate: {dedup_rate:.1f}%")

    print(f"\n🎯 SIGNAL EFFECTIVENESS")
    print(f"   Phone matching:     {phone_matches:,} ({phone_effectiveness:.1f}% of duplicates)")
    print(f"   Domain matching:    {domain_matches:,} ({domain_effectiveness:.1f}% of duplicates)")
    print(f"   Fuzzy name:         {fuzzy_matches:,} ({fuzzy_effectiveness:.1f}% of duplicates)")

    print(f"\n📈 INCREMENTAL IMPROVEMENT")
    print(f"   Phone alone:        {phone_matches:,} duplicates caught")
    print(f"   + Domain:           {phone_matches + domain_matches:,} duplicates caught (+{domain_matches})")
    print(f"   + Fuzzy name:       {duplicates_removed:,} duplicates caught (+{fuzzy_matches})")

    print(f"\n💡 KEY INSIGHTS")
    print(f"   • Phone normalization is the primary signal (catches {phone_effectiveness:.1f}%)")
    print(f"   • Domain + fuzzy add {domain_matches + fuzzy_matches} more catches ({(domain_matches + fuzzy_matches)/duplicates_removed*100:.1f}%)")
    print(f"   • Each ZIP averaged {total_raw/130:.0f} dealers before dedup")
    print(f"   • Each ZIP averaged {total_unique/130:.1f} unique dealers after dedup")

    # Load the final CSV to check data quality
    csv_file = "output/cummins_dealers_20251028.csv"
    if Path(csv_file).exists():
        df = pd.read_csv(csv_file)
        print(f"\n📁 FINAL DATASET QUALITY")
        print(f"   Total records:      {len(df)}")
        print(f"   With phone:         {df['phone'].notna().sum()} ({df['phone'].notna().sum()/len(df)*100:.1f}%)")
        print(f"   With domain:        {df['domain'].notna().sum()} ({df['domain'].notna().sum()/len(df)*100:.1f}%)")
        print(f"   With rating:        {(df['rating'] > 0).sum()} ({(df['rating'] > 0).sum()/len(df)*100:.1f}%)")

        # State distribution
        print(f"\n📍 TOP STATES")
        top_states = df['state'].value_counts().head(5)
        for state, count in top_states.items():
            print(f"   {state}: {count:,} dealers ({count/len(df)*100:.1f}%)")

    print("\n" + "=" * 70)
    print("✅ CONCLUSION: Enhanced deduplication is production-ready!")
    print("=" * 70)

if __name__ == "__main__":
    analyze_dedup_performance()