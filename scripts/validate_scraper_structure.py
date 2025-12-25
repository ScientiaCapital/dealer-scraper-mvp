#!/usr/bin/env python3
"""
OEM Scraper Structure Validation - No Network Required

Validates all 20 active OEM scrapers for:
1. Import success (module loads without error)
2. Factory registration (ScraperFactory.create works)
3. Required class attributes (OEM_NAME, DEALER_LOCATOR_URL)
4. Required methods (get_extraction_script, detect_capabilities, parse_dealer_data)
5. Extraction script syntax (JavaScript is valid)

Run: python scripts/validate_scraper_structure.py
"""

import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Track validation results
RESULTS = {
    "passed": [],
    "failed": [],
    "warnings": [],
}


def validate_js_syntax(script: str, oem_name: str) -> tuple:
    """
    Basic validation of JavaScript extraction script.

    Checks for:
    - Non-empty script
    - Contains function definition (arrow or regular)
    - Contains return statement
    - Common extraction patterns

    Returns:
        (is_valid, issues_list)
    """
    issues = []

    if not script or len(script.strip()) < 50:
        issues.append("Script too short or empty")
        return False, issues

    # Check for function pattern
    has_function = (
        "() =>" in script or
        "function" in script or
        "=>" in script
    )
    if not has_function:
        issues.append("No function definition found")

    # Check for return statement
    if "return" not in script:
        issues.append("No return statement found")

    # Check for common extraction patterns
    has_query = (
        "querySelector" in script or
        "querySelectorAll" in script or
        "getElementById" in script or
        "getElementsByClassName" in script
    )
    if not has_query:
        issues.append("No DOM query selectors found")

    # Check for dealer array
    has_dealers = "dealers" in script.lower() or "results" in script.lower()
    if not has_dealers:
        issues.append("No 'dealers' or 'results' array found")

    is_valid = len(issues) == 0 or (has_function and "return" in script)

    return is_valid, issues


def validate_scraper(oem_key: str, oem_name: str, scraper_class_path: str) -> Dict:
    """
    Validate a single scraper's structure.

    Args:
        oem_key: OEM identifier (e.g., "carrier")
        oem_name: Display name (e.g., "Carrier")
        scraper_class_path: Dotted path (e.g., "scrapers.carrier_scraper.CarrierScraper")

    Returns:
        Validation result dict
    """
    result = {
        "oem_key": oem_key,
        "oem_name": oem_name,
        "import_ok": False,
        "factory_ok": False,
        "oem_name_ok": False,
        "url_ok": False,
        "methods_ok": False,
        "extraction_script_ok": False,
        "issues": [],
        "warnings": [],
    }

    try:
        # Step 1: Import the module
        parts = scraper_class_path.rsplit(".", 1)
        module_path = parts[0]
        class_name = parts[1]

        module = __import__(module_path, fromlist=[class_name])
        ScraperClass = getattr(module, class_name)
        result["import_ok"] = True

    except ImportError as e:
        result["issues"].append(f"Import error: {e}")
        return result
    except AttributeError as e:
        result["issues"].append(f"Class not found: {e}")
        return result
    except Exception as e:
        result["issues"].append(f"Unexpected error: {e}")
        return result

    try:
        # Step 2: Check factory registration
        from scrapers.scraper_factory import ScraperFactory
        from scrapers.base_scraper import ScraperMode

        # Try to create via factory
        try:
            scraper = ScraperFactory.create(oem_key, mode=ScraperMode.PLAYWRIGHT)
            result["factory_ok"] = True
        except ValueError as e:
            result["issues"].append(f"Factory registration missing: {e}")
            # Try direct instantiation
            scraper = ScraperClass(mode=ScraperMode.PLAYWRIGHT)

        # Step 3: Check OEM_NAME
        if hasattr(scraper, 'OEM_NAME') and scraper.OEM_NAME:
            result["oem_name_ok"] = True
        else:
            result["issues"].append("OEM_NAME not set")

        # Step 4: Check DEALER_LOCATOR_URL
        if hasattr(scraper, 'DEALER_LOCATOR_URL') and scraper.DEALER_LOCATOR_URL:
            result["url_ok"] = True
            # Validate URL format
            url = scraper.DEALER_LOCATOR_URL
            if not url.startswith(("http://", "https://")):
                result["warnings"].append(f"URL may be invalid: {url[:50]}...")
        else:
            result["issues"].append("DEALER_LOCATOR_URL not set")

        # Step 5: Check required methods
        required_methods = [
            "get_extraction_script",
            "detect_capabilities",
            "parse_dealer_data",
            "scrape_zip_code",
        ]

        missing_methods = []
        for method in required_methods:
            if not hasattr(scraper, method) or not callable(getattr(scraper, method)):
                missing_methods.append(method)

        if missing_methods:
            result["issues"].append(f"Missing methods: {', '.join(missing_methods)}")
        else:
            result["methods_ok"] = True

        # Step 6: Validate extraction script
        if hasattr(scraper, 'get_extraction_script'):
            try:
                script = scraper.get_extraction_script()
                is_valid, js_issues = validate_js_syntax(script, oem_name)
                result["extraction_script_ok"] = is_valid
                if js_issues:
                    for issue in js_issues:
                        result["warnings"].append(f"JS: {issue}")
            except Exception as e:
                result["issues"].append(f"Extraction script error: {e}")

    except Exception as e:
        result["issues"].append(f"Validation error: {e}")

    return result


