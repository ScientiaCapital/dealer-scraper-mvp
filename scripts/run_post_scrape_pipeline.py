"""
Post-Scrape Pipeline - Multi-OEM Detection & Export

Runs immediately after multi-OEM scraping completes to:
1. Load all scraped dealer data from pickle files
2. Run multi-OEM cross-reference detection
3. Generate PLATINUM/GOLD/SILVER tier CSVs
4. Export summary statistics

Usage:
    python scripts/run_post_scrape_pipeline.py
"""

import os
import pickle
import json
from datetime import datetime
from pathlib import Path
from analysis.multi_oem_detector import MultiOEMDetector, MultiOEMMatch
from scrapers.base_scraper import StandardizedDealer
from typing import List, Dict

def load_dealers_from_pickle(pickle_path: str) -> List[StandardizedDealer]:
    """Load dealers from pickle file"""
    if not os.path.exists(pickle_path):
        print(f"⚠️  Pickle file not found: {pickle_path}")
        return []

    with open(pickle_path, "rb") as f:
        dealers = pickle.load(f)

    return dealers


def main():
    print("=" * 70)
    print("POST-SCRAPE PIPELINE")
    print("Multi-OEM Detection & Tier Classification")
    print("=" * 70)
    print()

    # Define output directory (from latest scrape run)
    output_dir = Path("output")

    # Find all pickle files (scraped dealer data)
    pickle_files = list(output_dir.glob("*_dealers_*.pkl"))

    if not pickle_files:
        print("❌ No pickle files found in output/ directory")
        print("⚠️  Make sure multi-OEM scraping completed successfully")
        return

    print(f"Found {len(pickle_files)} dealer data files:\n")

    # Initialize multi-OEM detector
    detector = MultiOEMDetector()

    # Load dealers from each OEM
    oem_counts = {}

    for pickle_file in sorted(pickle_files):
        # Extract OEM name from filename (e.g., "Generac_dealers_20250125.pkl" -> "Generac")
        oem_name = pickle_file.stem.split("_dealers_")[0]

        dealers = load_dealers_from_pickle(str(pickle_file))

        if dealers:
            detector.add_dealers(dealers, oem_name)
            oem_counts[oem_name] = len(dealers)
            print(f"  ✓ {oem_name}: {len(dealers):,} dealers")
        else:
            print(f"  ⚠️  {oem_name}: 0 dealers (file may be empty or corrupt)")

    print()

    # Run multi-OEM detection
    print("=" * 70)
    print("RUNNING MULTI-OEM CROSS-REFERENCE DETECTION")
    print("=" * 70)
    print()

    multi_oem_matches = detector.find_multi_oem_contractors(min_oem_count=1)

    # Classify into tiers
    platinum_tier = [m for m in multi_oem_matches if len(m.oem_sources) >= 3]
    gold_tier = [m for m in multi_oem_matches if len(m.oem_sources) == 2]
    silver_tier = [m for m in multi_oem_matches if len(m.oem_sources) == 1]

    print("=" * 70)
    print("TIER CLASSIFICATION")
    print("=" * 70)
    print()
    print(f"🏆 PLATINUM Tier (3+ OEMs): {len(platinum_tier):,} contractors")
    print(f"   - Highest value prospects")
    print(f"   - Managing 3+ monitoring platforms")
    print(f"   - Multi-OEM score: 100/100")
    print()
    print(f"🥈 GOLD Tier (2 OEMs): {len(gold_tier):,} contractors")
    print(f"   - High value prospects")
    print(f"   - Managing 2 monitoring platforms")
    print(f"   - Multi-OEM score: 60/100")
    print()
    print(f"🥉 SILVER Tier (1 OEM): {len(silver_tier):,} contractors")
    print(f"   - Standard prospects")
    print(f"   - Single-brand certification")
    print(f"   - Multi-OEM score: 20/100")
    print()

    # Export results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 70)
    print("EXPORTING RESULTS")
    print("=" * 70)
    print()

    # Export full multi-OEM dataset
    json_path = output_dir / f"multi_oem_contractors_{timestamp}.json"
    detector.export_results(str(json_path))
    print(f"✓ JSON: {json_path}")

    csv_path = output_dir / f"multi_oem_contractors_{timestamp}.csv"
    detector.export_csv(str(csv_path))
    print(f"✓ CSV: {csv_path}")

    # Export tier-specific CSVs
    def export_tier_csv(matches: List[MultiOEMMatch], tier_name: str):
        """Export tier-specific CSV"""
        import csv

        filepath = output_dir / f"{tier_name}_tier_contractors_{timestamp}.csv"

        fieldnames = [
            "Contractor Name", "Phone", "Domain", "Website",
            "City", "State", "ZIP",
            "OEM Count", "OEM Sources",
            "Multi-OEM Score", "Match Confidence", "Match Signals",
            "All Capabilities",
        ]

        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for match in matches:
                contact = match.get_best_contact_info()
                primary = match.primary_dealer

                writer.writerow({
                    "Contractor Name": primary.name,
                    "Phone": contact["phone"],
                    "Domain": contact["domain"],
                    "Website": contact["website"],
                    "City": primary.city,
                    "State": primary.state,
                    "ZIP": primary.zip,
                    "OEM Count": len(match.oem_sources),
                    "OEM Sources": ", ".join(sorted(match.oem_sources)),
                    "Multi-OEM Score": match.multi_oem_score,
                    "Match Confidence": match.match_confidence,
                    "Match Signals": ", ".join(match.match_signals),
                    "All Capabilities": ", ".join(sorted(match.get_all_capabilities())),
                })

        print(f"✓ {tier_name.upper()}: {filepath} ({len(matches):,} contractors)")

    print()
    print("Tier-specific exports:")
    export_tier_csv(platinum_tier, "PLATINUM")
    export_tier_csv(gold_tier, "GOLD")
    export_tier_csv(silver_tier, "SILVER")

    # Export summary statistics
    print()
    print("=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)
    print()

    summary = {
        "scrape_timestamp": timestamp,
        "oem_counts": oem_counts,
        "total_oems_scraped": len(oem_counts),
        "total_dealers_raw": sum(oem_counts.values()),
        "total_unique_contractors": len(multi_oem_matches),
        "tier_breakdown": {
            "platinum": len(platinum_tier),
            "gold": len(gold_tier),
            "silver": len(silver_tier),
        },
        "top_platinum_contractors": [
            {
                "name": m.primary_dealer.name,
                "oem_count": len(m.oem_sources),
                "oem_sources": list(m.oem_sources),
                "multi_oem_score": m.multi_oem_score,
                "city": m.primary_dealer.city,
                "state": m.primary_dealer.state,
            }
            for m in platinum_tier[:10]
        ]
    }

    summary_path = output_dir / f"scrape_summary_{timestamp}.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"✓ Summary: {summary_path}")
    print()

    # Print key stats
    print("KEY METRICS:")
    print(f"  - Total OEMs scraped: {len(oem_counts)}")
    print(f"  - Total dealers (raw): {sum(oem_counts.values()):,}")
    print(f"  - Unique contractors (deduplicated): {len(multi_oem_matches):,}")
    print(f"  - Deduplication rate: {(1 - len(multi_oem_matches) / sum(oem_counts.values())) * 100:.1f}%")
    print()
    print(f"  - PLATINUM tier (3+ OEMs): {len(platinum_tier):,}")
    print(f"  - GOLD tier (2 OEMs): {len(gold_tier):,}")
    print(f"  - SILVER tier (1 OEM): {len(silver_tier):,}")
    print()

    if platinum_tier:
        print("TOP 5 PLATINUM PROSPECTS (3+ OEMs):")
        for i, match in enumerate(platinum_tier[:5], 1):
            print(f"  {i}. {match.primary_dealer.name}")
            print(f"     OEMs: {', '.join(sorted(match.oem_sources))}")
            print(f"     Location: {match.primary_dealer.city}, {match.primary_dealer.state}")
            print(f"     Score: {match.multi_oem_score}/100 | Confidence: {match.match_confidence}%")
            print()

    print("=" * 70)
    print("PIPELINE COMPLETE ✓")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Review PLATINUM_tier_contractors CSV (highest priority)")
    print("  2. Run Apollo.io enrichment (employee count, revenue, LinkedIn)")
    print("  3. Generate executive package for Monday meeting")
    print()


if __name__ == "__main__":
    main()
