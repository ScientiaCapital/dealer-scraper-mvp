# Phase 3: Cross-Reference Engine Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a cross-reference engine that matches state license data with OEM contractor data using multi-signal matching (phone, domain, fuzzy name), enabling ICP enrichment with license metadata.

**Architecture:** Multi-signal matching pipeline with confidence scoring. Primary match on normalized phone numbers (96.5% accuracy based on OEM deduplication), fallback to domain matching (0.7% additional), tertiary fuzzy name matching (0.1% additional). Output: enriched contractor records with license metadata for improved ICP scoring.

**Tech Stack:** Python 3.9+, pandas, fuzzywuzzy, phonenumbers library, existing StandardizedDealer/StandardizedLicensee models

---

## Task 1: Phone Normalization Utility

**Files:**
- Create: `utils/phone_normalizer.py`
- Test: `tests/unit/test_phone_normalizer.py`

**Step 1: Write the failing test**

Create `tests/unit/test_phone_normalizer.py`:

```python
import pytest
from utils.phone_normalizer import normalize_phone

def test_normalize_removes_country_code():
    """Test US country code removal"""
    assert normalize_phone("+1-323-555-1234") == "3235551234"
    assert normalize_phone("1-323-555-1234") == "3235551234"

def test_normalize_removes_formatting():
    """Test formatting removal"""
    assert normalize_phone("(323) 555-1234") == "3235551234"
    assert normalize_phone("323-555-1234") == "3235551234"
    assert normalize_phone("323.555.1234") == "3235551234"

def test_normalize_handles_extensions():
    """Test extension stripping"""
    assert normalize_phone("323-555-1234 ext 123") == "3235551234"
    assert normalize_phone("323-555-1234x456") == "3235551234"

def test_normalize_handles_invalid():
    """Test invalid phone handling"""
    assert normalize_phone("") is None
    assert normalize_phone(None) is None
    assert normalize_phone("abc") is None
    assert normalize_phone("123") is None  # Too short

def test_normalize_returns_10_digits():
    """Test all valid outputs are 10 digits"""
    result = normalize_phone("323-555-1234")
    assert result is not None
    assert len(result) == 10
    assert result.isdigit()
```

**Step 2: Run test to verify it fails**

Run: `python3 -c "from tests.unit.test_phone_normalizer import test_normalize_removes_country_code; test_normalize_removes_country_code()"`

Expected: `ModuleNotFoundError: No module named 'utils.phone_normalizer'`

**Step 3: Write minimal implementation**

Create `utils/phone_normalizer.py`:

```python
"""
Phone number normalization for cross-reference matching.

Normalizes US phone numbers to 10-digit strings (area code + number).
Based on successful OEM deduplication pattern (96.5% accuracy).
"""
import re
from typing import Optional


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    """
    Normalize phone number to 10-digit string.

    Args:
        phone: Raw phone number in any format

    Returns:
        10-digit string or None if invalid

    Examples:
        >>> normalize_phone("+1-323-555-1234")
        "3235551234"
        >>> normalize_phone("(323) 555-1234")
        "3235551234"
        >>> normalize_phone("invalid")
        None
    """
    if not phone:
        return None

    # Convert to string and strip whitespace
    phone = str(phone).strip()

    # Remove extensions (ext, x, followed by digits)
    phone = re.sub(r'\s*(ext|x)\s*\d+', '', phone, flags=re.IGNORECASE)

    # Extract only digits
    digits = re.sub(r'\D', '', phone)

    # Handle US country code (1 + 10 digits)
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]

    # Validate 10-digit US number
    if len(digits) != 10:
        return None

    return digits
```

**Step 4: Run tests to verify they pass**

Run: `python3 -c "from tests.unit.test_phone_normalizer import test_normalize_removes_country_code, test_normalize_removes_formatting, test_normalize_handles_extensions, test_normalize_handles_invalid, test_normalize_returns_10_digits; [test() for test in [test_normalize_removes_country_code, test_normalize_removes_formatting, test_normalize_handles_extensions, test_normalize_handles_invalid, test_normalize_returns_10_digits]]; print('✅ All tests passed')"`

Expected: `✅ All tests passed`

**Step 5: Commit**

```bash
git add utils/phone_normalizer.py tests/unit/test_phone_normalizer.py
git commit -m "feat: add phone normalization for cross-reference matching

- Removes country codes, formatting, extensions
- Returns 10-digit strings for US numbers
- Handles invalid inputs gracefully
- Based on 96.5% accuracy from OEM deduplication

🤖 Generated with Claude Code"
```

