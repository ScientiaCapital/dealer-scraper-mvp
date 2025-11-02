#!/usr/bin/env python3
"""
22-OEM Sequential Execution System
Scrapes all 22 OEM networks with checkpoints and full validation.

NOTE: Currently 17 OEMs are production-ready. Missing:
- Generac (needs conversion to unified framework)
- Tesla (needs conversion to unified framework)
- Enphase (needs conversion to unified framework)
- Tigo (placeholder, needs implementation)
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# OEM Priority Order (HVAC → Generators → Solar → Battery)
# Updated to reflect 18 production-ready OEMs (22 planned, 4 not yet implemented)
OEM_PRIORITY_ORDER = [
    # Tier 1: HVAC Systems (6 OEMs)
    "Carrier",
    "Trane",
    "Lennox",
    "York",
    "Rheem",
    "Mitsubishi",

    # Tier 2: Backup Generators (3 OEMs - Generac needs conversion)
    "Kohler",
    "Cummins",
    "Briggs & Stratton",

    # Tier 3: Solar Inverters (8 OEMs - Enphase/Tigo not ready, ABB/Delta commented out)
    "Fronius",
    "SMA",
    "Sol-Ark",
    "GoodWe",
    "Growatt",
    "Sungrow",
    "SolarEdge",
    # "ABB",      # Commented out in scraper (FIMER acquisition)
    # "Delta",    # Commented out in scraper (no public locator)
    # "Tigo",     # Commented out in scraper (needs implementation)

    # Tier 4: Battery Storage (1 OEM - Tesla needs conversion)
    "SimpliPhi"
    # "Tesla",    # Needs conversion to unified framework
]

# Configuration
CHECKPOINT_INTERVAL = 25
TODAY = datetime.now().strftime("%Y%m%d")


def delete_checkpoints(oem_name: str) -> None:
    """
    Delete all checkpoint files for an OEM (fresh start policy).

    Args:
        oem_name: Name of OEM (e.g., "Carrier", "Briggs & Stratton")
    """
    # Normalize OEM name: lowercase, replace spaces with _, replace & with "and"
    oem_dir_name = oem_name.lower().replace(" ", "_").replace("&", "and")
    checkpoint_dir = PROJECT_ROOT / "output" / "oem_data" / oem_dir_name / "checkpoints"

    if checkpoint_dir.exists():
        checkpoint_files = list(checkpoint_dir.glob("checkpoint_*.json"))
        if checkpoint_files:
            print(f"  → Deleting {len(checkpoint_files)} old checkpoints...")
            for checkpoint_file in checkpoint_files:
                checkpoint_file.unlink()
            print(f"  ✓ Checkpoints deleted")
    else:
        print(f"  → No existing checkpoints")
