"""
Pipeline Tools for Claude Agent SDK
Provides MCP tools for monitoring and managing the lead generation pipeline
"""

import sys
import csv
from pathlib import Path
from typing import Any
from datetime import datetime
from claude_agent_sdk import tool

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@tool(
    name="get_pipeline_stats",
    description="Get comprehensive statistics about the lead generation pipeline. Shows scraped data, multi-OEM analysis, scoring results, and tier distribution.",
    input_schema={}
)
async def get_pipeline_stats(args: dict[str, Any]) -> dict[str, Any]:
    """Get pipeline statistics and status."""
    try:
        output_dir = Path("output")

        if not output_dir.exists():
            return {
                "content": [{
                    "type": "text",
                    "text": "❌ Output directory not found. No pipeline data available yet.\n\n💡 Run scrapers first using 'run_scraper' tool."
                }]
            }

        result_text = "📊 Lead Generation Pipeline Statistics\n"
        result_text += "=" * 50 + "\n\n"

        # Find all CSV files and categorize them
        csv_files = list(output_dir.glob("*.csv"))

        if not csv_files:
            return {
                "content": [{
                    "type": "text",
                    "text": "❌ No data files found in pipeline.\n\n💡 Run scrapers first using 'run_scraper' tool."
                }]
            }

        # Categorize files
        scraped_files = [f for f in csv_files if 'deduped' in f.name.lower() or any(oem in f.name.lower() for oem in ['generac', 'tesla', 'enphase', 'cummins'])]
        multi_oem_files = [f for f in csv_files if 'multi_oem' in f.name.lower() or 'crossover' in f.name.lower()]
        scored_files = [f for f in csv_files if 'icp_scored' in f.name.lower() or 'scored' in f.name.lower()]
        srec_files = [f for f in csv_files if 'srec' in f.name.lower()]

        # 1. Scraped Data
        result_text += "🔍 SCRAPED DATA\n"
        result_text += "-" * 50 + "\n"
        if scraped_files:
            total_scraped = 0
            for file in scraped_files[:5]:  # Show top 5
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        count = sum(1 for _ in csv.DictReader(f))
                        total_scraped += count
                        mod_time = datetime.fromtimestamp(file.stat().st_mtime)
                        result_text += f"  📄 {file.name}\n"
                        result_text += f"      Contractors: {count:,} | Modified: {mod_time.strftime('%Y-%m-%d %H:%M')}\n"
                except:
                    pass
            result_text += f"\n  Total unique contractors: {total_scraped:,}\n\n"
        else:
            result_text += "  ⚠️ No scraped data found\n\n"

        # 2. Multi-OEM Analysis
        result_text += "🔗 MULTI-OEM ANALYSIS\n"
        result_text += "-" * 50 + "\n"
        if multi_oem_files:
            latest_multi_oem = multi_oem_files[0]
            try:
                with open(latest_multi_oem, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    contractors = list(reader)
                    triple_plus = len([c for c in contractors if int(c.get('oem_count', 0)) >= 3])
                    dual = len([c for c in contractors if int(c.get('oem_count', 0)) == 2])

                    result_text += f"  📄 {latest_multi_oem.name}\n"
                    result_text += f"      Multi-OEM contractors: {len(contractors):,}\n"
                    result_text += f"      🏆 Triple+ OEM (3+ brands): {triple_plus:,}\n"
                    result_text += f"      🥈 Dual OEM (2 brands): {dual:,}\n\n"
            except:
                result_text += f"  📄 {latest_multi_oem.name} (unable to read)\n\n"
        else:
            result_text += "  ⚠️ No multi-OEM analysis found\n"
            result_text += "  💡 Run 'analyze_multi_oem_contractors' to detect multi-brand contractors\n\n"

        # 3. ICP Scored Leads
        result_text += "🎯 ICP SCORED LEADS\n"
        result_text += "-" * 50 + "\n"
        if scored_files:
            latest_scored = scored_files[0]
            try:
                with open(latest_scored, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    contractors = list(reader)

                    # Count by tier
                    tier_counts = {
                        'PLATINUM': len([c for c in contractors if c.get('tier') == 'PLATINUM']),
                        'GOLD': len([c for c in contractors if c.get('tier') == 'GOLD']),
                        'SILVER': len([c for c in contractors if c.get('tier') == 'SILVER']),
                        'BRONZE': len([c for c in contractors if c.get('tier') == 'BRONZE'])
                    }

                    result_text += f"  📄 {latest_scored.name}\n"
                    result_text += f"      Total scored: {len(contractors):,}\n"
                    result_text += f"      💎 PLATINUM (80-100): {tier_counts['PLATINUM']:,}\n"
                    result_text += f"      🥇 GOLD (60-79): {tier_counts['GOLD']:,}\n"
                    result_text += f"      🥈 SILVER (40-59): {tier_counts['SILVER']:,}\n"
                    result_text += f"      🥉 BRONZE (<40): {tier_counts['BRONZE']:,}\n\n"
            except:
                result_text += f"  📄 {latest_scored.name} (unable to read)\n\n"
        else:
            result_text += "  ⚠️ No scored leads found\n"
            result_text += "  💡 Run 'score_leads' to apply Coperniq ICP scoring\n\n"

        # 4. SREC Filtered
        result_text += "🗺️ SREC STATE FILTERING\n"
        result_text += "-" * 50 + "\n"
        if srec_files:
            latest_srec = srec_files[0]
            try:
                with open(latest_srec, 'r', encoding='utf-8') as f:
                    count = sum(1 for _ in csv.DictReader(f))
                    result_text += f"  📄 {latest_srec.name}\n"
                    result_text += f"      SREC contractors: {count:,}\n\n"
            except:
                result_text += f"  📄 {latest_srec.name} (unable to read)\n\n"
        else:
            result_text += "  ⚠️ No SREC filtered data found\n"
            result_text += "  💡 Run 'filter_srec_states' to focus on sustainable markets\n\n"

        # Summary
        result_text += "=" * 50 + "\n"
        result_text += "💡 NEXT STEPS:\n"
        result_text += "  1. Run scrapers for additional OEMs if needed\n"
        result_text += "  2. Analyze for multi-OEM contractors (highest value)\n"
        result_text += "  3. Score leads with ICP algorithm\n"
        result_text += "  4. Filter to SREC states for sustainability\n"
        result_text += "  5. Export GOLD/PLATINUM tiers for outreach\n"

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
                "text": f"❌ Error getting pipeline stats: {str(e)}"
            }]
        }


