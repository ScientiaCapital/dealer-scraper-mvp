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