---

## Task 2: Domain Extraction Utility

**Files:**
- Create: `utils/domain_extractor.py`
- Test: `tests/unit/test_domain_extractor.py`

**Step 1: Write the failing test**

Create `tests/unit/test_domain_extractor.py`:

```python
import pytest
from utils.domain_extractor import extract_domain

def test_extract_removes_www():
    """Test www prefix removal"""
    assert extract_domain("www.example.com") == "example.com"
    assert extract_domain("www.subdomain.example.com") == "subdomain.example.com"

def test_extract_removes_protocol():
    """Test protocol removal"""
    assert extract_domain("https://example.com") == "example.com"
    assert extract_domain("http://www.example.com") == "example.com"
    assert extract_domain("https://www.example.com/path") == "example.com"

def test_extract_removes_path():
    """Test path removal"""
    assert extract_domain("example.com/about") == "example.com"
    assert extract_domain("example.com/about/team") == "example.com"

def test_extract_keeps_subdomain():
    """Test subdomain preservation"""
    assert extract_domain("shop.example.com") == "shop.example.com"
    assert extract_domain("blog.shop.example.com") == "blog.shop.example.com"

def test_extract_handles_invalid():
    """Test invalid domain handling"""
    assert extract_domain("") is None
    assert extract_domain(None) is None
    assert extract_domain("not a domain") is None

def test_extract_lowercases():
    """Test case normalization"""
    assert extract_domain("EXAMPLE.COM") == "example.com"
    assert extract_domain("Example.COM") == "example.com"
```

**Step 2: Run test to verify it fails**

Run: `python3 -c "from tests.unit.test_domain_extractor import test_extract_removes_www; test_extract_removes_www()"`

Expected: `ModuleNotFoundError: No module named 'utils.domain_extractor'`

**Step 3: Write minimal implementation**

Create `utils/domain_extractor.py`:

```python
"""
Domain extraction for cross-reference matching.

Extracts and normalizes domains from URLs and website strings.
"""
import re
from typing import Optional
from urllib.parse import urlparse


def extract_domain(url: Optional[str]) -> Optional[str]:
    """
    Extract domain from URL or website string.

    Removes protocol, www prefix, and paths. Preserves non-www subdomains.
    Normalizes to lowercase.

    Args:
        url: URL or website string

    Returns:
        Normalized domain or None if invalid

    Examples:
        >>> extract_domain("https://www.example.com/about")
        "example.com"
        >>> extract_domain("shop.example.com")
        "shop.example.com"
    """
    if not url:
        return None

    url = str(url).strip().lower()

    # Add protocol if missing (for urlparse)
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url

    # Parse URL
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0]
    except:
        return None

    if not domain or '.' not in domain:
        return None

    # Remove www prefix
    if domain.startswith('www.'):
        domain = domain[4:]

    return domain
```

**Step 4: Run tests to verify they pass**

Run: `python3 -c "from tests.unit.test_domain_extractor import test_extract_removes_www, test_extract_removes_protocol, test_extract_removes_path, test_extract_keeps_subdomain, test_extract_handles_invalid, test_extract_lowercases; [test() for test in [test_extract_removes_www, test_extract_removes_protocol, test_extract_removes_path, test_extract_keeps_subdomain, test_extract_handles_invalid, test_extract_lowercases]]; print('✅ All tests passed')"`

Expected: `✅ All tests passed`

**Step 5: Commit**

```bash
git add utils/domain_extractor.py tests/unit/test_domain_extractor.py
git commit -m "feat: add domain extraction for cross-reference matching

- Removes protocols, www prefix, paths
- Preserves non-www subdomains
- Normalizes to lowercase
- Handles invalid inputs gracefully

🤖 Generated with Claude Code"
```

---

## Task 3: License-OEM Cross-Reference Matcher

**Files:**
- Create: `analysis/license_oem_matcher.py`
- Test: `tests/unit/test_license_oem_matcher.py`

**Step 1: Write the failing test**

Create `tests/unit/test_license_oem_matcher.py`:

