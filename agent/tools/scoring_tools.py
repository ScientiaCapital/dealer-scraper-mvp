"""
Scoring Tools for Claude Agent SDK
Provides MCP tools for ICP scoring and lead prioritization
"""

import sys
import csv
from pathlib import Path
from typing import Any
from datetime import datetime
from claude_agent_sdk import tool

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from targeting.coperniq_lead_scorer import CoperniqLeadScorer
from targeting.icp_filter import ICPFilter
from targeting.srec_itc_filter import SRECITCFilter


@tool(
    name="score_leads",
    description="Apply Coperniq's ICP scoring algorithm to contractor data. Scores based on: Resimercial (35%), Multi-OEM (25%), MEP+R (25%), O&M (15%). Returns scored leads sorted by tier. Parameters: input_file (CSV file path, required)",
    input_schema={
        "input_file": str
    }
)
async def score_leads(args: dict[str, Any]) -> dict[str, Any]:
    """
    Score contractor leads using Coperniq's ICP algorithm.

    Args:
        input_file: Path to CSV file containing contractor data
    """
    try:
        input_file = args["input_file"]
        input_path = Path(input_file)

        if not input_path.exists():
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Error: File not found: {input_file}\n\n💡 Use 'get_latest_scraped_data' to find available CSV files."
                }]
            }

        result_text = f"🎯 Scoring contractor leads with Coperniq ICP algorithm...\n"
        result_text += f"   Input file: {input_path.name}\n\n"

        # Load contractors
        contractors = []
        with open(input_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                contractors.append(row)

        result_text += f"   Loaded contractors: {len(contractors)}\n\n"

        # Initialize scorer
        scorer = CoperniqLeadScorer()

        # Score each contractor
        scored_contractors = []
        for contractor in contractors:
            # Convert to dictionary if needed
            contractor_dict = dict(contractor)

            # Apply scoring
            score = scorer.score_contractor(contractor_dict)
            contractor_dict['coperniq_score'] = score

            # Determine tier
            if score >= 80:
                contractor_dict['tier'] = 'PLATINUM'
            elif score >= 60:
                contractor_dict['tier'] = 'GOLD'
            elif score >= 40:
                contractor_dict['tier'] = 'SILVER'
            else:
                contractor_dict['tier'] = 'BRONZE'

            scored_contractors.append(contractor_dict)

        # Sort by score (highest first)
        scored_contractors.sort(key=lambda x: x['coperniq_score'], reverse=True)

        # Calculate tier distribution
        tier_counts = {
            'PLATINUM': len([c for c in scored_contractors if c['tier'] == 'PLATINUM']),
            'GOLD': len([c for c in scored_contractors if c['tier'] == 'GOLD']),
            'SILVER': len([c for c in scored_contractors if c['tier'] == 'SILVER']),
            'BRONZE': len([c for c in scored_contractors if c['tier'] == 'BRONZE'])
        }

        result_text += f"✅ Scoring complete!\n\n"
        result_text += f"📊 Tier Distribution:\n"
        result_text += f"   💎 PLATINUM (80-100): {tier_counts['PLATINUM']} contractors\n"
        result_text += f"   🥇 GOLD (60-79): {tier_counts['GOLD']} contractors\n"
        result_text += f"   🥈 SILVER (40-59): {tier_counts['SILVER']} contractors\n"
        result_text += f"   🥉 BRONZE (<40): {tier_counts['BRONZE']} contractors\n\n"

        # Show top 10 prospects
        if scored_contractors:
            result_text += f"🏆 Top 10 Prospects:\n\n"
            for i, contractor in enumerate(scored_contractors[:10], 1):
                result_text += f"{i}. {contractor.get('name', 'Unknown')} ({contractor['tier']})\n"
                result_text += f"   Score: {contractor['coperniq_score']}/100\n"
                result_text += f"   Phone: {contractor.get('phone', 'N/A')}\n"
                result_text += f"   Location: {contractor.get('city', '')}, {contractor.get('state', '')}\n\n"

        # Save scored results
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d")
        output_file = output_dir / f"icp_scored_leads_{timestamp}.csv"

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if scored_contractors:
                fieldnames = list(scored_contractors[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(scored_contractors)

        result_text += f"💾 Scored leads saved to: {output_file}\n\n"
        result_text += f"💡 Focus on GOLD and PLATINUM tiers for immediate outreach."

        return {
            "content": [{
                "type": "text",
                "text": result_text
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"❌ Error scoring leads: {str(e)}"
            }]
        }


@tool(
    name="filter_srec_states",
    description="Filter contractors to SREC (Solar Renewable Energy Credit) states only. These are sustainable markets with post-ITC incentive programs. Parameters: input_file (CSV file path, required)",
    input_schema={
        "input_file": str
    }
)
async def filter_srec_states(args: dict[str, Any]) -> dict[str, Any]:
    """
    Filter contractors to SREC states only.

    Args:
        input_file: Path to CSV file containing contractor data
    """
    try:
        input_file = args["input_file"]
        input_path = Path(input_file)

        if not input_path.exists():
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Error: File not found: {input_file}"
                }]
            }

        result_text = f"🗺️ Filtering contractors to SREC states...\n"
        result_text += f"   Input file: {input_path.name}\n\n"

        # Load contractors
        contractors = []
        with open(input_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                contractors.append(row)

        result_text += f"   Total contractors: {len(contractors)}\n\n"

        # Initialize filter
        srec_filter = SRECITCFilter()

        # Filter to SREC states
        srec_contractors = []
        for contractor in contractors:
            state = contractor.get('state', '')
            if srec_filter.is_srec_state(state):
                # Add priority and urgency tags
                contractor['srec_state_priority'] = srec_filter.get_state_priority(state)
                contractor['itc_urgency'] = srec_filter.get_itc_urgency(state)
                srec_contractors.append(contractor)

        # Calculate statistics
        priority_counts = {}
        for contractor in srec_contractors:
            priority = contractor['srec_state_priority']
            priority_counts[priority] = priority_counts.get(priority, 0) + 1

        result_text += f"✅ Filtering complete!\n\n"
        result_text += f"📊 Results:\n"
        result_text += f"   SREC contractors: {len(srec_contractors)}\n"
        result_text += f"   Filtered out: {len(contractors) - len(srec_contractors)}\n\n"

        result_text += f"🎯 Priority Distribution:\n"
        for priority in ['HIGH', 'MEDIUM', 'LOW']:
            count = priority_counts.get(priority, 0)
            result_text += f"   {priority}: {count} contractors\n"

        # Save filtered results
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d")
        output_file = output_dir / f"srec_filtered_{timestamp}.csv"

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if srec_contractors:
                fieldnames = list(srec_contractors[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(srec_contractors)

        result_text += f"\n💾 Filtered contractors saved to: {output_file}\n\n"
        result_text += f"💡 SREC states have sustainable incentives after federal ITC expires."

        return {
            "content": [{
                "type": "text",
                "text": result_text
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"❌ Error filtering SREC states: {str(e)}"
            }]
        }
