#!/usr/bin/env python3
"""
Extract top 40-50 wealthiest ZIP codes across SREC states for targeted scraping.

This creates a prioritized list for high-value contractor prospecting.
"""

import json
from config import WEALTHY_ZIPS

def get_top_wealthy_zips(num_zips=40):
    """
    Get top wealthy ZIPs across all SREC states.

    Takes top 10 from CA, top 8 from TX, top 8 from PA,
    top 8 from MA, top 8 from NJ, top 8 from FL = 50 total

    Or for 40 total: 10 CA, 6 each for others = 40
    """

    if num_zips == 40:
        # 10 CA + 6 each for TX, PA, MA, NJ, FL = 40
        distribution = {
            "CA": 10,
            "TX": 6,
            "PA": 6,
            "MA": 6,
            "NJ": 6,
            "FL": 6
        }
    elif num_zips == 50:
        # 10 CA + 8 each for others = 50
        distribution = {
            "CA": 10,
            "TX": 8,
            "PA": 8,
            "MA": 8,
            "NJ": 8,
            "FL": 8
        }
    else:
        # Default: take 10 from each state = 60
        distribution = {
            "CA": 10,
            "TX": 10,
            "PA": 10,
            "MA": 10,
            "NJ": 10,
            "FL": 10
        }

    selected_zips = []
    state_breakdown = {}

    for state, count in distribution.items():
        zips = WEALTHY_ZIPS.get(state, [])[:count]
        selected_zips.extend(zips)
        state_breakdown[state] = {
            "count": len(zips),
            "zips": zips
        }

    return selected_zips, state_breakdown

def main():
    print("=" * 70)
    print("WEALTHY ZIP CODES FOR SREC STATES SCRAPING")
    print("=" * 70)
    print()

    # Get top 40
    zips_40, breakdown_40 = get_top_wealthy_zips(40)

    print("📊 TOP 40 WEALTHY ZIP CODES")
    print("=" * 70)
    for state, data in breakdown_40.items():
        print(f"\n{state} ({data['count']} ZIPs):")
        for zip_code in data['zips']:
            print(f"  • {zip_code}")

    print(f"\n\n{'=' * 70}")
    print(f"TOTAL: {len(zips_40)} ZIP codes selected")
    print("=" * 70)

    # Save to JSON for scraping
    output = {
        "description": "Top 40 wealthiest ZIP codes across SREC states (CA, TX, PA, MA, NJ, FL)",
        "total_zips": len(zips_40),
        "states": list(breakdown_40.keys()),
        "breakdown": breakdown_40,
        "all_zips": zips_40,
        "scraping_notes": "Use these ZIPs for targeted contractor prospecting in high-value markets"
    }

    with open('output/wealthy_zips_target.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("\n✅ Saved to: output/wealthy_zips_target.json")
    print()

    # Also create a simple CSV
    with open('output/wealthy_zips_target.csv', 'w') as f:
        f.write("zip_code,state\n")
        for state, data in breakdown_40.items():
            for zip_code in data['zips']:
                f.write(f"{zip_code},{state}\n")

    print("✅ Saved to: output/wealthy_zips_target.csv")
    print()

if __name__ == "__main__":
    main()