```python
import pytest
from analysis.license_oem_matcher import LicenseOEMMatcher
from scrapers.license.models import StandardizedLicensee
from scrapers.base_scraper import StandardizedDealer

def test_match_by_phone_exact():
    """Test exact phone number matching"""
    licensee = StandardizedLicensee(
        licensee_name="ABC Electric",
        license_number="12345",
        license_type="Electrical",
        license_status="Active",
        city="Los Angeles",
        state="CA",
        zip="90001",
        source_state="CA",
        source_tier="BULK",
        phone="323-555-1234"
    )

    dealer = StandardizedDealer(
        name="ABC Electrical Services",
        phone="+1 (323) 555-1234",  # Different format, same number
        city="Los Angeles",
        state="CA",
        zip="90001",
        oem_source="Generac",
        scraped_from_zip="90001"
    )

    matcher = LicenseOEMMatcher()
    matches = matcher.match([licensee], [dealer])

    assert len(matches) == 1
    assert matches[0]["licensee"] == licensee
    assert matches[0]["dealer"] == dealer
    assert matches[0]["match_type"] == "phone"
    assert matches[0]["confidence"] == 100

def test_match_by_domain():
    """Test domain matching when phone missing"""
    licensee = StandardizedLicensee(
        licensee_name="XYZ Solar",
        license_number="67890",
        license_type="Electrical",
        license_status="Active",
        city="San Diego",
        state="CA",
        zip="92101",
        source_state="CA",
        source_tier="BULK",
        website="https://www.xyzsolar.com"
    )

    dealer = StandardizedDealer(
        name="XYZ Solar Inc",
        domain="xyzsolar.com",
        city="San Diego",
        state="CA",
        zip="92101",
        oem_source="Tesla",
        scraped_from_zip="92101"
    )

    matcher = LicenseOEMMatcher()
    matches = matcher.match([licensee], [dealer])

    assert len(matches) == 1
    assert matches[0]["match_type"] == "domain"
    assert matches[0]["confidence"] == 90

def test_no_match_different_data():
    """Test no match when data doesn't align"""
    licensee = StandardizedLicensee(
        licensee_name="Company A",
        license_number="11111",
        license_type="Electrical",
        license_status="Active",
        city="Austin",
        state="TX",
        zip="78701",
        source_state="TX",
        source_tier="BULK",
        phone="512-555-1111"
    )

    dealer = StandardizedDealer(
        name="Company B",
        phone="512-555-2222",  # Different number
        city="Austin",
        state="TX",
        zip="78701",
        oem_source="Generac",
        scraped_from_zip="78701"
    )

    matcher = LicenseOEMMatcher()
    matches = matcher.match([licensee], [dealer])

    assert len(matches) == 0

def test_match_returns_enriched_dealer():
    """Test matched dealer gets enriched with license metadata"""
    licensee = StandardizedLicensee(
        licensee_name="Test Contractor",
        license_number="99999",
        license_type="HVAC",
        license_status="Active",
        city="Miami",
        state="FL",
        zip="33101",
        source_state="FL",
        source_tier="BULK",
        phone="305-555-9999"
    )

    dealer = StandardizedDealer(
        name="Test HVAC",
        phone="305-555-9999",
        city="Miami",
        state="FL",
        zip="33101",
        oem_source="Carrier",
        scraped_from_zip="33101"
    )

    matcher = LicenseOEMMatcher()
    matches = matcher.match([licensee], [dealer])

    match = matches[0]
    enriched = match["enriched_dealer"]

    # Verify enrichment fields
    assert enriched["license_number"] == "99999"
    assert enriched["license_type"] == "HVAC"
    assert enriched["license_status"] == "Active"
    assert enriched["license_state"] == "FL"
```

**Step 2: Run test to verify it fails**

Run: `python3 -c "from tests.unit.test_license_oem_matcher import test_match_by_phone_exact; test_match_by_phone_exact()"`

Expected: `ModuleNotFoundError: No module named 'analysis.license_oem_matcher'`

**Step 3: Write minimal implementation**

Create `analysis/license_oem_matcher.py`:

