#!/usr/bin/env python3
"""
OEM Scraper Final Audit - Comprehensive Validation Run

Validates ALL OEM scrapers by:
1. Navigating to each dealer locator URL
2. Running test extraction (1 ZIP code)
3. Verifying data captured with new enrichment fields
4. Saving audit results as JSON proof

Run: ./venv/bin/python3 scripts/audit_all_scrapers.py
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base_scraper import ScraperMode, StandardizedDealer


# ═══════════════════════════════════════════════════════════════════════════
# OEM REGISTRY - All scrapers to audit
# ═══════════════════════════════════════════════════════════════════════════

WORKING_OEMS = {
    "carrier": {
        "name": "Carrier",
        "scraper": "scrapers.carrier_scraper.CarrierScraper",
        "test_zip": "75201",  # Dallas, TX - high dealer density
        "category": "HVAC",
        "expected_records": 2618,
    },
    "trane": {
        "name": "Trane",
        "scraper": "scrapers.trane_scraper.TraneScraper",
        "test_zip": "75201",  # Dallas
        "category": "HVAC",
        "expected_records": 2802,
    },
    "mitsubishi": {
        "name": "Mitsubishi",
        "scraper": "scrapers.mitsubishi_scraper.MitsubishiScraper",
        "test_zip": "94102",  # San Francisco - commercial focus
        "category": "HVAC",
        "expected_records": 1799,
    },
    "generac": {
        "name": "Generac",
        "scraper": "scrapers.generac_scraper.GeneracScraper",
        "test_zip": "77001",  # Houston - storm belt
        "category": "Generator",
        "expected_records": 1706,
    },
    "rheem": {
        "name": "Rheem",
        "scraper": "scrapers.rheem_scraper.RheemScraper",
        "test_zip": "30301",  # Atlanta HQ
        "category": "HVAC",
        "expected_records": 1648,
    },
    "briggs": {
        "name": "Briggs & Stratton",
        "scraper": "scrapers.briggs_scraper.BriggsScraper",
        "test_zip": "53201",  # Milwaukee HQ
        "category": "Generator",
        "expected_records": 782,
    },
    "cummins": {
        "name": "Cummins",
        "scraper": "scrapers.cummins_scraper.CumminsScraper",
        "test_zip": "47201",  # Columbus, IN HQ
        "category": "Generator",
        "expected_records": 702,
    },
    "schneider": {
        "name": "Schneider Electric",
        "scraper": "scrapers.schneider_scraper.SchneiderScraper",
        "test_zip": "02116",  # Boston - tech hub
        "category": "Electrical",
        "expected_records": 143,
    },
    "york": {
        "name": "York",
        "scraper": "scrapers.york_scraper.YorkScraper",
        "test_zip": "17401",  # York, PA HQ
        "category": "HVAC",
        "expected_records": 90,
    },
    "tesla": {
        "name": "Tesla",
        "scraper": "scrapers.tesla_scraper.TeslaScraper",
        "test_zip": "94102",  # San Francisco
        "category": "Solar/Battery",
        "expected_records": 67,
    },
    "sma": {
        "name": "SMA",
        "scraper": "scrapers.sma_scraper.SMAScraper",
        "test_zip": "95054",  # Silicon Valley
        "category": "Inverter",
        "expected_records": 43,
    },
    "enphase": {
        "name": "Enphase",
        "scraper": "scrapers.enphase_scraper.EnphaseScraper",
        "test_zip": "94538",  # Fremont, CA HQ
        "category": "Microinverter",
        "expected_records": 26,
    },
}

BROKEN_OEMS = [
    "kohler",      # Extraction validated, needs Browserbase
    "lennox",      # URL changed
    "abb",         # URL changed
    "delta",       # No dealer locator found
    "fronius",     # JS rendering required
    "goodwe",      # Website changed
    "growatt",     # Website down/moved
    "honeywell",   # URL changed
    "johnson_controls",  # No public locator
    "sensi",       # URL changed
    "simpliphi",   # Connection timeout
    "solark",      # URL changed
    "solaredge",   # URL changed
    "sungrow",     # Website changed
    "tigo",        # URL changed
]


# ═══════════════════════════════════════════════════════════════════════════
# AUDIT FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def load_scraper_class(scraper_path: str):
    """
    Dynamically import and return a scraper class.

    Args:
        scraper_path: Dotted path like "scrapers.carrier_scraper.CarrierScraper"

    Returns:
        Scraper class
    """
    parts = scraper_path.rsplit(".", 1)
    module_path = parts[0]
    class_name = parts[1]

    module = __import__(module_path, fromlist=[class_name])
    return getattr(module, class_name)


def test_scraper(oem_key: str, oem_config: Dict) -> Dict[str, Any]:
    """
    Test a single OEM scraper with one ZIP code.

    Args:
        oem_key: OEM identifier (e.g., "carrier")
        oem_config: OEM configuration dict

    Returns:
        Test result dict
    """
    result = {
        "oem_key": oem_key,
        "oem_name": oem_config["name"],
        "category": oem_config["category"],
        "test_zip": oem_config["test_zip"],
        "status": "pending",
        "dealers_found": 0,
        "sample_dealers": [],
        "has_phone": 0,
        "has_website": 0,
        "has_rating": 0,
        "multi_trade_count": 0,
        "error": None,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "duration_seconds": 0,
    }

    start_time = time.time()

    try:
        print(f"\n{'='*60}")
        print(f"  TESTING: {oem_config['name']} ({oem_config['category']})")
        print(f"  ZIP: {oem_config['test_zip']}")
        print(f"{'='*60}")

        # Load scraper class
        ScraperClass = load_scraper_class(oem_config["scraper"])
        scraper = ScraperClass(mode=ScraperMode.PLAYWRIGHT)

        # Run test extraction
        dealers = scraper.scrape_zip_code(oem_config["test_zip"])

        if dealers:
            result["status"] = "working"
            result["dealers_found"] = len(dealers)

            # Analyze results
            for dealer in dealers:
                if dealer.phone:
                    result["has_phone"] += 1
                if dealer.website:
                    result["has_website"] += 1
                if dealer.rating and dealer.rating > 0:
                    result["has_rating"] += 1
                if hasattr(dealer.capabilities, 'is_multi_trade') and dealer.capabilities.is_multi_trade:
                    result["multi_trade_count"] += 1

            # Save sample dealers (first 3)
            result["sample_dealers"] = [
                {
                    "name": d.name,
                    "phone": d.phone,
                    "city": d.city,
                    "state": d.state,
                    "website": d.website,
                    "rating": d.rating,
                    "multi_trade": hasattr(d.capabilities, 'is_multi_trade') and d.capabilities.is_multi_trade,
                }
                for d in dealers[:3]
            ]

            # Calculate percentages
            phone_pct = (result["has_phone"] / len(dealers) * 100) if dealers else 0
            website_pct = (result["has_website"] / len(dealers) * 100) if dealers else 0

            print(f"\n  ✅ WORKING - Found {len(dealers)} dealers")
            print(f"     Phone coverage: {result['has_phone']}/{len(dealers)} ({phone_pct:.0f}%)")
            print(f"     Website coverage: {result['has_website']}/{len(dealers)} ({website_pct:.0f}%)")
            print(f"     Multi-trade signals: {result['multi_trade_count']}")

        else:
            result["status"] = "partial"
            print(f"\n  ⚠️  PARTIAL - No dealers returned for test ZIP")

    except Exception as e:
        result["status"] = "broken"
        result["error"] = str(e)
        print(f"\n  ❌ BROKEN - Error: {str(e)}")

        import traceback
        traceback.print_exc()

    # Finalize timing
    result["completed_at"] = datetime.now().isoformat()
    result["duration_seconds"] = round(time.time() - start_time, 2)

    return result


def run_full_audit(oems_to_test: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Run full audit on all (or specified) OEM scrapers.

    Args:
        oems_to_test: Optional list of OEM keys to test (default: all working OEMs)

    Returns:
        Full audit report dict
    """
    if oems_to_test is None:
        oems_to_test = list(WORKING_OEMS.keys())

    audit_report = {
        "audit_date": datetime.now().strftime("%Y-%m-%d"),
        "audit_timestamp": datetime.now().isoformat(),
        "total_oems_tested": len(oems_to_test),
        "working": 0,
        "partial": 0,
        "broken": 0,
        "total_dealers_found": 0,
        "results": [],
    }

    print("\n" + "═"*60)
    print("  OEM SCRAPER FINAL AUDIT")
    print(f"  Date: {audit_report['audit_date']}")
    print(f"  Testing: {len(oems_to_test)} OEMs")
    print("═"*60)

    for oem_key in oems_to_test:
        if oem_key not in WORKING_OEMS:
            print(f"\n⚠️  Skipping unknown OEM: {oem_key}")
            continue

        oem_config = WORKING_OEMS[oem_key]
        result = test_scraper(oem_key, oem_config)
        audit_report["results"].append(result)

        # Update counts
        if result["status"] == "working":
            audit_report["working"] += 1
        elif result["status"] == "partial":
            audit_report["partial"] += 1
        else:
            audit_report["broken"] += 1

        audit_report["total_dealers_found"] += result["dealers_found"]

        # Brief pause between scrapers
        time.sleep(2)

    return audit_report


