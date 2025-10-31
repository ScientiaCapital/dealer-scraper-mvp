"""
ICP Filter - Identify Ideal Customer Profile Contractors

Filters for the sweet spot: Resimercial contractors with O&M capabilities.

Target Profile:
1. Resimercial (both residential + commercial work)
2. O&M Services (ongoing maintenance contracts)
3. Multi-OEM certified (managing 2+ monitoring platforms)
4. MEP+R self-performers (commercial capability indicator)

These contractors are ideal for Coperniq because:
- They have the pain (managing multiple monitoring platforms)
- They have recurring revenue (O&M contracts = sticky customers)
- They have sophistication (commercial + multi-trade)
"""

from typing import List, Set
from dataclasses import dataclass
from analysis.multi_oem_detector import MultiOEMMatch


@dataclass
class ICPScore:
    """ICP scoring breakdown for a contractor"""
    contractor: MultiOEMMatch

    # Core ICP dimensions (0-100 each)
    resimercial_score: int = 0  # Both residential + commercial
    om_score: int = 0  # Operations & maintenance services
    multi_oem_score: int = 0  # Number of OEM certifications
    mepr_score: int = 0  # MEP+R self-performing capability

    # Composite scores
    icp_fit_score: int = 0  # Overall ICP fit (0-100)
    icp_tier: str = "BRONZE"  # PLATINUM, GOLD, SILVER, BRONZE

    # Flags
    is_ideal_icp: bool = False  # All 4 dimensions present

    def __post_init__(self):
        """Calculate composite scores after initialization"""
        self.calculate_composite_scores()

    def calculate_composite_scores(self):
        """Calculate overall ICP fit score and tier"""
        # Weighted ICP scoring (Year 1 GTM-Aligned):
        # - Resimercial: 35% (both resi+commercial = scaling $5-10M → $50-100M)
        # - Multi-OEM: 25% (managing 3-4+ platforms = core pain point)
        # - MEP+R: 25% (self-performing multi-trade = platform power users, blue ocean)
        # - O&M: 15% (bonus, platform features maturing in Year 2)

        self.icp_fit_score = int(
            self.resimercial_score * 0.35 +
            self.multi_oem_score * 0.25 +
            self.mepr_score * 0.25 +
            self.om_score * 0.15
        )

        # Tier classification
        if self.icp_fit_score >= 80:
            self.icp_tier = "PLATINUM"
        elif self.icp_fit_score >= 60:
            self.icp_tier = "GOLD"
        elif self.icp_fit_score >= 40:
            self.icp_tier = "SILVER"
        else:
            self.icp_tier = "BRONZE"

        # Ideal ICP flag (all 4 dimensions present)
        self.is_ideal_icp = all([
            self.resimercial_score >= 70,
            self.om_score >= 70,
            self.multi_oem_score >= 50,
            self.mepr_score >= 50
        ])


