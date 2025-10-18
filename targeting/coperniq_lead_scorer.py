"""
Coperniq Lead Scoring Algorithm

Multi-dimensional scoring system to prioritize contractor prospects for Coperniq's
brand-agnostic monitoring platform.

Scoring Dimensions (0-100 total):

1. Multi-OEM Presence (40 points):
   - 3+ OEMs: 40 points (JACKPOT - desperately need unified platform)
   - 2 OEMs: 25 points (strong prospect - managing 2 brands is painful)
   - 1 OEM: 10 points (single-brand - lower priority)

2. SREC State Priority (20 points):
   - HIGH priority state: 20 points (sustainable market post-ITC)
   - MEDIUM priority state: 10 points (developing market)
   - LOW/non-SREC: 0 points (lower priority post-ITC)

3. Commercial Capability (20 points):
   - 50+ employees: 20 points (large commercial contractor)
   - 10-50 employees: 15 points (mid-size commercial)
   - 5-10 employees: 10 points (small commercial)
   - <5 employees: 5 points (residential focus)
   Note: Requires Apollo enrichment for employee count

4. Geographic Value (10 points):
   - Top 10 wealthy ZIPs in state: 10 points
   - Top 30 wealthy ZIPs in state: 7 points
   - Other high-value territory: 3 points
   - Outside target territory: 0 points

5. ITC Urgency (10 points):
   - CRITICAL (commercial deadline Q2 2026): 10 points
   - HIGH (residential deadline Dec 2025): 7 points
   - MEDIUM (SREC sustainable): 5 points
   - LOW (non-SREC): 2 points

Higher scores = higher priority for outreach (limited sales bandwidth)
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from analysis.multi_oem_detector import MultiOEMMatch
from targeting.srec_itc_filter import SRECPriority, ITCUrgency
import json


# Wealthy ZIP codes by state (top 30 per state for geographic scoring)
# Source: IRS/Census data for high-income ZIP codes
WEALTHY_ZIPS = {
    "CA": [
        # San Francisco Bay Area
        "94027",  # Atherton
        "94301", "94304",  # Palo Alto
        "94022",  # Los Altos
        "94024",  # Los Altos Hills
        # Los Angeles
        "90210", "90212",  # Beverly Hills
        "90265",  # Malibu
        "90272",  # Pacific Palisades
        "92657", "92660", "92662",  # Newport Beach
        "92037",  # La Jolla
        "92067",  # Rancho Santa Fe
        # Additional
        "94920",  # Belvedere Tiburon
        "94028",  # Portola Valley
        "94956",  # Ross
        "93108",  # Montecito
        "92625",  # Corona del Mar
    ],
    "TX": [
        # Houston
        "77019",  # River Oaks
        "77024",  # Memorial
        "77005",  # West University
        "77056",  # Galleria
        # Dallas
        "75205", "75225",  # Highland Park
        "75229",  # Preston Hollow
        # Austin
        "78746",  # Westlake Hills
        "78733",  # Westlake
        "78730",  # Barton Creek
        # Additional
        "78734",  # Lakeway
        "77007",  # Heights (Houston)
        "76107",  # Fort Worth - Rivercrest
    ],
    "PA": [
        # Philadelphia suburbs
        "19035",  # Gladwyne
        "19003",  # Ardmore
        "19087",  # Wayne
        "19085",  # Villanova
        "19301",  # Paoli
        # Pittsburgh
        "15215",  # Fox Chapel
        "15238",  # Sewickley
        # Additional
        "19010",  # Bryn Mawr
        "19041",  # Haverford
        "19066",  # Merion Station
    ],
    "MA": [
        # Boston suburbs
        "02467",  # Chestnut Hill
        "02481",  # Wellesley
        "02492",  # Needham
        "02445",  # Brookline
        "02482",  # Wellesley Hills
        "02459",  # Newton Centre
        "02468",  # Waban
        "01752",  # Marlborough
        # Additional
        "02142",  # Cambridge
        "02138",  # Cambridge
        "02139",  # Cambridge
    ],
    "NJ": [
        "07078",  # Short Hills
        "07920",  # Basking Ridge
        "07931",  # Far Hills
        "07039",  # Livingston
        "07726",  # Englishtown
        "07733",  # Holmdel
        "08540",  # Princeton
        "07869",  # Randolph
        # Additional
        "07046",  # Mountain Lakes
        "07670",  # Tenafly
        "07450",  # Ridgewood
    ],
    "FL": [
        # Miami
        "33109",  # Fisher Island
        "33158",  # Pinecrest
        "33156",  # Palmetto Bay
        # Palm Beach
        "33480",  # Palm Beach
        "33455",  # Hobe Sound
        # Naples/Fort Myers
        "34102",  # Naples
        "34103",  # Old Naples
        # Tampa
        "33606",  # South Tampa
        "33629",  # Bayshore
        # Additional
        "33139",  # Miami Beach
        "33004",  # Dania Beach
    ],
}


@dataclass
class CoperniqScore:
    """
    Complete Coperniq lead scoring result.
    
    Includes individual dimension scores and total 0-100 score.
    """
    # Contractor identifier
    contractor_name: str
    contractor_phone: str
    contractor_domain: str
    
    # Individual dimension scores
    multi_oem_score: int = 0          # 0-40 points
    srec_state_score: int = 0         # 0-20 points
    commercial_capability_score: int = 0  # 0-20 points
    geographic_score: int = 0         # 0-10 points
    itc_urgency_score: int = 0        # 0-10 points
    
    # Total Coperniq score (0-100)
    total_score: int = 0
    
    # Scoring metadata
    score_breakdown: Dict[str, str] = field(default_factory=dict)
    priority_tier: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    
    def calculate_total(self) -> int:
        """Calculate total score from dimensions"""
        self.total_score = (
            self.multi_oem_score +
            self.srec_state_score +
            self.commercial_capability_score +
            self.geographic_score +
            self.itc_urgency_score
        )
        
        # Assign priority tier
        if self.total_score >= 80:
            self.priority_tier = "HIGH"
        elif self.total_score >= 50:
            self.priority_tier = "MEDIUM"
        else:
            self.priority_tier = "LOW"
        
        return self.total_score
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export"""
        return {
            "contractor_name": self.contractor_name,
            "contractor_phone": self.contractor_phone,
            "contractor_domain": self.contractor_domain,
            "total_score": self.total_score,
            "priority_tier": self.priority_tier,
            "dimension_scores": {
                "multi_oem": self.multi_oem_score,
                "srec_state": self.srec_state_score,
                "commercial_capability": self.commercial_capability_score,
                "geographic": self.geographic_score,
                "itc_urgency": self.itc_urgency_score,
            },
            "score_breakdown": self.score_breakdown,
        }


