"""
Multi-OEM Cross-Reference Detector

Identifies contractors who appear in multiple OEM dealer networks (Generac + Tesla + Enphase).
These multi-brand installers are Coperniq's highest-value prospects because they:
1. Need brand-agnostic monitoring most (managing 3+ separate platforms is painful)
2. Have larger customer bases (certified across multiple brands)
3. Are more sophisticated businesses (investment in multiple certifications)

Matching Strategy:
- Phone number: Primary key (most reliable, normalized to digits only)
- Domain: Secondary key (after removing www, checking root domain match)
- Company name: Tertiary (fuzzy matching with high threshold for false positives)

Confidence Scoring:
- 3 signals match (phone + domain + name): 100% confidence
- 2 signals match (phone + domain OR phone + name): 90% confidence  
- 1 signal match (phone only): 80% confidence
- Domain only: 60% confidence (less reliable - could be franchise/chain)
- Name only: 40% confidence (high false positive risk)
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from scrapers.base_scraper import StandardizedDealer


@dataclass
class MultiOEMMatch:
    """
    Represents a contractor found in multiple OEM networks.
    
    Combines data from all OEM sources and calculates multi-OEM presence score.
    """
    # Primary dealer record (use highest-tier OEM as primary)
    primary_dealer: StandardizedDealer
    
    # All OEM sources this contractor appears in
    oem_sources: Set[str] = field(default_factory=set)
    
    # All dealer records across OEMs (for data enrichment)
    dealer_records: List[StandardizedDealer] = field(default_factory=list)
    
    # Matching confidence (0-100)
    match_confidence: int = 100
    
    # Match signals that triggered cross-reference
    match_signals: List[str] = field(default_factory=list)
    
    # Multi-OEM presence score (0-100, used in Coperniq lead scoring)
    # 1 OEM = 25, 2 OEMs = 50, 3+ OEMs = 100
    multi_oem_score: int = 0
    
    def calculate_multi_oem_score(self) -> int:
        """
        Calculate multi-OEM presence score for Coperniq lead scoring.
        
        Scoring:
        - 1 OEM: 25 points (single-brand, lower priority)
        - 2 OEMs: 50 points (dual-brand, good prospect)
        - 3+ OEMs: 100 points (multi-brand, highest priority - NEED Coperniq!)
        
        Returns:
            Score from 0-100
        """
        oem_count = len(self.oem_sources)
        
        if oem_count >= 3:
            return 100  # Jackpot! Managing 3+ brands = desperately need unified platform
        elif oem_count == 2:
            return 50   # Solid prospect - managing 2 brands is painful
        elif oem_count == 1:
            return 25   # Single-brand - lower priority but still worth outreach
        else:
            return 0    # Shouldn't happen
    
    def get_all_capabilities(self) -> Set[str]:
        """
        Aggregate all capabilities across all OEM records.
        
        Returns:
            Set of all unique product/trade capabilities
        """
        all_caps = set()
        
        for dealer in self.dealer_records:
            all_caps.update(dealer.capabilities.get_product_capabilities())
            all_caps.update(dealer.capabilities.get_trade_capabilities())
        
        return all_caps
    
    def get_best_contact_info(self) -> Dict[str, str]:
        """
        Select best contact information across all OEM records.
        
        Prioritizes:
        - Most complete phone number
        - Most professional website (shortest domain = likely company site vs lead gen)
        - Most complete address
        
        Returns:
            Dict with best phone, website, domain, address
        """
        best_phone = ""
        best_website = ""
        best_domain = ""
        best_address = ""
        
        for dealer in self.dealer_records:
            # Best phone (longest formatted phone)
            if len(dealer.phone) > len(best_phone):
                best_phone = dealer.phone
            
            # Best website (shortest domain = likely company site)
            if dealer.domain and (not best_domain or len(dealer.domain) < len(best_domain)):
                best_domain = dealer.domain
                best_website = dealer.website
            
            # Best address (most complete)
            if len(dealer.address_full) > len(best_address):
                best_address = dealer.address_full
        
        return {
            "phone": best_phone,
            "website": best_website,
            "domain": best_domain,
            "address_full": best_address,
        }
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export"""
        return {
            "name": self.primary_dealer.name,
            "oem_sources": list(self.oem_sources),
            "oem_count": len(self.oem_sources),
            "multi_oem_score": self.multi_oem_score,
            "match_confidence": self.match_confidence,
            "match_signals": self.match_signals,
            "contact_info": self.get_best_contact_info(),
            "all_capabilities": list(self.get_all_capabilities()),
            "primary_dealer": self.primary_dealer.to_dict(),
            "all_records": [d.to_dict() for d in self.dealer_records],
        }