```python
"""
Cross-reference matcher for state licenses and OEM contractors.

Multi-signal matching pipeline:
1. Phone normalization (96.5% accuracy)
2. Domain matching (0.7% additional)
3. Fuzzy name matching (0.1% additional)
"""
from typing import List, Dict, Any
from scrapers.license.models import StandardizedLicensee
from scrapers.base_scraper import StandardizedDealer
from utils.phone_normalizer import normalize_phone
from utils.domain_extractor import extract_domain


class LicenseOEMMatcher:
    """
    Matches state license data with OEM contractor data.

    Uses multi-signal matching with confidence scoring:
    - Phone: 100% confidence (primary signal)
    - Domain: 90% confidence (secondary signal)
    - Fuzzy name: 80% confidence (tertiary signal)
    """

    def match(
        self,
        licensees: List[StandardizedLicensee],
        dealers: List[StandardizedDealer]
    ) -> List[Dict[str, Any]]:
        """
        Match licensees with dealers using multi-signal approach.

        Args:
            licensees: List of state license records
            dealers: List of OEM contractor records

        Returns:
            List of match dictionaries with:
            - licensee: StandardizedLicensee
            - dealer: StandardizedDealer
            - match_type: "phone", "domain", or "fuzzy_name"
            - confidence: 80-100
            - enriched_dealer: Dealer dict with license metadata added
        """
        matches = []

        # Build phone lookup for dealers
        dealer_phone_map = {}
        for dealer in dealers:
            phone = normalize_phone(dealer.phone)
            if phone:
                if phone not in dealer_phone_map:
                    dealer_phone_map[phone] = []
                dealer_phone_map[phone].append(dealer)

        # Build domain lookup for dealers
        dealer_domain_map = {}
        for dealer in dealers:
            domain = extract_domain(dealer.domain or dealer.website)
            if domain:
                if domain not in dealer_domain_map:
                    dealer_domain_map[domain] = []
                dealer_domain_map[domain].append(dealer)

        # Match each licensee
        for licensee in licensees:
            matched = False

            # Try phone match first (highest confidence)
            licensee_phone = normalize_phone(licensee.phone)
            if licensee_phone and licensee_phone in dealer_phone_map:
                for dealer in dealer_phone_map[licensee_phone]:
                    matches.append({
                        "licensee": licensee,
                        "dealer": dealer,
                        "match_type": "phone",
                        "confidence": 100,
                        "enriched_dealer": self._enrich_dealer(dealer, licensee)
                    })
                    matched = True

            # Try domain match if no phone match
            if not matched:
                licensee_domain = extract_domain(licensee.website)
                if licensee_domain and licensee_domain in dealer_domain_map:
                    for dealer in dealer_domain_map[licensee_domain]:
                        matches.append({
                            "licensee": licensee,
                            "dealer": dealer,
                            "match_type": "domain",
                            "confidence": 90,
                            "enriched_dealer": self._enrich_dealer(dealer, licensee)
                        })
                        matched = True

        return matches

    def _enrich_dealer(
        self,
        dealer: StandardizedDealer,
        licensee: StandardizedLicensee
    ) -> Dict[str, Any]:
        """
        Create enriched dealer dict with license metadata.

        Args:
            dealer: Original dealer record
            licensee: Matched license record

        Returns:
            Dealer dict with added license fields
        """
        # Convert dealer to dict
        enriched = {
            "name": dealer.name,
            "phone": dealer.phone,
            "domain": dealer.domain,
            "website": dealer.website,
            "city": dealer.city,
            "state": dealer.state,
            "zip": dealer.zip,
            "oem_source": dealer.oem_source,
            "scraped_from_zip": dealer.scraped_from_zip,
            # Add license metadata
            "license_number": licensee.license_number,
            "license_type": licensee.license_type,
            "license_status": licensee.license_status,
            "license_state": licensee.source_state,
            "license_tier": licensee.source_tier,
        }

        # Add optional date fields if present
        if licensee.issue_date:
            enriched["license_issue_date"] = licensee.issue_date
        if licensee.expiration_date:
            enriched["license_expiration_date"] = licensee.expiration_date
        if licensee.original_issue_date:
            enriched["license_original_issue_date"] = licensee.original_issue_date

        return enriched
```

**Step 4: Run tests to verify they pass**

Run: `python3 -c "from tests.unit.test_license_oem_matcher import test_match_by_phone_exact, test_match_by_domain, test_no_match_different_data, test_match_returns_enriched_dealer; [test() for test in [test_match_by_phone_exact, test_match_by_domain, test_no_match_different_data, test_match_returns_enriched_dealer]]; print('✅ All tests passed')"`

Expected: `✅ All tests passed`

**Step 5: Commit**

```bash
git add analysis/license_oem_matcher.py tests/unit/test_license_oem_matcher.py
git commit -m "feat: add license-OEM cross-reference matcher

- Multi-signal matching: phone (100%), domain (90%)
- Enriches dealers with license metadata
- Returns match confidence scores
- Based on OEM deduplication patterns

🤖 Generated with Claude Code"
```

