"""
Coperniq Lead Generation Script - MVP

Generates scored contractor leads for immediate outreach.

MVP Flow (Generac only):
1. Scrape Generac dealers from SREC states (CA, TX, PA, MA, NJ, FL)
2. Filter to SREC states only
3. Convert to MultiOEMMatch format (for compatibility with scorer)
4. Score with Coperniq algorithm
5. Export to CSV sorted by score (HIGH priority first)

Output: coperniq_leads_YYYYMMDD.csv

Usage:
    # RUNPOD mode (automated cloud scraping)
    python scripts/generate_leads.py --mode runpod --states CA TX PA
    
    # PLAYWRIGHT mode (manual MCP workflow)
    python scripts/generate_leads.py --mode playwright --states CA
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.generac_scraper import GeneracScraper
from scrapers.base_scraper import ScraperMode
from targeting.srec_itc_filter import SRECITCFilter
from targeting.coperniq_lead_scorer import CoperniqLeadScorer
from analysis.multi_oem_detector import MultiOEMMatch
import argparse


# SREC State ZIP codes (major metros)
SREC_STATE_ZIPS = {
    "CA": [
        # San Francisco Bay Area
        "94102", "94301", "94022", "94024",  # SF, Palo Alto, Los Altos
        # Los Angeles
        "90001", "90210", "90265", "91101",  # LA, Beverly Hills, Malibu, Pasadena
        # San Diego
        "92101", "92037", "92067",  # Downtown SD, La Jolla, Rancho Santa Fe
        # Sacramento
        "95814", "95819",  # Downtown, East Sac
        # Orange County
        "92660", "92625",  # Newport Beach, Corona del Mar
    ],
    "TX": [
        # Houston
        "77002", "77019", "77024", "77005",  # Downtown, River Oaks, Memorial, West U
        # Dallas
        "75201", "75205", "75225",  # Downtown, Highland Park
        # Austin
        "78701", "78746", "78733",  # Downtown, Westlake Hills
        # San Antonio
        "78201", "78209",  # Downtown, Alamo Heights
        # Fort Worth
        "76102", "76107",  # Downtown, Rivercrest
    ],
    "PA": [
        # Philadelphia
        "19102", "19103", "19146",  # Center City
        # Philadelphia suburbs
        "19035", "19087", "19085",  # Gladwyne, Wayne, Villanova
        # Pittsburgh
        "15222", "15215", "15238",  # Downtown, Fox Chapel, Sewickley
    ],
    "MA": [
        # Boston
        "02108", "02116", "02199",  # Downtown, Back Bay
        # Boston suburbs
        "02467", "02481", "02492", "02445",  # Chestnut Hill, Wellesley, Needham, Brookline
        # Cambridge
        "02138", "02139", "02142",  # Cambridge
    ],
    "NJ": [
        # Northern NJ
        "07078", "07920", "07039",  # Short Hills, Basking Ridge, Livingston
        # Central NJ
        "08540", "08648",  # Princeton, Lawrence
        # Shore
        "07733", "07740",  # Holmdel, Long Branch
    ],
    "FL": [
        # Miami
        "33109", "33139", "33158",  # Fisher Island, Miami Beach, Pinecrest
        # Palm Beach
        "33480", "33455",  # Palm Beach, Hobe Sound
        # Naples
        "34102", "34103",  # Naples, Old Naples
        # Tampa
        "33606", "33629",  # South Tampa, Bayshore
        # Orlando
        "32801", "32819",  # Downtown, Dr. Phillips
    ],
}


def create_single_oem_match(dealer, oem_name="Generac"):
    """
    Convert StandardizedDealer to MultiOEMMatch format.
    
    This allows single-OEM dealers to be scored with the Coperniq algorithm,
    which expects MultiOEMMatch objects.
    
    Args:
        dealer: StandardizedDealer object
        oem_name: OEM source name
    
    Returns:
        MultiOEMMatch object with single OEM
    """
    match = MultiOEMMatch(
        primary_dealer=dealer,
        oem_sources={oem_name},
        dealer_records=[dealer],
        match_confidence=100,  # Single source = 100% confidence
        match_signals=["single_oem"],
    )
    match.multi_oem_score = match.calculate_multi_oem_score()
    
    return match


def main():
    parser = argparse.ArgumentParser(description="Generate Coperniq contractor leads")
    parser.add_argument(
        "--mode",
        choices=["runpod", "playwright"],
        default="runpod",
        help="Scraping mode (runpod = automated, playwright = manual MCP)"
    )
    parser.add_argument(
        "--states",
        nargs="+",
        default=["CA"],
        choices=list(SREC_STATE_ZIPS.keys()),
        help="SREC states to scrape (e.g., --states CA TX PA)"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory for results"
    )
    parser.add_argument(
        "--limit-zips",
        type=int,
        default=None,
        help="Limit number of ZIPs per state (for testing)"
    )
    
    args = parser.parse_args()
    
    # Print header
    print("\n" + "="*70)
    print("🚀 COPERNIQ LEAD GENERATION - MVP")
    print("="*70)
    print(f"Mode: {args.mode.upper()}")
    print(f"Target States: {', '.join(args.states)}")
    print(f"Output: {args.output_dir}/")
    print("="*70 + "\n")
    
    # Build ZIP code list
    all_zips = []
    for state in args.states:
        state_zips = SREC_STATE_ZIPS[state]
        if args.limit_zips:
            state_zips = state_zips[:args.limit_zips]
        all_zips.extend(state_zips)
        print(f"  {state}: {len(state_zips)} ZIPs")
    
    print(f"\nTotal ZIPs to scrape: {len(all_zips)}\n")
    
    # Initialize scraper
    mode = ScraperMode.RUNPOD if args.mode == "runpod" else ScraperMode.PLAYWRIGHT
    scraper = GeneracScraper(mode=mode)
    
    # Scrape dealers
    print("STEP 1: Scraping Generac dealers...")
    print("-" * 70)
    
    if mode == ScraperMode.PLAYWRIGHT:
        print("\n⚠️  PLAYWRIGHT MODE - Manual workflow required")
        print("Follow the MCP tool instructions printed for each ZIP code\n")
        scraper.scrape_multiple(all_zips)
        print("\n⚠️  After manual scraping, re-run this script to process results")
        return
    else:
        dealers = scraper.scrape_multiple(all_zips, verbose=True)
        scraper.deduplicate()
        print(f"\n✅ Scraped {len(scraper.dealers)} unique Generac dealers")
    
    # Convert to MultiOEMMatch format for scoring
    print("\nSTEP 2: Preparing dealers for scoring...")
    print("-" * 70)
    dealer_matches = [create_single_oem_match(d, "Generac") for d in scraper.dealers]
    print(f"✅ Converted {len(dealer_matches)} dealers to scoring format")
    
    # Filter to SREC states
    print("\nSTEP 3: Filtering to SREC states...")
    print("-" * 70)
    srec_filter = SRECITCFilter()
    srec_result = srec_filter.filter_contractors(dealer_matches)
    print(srec_result.summary())
    
    # Score with Coperniq algorithm
    print("\nSTEP 4: Scoring with Coperniq algorithm...")
    print("-" * 70)
    scorer = CoperniqLeadScorer()
    scores = scorer.score_contractors(srec_result.contractors)
    
    # Export results
    print("\nSTEP 5: Exporting results...")
    print("-" * 70)
    
    os.makedirs(args.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Export scored leads CSV
    csv_path = f"{args.output_dir}/coperniq_leads_{timestamp}.csv"
    scorer.export_csv(scores, csv_path)
    
    # Export full JSON
    json_path = f"{args.output_dir}/coperniq_leads_{timestamp}.json"
    scorer.export_results(scores, json_path)
    
    # Also save raw dealers for reference
    raw_csv_path = f"{args.output_dir}/generac_dealers_raw_{timestamp}.csv"
    scraper.save_csv(raw_csv_path)
    
    # Print top 10 prospects
    print("\n" + "="*70)
    print("🎯 TOP 10 COPERNIQ PROSPECTS")
    print("="*70)
    
    for i, score in enumerate(scorer.get_top_prospects(scores, 10), 1):
        print(f"\n{i}. {score.contractor_name}")
        print(f"   Score: {score.total_score}/100 ({score.priority_tier})")
        print(f"   Phone: {score.contractor_phone}")
        print(f"   Domain: {score.contractor_domain}")
        print(f"   Breakdown:")
        print(f"     • Multi-OEM: {score.multi_oem_score}/40 - {score.score_breakdown['multi_oem']}")
        print(f"     • SREC State: {score.srec_state_score}/20 - {score.score_breakdown['srec_state']}")
        print(f"     • Commercial: {score.commercial_capability_score}/20 - {score.score_breakdown['commercial_capability']}")
        print(f"     • Geographic: {score.geographic_score}/10 - {score.score_breakdown['geographic']}")
        print(f"     • ITC Urgency: {score.itc_urgency_score}/10 - {score.score_breakdown['itc_urgency']}")
    
    print("\n" + "="*70)
    print("✅ LEAD GENERATION COMPLETE")
    print("="*70)
    print(f"\nOutputs:")
    print(f"  📊 Scored Leads CSV: {csv_path}")
    print(f"  📄 Full JSON: {json_path}")
    print(f"  📋 Raw Dealers CSV: {raw_csv_path}")
    print(f"\n🚀 Start calling HIGH priority leads first (score 80-100)")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