def print_validation_report(results: List[Dict]) -> None:
    """Print formatted validation report."""

    print("\n" + "═" * 70)
    print("  OEM SCRAPER STRUCTURE VALIDATION REPORT")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 70)

    # Summary
    passed = [r for r in results if not r["issues"]]
    warnings = [r for r in results if not r["issues"] and r["warnings"]]
    failed = [r for r in results if r["issues"]]

    print(f"\n  Total scrapers: {len(results)}")
    print(f"  ✅ Passed: {len(passed)}")
    print(f"  ⚠️  Warnings: {len(warnings)}")
    print(f"  ❌ Failed: {len(failed)}")

    # Detailed results table
    print(f"\n  {'OEM':<20} {'Import':<8} {'Factory':<8} {'URL':<8} {'Methods':<8} {'Script':<8} {'Status'}")
    print(f"  {'-'*76}")

    for r in results:
        status = "✅" if not r["issues"] else "❌"
        import_s = "✓" if r["import_ok"] else "✗"
        factory_s = "✓" if r["factory_ok"] else "✗"
        url_s = "✓" if r["url_ok"] else "✗"
        methods_s = "✓" if r["methods_ok"] else "✗"
        script_s = "✓" if r["extraction_script_ok"] else "✗"

        print(f"  {r['oem_name']:<20} {import_s:<8} {factory_s:<8} {url_s:<8} {methods_s:<8} {script_s:<8} {status}")

    # Failed details
    if failed:
        print(f"\n  ❌ FAILED SCRAPERS ({len(failed)}):")
        for r in failed:
            print(f"\n  {r['oem_name']}:")
            for issue in r["issues"]:
                print(f"     • {issue}")

    # Warnings
    if warnings:
        print(f"\n  ⚠️  SCRAPERS WITH WARNINGS ({len(warnings)}):")
        for r in warnings:
            print(f"\n  {r['oem_name']}:")
            for warn in r["warnings"]:
                print(f"     • {warn}")

    print("\n" + "═" * 70)


def main():
    """Run structure validation on all active scrapers."""

    # All 20 active scrapers (from __init__.py)
    # Note: Factory keys use lowercase with spaces (e.g., "johnson controls")
    ACTIVE_SCRAPERS = {
        # HVAC (8)
        "carrier": ("Carrier", "scrapers.carrier_scraper.CarrierScraper"),
        "trane": ("Trane", "scrapers.trane_scraper.TraneScraper"),
        "lennox": ("Lennox", "scrapers.lennox_scraper.LennoxScraper"),
        "york": ("York", "scrapers.york_scraper.YorkScraper"),
        "rheem": ("Rheem", "scrapers.rheem_scraper.RheemScraper"),
        "mitsubishi": ("Mitsubishi", "scrapers.mitsubishi_scraper.MitsubishiScraper"),
        "honeywell home": ("Honeywell", "scrapers.honeywell_scraper.HoneywellHomeScraper"),
        "sensi": ("Sensi", "scrapers.sensi_scraper.SensiScraper"),
        # Generators (4)
        "generac": ("Generac", "scrapers.generac_scraper.GeneracScraper"),
        "briggs & stratton": ("Briggs & Stratton", "scrapers.briggs_scraper.BriggsStrattonScraper"),
        "cummins": ("Cummins", "scrapers.cummins_scraper.CumminsScraper"),
        "kohler": ("Kohler", "scrapers.kohler_scraper.KohlerScraper"),
        # Solar Inverters (6)
        "tesla": ("Tesla", "scrapers.tesla_scraper.TeslaScraper"),
        "enphase": ("Enphase", "scrapers.enphase_scraper.EnphaseScraper"),
        "fronius": ("Fronius", "scrapers.fronius_scraper.FroniusScraper"),
        "sma": ("SMA", "scrapers.sma_scraper.SMAScraper"),
        "solark": ("Sol-Ark", "scrapers.solark_scraper.SolArkScraper"),
        "solaredge": ("SolarEdge", "scrapers.solaredge_scraper.SolarEdgeScraper"),
        # Battery (1)
        "simpliphi": ("SimpliPhi", "scrapers.simpliphi_scraper.SimpliPhiScraper"),
        # Building Automation (1)
        "schneider electric": ("Schneider Electric", "scrapers.schneider_scraper.SchneiderElectricScraper"),
    }

    print("\n🔍 Validating 20 OEM scraper structures...\n")

    results = []
    for oem_key, (oem_name, class_path) in ACTIVE_SCRAPERS.items():
        print(f"  Checking {oem_name}...", end=" ")
        result = validate_scraper(oem_key, oem_name, class_path)
        results.append(result)

        if result["issues"]:
            print("❌")
        elif result["warnings"]:
            print("⚠️")
        else:
            print("✓")

    # Print report
    print_validation_report(results)

    # Return exit code
    failed_count = len([r for r in results if r["issues"]])
    return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