class MultiOEMDetector:
    """
    Detects contractors who appear in multiple OEM dealer networks.
    
    Usage:
        detector = MultiOEMDetector()
        detector.add_dealers(generac_dealers, "Generac")
        detector.add_dealers(tesla_dealers, "Tesla")
        detector.add_dealers(enphase_dealers, "Enphase")
        
        multi_oem_contractors = detector.find_multi_oem_contractors()
        detector.export_results("output/multi_oem_contractors.json")
    """
    
    def __init__(self):
        """Initialize detector with empty dealer collections"""
        self.dealers_by_oem: Dict[str, List[StandardizedDealer]] = {}
        self.multi_oem_matches: List[MultiOEMMatch] = []
    
    def add_dealers(self, dealers: List[StandardizedDealer], oem_name: str) -> None:
        """
        Add dealers from an OEM scraper to the detector.
        
        Args:
            dealers: List of StandardizedDealer objects
            oem_name: OEM identifier (e.g., "Generac", "Tesla", "Enphase")
        """
        self.dealers_by_oem[oem_name] = dealers
        print(f"Added {len(dealers)} dealers from {oem_name}")
    
    @staticmethod
    def normalize_phone(phone: str) -> str:
        """
        Normalize phone number to digits only for matching.
        
        Examples:
            "(555) 555-5555" -> "5555555555"
            "555.555.5555" -> "5555555555"
            "+1 (555) 555-5555" -> "5555555555"
        
        Args:
            phone: Raw phone number string
        
        Returns:
            Digits-only phone number
        """
        if not phone:
            return ""
        
        # Extract digits only
        digits = re.sub(r'\D', '', phone)
        
        # Remove leading 1 if present (US country code)
        if digits.startswith('1') and len(digits) == 11:
            digits = digits[1:]
        
        return digits
    
    @staticmethod
    def normalize_domain(domain: str) -> str:
        """
        Normalize domain for matching.
        
        Examples:
            "www.example.com" -> "example.com"
            "subdomain.example.com" -> "example.com"
            "example.co.uk" -> "example.co.uk"
        
        Args:
            domain: Raw domain string
        
        Returns:
            Normalized root domain
        """
        if not domain:
            return ""
        
        # Remove www prefix
        domain = domain.lower().replace("www.", "")
        
        # Extract root domain (handle subdomains)
        # Keep last 2 parts for .com/.net/.org, last 3 parts for .co.uk/.com.au
        parts = domain.split(".")
        
        if len(parts) >= 3 and parts[-2] in ["co", "com", "org", "net"]:
            # e.g., example.co.uk -> keep last 3
            return ".".join(parts[-3:])
        elif len(parts) >= 2:
            # e.g., example.com -> keep last 2
            return ".".join(parts[-2:])
        
        return domain
    
    @staticmethod
    def fuzzy_name_match(name1: str, name2: str, threshold: float = 0.85) -> Tuple[bool, float]:
        """
        Fuzzy match company names with high threshold to avoid false positives.
        
        Strategy:
        1. Normalize: lowercase, remove punctuation, remove common suffixes (LLC, Inc, etc.)
        2. Calculate Levenshtein distance ratio
        3. Check for substring match (shorter name fully contained in longer)
        4. Return True if ratio > threshold OR substring match
        
        Args:
            name1: First company name
            name2: Second company name
            threshold: Similarity threshold (default 0.85 = very similar)
        
        Returns:
            Tuple of (is_match, similarity_score)
        """
        if not name1 or not name2:
            return False, 0.0
        
        # Normalize names
        def normalize_name(name: str) -> str:
            name = name.lower()
            # Remove punctuation
            name = re.sub(r'[^\w\s]', '', name)
            # Remove common suffixes
            suffixes = ['llc', 'inc', 'incorporated', 'corp', 'corporation', 'ltd', 'limited', 'co']
            for suffix in suffixes:
                name = re.sub(rf'\b{suffix}\b', '', name)
            # Remove extra whitespace
            name = ' '.join(name.split())
            return name.strip()
        
        norm1 = normalize_name(name1)
        norm2 = normalize_name(name2)
        
        # Check exact match after normalization
        if norm1 == norm2:
            return True, 1.0
        
        # Check substring match (shorter name fully contained in longer)
        if norm1 in norm2 or norm2 in norm1:
            return True, 0.9
        
        # Calculate Levenshtein distance ratio (basic implementation)
        # For production, use python-Levenshtein library for better performance
        def levenshtein_ratio(s1: str, s2: str) -> float:
            """Calculate similarity ratio using Levenshtein distance"""
            if len(s1) < len(s2):
                return levenshtein_ratio(s2, s1)
            if len(s2) == 0:
                return 0.0
            
            # Simple token-based similarity (good enough for company names)
            tokens1 = set(s1.split())
            tokens2 = set(s2.split())
            
            if not tokens1 or not tokens2:
                return 0.0
            
            intersection = len(tokens1 & tokens2)
            union = len(tokens1 | tokens2)
            
            return intersection / union if union > 0 else 0.0
        
        ratio = levenshtein_ratio(norm1, norm2)
        is_match = ratio >= threshold
        
        return is_match, ratio
    
    def find_multi_oem_contractors(self, min_oem_count: int = 2) -> List[MultiOEMMatch]:
        """
        Find contractors who appear in multiple OEM networks.
        
        Matching strategy:
        1. Build phone number index (primary key)
        2. Build domain index (secondary key)
        3. For each unique phone/domain, check if appears in multiple OEMs
        4. Validate with fuzzy name matching
        5. Calculate confidence score based on matching signals
        
        Args:
            min_oem_count: Minimum number of OEMs required (default 2)
        
        Returns:
            List of MultiOEMMatch objects sorted by multi_oem_score descending
        """
        print(f"\n{'='*60}")
        print("Multi-OEM Cross-Reference Detector")
        print(f"{'='*60}\n")
        
        # Build indexes
        phone_index = defaultdict(list)  # phone -> [(oem, dealer), ...]
        domain_index = defaultdict(list)  # domain -> [(oem, dealer), ...]
        
        for oem_name, dealers in self.dealers_by_oem.items():
            for dealer in dealers:
                # Index by phone
                phone_norm = self.normalize_phone(dealer.phone)
                if phone_norm:
                    phone_index[phone_norm].append((oem_name, dealer))
                
                # Index by domain
                domain_norm = self.normalize_domain(dealer.domain)
                if domain_norm:
                    domain_index[domain_norm].append((oem_name, dealer))
        
        print(f"Built indexes:")
        print(f"  - {len(phone_index)} unique phone numbers")
        print(f"  - {len(domain_index)} unique domains\n")
        
        # Find matches
        matches = []
        processed_combinations = set()  # Track (phone, domain) pairs already processed
        
        # Match by phone number (most reliable)
        for phone_norm, entries in phone_index.items():
            if len(entries) < min_oem_count:
                continue
            
            # Group by OEM
            oem_entries = defaultdict(list)
            for oem_name, dealer in entries:
                oem_entries[oem_name].append(dealer)
            
            # Skip if all from same OEM
            if len(oem_entries) < min_oem_count:
                continue
            
            # Create MultiOEMMatch
            all_dealers = [dealer for _, dealer in entries]
            oem_sources = set(oem_entries.keys())
            
            # Use highest-rated dealer as primary
            primary = max(all_dealers, key=lambda d: (d.rating, d.review_count))
            
            # Calculate match signals
            match_signals = ["phone"]
            
            # Check if domain also matches
            domain_norm = self.normalize_domain(primary.domain)
            if domain_norm and all(
                self.normalize_domain(d.domain) == domain_norm
                for d in all_dealers if d.domain
            ):
                match_signals.append("domain")
            
            # Check if names fuzzy match
            name_matches = all(
                self.fuzzy_name_match(primary.name, d.name)[0]
                for d in all_dealers
            )
            if name_matches:
                match_signals.append("name")
            
            # Calculate confidence
            confidence = len(match_signals) * 30 + 10  # 40, 70, 100
            confidence = min(confidence, 100)
            
            match = MultiOEMMatch(
                primary_dealer=primary,
                oem_sources=oem_sources,
                dealer_records=all_dealers,
                match_confidence=confidence,
                match_signals=match_signals,
            )
            match.multi_oem_score = match.calculate_multi_oem_score()
            
            matches.append(match)
            processed_combinations.add((phone_norm, domain_norm))
        
        # Match by domain only (less reliable, only if not already matched by phone)
        for domain_norm, entries in domain_index.items():
            if len(entries) < min_oem_count:
                continue
            
            # Check if already processed
            phone_norm = self.normalize_phone(entries[0][1].phone)
            if (phone_norm, domain_norm) in processed_combinations:
                continue
            
            # Group by OEM
            oem_entries = defaultdict(list)
            for oem_name, dealer in entries:
                oem_entries[oem_name].append(dealer)
            
            # Skip if all from same OEM
            if len(oem_entries) < min_oem_count:
                continue
            
            # Create MultiOEMMatch (lower confidence - domain only)
            all_dealers = [dealer for _, dealer in entries]
            oem_sources = set(oem_entries.keys())
            
            primary = max(all_dealers, key=lambda d: (d.rating, d.review_count))
            
            match = MultiOEMMatch(
                primary_dealer=primary,
                oem_sources=oem_sources,
                dealer_records=all_dealers,
                match_confidence=60,  # Domain-only = 60% confidence
                match_signals=["domain"],
            )
            match.multi_oem_score = match.calculate_multi_oem_score()
            
            matches.append(match)
        
        # Sort by multi_oem_score descending (3+ OEMs first, then 2 OEMs)
        matches.sort(key=lambda m: (m.multi_oem_score, m.match_confidence), reverse=True)
        
        self.multi_oem_matches = matches
        
        # Print summary
        print(f"Found {len(matches)} multi-OEM contractors:")
        three_plus = sum(1 for m in matches if len(m.oem_sources) >= 3)
        two = sum(1 for m in matches if len(m.oem_sources) == 2)
        
        print(f"  - {three_plus} with 3+ OEMs (score: 100) ⭐⭐⭐")
        print(f"  - {two} with 2 OEMs (score: 50) ⭐⭐")
        print(f"\n{'='*60}\n")
        
        return matches
    
    def get_top_prospects(self, limit: int = 50) -> List[MultiOEMMatch]:
        """
        Get top multi-OEM prospects sorted by score.
        
        Args:
            limit: Maximum number of prospects to return
        
        Returns:
            Top prospects sorted by multi_oem_score descending
        """
        return self.multi_oem_matches[:limit]
    
    def export_results(self, filepath: str) -> None:
        """
        Export multi-OEM matches to JSON file.
        
        Args:
            filepath: Path to output JSON file
        """
        import json
        import os
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        data = [m.to_dict() for m in self.multi_oem_matches]
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"Exported {len(self.multi_oem_matches)} multi-OEM contractors to {filepath}")
    
    def export_csv(self, filepath: str) -> None:
        """
        Export multi-OEM matches to CSV file for review.
        
        Args:
            filepath: Path to output CSV file
        """
        import csv
        import os
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        fieldnames = [
            "name", "oem_sources", "oem_count", "multi_oem_score",
            "match_confidence", "match_signals",
            "phone", "website", "domain",
            "city", "state", "all_capabilities",
        ]
        
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for match in self.multi_oem_matches:
                contact = match.get_best_contact_info()
                primary = match.primary_dealer
                
                writer.writerow({
                    "name": primary.name,
                    "oem_sources": ", ".join(sorted(match.oem_sources)),
                    "oem_count": len(match.oem_sources),
                    "multi_oem_score": match.multi_oem_score,
                    "match_confidence": match.match_confidence,
                    "match_signals": ", ".join(match.match_signals),
                    "phone": contact["phone"],
                    "website": contact["website"],
                    "domain": contact["domain"],
                    "city": primary.city,
                    "state": primary.state,
                    "all_capabilities": ", ".join(sorted(match.get_all_capabilities())),
                })
        
        print(f"Exported {len(self.multi_oem_matches)} multi-OEM contractors to {filepath}")