def save_audit_report(report: Dict[str, Any]) -> str:
    """
    Save audit report to JSON file.

    Args:
        report: Audit report dict

    Returns:
        Path to saved file
    """
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")
    filepath = output_dir / f"audit_results_{date_str}.json"

    with open(filepath, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📁 Audit report saved: {filepath}")
    return str(filepath)


def print_summary(report: Dict[str, Any]) -> None:
    """Print human-readable summary of audit results."""

    print("\n" + "═"*60)
    print("  AUDIT SUMMARY")
    print("═"*60)

    print(f"\n  Date: {report['audit_date']}")
    print(f"  OEMs Tested: {report['total_oems_tested']}")
    print(f"  Total Dealers Found: {report['total_dealers_found']}")

    print(f"\n  Status Breakdown:")
    print(f"    ✅ WORKING: {report['working']}")
    print(f"    ⚠️  PARTIAL: {report['partial']}")
    print(f"    ❌ BROKEN:  {report['broken']}")

    # Detailed breakdown by OEM
    print(f"\n  {'OEM':<20} {'Status':<12} {'Dealers':<10} {'Phone %':<10} {'Multi-Trade':<12}")
    print(f"  {'-'*74}")

    for result in report["results"]:
        status_icon = {
            "working": "✅",
            "partial": "⚠️",
            "broken": "❌",
        }.get(result["status"], "?")

        dealers = result["dealers_found"]
        phone_pct = (result["has_phone"] / dealers * 100) if dealers > 0 else 0

        print(f"  {result['oem_name']:<20} {status_icon} {result['status']:<8} {dealers:<10} {phone_pct:<9.0f}% {result['multi_trade_count']:<12}")

    print("\n" + "═"*60)

    # List broken scrapers for follow-up
    if BROKEN_OEMS:
        print(f"\n  📋 BROKEN SCRAPERS (not tested, need investigation):")
        for oem in BROKEN_OEMS:
            print(f"     • {oem}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Run the full OEM scraper audit."""

    import argparse

    parser = argparse.ArgumentParser(description="OEM Scraper Audit")
    parser.add_argument(
        "--oems",
        nargs="+",
        help="Specific OEMs to test (default: all working OEMs)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: test only first 3 OEMs"
    )

    args = parser.parse_args()

    # Determine which OEMs to test
    if args.oems:
        oems_to_test = args.oems
    elif args.quick:
        oems_to_test = list(WORKING_OEMS.keys())[:3]
    else:
        oems_to_test = list(WORKING_OEMS.keys())

    # Run audit
    report = run_full_audit(oems_to_test)

    # Save report
    save_audit_report(report)

    # Print summary
    print_summary(report)

    print("\n✅ Audit complete!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
