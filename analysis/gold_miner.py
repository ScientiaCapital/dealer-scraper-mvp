"""
Gold Miner - Identify High-Value Contractors for Coperniq

Finds the "gold" contractors:
1. Multi-OEM certified (2-4 brands) - juggling multiple monitoring apps
2. MEP+R self-performers - complex commercial projects
3. High-tier dealers (Premier, Platinum, Gold)
4. Commercial focus with SREC state presence
"""

import pandas as pd
from typing import List, Dict, Set
import re


class GoldMiner:
    """
    Identifies the highest-value contractor ICPs for Coperniq.
    """

    # MEP+R indicators (self-performing contractors)
    MEP_INDICATORS = [
        'mechanical', 'mep', 'hvac', 'plumbing', 'engineering',
        'electrical', 'controls', 'automation', 'energy', 'facilities',
        'systems', 'services', 'solutions', 'contractors', 'builders'
    ]

    # Commercial indicators
    COMMERCIAL_INDICATORS = [
        'commercial', 'industrial', 'enterprise', 'corporate',
        'business', 'professional', 'facilities', 'institutional'
    ]

    # High-tier indicators
    HIGH_TIER = ['Premier', 'Platinum', 'Gold', 'Elite', 'PowerPro']

    def __init__(self):
        self.gold_contractors = []
        self.silver_contractors = []
        self.bronze_contractors = []

    def identify_mepr_contractors(self, contractors: pd.DataFrame) -> pd.DataFrame:
        """
        Identify MEP+R self-performing contractors.

        These are the Southland Industries types - large commercial contractors
        doing mechanical, electrical, plumbing + renewables.
        """
        mepr_scores = []

        for _, contractor in contractors.iterrows():
            score = 0
            name_lower = str(contractor.get('contractor_name', '')).lower()

            # Check for MEP indicators in name
            for indicator in self.MEP_INDICATORS:
                if indicator in name_lower:
                    score += 10

            # Check for commercial focus
            for indicator in self.COMMERCIAL_INDICATORS:
                if indicator in name_lower:
                    score += 5

            # Check tier (Premier/Platinum = likely commercial)
            tier = str(contractor.get('tier', ''))
            if any(t in tier for t in self.HIGH_TIER):
                score += 15

            # Check for multiple capabilities (electrical + HVAC + plumbing)
            # This would come from enrichment data

            mepr_scores.append(score)

        contractors['mepr_score'] = mepr_scores
        return contractors

    def identify_multi_oem(self, contractors: pd.DataFrame) -> pd.DataFrame:
        """
        Identify contractors certified with multiple OEMs.

        For now, we only have Generac data, but this will cross-reference
        with Tesla, Enphase, and SolarEdge once we have those datasets.
        """
        # Placeholder for multi-OEM detection
        # Will implement once we have multiple OEM datasets
        contractors['oem_count'] = 1  # All are Generac for now
        contractors['oem_brands'] = 'Generac'

        return contractors

    def calculate_gold_score(self, contractors: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate overall "gold score" for each contractor.

        Scoring dimensions:
        1. MEP+R indicators (0-50 points)
        2. Multi-OEM presence (0-40 points)
        3. Commercial capability (0-30 points)
        4. SREC state + ITC urgency (0-30 points)
        5. Tier/certification level (0-20 points)
        """
        gold_scores = []

        for _, contractor in contractors.iterrows():
            score = 0

            # MEP+R score (normalized to 0-50)
            mepr_score = min(contractor.get('mepr_score', 0), 50)
            score += mepr_score

            # Multi-OEM score (will be 40 for 3+ OEMs, 25 for 2, 10 for 1)
            oem_count = contractor.get('oem_count', 1)
            if oem_count >= 3:
                score += 40
            elif oem_count == 2:
                score += 25
            else:
                score += 10

            # Commercial capability (from tier and name)
            tier = str(contractor.get('tier', ''))
            if any(t in tier for t in self.HIGH_TIER):
                score += 30

            # SREC state + ITC urgency
            if contractor.get('srec_state_priority') == 'HIGH':
                score += 20
            if contractor.get('itc_urgency') in ['CRITICAL', 'HIGH']:
                score += 10

            # Tier bonus
            if 'Premier' in tier or 'Platinum' in tier:
                score += 20
            elif 'Gold' in tier or 'Elite' in tier:
                score += 15

            gold_scores.append(score)

        contractors['gold_score'] = gold_scores

        # Classify into tiers
        contractors['gold_tier'] = contractors['gold_score'].apply(
            lambda x: 'GOLD' if x >= 100 else 'SILVER' if x >= 70 else 'BRONZE'
        )

        return contractors

    def mine_for_gold(self, csv_path: str) -> Dict:
        """
        Process contractor list and identify gold contractors.

        Returns dict with gold, silver, and bronze tier contractors.
        """
        print("\n" + "="*60)
        print("🔍 GOLD MINER - Finding High-Value Contractors")
        print("="*60)

        # Load contractors
        contractors = pd.read_csv(csv_path)
        print(f"\nAnalyzing {len(contractors)} contractors...")

        # Identify MEP+R contractors
        contractors = self.identify_mepr_contractors(contractors)

        # Identify multi-OEM (placeholder for now)
        contractors = self.identify_multi_oem(contractors)

        # Calculate gold scores
        contractors = self.calculate_gold_score(contractors)

        # Sort by gold score
        contractors = contractors.sort_values('gold_score', ascending=False)

        # Separate into tiers
        gold = contractors[contractors['gold_tier'] == 'GOLD']
        silver = contractors[contractors['gold_tier'] == 'SILVER']
        bronze = contractors[contractors['gold_tier'] == 'BRONZE']

        print(f"\n⭐ RESULTS:")
        print(f"  GOLD contractors (100+ score): {len(gold)}")
        print(f"  SILVER contractors (70-99): {len(silver)}")
        print(f"  BRONZE contractors (<70): {len(bronze)}")

        # Show top 10 gold contractors
        if not gold.empty:
            print(f"\n🏆 TOP 10 GOLD CONTRACTORS:")
            print("="*60)
            for i, contractor in gold.head(10).iterrows():
                print(f"\n#{contractors.index.get_loc(i)+1}: {contractor['contractor_name']}")
                print(f"  Score: {contractor['gold_score']}/170")
                print(f"  Phone: {contractor['phone']}")
                print(f"  Domain: {contractor.get('domain', 'N/A')}")
                print(f"  MEP+R Score: {contractor['mepr_score']}")
                print(f"  Tier: {contractor.get('tier', 'Standard')}")

        # Save enhanced CSV
        output_path = csv_path.replace('.csv', '_gold_enhanced.csv')
        contractors.to_csv(output_path, index=False)
        print(f"\n✅ Enhanced CSV saved: {output_path}")

        return {
            'gold': gold,
            'silver': silver,
            'bronze': bronze,
            'total': len(contractors)
        }

    def export_gold_list(self, gold_contractors: pd.DataFrame, output_path: str):
        """
        Export just the gold contractors for immediate outreach.
        """
        gold_export = gold_contractors[[
            'contractor_name', 'phone', 'domain',
            'gold_score', 'mepr_score', 'tier',
            'srec_state_priority', 'itc_urgency'
        ]].copy()

        gold_export.to_csv(output_path, index=False)
        print(f"\n🏆 Gold list exported: {output_path}")
        return output_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
        miner = GoldMiner()
        results = miner.mine_for_gold(csv_path)

        # Export gold list
        if not results['gold'].empty:
            gold_path = csv_path.replace('.csv', '_GOLD_ONLY.csv')
            miner.export_gold_list(results['gold'], gold_path)
    else:
        print("Usage: python gold_miner.py <contractor_csv>")