---

## Task 4: Integration Script for CA/FL/TX Cross-Reference

**Files:**
- Create: `scripts/run_tier1_cross_reference.py`
- Test: Manual execution test

**Step 1: Write the script**

Create `scripts/run_tier1_cross_reference.py`:

```python
#!/usr/bin/env python3
"""
Tier 1 Cross-Reference Script

Matches CA/FL/TX license data with existing OEM contractor database.
Outputs enriched contractor list with license metadata.

Usage:
    python3 scripts/run_tier1_cross_reference.py \\
        --license-files ca_licenses.csv fl_licenses.csv tx_licenses.csv \\
        --oem-contractors output/grandmaster_list_expanded_20251029.csv \\
        --output output/cross_referenced_contractors.csv
"""
import argparse
import pandas as pd
from typing import List
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.license.scraper_factory import LicenseScraperFactory
from scrapers.license.models import ScraperMode, StandardizedLicensee
from scrapers.base_scraper import StandardizedDealer
from analysis.license_oem_matcher import LicenseOEMMatcher


def load_licensees(file_paths: List[str]) -> List[StandardizedLicensee]:
    """
    Load and parse license files.

    Args:
        file_paths: List of CSV file paths

    Returns:
        List of StandardizedLicensee objects
    """
    all_licensees = []

    for file_path in file_paths:
        print(f"Loading {file_path}...")

        # Determine state from filename
        file_name = Path(file_path).stem.upper()
        state = None
        if 'CA' in file_name or 'CALIF' in file_name:
            state = "CA"
        elif 'FL' in file_name or 'FLOR' in file_name:
            state = "FL"
        elif 'TX' in file_name or 'TEXAS' in file_name:
            state = "TX"

        if not state:
            print(f"  ⚠️  Could not determine state from filename: {file_name}")
            continue

        # Create scraper and parse
        scraper = LicenseScraperFactory.create(state, mode=ScraperMode.PLAYWRIGHT)
        licensees = scraper.parse_file(file_path)

        print(f"  ✅ Loaded {len(licensees)} {state} licenses")
        all_licensees.extend(licensees)

    return all_licensees


def load_oem_contractors(file_path: str) -> List[StandardizedDealer]:
    """
    Load OEM contractor CSV.

    Args:
        file_path: Path to OEM contractor CSV

    Returns:
        List of StandardizedDealer objects
    """
    print(f"Loading OEM contractors from {file_path}...")

    df = pd.read_csv(file_path)

    dealers = []
    for _, row in df.iterrows():
        dealer = StandardizedDealer(
            name=row.get('name', ''),
            phone=row.get('phone'),
            domain=row.get('domain'),
            website=row.get('website'),
            street=row.get('street'),
            city=row.get('city', ''),
            state=row.get('state', ''),
            zip=row.get('zip', ''),
            oem_source=row.get('oem_source', ''),
            scraped_from_zip=row.get('scraped_from_zip', '')
        )
        dealers.append(dealer)

    print(f"  ✅ Loaded {len(dealers)} OEM contractors")
    return dealers


def main():
    parser = argparse.ArgumentParser(description='Cross-reference Tier 1 licenses with OEM contractors')
    parser.add_argument('--license-files', nargs='+', required=True,
                       help='License CSV files (CA, FL, TX)')
    parser.add_argument('--oem-contractors', required=True,
                       help='OEM contractor CSV file')
    parser.add_argument('--output', required=True,
                       help='Output CSV path for enriched contractors')

    args = parser.parse_args()

    print("=" * 60)
    print("TIER 1 CROSS-REFERENCE SCRIPT")
    print("=" * 60)
    print()

    # Load data
    licensees = load_licensees(args.license_files)
    dealers = load_oem_contractors(args.oem_contractors)

    print()
    print(f"Total licensees loaded: {len(licensees)}")
    print(f"Total OEM contractors loaded: {len(dealers)}")
    print()

    # Match
    print("Running cross-reference matcher...")
    matcher = LicenseOEMMatcher()
    matches = matcher.match(licensees, dealers)

    print(f"  ✅ Found {len(matches)} matches")
    print()

    # Analyze matches
    by_type = {}
    for match in matches:
        match_type = match['match_type']
        by_type[match_type] = by_type.get(match_type, 0) + 1

    print("Match breakdown:")
    for match_type, count in by_type.items():
        pct = (count / len(matches) * 100) if matches else 0
        print(f"  - {match_type}: {count} ({pct:.1f}%)")
    print()

    # Export enriched contractors
    print(f"Exporting to {args.output}...")

    enriched_records = [match['enriched_dealer'] for match in matches]
    df_output = pd.DataFrame(enriched_records)

    # Ensure output directory exists
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    df_output.to_csv(args.output, index=False)

    print(f"  ✅ Exported {len(enriched_records)} enriched contractors")
    print()
    print("=" * 60)
    print("COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
```

