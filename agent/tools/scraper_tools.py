"""
Scraper Tools for Claude Agent SDK
Provides MCP tools for orchestrating OEM dealer scrapers
"""

import sys
import importlib.util
from pathlib import Path
from typing import Any
from claude_agent_sdk import tool

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load config.py directly to avoid conflict with config/ package
config_path = project_root / "config.py"
spec = importlib.util.spec_from_file_location("root_config", config_path)
root_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(root_config)
ZIP_CODES_SREC_ALL = root_config.ZIP_CODES_SREC_ALL

from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode


@tool(
    name="list_available_scrapers",
    description="List all available OEM scrapers and their status. Returns a list of registered scrapers that can be executed.",
    input_schema={}
)
async def list_available_scrapers(args: dict[str, Any]) -> dict[str, Any]:
    """List all registered OEM scrapers."""
    try:
        # Get registered scrapers from factory
        registered_scrapers = ScraperFactory.list_registered()

        result_text = f"📋 Available OEM Scrapers ({len(registered_scrapers)} total):\n\n"

        for oem in registered_scrapers:
            result_text += f"  ✅ {oem}\n"

        result_text += "\n💡 Use 'run_scraper' tool to execute any of these scrapers."

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
                "text": f"❌ Error listing scrapers: {str(e)}"
            }]
        }


@tool(
    name="get_srec_states",
    description="Get the list of SREC (Solar Renewable Energy Credit) states with ZIP codes configured for scraping.",
    input_schema={}
)
async def get_srec_states(args: dict[str, Any]) -> dict[str, Any]:
    """Get SREC states and ZIP codes."""
    try:
        # Get unique states from ZIP_CODES_SREC_ALL
        states_with_counts = {}
        for state, zips in ZIP_CODES_SREC_ALL.items():
            states_with_counts[state] = len(zips)

        total_zips = sum(states_with_counts.values())

        result_text = f"🗺️ SREC States Configuration ({len(states_with_counts)} states, {total_zips} total ZIPs):\n\n"

        # Sort by state name
        for state in sorted(states_with_counts.keys()):
            count = states_with_counts[state]
            result_text += f"  {state}: {count} ZIPs\n"

        result_text += "\n💡 These are high-value sustainable markets with post-ITC incentive programs."

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
                "text": f"❌ Error retrieving SREC states: {str(e)}"
            }]
        }


@tool(
    name="run_scraper",
    description="Execute an OEM scraper for specific states and ZIP codes. Returns scraped dealer data. Parameters: oem_name (str, required), states (list of state codes like ['CA', 'TX'], required), mode (str, optional, default='PLAYWRIGHT'), limit_zips (int, optional, limits ZIPs per state for testing)",
    input_schema={
        "oem_name": str,
        "states": list,
        "mode": str,
        "limit_zips": int
    }
)
async def run_scraper(args: dict[str, Any]) -> dict[str, Any]:
    """
    Run a specific OEM scraper for given states.

    Args:
        oem_name: OEM brand name (e.g., "Generac", "Tesla", "Enphase")
        states: List of state codes (e.g., ["CA", "TX"])
        mode: Scraping mode ("PLAYWRIGHT", "RUNPOD", or "BROWSERBASE"), default "PLAYWRIGHT"
        limit_zips: Optional limit on ZIPs per state (for testing), default None (all ZIPs)
    """
    try:
        oem_name = args["oem_name"]
        states = args["states"]
        mode_str = args.get("mode", "PLAYWRIGHT").upper()
        limit_zips = args.get("limit_zips")

        # Convert mode string to ScraperMode enum
        try:
            mode = ScraperMode[mode_str]
        except KeyError:
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Invalid mode '{mode_str}'. Valid modes: PLAYWRIGHT, RUNPOD, BROWSERBASE"
                }]
            }

        # Create scraper instance
        try:
            scraper = ScraperFactory.create(oem_name, mode=mode)
        except ValueError as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Error creating scraper: {str(e)}\n\n💡 Use 'list_available_scrapers' to see valid OEM names."
                }]
            }

        # Collect ZIPs for requested states
        target_zips = []
        for state in states:
            if state not in ZIP_CODES_SREC_ALL:
                return {
                    "content": [{
                        "type": "text",
                        "text": f"❌ Invalid state '{state}'. Use 'get_srec_states' to see valid states."
                    }]
                }
            state_zips = ZIP_CODES_SREC_ALL[state]
            if limit_zips:
                state_zips = state_zips[:limit_zips]
            target_zips.extend(state_zips)

        result_text = f"🚀 Starting {oem_name} scraper...\n"
        result_text += f"   States: {', '.join(states)}\n"
        result_text += f"   Mode: {mode_str}\n"
        result_text += f"   Target ZIPs: {len(target_zips)}\n\n"

        # Run the scraper
        dealers = []
        for i, zip_code in enumerate(target_zips, 1):
            result_text += f"   [{i}/{len(target_zips)}] Scraping ZIP {zip_code}...\n"
            zip_dealers = scraper.scrape_zip(zip_code)
            dealers.extend(zip_dealers)

        # Deduplicate by phone
        unique_dealers = scraper.deduplicate_by_phone(dealers)

        result_text += f"\n✅ Scraping complete!\n"
        result_text += f"   Total dealers found: {len(dealers)}\n"
        result_text += f"   Unique dealers (after deduplication): {len(unique_dealers)}\n"
        result_text += f"   Deduplication rate: {((len(dealers) - len(unique_dealers)) / len(dealers) * 100):.1f}%\n\n"
        result_text += f"💡 Use 'analyze_contractors' to find multi-OEM contractors or 'score_leads' to apply ICP scoring."

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
                "text": f"❌ Error running scraper: {str(e)}"
            }]
        }
