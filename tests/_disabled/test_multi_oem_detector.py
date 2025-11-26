#!/usr/bin/env python3
"""
Quick test of multi-OEM detection on manual MCP Playwright results

Finds contractors certified with 2+ OEM brands (highest value Coperniq prospects)
"""

import json
from analysis.multi_oem_detector import MultiOEMDetector
from scrapers.base_scraper import StandardizedDealer

def load_test_data():
    """Load manually scraped test data from all 3 OEMs"""

    tesla_dealers = []
    enphase_dealers = []
    solaredge_dealers = []

    # Tesla results (108 installers)
    try:
        with open('output/test_tesla_mcp_94102.json', 'r') as f:
            tesla_data = json.load(f)
            for dealer_dict in tesla_data.get('dealers', []):
                # Convert to StandardizedDealer
                dealer = StandardizedDealer(
                    name=dealer_dict.get('name', ''),
                    phone=dealer_dict.get('phone', ''),
                    domain='',  # Extract from website if available
                    website=dealer_dict.get('website', ''),
                    street='',
                    city='',
                    state='',
                    zip='',
                    address_full='',
                    tier=dealer_dict.get('tier', ''),
                    certifications=dealer_dict.get('certifications', []),
                    oem_source='Tesla',
                    scraped_from_zip='94102'
                )
                tesla_dealers.append(dealer)
            print(f"✅ Loaded {len(tesla_data.get('dealers', []))} Tesla installers")
    except FileNotFoundError:
        print("⚠️  Tesla data not found (test_tesla_mcp_94102.json)")

    # Enphase results (27 installers)
    try:
        with open('output/test_enphase_mcp_94102.json', 'r') as f:
            enphase_data = json.load(f)
            for dealer_dict in enphase_data.get('dealers', []):
                dealer = StandardizedDealer(
                    name=dealer_dict.get('name', ''),
                    phone=dealer_dict.get('phone', ''),
                    domain='',
                    website=dealer_dict.get('website', ''),
                    street='',
                    city='',
                    state='',
                    zip='',
                    address_full='',
                    tier=dealer_dict.get('tier', ''),
                    certifications=dealer_dict.get('certifications', []),
                    oem_source='Enphase',
                    scraped_from_zip='94102'
                )
                enphase_dealers.append(dealer)
            print(f"✅ Loaded {len(enphase_data.get('dealers', []))} Enphase installers")
    except FileNotFoundError:
        print("⚠️  Enphase data not found (test_enphase_mcp_94102.json)")

    # SolarEdge results (3 installers)
    try:
        with open('output/test_solaredge_mcp_sf.json', 'r') as f:
            solaredge_data = json.load(f)
            for dealer_dict in solaredge_data.get('dealers', []):
                dealer = StandardizedDealer(
                    name=dealer_dict.get('name', ''),
                    phone=dealer_dict.get('phone', ''),
                    domain='',
                    website=dealer_dict.get('website', ''),
                    street='',
                    city='',
                    state='',
                    zip='',
                    address_full='',
                    tier=dealer_dict.get('tier', ''),
                    certifications=dealer_dict.get('certifications', []),
                    oem_source='SolarEdge',
                    scraped_from_zip='SF'
                )
                solaredge_dealers.append(dealer)
            print(f"✅ Loaded {len(solaredge_data.get('dealers', []))} SolarEdge installers")
    except FileNotFoundError:
        print("⚠️  SolarEdge data not found (test_solaredge_mcp_sf.json)")

    return tesla_dealers, enphase_dealers, solaredge_dealers

def main():
    print("="*70)
    print("Multi-OEM Detection Test - Manual MCP Playwright Results")
    print("="*70)
    print()

    # Load test data
    tesla_dealers, enphase_dealers, solaredge_dealers = load_test_data()

    total_dealers = len(tesla_dealers) + len(enphase_dealers) + len(solaredge_dealers)
    if total_dealers == 0:
        print("❌ No dealer data found!")
        return

    print(f"\n📊 Total dealers loaded: {total_dealers}")
    print()

    # Run multi-OEM detection
    print("Running multi-OEM detection...")
    detector = MultiOEMDetector()

    # Add dealers by OEM
    detector.add_dealers(tesla_dealers, "Tesla")
    detector.add_dealers(enphase_dealers, "Enphase")
    detector.add_dealers(solaredge_dealers, "SolarEdge")

    # Find multi-OEM matches (min_oem_count=1 to see all contractors)
    matches = detector.find_multi_oem_contractors(min_oem_count=1)

    print(f"\n{'='*70}")
    print("MULTI-OEM DETECTION RESULTS")
    print(f"{'='*70}\n")

    # Group by OEM count
    multi_oem_3plus = [m for m in matches if len(m.oem_sources) >= 3]
    multi_oem_2 = [m for m in matches if len(m.oem_sources) == 2]
    single_oem = [m for m in matches if len(m.oem_sources) == 1]

    print(f"🏆 3+ OEM Certifications: {len(multi_oem_3plus)} contractors")
    print(f"🥈 2 OEM Certifications: {len(multi_oem_2)} contractors")
    print(f"🥉 Single OEM: {len(single_oem)} contractors")
    print()

    # Show multi-OEM contractors (GOLD prospects!)
    if multi_oem_3plus:
        print(f"\n{'='*70}")
        print("🏆 TRIPLE-CERTIFIED CONTRACTORS (Highest Value!)")
        print(f"{'='*70}\n")

        for match in multi_oem_3plus:
            print(f"✨ {match.primary_dealer.name}")
            print(f"   OEMs: {', '.join(sorted(match.oem_sources))}")
            print(f"   Phone: {match.primary_dealer.phone or 'N/A'}")
            print(f"   Confidence: {match.match_confidence}%")
            print(f"   Multi-OEM Score: {match.multi_oem_score}/100")
            print()

    if multi_oem_2:
        print(f"\n{'='*70}")
        print("🥈 DUAL-CERTIFIED CONTRACTORS (High Value)")
        print(f"{'='*70}\n")

        for match in multi_oem_2[:10]:  # Show first 10
            print(f"• {match.primary_dealer.name}")
            print(f"  OEMs: {', '.join(sorted(match.oem_sources))}")
            print(f"  Phone: {match.primary_dealer.phone or 'N/A'}")
            print(f"  Confidence: {match.match_confidence}%")
            print(f"  Multi-OEM Score: {match.multi_oem_score}/100")
            print()

        if len(multi_oem_2) > 10:
            print(f"  ... and {len(multi_oem_2) - 10} more dual-certified contractors\n")

    # Summary stats
    print(f"\n{'='*70}")
    print("SUMMARY STATISTICS")
    print(f"{'='*70}\n")

    print(f"Total unique contractors: {len(matches)}")
    print(f"Multi-brand contractors (2+ OEMs): {len(multi_oem_2) + len(multi_oem_3plus)}")
    print(f"Multi-brand percentage: {((len(multi_oem_2) + len(multi_oem_3plus)) / len(matches) * 100):.1f}%")
    print()

    # OEM coverage
    oem_counts = {}
    for match in matches:
        for oem in match.oem_sources:
            oem_counts[oem] = oem_counts.get(oem, 0) + 1

    print("OEM Coverage:")
    for oem, count in sorted(oem_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {oem}: {count} contractors")
    print()

if __name__ == "__main__":
    main()