**Step 2: Make script executable**

Run: `chmod +x scripts/run_tier1_cross_reference.py`

**Step 3: Test with fixture data**

Run:
```bash
python3 scripts/run_tier1_cross_reference.py \
    --license-files tests/fixtures/ca_sample.csv tests/fixtures/fl_sample.csv tests/fixtures/tx_sample.csv \
    --oem-contractors tests/fixtures/oem_sample.csv \
    --output output/test_cross_reference.csv
```

Expected output:
```
============================================================
TIER 1 CROSS-REFERENCE SCRIPT
============================================================

Loading tests/fixtures/ca_sample.csv...
  ✅ Loaded 5 CA licenses
Loading tests/fixtures/fl_sample.csv...
  ✅ Loaded 5 FL licenses
Loading tests/fixtures/tx_sample.csv...
  ✅ Loaded 5 TX licenses

Total licensees loaded: 15
Total OEM contractors loaded: X

Running cross-reference matcher...
  ✅ Found X matches

Match breakdown:
  - phone: X (XX.X%)
  - domain: X (XX.X%)

Exporting to output/test_cross_reference.csv...
  ✅ Exported X enriched contractors

============================================================
COMPLETE
============================================================
```

**Step 4: Create OEM sample fixture for testing**

Create `tests/fixtures/oem_sample.csv`:

```csv
name,phone,domain,website,city,state,zip,oem_source,scraped_from_zip
ABC Electrical Services,323-555-0100,abcelectrical.com,https://abcelectrical.com,Los Angeles,CA,90001,Generac,90001
XYZ HVAC Corp,415-555-0200,xyzhvac.com,https://xyzhvac.com,San Francisco,CA,94102,Carrier,94102
Low Voltage Solutions,619-555-0300,lowvoltage.com,https://lowvoltage.com,San Diego,CA,92101,Enphase,92101
```

**Step 5: Commit**

```bash
git add scripts/run_tier1_cross_reference.py tests/fixtures/oem_sample.csv
chmod +x scripts/run_tier1_cross_reference.py
git commit -m "feat: add Tier 1 cross-reference integration script

- Loads CA/FL/TX license CSVs
- Matches with OEM contractor database
- Exports enriched contractors with license metadata
- CLI with progress reporting
- Test fixtures included

Usage:
  python3 scripts/run_tier1_cross_reference.py \\
    --license-files <license_csvs> \\
    --oem-contractors <oem_csv> \\
    --output <output_csv>

🤖 Generated with Claude Code"
```

---

## Task 5: Documentation and Production Readiness

**Files:**
- Create: `docs/cross-reference-usage.md`
- Modify: `CLAUDE.md` (add Phase 3 section)

**Step 1: Create usage documentation**

Create `docs/cross-reference-usage.md`:

```markdown
# Cross-Reference Engine Usage Guide

## Overview

The cross-reference engine matches state contractor licenses with OEM dealer data to enrich contractor profiles with license metadata. This enables improved ICP scoring using license age, trade capabilities, and licensing status.

## Architecture

**Multi-Signal Matching Pipeline:**

1. **Phone Normalization** (96.5% accuracy)
   - Primary matching signal
   - Strips formatting, country codes, extensions
   - Returns 10-digit US numbers
   - Confidence: 100%

2. **Domain Matching** (0.7% additional)
   - Secondary signal when phone unavailable
   - Extracts root domains from URLs
   - Removes www, protocols, paths
   - Confidence: 90%

3. **Fuzzy Name Matching** (0.1% additional) - Future
   - Tertiary signal for ambiguous matches
   - 85% similarity threshold + same state
   - Confidence: 80%

## Components

### Utilities

**`utils/phone_normalizer.py`**
```python
from utils.phone_normalizer import normalize_phone