class CoperniqLeadScorer:
    """
    Calculate Coperniq-specific lead scores for prioritizing outreach.
    
    Usage:
        scorer = CoperniqLeadScorer()
        scores = scorer.score_contractors(multi_oem_contractors)
        scorer.export_results(scores, "output/coperniq_scored_leads.json")
        
        # Get top 50 prospects
        top_prospects = scorer.get_top_prospects(scores, limit=50)
    """
    
    def __init__(self):
        """Initialize scorer with wealthy ZIP database"""
        self.wealthy_zips = WEALTHY_ZIPS
    
    def score_multi_oem_presence(self, contractor: MultiOEMMatch) -> Tuple[int, str]:
        """
        Score based on number of OEM certifications.
        
        Logic:
        - 3+ OEMs: 40 points (managing 3+ brands = desperately need unified platform)
        - 2 OEMs: 25 points (dual-brand = strong pain point)
        - 1 OEM: 10 points (single-brand = lower priority)
        
        Args:
            contractor: MultiOEMMatch object
        
        Returns:
            Tuple of (score, explanation)
        """
        oem_count = len(contractor.oem_sources)
        
        if oem_count >= 3:
            return 40, f"3+ OEM brands ({', '.join(sorted(contractor.oem_sources))}) - CRITICAL NEED"
        elif oem_count == 2:
            return 25, f"2 OEM brands ({', '.join(sorted(contractor.oem_sources))}) - Strong prospect"
        elif oem_count == 1:
            return 10, f"1 OEM brand ({list(contractor.oem_sources)[0]}) - Lower priority"
        else:
            return 0, "No OEM certifications"
    
    def score_srec_state(self, contractor: MultiOEMMatch) -> Tuple[int, str]:
        """
        Score based on SREC state priority.
        
        Args:
            contractor: MultiOEMMatch object (should have srec_metadata)
        
        Returns:
            Tuple of (score, explanation)
        """
        if not hasattr(contractor, "srec_metadata"):
            return 0, "Not in SREC state"
        
        priority = contractor.srec_metadata.get("priority")
        state_name = contractor.srec_metadata.get("state_name")
        program = contractor.srec_metadata.get("program")
        
        if priority == SRECPriority.HIGH.value:
            return 20, f"{state_name} - HIGH priority SREC state ({program})"
        elif priority == SRECPriority.MEDIUM.value:
            return 10, f"{state_name} - MEDIUM priority SREC state ({program})"
        else:
            return 0, f"{state_name} - LOW/no SREC program"
    
    def score_commercial_capability(self, contractor: MultiOEMMatch) -> Tuple[int, str]:
        """
        Score based on commercial capability (employee count from Apollo).
        
        Note: This requires Apollo enrichment. Defaults to tier-based estimation.
        
        Args:
            contractor: MultiOEMMatch object
        
        Returns:
            Tuple of (score, explanation)
        """
        # Check if Apollo enriched
        employee_count = contractor.primary_dealer.employee_count
        
        if employee_count is not None:
            # Apollo data available
            if employee_count >= 50:
                return 20, f"{employee_count} employees - Large commercial contractor"
            elif employee_count >= 10:
                return 15, f"{employee_count} employees - Mid-size commercial"
            elif employee_count >= 5:
                return 10, f"{employee_count} employees - Small commercial"
            else:
                return 5, f"{employee_count} employees - Residential focus"
        else:
            # Estimate from OEM tier (fallback before Apollo enrichment)
            tier = contractor.primary_dealer.tier
            
            if tier in ["Premier", "Platinum"]:
                return 15, f"{tier} tier (est. mid-size commercial)"
            elif tier in ["Elite Plus", "Gold"]:
                return 10, f"{tier} tier (est. small commercial)"
            else:
                return 5, f"{tier} tier (est. residential focus)"
    
    def score_geographic_value(self, contractor: MultiOEMMatch) -> Tuple[int, str]:
        """
        Score based on proximity to wealthy ZIP codes.
        
        High-income territories = contractors serving customers who pay for quality work.
        
        Args:
            contractor: MultiOEMMatch object
        
        Returns:
            Tuple of (score, explanation)
        """
        state = contractor.primary_dealer.state
        zip_code = contractor.primary_dealer.zip
        
        if state not in self.wealthy_zips:
            return 0, f"State {state} not in wealthy ZIP database"
        
        wealthy_zips_for_state = self.wealthy_zips[state]
        
        # Check if in top 10 wealthy ZIPs
        if zip_code in wealthy_zips_for_state[:10]:
            return 10, f"ZIP {zip_code} in top 10 wealthy ZIPs for {state}"
        
        # Check if in top 30 wealthy ZIPs
        elif zip_code in wealthy_zips_for_state:
            return 7, f"ZIP {zip_code} in top 30 wealthy ZIPs for {state}"
        
        # Check if within proximity (same city as wealthy ZIP)
        # This is simplified - could use actual distance calculation
        city = contractor.primary_dealer.city.lower()
        for wealthy_zip in wealthy_zips_for_state:
            # This would require ZIP-to-city mapping for proper implementation
            # For now, give partial credit
            pass
        
        return 3, f"ZIP {zip_code} in {state} (standard territory)"
    
    def score_itc_urgency(self, contractor: MultiOEMMatch) -> Tuple[int, str]:
        """
        Score based on ITC deadline urgency.
        
        Args:
            contractor: MultiOEMMatch object (should have srec_metadata)
        
        Returns:
            Tuple of (score, explanation)
        """
        if not hasattr(contractor, "srec_metadata"):
            return 2, "No ITC urgency (non-SREC state)"
        
        urgency = contractor.srec_metadata.get("urgency")
        
        if urgency == ITCUrgency.CRITICAL.value:
            return 10, "CRITICAL - Commercial projects must start by Q2 2026"
        elif urgency == ITCUrgency.HIGH.value:
            return 7, "HIGH - Residential ITC expires Dec 2025"
        elif urgency == ITCUrgency.MEDIUM.value:
            return 5, "MEDIUM - SREC state (sustainable post-ITC)"
        else:
            return 2, "LOW - Non-SREC state"
    
    def score_contractor(self, contractor: MultiOEMMatch) -> CoperniqScore:
        """
        Calculate complete Coperniq score for a contractor.
        
        Args:
            contractor: MultiOEMMatch object
        
        Returns:
            CoperniqScore object with all dimensions scored
        """
        # Score each dimension
        multi_oem_score, multi_oem_explanation = self.score_multi_oem_presence(contractor)
        srec_score, srec_explanation = self.score_srec_state(contractor)
        commercial_score, commercial_explanation = self.score_commercial_capability(contractor)
        geo_score, geo_explanation = self.score_geographic_value(contractor)
        urgency_score, urgency_explanation = self.score_itc_urgency(contractor)
        
        # Create score object
        score = CoperniqScore(
            contractor_name=contractor.primary_dealer.name,
            contractor_phone=contractor.primary_dealer.phone,
            contractor_domain=contractor.primary_dealer.domain,
            multi_oem_score=multi_oem_score,
            srec_state_score=srec_score,
            commercial_capability_score=commercial_score,
            geographic_score=geo_score,
            itc_urgency_score=urgency_score,
            score_breakdown={
                "multi_oem": multi_oem_explanation,
                "srec_state": srec_explanation,
                "commercial_capability": commercial_explanation,
                "geographic": geo_explanation,
                "itc_urgency": urgency_explanation,
            },
        )
        
        # Calculate total
        score.calculate_total()
        
        return score
    
    def score_contractors(self, contractors: List[MultiOEMMatch]) -> List[CoperniqScore]:
        """
        Score all contractors and return sorted by total score descending.
        
        Args:
            contractors: List of MultiOEMMatch objects
        
        Returns:
            List of CoperniqScore objects sorted by score (high to low)
        """
        print(f"\n{'='*60}")
        print("Coperniq Lead Scoring Algorithm")
        print(f"{'='*60}\n")
        
        scores = [self.score_contractor(c) for c in contractors]
        
        # Sort by total score descending
        scores.sort(key=lambda s: s.total_score, reverse=True)
        
        # Print summary
        high_priority = sum(1 for s in scores if s.priority_tier == "HIGH")
        medium_priority = sum(1 for s in scores if s.priority_tier == "MEDIUM")
        low_priority = sum(1 for s in scores if s.priority_tier == "LOW")
        
        print(f"Scored {len(scores)} contractors:")
        print(f"  HIGH priority (80-100): {high_priority} ⭐⭐⭐")
        print(f"  MEDIUM priority (50-79): {medium_priority} ⭐⭐")
        print(f"  LOW priority (<50): {low_priority} ⭐")
        print(f"\n{'='*60}\n")
        
        return scores
    
    def get_top_prospects(self, scores: List[CoperniqScore], limit: int = 50) -> List[CoperniqScore]:
        """
        Get top N prospects sorted by score.
        
        Args:
            scores: List of CoperniqScore objects
            limit: Maximum number to return
        
        Returns:
            Top prospects
        """
        return scores[:limit]
    
    def export_results(self, scores: List[CoperniqScore], filepath: str) -> None:
        """
        Export scored contractors to JSON file.
        
        Args:
            scores: List of CoperniqScore objects
            filepath: Path to output JSON file
        """
        import os
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        data = [s.to_dict() for s in scores]
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"Exported {len(scores)} scored contractors to {filepath}")
    
    def export_csv(self, scores: List[CoperniqScore], filepath: str) -> None:
        """
        Export scored contractors to CSV for review.
        
        Args:
            scores: List of CoperniqScore objects
            filepath: Path to output CSV file
        """
        import csv
        import os
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        fieldnames = [
            "priority_tier", "total_score",
            "contractor_name", "phone", "domain",
            "multi_oem_score", "srec_state_score", "commercial_score",
            "geographic_score", "itc_urgency_score",
            "multi_oem_explanation", "srec_explanation",
        ]
        
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for score in scores:
                writer.writerow({
                    "priority_tier": score.priority_tier,
                    "total_score": score.total_score,
                    "contractor_name": score.contractor_name,
                    "phone": score.contractor_phone,
                    "domain": score.contractor_domain,
                    "multi_oem_score": score.multi_oem_score,
                    "srec_state_score": score.srec_state_score,
                    "commercial_score": score.commercial_capability_score,
                    "geographic_score": score.geographic_score,
                    "itc_urgency_score": score.itc_urgency_score,
                    "multi_oem_explanation": score.score_breakdown.get("multi_oem", ""),
                    "srec_explanation": score.score_breakdown.get("srec_state", ""),
                })
        
        print(f"Exported {len(scores)} scored contractors to {filepath}")