@tool(
    name="export_top_prospects",
    description="Export top prospects for immediate outreach. Filters to GOLD and PLATINUM tiers only. Parameters: input_file (path to scored CSV file, required), limit (max number of prospects to export, default 50)",
    input_schema={
        "input_file": str,
        "limit": int
    }
)
async def export_top_prospects(args: dict[str, Any]) -> dict[str, Any]:
    """
    Export top-tier prospects for BDR outreach.

    Args:
        input_file: Path to CSV file containing scored contractor data
        limit: Maximum number of prospects to export (default: 50)
    """
    try:
        input_file = args["input_file"]
        limit = args.get("limit", 50)
        input_path = Path(input_file)

        if not input_path.exists():
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Error: File not found: {input_file}\n\n💡 Use 'get_latest_scraped_data' to find scored CSV files."
                }]
            }

        result_text = f"🎯 Exporting top {limit} prospects for outreach...\n"
        result_text += f"   Input file: {input_path.name}\n\n"

        # Load and filter contractors
        contractors = []
        with open(input_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Only include GOLD and PLATINUM tiers
                if row.get('tier') in ['GOLD', 'PLATINUM']:
                    contractors.append(row)

        # Sort by score (highest first)
        contractors.sort(key=lambda x: int(x.get('coperniq_score', 0)), reverse=True)

        # Limit to top N
        top_prospects = contractors[:limit]

        result_text += f"✅ Found {len(contractors)} GOLD/PLATINUM prospects\n"
        result_text += f"   Exporting top {len(top_prospects)} for outreach\n\n"

        # Show preview of top 10
        result_text += "🏆 Top 10 Preview:\n\n"
        for i, contractor in enumerate(top_prospects[:10], 1):
            result_text += f"{i}. {contractor.get('name', 'Unknown')} ({contractor.get('tier')})\n"
            result_text += f"   Score: {contractor.get('coperniq_score')}/100\n"
            result_text += f"   Phone: {contractor.get('phone', 'N/A')}\n"
            result_text += f"   Location: {contractor.get('city', '')}, {contractor.get('state', '')}\n\n"

        # Save export
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d")
        output_file = output_dir / f"top_{limit}_prospects_{timestamp}.csv"

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if top_prospects:
                fieldnames = list(top_prospects[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(top_prospects)

        result_text += f"💾 Top prospects exported to: {output_file}\n\n"
        result_text += f"🚀 READY FOR OUTREACH:\n"
        result_text += f"   - Import to Close CRM\n"
        result_text += f"   - Load into email sequences\n"
        result_text += f"   - Begin cold calling campaign\n"

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
                "text": f"❌ Error exporting prospects: {str(e)}"
            }]
        }