# Normalize various phone formats
normalize_phone("+1-323-555-1234")  # → "3235551234"
normalize_phone("(323) 555-1234")   # → "3235551234"
normalize_phone("invalid")           # → None
```

**`utils/domain_extractor.py`**
```python
from utils.domain_extractor import extract_domain

# Extract domains from URLs
extract_domain("https://www.example.com/about")  # → "example.com"
extract_domain("shop.example.com")               # → "shop.example.com"
```

### Core Matcher

**`analysis/license_oem_matcher.py`**
```python
from analysis.license_oem_matcher import LicenseOEMMatcher

matcher = LicenseOEMMatcher()
matches = matcher.match(licensees, dealers)

# Returns list of match dicts:
# {
#     "licensee": StandardizedLicensee,
#     "dealer": StandardizedDealer,
#     "match_type": "phone" | "domain",
#     "confidence": 80-100,
#     "enriched_dealer": {...}  # With license metadata
# }
```

## Usage

### Command-Line Script

```bash
# Match CA/FL/TX licenses with OEM contractors
python3 scripts/run_tier1_cross_reference.py \
    --license-files ca_licenses.csv fl_licenses.csv tx_licenses.csv \
    --oem-contractors output/grandmaster_list_expanded_20251029.csv \
    --output output/cross_referenced_contractors_$(date +%Y%m%d).csv
```

**Output:**
- Enriched contractor CSV with license metadata
- Match statistics by type
- Confidence scores per match

### Programmatic Usage

```python
from scrapers.license.scraper_factory import LicenseScraperFactory
from scrapers.base_scraper import StandardizedDealer
from analysis.license_oem_matcher import LicenseOEMMatcher
import pandas as pd

# 1. Load license data
ca_scraper = LicenseScraperFactory.create("CA", mode=ScraperMode.PLAYWRIGHT)
licensees = ca_scraper.parse_file("ca_licenses.csv")

# 2. Load OEM data
df_oem = pd.read_csv("oem_contractors.csv")
dealers = [StandardizedDealer(**row) for _, row in df_oem.iterrows()]

# 3. Match
matcher = LicenseOEMMatcher()
matches = matcher.match(licensees, dealers)

# 4. Analyze
print(f"Total matches: {len(matches)}")
phone_matches = [m for m in matches if m['match_type'] == 'phone']
print(f"Phone matches: {len(phone_matches)} ({len(phone_matches)/len(matches)*100:.1f}%)")

# 5. Export enriched
enriched = [m['enriched_dealer'] for m in matches]
pd.DataFrame(enriched).to_csv("enriched_contractors.csv", index=False)
```

## Enrichment Fields

Matched dealers gain these license metadata fields:

- `license_number` - State-issued license number
- `license_type` - "Electrical", "LowVoltage", "HVAC"
- `license_status` - "Active", "Inactive", "Expired", etc.
- `license_state` - Source state (CA, FL, TX)
- `license_tier` - "BULK", "API", or "SCRAPER"
- `license_issue_date` - When license was issued (optional)
- `license_expiration_date` - When license expires (optional)
- `license_original_issue_date` - First licensed (growth signal, optional)

## ICP Scoring Enhancements

Use enrichment data to improve ICP scoring:

**License Age (Growth Signal):**
```python
# Contractors licensed <2 years = growing businesses
from datetime import datetime, timedelta
two_years_ago = datetime.now().date() - timedelta(days=730)

if licensee.original_issue_date and licensee.original_issue_date > two_years_ago:
    icp_score += 15  # Growth signal bonus
```

**Multi-Trade Capabilities:**
```python
# Contractors with multiple license types = MEP+R signal
license_types = set(match['license_type'] for match in contractor_matches)

if len(license_types) >= 2:
    icp_score += 20  # Multi-trade bonus
```

**Active Licensing:**
```python
# Active licenses = operational contractors
if licensee.license_status == "Active":
    icp_score += 10  # Active business bonus