# Example usage
if __name__ == "__main__":
    from analysis.multi_oem_detector import MultiOEMDetector
    from targeting.srec_itc_filter import SRECITCFilter
    from scrapers.scraper_factory import ScraperFactory
    from scrapers.base_scraper import ScraperMode
    
    # Scrape dealers from SREC states
    CA_ZIPS = ["94102", "90210", "92037"]
    
    generac = ScraperFactory.create("Generac", mode=ScraperMode.RUNPOD)
    generac_dealers = generac.scrape_multiple(CA_ZIPS)
    
    # Detect multi-OEM contractors
    detector = MultiOEMDetector()
    detector.add_dealers(generac_dealers, "Generac")
    multi_oem = detector.find_multi_oem_contractors()
    
    # Filter to SREC states
    srec_filter = SRECITCFilter()
    srec_result = srec_filter.filter_contractors(multi_oem)
    
    # Score with Coperniq algorithm
    scorer = CoperniqLeadScorer()
    scores = scorer.score_contractors(srec_result.contractors)
    
    # Export results
    scorer.export_results(scores, "output/coperniq_scored_leads.json")
    scorer.export_csv(scores, "output/coperniq_scored_leads.csv")
    
    # Show top 10
    print("\nTop 10 Coperniq Prospects:")
    for i, score in enumerate(scorer.get_top_prospects(scores, 10), 1):
        print(f"{i}. {score.contractor_name} - Score: {score.total_score}/100 ({score.priority_tier})")
