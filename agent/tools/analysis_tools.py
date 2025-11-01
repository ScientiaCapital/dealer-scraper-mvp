"""
Analysis Tools for Claude Agent SDK
Provides MCP tools for analyzing contractor data and detecting multi-OEM patterns
"""

import sys
import csv
from pathlib import Path
from typing import Any
from datetime import datetime
from claude_agent_sdk import tool

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis.multi_oem_detector import MultiOEMDetector


@tool(
    name="analyze_multi_oem_contractors",
    description="Analyze scraped contractor data to find multi-OEM contractors (those certified with 2+ brands). These are the highest-value prospects. Parameters: input_files (list of CSV file paths to analyze, required)",
    input_schema={
        "input_files": list
    }
)
async def analyze_multi_oem_contractors(args: dict[str, Any]) -> dict[str, Any]:
    """
    Analyze contractor data to find multi-OEM crossover contractors.

    Args:
        input_files: List of CSV file paths containing scraped dealer data
    """
    try:
        input_files = args["input_files"]

        if not input_files:
            return {
                "content": [{
                    "type": "text",
                    "text": "❌ Error: No input files provided. Please specify at least one CSV file path."
                }]
            }

        # Verify files exist
        missing_files = []
        for file_path in input_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)

        if missing_files:
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Error: The following files do not exist:\n" + "\n".join(f"  - {f}" for f in missing_files)
                }]
            }

        result_text = f"🔍 Analyzing contractor data for multi-OEM patterns...\n"
        result_text += f"   Input files: {len(input_files)}\n\n"

        # Initialize detector
        detector = MultiOEMDetector()

        # Load contractors from all files
        total_contractors = 0
        for file_path in input_files:
            result_text += f"   📂 Loading {Path(file_path).name}...\n"
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    detector.add_contractor(
                        name=row.get('name', ''),
                        phone=row.get('phone', ''),
                        domain=row.get('domain', ''),
                        state=row.get('state', ''),
                        oem_source=row.get('oem_source', '')
                    )
                    total_contractors += 1

        result_text += f"\n   Total contractors loaded: {total_contractors}\n\n"

        # Find multi-OEM matches
        multi_oem_matches = detector.find_multi_oem_contractors()

        # Categorize by OEM count
        triple_plus = [m for m in multi_oem_matches if m.oem_count >= 3]
        dual = [m for m in multi_oem_matches if m.oem_count == 2]

        result_text += f"✅ Analysis complete!\n\n"
        result_text += f"📊 Multi-OEM Contractors Found: {len(multi_oem_matches)}\n"
        result_text += f"   🏆 Triple+ OEM (3+ brands): {len(triple_plus)} contractors\n"
        result_text += f"   🥈 Dual OEM (2 brands): {len(dual)} contractors\n\n"

        if triple_plus:
            result_text += f"🏆 Top Triple+ OEM Contractors (UNICORNS):\n"
            for i, match in enumerate(triple_plus[:5], 1):
                result_text += f"   {i}. {match.name}\n"
                result_text += f"      Brands: {', '.join(sorted(match.oem_sources))}\n"
                result_text += f"      Phone: {match.phone}\n"
                result_text += f"      Confidence: {match.confidence_score}%\n\n"

        if dual:
            result_text += f"🥈 Sample Dual OEM Contractors:\n"
            for i, match in enumerate(dual[:5], 1):
                result_text += f"   {i}. {match.name}\n"
                result_text += f"      Brands: {', '.join(sorted(match.oem_sources))}\n"
                result_text += f"      Phone: {match.phone}\n"
                result_text += f"      Confidence: {match.confidence_score}%\n\n"

        # Save results
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d")
        output_file = output_dir / f"multi_oem_analysis_{timestamp}.csv"

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if multi_oem_matches:
                fieldnames = ['name', 'phone', 'domain', 'state', 'oem_count', 'oem_sources', 'confidence_score']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for match in multi_oem_matches:
                    writer.writerow({
                        'name': match.name,
                        'phone': match.phone,
                        'domain': match.domain,
                        'state': match.state,
                        'oem_count': match.oem_count,
                        'oem_sources': ', '.join(sorted(match.oem_sources)),
                        'confidence_score': match.confidence_score
                    })

        result_text += f"💾 Results saved to: {output_file}\n\n"
        result_text += f"💡 Multi-OEM contractors are the highest-value prospects (managing 2-3+ platforms = core pain point)."

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
                "text": f"❌ Error analyzing contractors: {str(e)}"
            }]
        }


@tool(
    name="get_latest_scraped_data",
    description="Find the most recent scraped data files in the output/ directory. Returns list of CSV files with metadata.",
    input_schema={}
)
async def get_latest_scraped_data(args: dict[str, Any]) -> dict[str, Any]:
    """Find and list recent scraped data files."""
    try:
        output_dir = Path("output")

        if not output_dir.exists():
            return {
                "content": [{
                    "type": "text",
                    "text": "❌ Output directory not found. No scraped data available yet."
                }]
            }

        # Find all CSV files
        csv_files = list(output_dir.glob("*.csv"))

        if not csv_files:
            return {
                "content": [{
                    "type": "text",
                    "text": "❌ No CSV files found in output/ directory. Run scrapers first."
                }]
            }

        # Sort by modification time (most recent first)
        csv_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        result_text = f"📂 Recent Scraped Data Files ({len(csv_files)} total):\n\n"

        for i, file in enumerate(csv_files[:10], 1):  # Show top 10
            mod_time = datetime.fromtimestamp(file.stat().st_mtime)
            size_kb = file.stat().st_size / 1024

            # Count rows
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    row_count = sum(1 for _ in csv.DictReader(f))
            except:
                row_count = "unknown"

            result_text += f"{i}. {file.name}\n"
            result_text += f"   Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            result_text += f"   Size: {size_kb:.1f} KB | Rows: {row_count}\n"
            result_text += f"   Path: {file}\n\n"

        result_text += "💡 Use these file paths with 'analyze_multi_oem_contractors' or 'score_leads'."

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
                "text": f"❌ Error finding scraped data: {str(e)}"
            }]
        }