```

## Performance

**Benchmarks (based on OEM deduplication):**
- Phone normalization: 96.5% of matches
- Domain extraction: 0.7% additional
- Total expected: ~97% match rate for contractors with contact info

**Scale:**
- CA: 50,000+ licenses
- FL: 35,000+ licenses
- TX: 35,000+ licenses
- OEM contractors: 8,277

**Expected enrichment:** 6,000-7,000 contractors (assuming 80% of OEM contractors operate in CA/FL/TX and have matching phone/domain)

## Testing

Run unit tests:
```bash
python3 -m pytest tests/unit/test_phone_normalizer.py -v
python3 -m pytest tests/unit/test_domain_extractor.py -v
python3 -m pytest tests/unit/test_license_oem_matcher.py -v
```

Test with fixtures:
```bash
python3 scripts/run_tier1_cross_reference.py \
    --license-files tests/fixtures/ca_sample.csv \
    --oem-contractors tests/fixtures/oem_sample.csv \
    --output output/test_enrichment.csv
```

## Next Steps

1. **Download Real Data** (Phase 3a)
   - Visit CA CSLB data portal
   - Download FL MyFloridaLicense files
   - Obtain TX TDLR Excel sheets

2. **Run Production Cross-Reference** (Phase 3b)
   - Parse real license data
   - Match with grandmaster list
   - Export enriched contractors

3. **ICP Re-Scoring** (Phase 3c)
   - Apply license metadata to ICP algorithm
   - Measure scoring accuracy improvement
   - Target: 10%+ improvement

4. **Massachusetts API** (Phase 4)
   - Implement Tier 2 API client
   - Add REST API scraper to factory

5. **Playwright Scrapers** (Phase 5)
   - PA, NJ, NY, IL (SREC states)
   - Expand to remaining 42 states
```

**Step 2: Update CLAUDE.md**

Add to `CLAUDE.md` under "Current Status":

```markdown
## Current Status (as of Oct 31, 2025):

[... existing content ...]

### Phase 3: Cross-Reference Engine (NEW)
- ✅ Phone normalization utility (96.5% accuracy)
- ✅ Domain extraction utility
- ✅ License-OEM matcher with multi-signal pipeline
- ✅ Tier 1 integration script (CA, FL, TX)
- ✅ Usage documentation
- ⏳ Real data download and parsing
- ⏳ ICP re-scoring with license metadata
```

Add new section after "Testing":

```markdown
## Cross-Reference & Enrichment

### License-OEM Matching

**Multi-Signal Pipeline** (`analysis/license_oem_matcher.py`):
- Phone matching: 100% confidence (primary signal)
- Domain matching: 90% confidence (secondary signal)
- Fuzzy name matching: 80% confidence (future)

**Utilities:**
- `utils/phone_normalizer.py` - Normalizes US phone numbers to 10 digits
- `utils/domain_extractor.py` - Extracts root domains from URLs

**Usage:**
```bash
python3 scripts/run_tier1_cross_reference.py \
    --license-files ca_licenses.csv fl_licenses.csv tx_licenses.csv \
    --oem-contractors output/grandmaster_list_expanded_20251029.csv \
    --output output/cross_referenced_contractors_$(date +%Y%m%d).csv
```

**Enrichment Fields:**
- `license_number`, `license_type`, `license_status`
- `license_state`, `license_tier`
- `license_issue_date`, `license_expiration_date`
- `license_original_issue_date` (growth signal)

**Expected Impact:**
- 6,000-7,000 enriched contractors (80% of OEM contractors in CA/FL/TX)
- ICP scoring improvement: 10%+ (license age, multi-trade, active status)
- License metadata enables trade capability validation
```

**Step 3: Commit documentation**

```bash
git add docs/cross-reference-usage.md CLAUDE.md
git commit -m "docs: add cross-reference engine documentation

- Comprehensive usage guide
- Architecture explanation
- Command-line and programmatic examples
- ICP scoring enhancement strategies
- Performance benchmarks
- Updated CLAUDE.md with Phase 3 status

🤖 Generated with Claude Code"
```

---

## Summary

**Phase 3 Complete: Cross-Reference Engine Ready**

**What We Built:**
1. Phone normalization utility (96.5% accuracy)
2. Domain extraction utility
3. License-OEM matcher with multi-signal pipeline
4. Tier 1 integration script
5. Comprehensive documentation

**Test Coverage:**
- 5 phone normalization tests
- 6 domain extraction tests
- 4 matcher tests
- Manual integration test

**Next Actions:**
1. Download real CA/FL/TX license data
2. Run production cross-reference
3. Analyze match rates and enrichment quality
4. Apply license metadata to ICP scoring
5. Measure scoring improvement

**Files Created:** 8
**Total Lines:** ~850 (code + tests + docs)
**Commits:** 5