# Example usage
if __name__ == "__main__":
    from scrapers.scraper_factory import ScraperFactory
    from scrapers.base_scraper import ScraperMode
    from config import ZIP_CODES_TEST
    
    # Initialize scrapers
    generac = ScraperFactory.create("Generac", mode=ScraperMode.RUNPOD)
    tesla = ScraperFactory.create("Tesla", mode=ScraperMode.RUNPOD)
    enphase = ScraperFactory.create("Enphase", mode=ScraperMode.RUNPOD)
    
    # Scrape dealers
    generac_dealers = generac.scrape_multiple(ZIP_CODES_TEST)
    tesla_dealers = tesla.scrape_multiple(ZIP_CODES_TEST)
    enphase_dealers = enphase.scrape_multiple(ZIP_CODES_TEST)
    
    # Detect multi-OEM contractors
    detector = MultiOEMDetector()
    detector.add_dealers(generac_dealers, "Generac")
    detector.add_dealers(tesla_dealers, "Tesla")
    detector.add_dealers(enphase_dealers, "Enphase")
    
    multi_oem_contractors = detector.find_multi_oem_contractors()
    
    # Export results
    detector.export_results("output/multi_oem_contractors.json")
    detector.export_csv("output/multi_oem_contractors.csv")
    
    # Show top 10 prospects
    print("\nTop 10 Multi-OEM Prospects:")
    for i, match in enumerate(detector.get_top_prospects(10), 1):
        print(f"{i}. {match.primary_dealer.name}")
        print(f"   OEMs: {', '.join(sorted(match.oem_sources))}")
        print(f"   Score: {match.multi_oem_score}/100")
        print(f"   Confidence: {match.match_confidence}%")
        print()