class ICPFilter:
    """
    Filter and score contractors based on ICP fit.

    Ideal Customer Profile:
    - Resimercial (residential + commercial)
    - O&M services (ongoing maintenance)
    - Multi-OEM certified
    - MEP+R self-performers
    """

    # O&M indicators (service contract keywords)
    OM_KEYWORDS = [
        'service', 'maintenance', 'repair', 'o&m', 'om',
        'preventive', 'annual', '24/7', 'emergency', 'monitoring',
        'support', 'warranty', 'care', 'protection', 'coverage'
    ]

    # Commercial indicators
    COMMERCIAL_KEYWORDS = [
        'commercial', 'industrial', 'enterprise', 'corporate',
        'business', 'institutional', 'facility', 'facilities'
    ]

    # MEP+R indicators (self-performing contractors)
    MEPR_KEYWORDS = [
        'mechanical', 'mep', 'hvac', 'plumbing', 'engineering',
        'electrical', 'controls', 'automation', 'energy', 'facilities',
        'systems', 'solutions', 'contractors', 'builders', 'gc',
        'general contractor'
    ]

    def __init__(self):
        self.platinum_contractors = []
        self.gold_contractors = []
        self.silver_contractors = []
        self.bronze_contractors = []

    def score_resimercial(self, match: MultiOEMMatch) -> int:
        """
        Score resimercial capability (0-100).

        100 = Explicit residential + commercial
        80 = Strong commercial indicators
        60 = Moderate commercial indicators
        40 = Residential only but high-tier
        20 = Residential only, standard tier
        0 = Unknown
        """
        dealer = match.primary_dealer
        caps = dealer.capabilities
        name_lower = dealer.name.lower()

        # Explicit flags from scraper
        if caps.is_residential and caps.is_commercial:
            return 100  # Perfect resimercial

        # Check for commercial keywords in name
        commercial_hits = sum(1 for kw in self.COMMERCIAL_KEYWORDS if kw in name_lower)
        if commercial_hits >= 2:
            return 80  # Strong commercial focus
        elif commercial_hits == 1:
            return 60  # Moderate commercial

        # High-tier dealers often do commercial
        if dealer.tier in ['Premier', 'Platinum', 'Elite Plus', 'PowerPro']:
            return 40  # Likely some commercial

        # Residential only
        if caps.is_residential and not caps.is_commercial:
            return 20

        return 0

    def score_om_capability(self, match: MultiOEMMatch) -> int:
        """
        Score O&M (Operations & Maintenance) capability (0-100).

        100 = Explicit O&M certification or service contract focus
        80 = Strong O&M keywords in name
        60 = Moderate O&M indicators
        40 = Basic service mentioned
        20 = No O&M indicators but high-tier
        0 = No O&M indicators
        """
        dealer = match.primary_dealer
        caps = dealer.capabilities
        name_lower = dealer.name.lower()

        # Explicit O&M flag from scraper
        if hasattr(dealer, 'has_ops_maintenance') and dealer.has_ops_maintenance:
            return 100

        # Check certifications for O&M
        cert_text = ' '.join(dealer.certifications).lower()
        if any(kw in cert_text for kw in ['o&m', 'maintenance', 'service provider']):
            return 100

        # Check name for O&M keywords
        om_hits = sum(1 for kw in self.OM_KEYWORDS if kw in name_lower)
        if om_hits >= 3:
            return 80  # Strong O&M focus (e.g., "ABC Service & Maintenance")
        elif om_hits == 2:
            return 60  # Moderate O&M
        elif om_hits == 1:
            return 40  # Basic service mention

        # High-tier dealers often offer maintenance
        if dealer.tier in ['Premier', 'Platinum', 'Elite Plus']:
            return 20

        return 0

    def score_multi_oem(self, match: MultiOEMMatch) -> int:
        """
        Score multi-OEM certification (0-100).

        100 = 4+ OEMs
        75 = 3 OEMs
        50 = 2 OEMs
        25 = 1 OEM
        """
        oem_count = len(match.oem_sources)

        if oem_count >= 4:
            return 100
        elif oem_count == 3:
            return 75
        elif oem_count == 2:
            return 50
        elif oem_count == 1:
            return 25
        else:
            return 0

    def score_mepr_capability(self, match: MultiOEMMatch) -> int:
        """
        Score MEP+R (Mechanical, Electrical, Plumbing + Renewables) capability (0-100).

        100 = 3+ MEP+R keywords (full self-performer)
        75 = 2 MEP+R keywords
        50 = 1 MEP+R keyword
        25 = Electrical only (required for all)
        0 = No MEP+R indicators
        """
        dealer = match.primary_dealer
        caps = dealer.capabilities
        name_lower = dealer.name.lower()

        # Count MEP+R keywords in name
        mepr_hits = sum(1 for kw in self.MEPR_KEYWORDS if kw in name_lower)

        # Capability-based scoring
        capability_count = sum([
            caps.has_hvac if hasattr(caps, 'has_hvac') else False,
            caps.has_plumbing if hasattr(caps, 'has_plumbing') else False,
            caps.has_electrical,  # All have this
        ])

        # Combine name keywords + capabilities
        total_indicators = mepr_hits + capability_count

        if total_indicators >= 4:
            return 100  # Full MEP+R self-performer
        elif total_indicators == 3:
            return 75
        elif total_indicators == 2:
            return 50
        elif total_indicators == 1:
            return 25
        else:
            return 0

    def score_contractors(self, contractors: List[MultiOEMMatch]) -> List[ICPScore]:
        """
        Score all contractors for ICP fit.

        Returns list of ICPScore objects sorted by icp_fit_score (highest first).
        """
        scores = []

        for match in contractors:
            score = ICPScore(
                contractor=match,
                resimercial_score=self.score_resimercial(match),
                om_score=self.score_om_capability(match),
                multi_oem_score=self.score_multi_oem(match),
                mepr_score=self.score_mepr_capability(match)
            )
            scores.append(score)

        # Sort by ICP fit score (highest first)
        scores.sort(key=lambda x: x.icp_fit_score, reverse=True)

        # Categorize into tiers
        self.platinum_contractors = [s for s in scores if s.icp_tier == "PLATINUM"]
        self.gold_contractors = [s for s in scores if s.icp_tier == "GOLD"]
        self.silver_contractors = [s for s in scores if s.icp_tier == "SILVER"]
        self.bronze_contractors = [s for s in scores if s.icp_tier == "BRONZE"]

        return scores

    def filter_ideal_icp(self, scores: List[ICPScore]) -> List[ICPScore]:
        """
        Filter to only ideal ICP contractors (all 4 dimensions strong).

        Returns contractors with is_ideal_icp = True.
        """
        return [s for s in scores if s.is_ideal_icp]

    def export_icp_report(self, scores: List[ICPScore], output_path: str):
        """
        Export detailed ICP analysis report.

        CSV columns:
        - Contractor name, phone, domain
        - ICP fit score, tier
        - Resimercial score, O&M score, Multi-OEM score, MEP+R score
        - Is ideal ICP flag
        - OEM sources
        """
        import csv

        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'Contractor Name',
                'Phone',
                'Domain',
                'ICP Fit Score',
                'ICP Tier',
                'Resimercial Score',
                'O&M Score',
                'Multi-OEM Score',
                'MEP+R Score',
                'Is Ideal ICP',
                'OEM Count',
                'OEM Sources',
                'Tier',
                'State',
                'City'
            ])

            # Data rows
            for score in scores:
                dealer = score.contractor.primary_dealer
                writer.writerow([
                    dealer.name,
                    dealer.phone,
                    dealer.domain,
                    score.icp_fit_score,
                    score.icp_tier,
                    score.resimercial_score,
                    score.om_score,
                    score.multi_oem_score,
                    score.mepr_score,
                    'YES' if score.is_ideal_icp else 'NO',
                    len(score.contractor.oem_sources),
                    ', '.join(sorted(score.contractor.oem_sources)),
                    dealer.tier,
                    dealer.state,
                    dealer.city
                ])

        print(f"✓ ICP report saved: {output_path}")

        # Print summary
        ideal_count = len([s for s in scores if s.is_ideal_icp])
        print()
        print("ICP TIER BREAKDOWN:")
        print(f"  PLATINUM (80-100):  {len(self.platinum_contractors):4d} contractors  ← CALL FIRST!")
        print(f"  GOLD (60-79):       {len(self.gold_contractors):4d} contractors  ← High priority")
        print(f"  SILVER (40-59):     {len(self.silver_contractors):4d} contractors")
        print(f"  BRONZE (<40):       {len(self.bronze_contractors):4d} contractors")
        print()
        print(f"🎯 IDEAL ICP (all 4 dimensions): {ideal_count} contractors")

        return output_path


if __name__ == "__main__":
    import sys
    from analysis.multi_oem_detector import MultiOEMDetector
    from scrapers.base_scraper import StandardizedDealer

    # Example usage
    print("\n" + "="*60)
    print("ICP FILTER - Test Run")
    print("="*60)

    # Mock test data
    # In production, load from CSV or multi-OEM detector
    print("\nTo use this filter:")
    print("1. Run multi-OEM scraping to get contractors")
    print("2. Pass contractors to ICPFilter.score_contractors()")
    print("3. Export ICP report with filter.export_icp_report()")
    print()
    print("Example:")
    print("  icp_filter = ICPFilter()")
    print("  scores = icp_filter.score_contractors(multi_oem_matches)")
    print("  icp_filter.export_icp_report(scores, 'output/icp_analysis.csv')")
