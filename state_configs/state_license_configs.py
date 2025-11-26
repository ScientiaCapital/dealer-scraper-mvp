"""
State contractor license database configurations.

Each state classified into tier based on data access method:
- BULK: States with CSV/Excel export portals
- API: States with REST APIs
- SCRAPER: States requiring Playwright automation
"""

STATE_CONFIGS = {
    # ==================== TIER 1: BULK DOWNLOAD STATES ====================

    "CA": {
        "tier": "BULK",
        "download_url": "https://www.cslb.ca.gov/onlineservices/dataportal/",
        "format": "csv",
        "license_types": {
            "Electrical": ["C-10"],
            "LowVoltage": ["C-7"],
            "HVAC": ["C-20"]
        },
        "estimated_volume": 50000,
        "notes": "CSLB Public Data Portal - downloadable CSV by classification"
    },

    "FL": {
        "tier": "BULK",
        "download_url": "https://www2.myfloridalicense.com/",
        "format": "csv",
        "license_types": {
            "Electrical": ["ER"],
            "LowVoltage": ["EL"],
            "HVAC": ["CAC"]
        },
        "estimated_volume": 35000,
        "notes": "MyFloridaLicense - downloadable active licensee files"
    },

    "TX": {
        "tier": "BULK",
        "download_url": "https://www.tdlr.texas.gov/apps/",
        "format": "xlsx",
        "license_types": {
            "Electrical": ["Electrical Contractor"],
            "LowVoltage": ["Low Voltage Contractor"],
            "HVAC": ["Air Conditioning Contractor"]
        },
        "estimated_volume": 35000,
        "notes": "TDLR databases - multiple Excel files per license type"
    },

    # ==================== TIER 2: API-ENABLED STATES ====================

    "MA": {
        "tier": "API",
        "api_url": "https://licensing.api.secure.digital.mass.gov/",
        "api_key": None,  # Public API
        "license_types": {
            "Electrical": ["Electrical Contractor"],
            "HVAC": ["HVAC Contractor"]
        },
        "estimated_volume": 8000,
        "notes": "REST API with JSON responses, pagination required"
    },

    # ==================== TIER 3: SCRAPER STATES ====================

    "PA": {
        "tier": "SCRAPER",
        "search_url": "https://www.dli.pa.gov",
        "license_types": {
            "Electrical": ["Electrical Contractor"],
            "HVAC": ["HVAC Contractor"]
        },
        "estimated_volume": 15000,
        "notes": "Requires Playwright automation"
    },

    "NJ": {
        "tier": "SCRAPER",
        "search_url": "https://www.nj.gov/oag/ca/publicrecords/",
        "license_types": {
            "Electrical": ["Electrical Contractor"],
            "HVAC": ["HVAC Contractor"]
        },
        "estimated_volume": 12000,
        "notes": "Requires Playwright automation"
    },

    "NY": {
        "tier": "SCRAPER",
        "search_url": "https://www.dos.ny.gov/licensing/",
        "license_types": {
            "Electrical": ["Licensed Electrician"],
            "HVAC": ["HVAC Contractor"]
        },
        "estimated_volume": 20000,
        "notes": "Requires Playwright automation"
    },

    "IL": {
        "tier": "SCRAPER",
        "search_url": "https://www.cyberdriveillinois.com/departments/index/register/home.html",
        "license_types": {
            "Electrical": ["Licensed Electrician"],
            "HVAC": ["HVAC Contractor"]
        },
        "estimated_volume": 10000,
        "notes": "Limited searchability, requires Playwright"
    },

    # ==================== PLACEHOLDER CONFIGS (42 remaining states) ====================
    # TODO: Research and configure these states in Phase 3

    "AL": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 5000, "notes": "TBD"},
    "AK": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 1000, "notes": "TBD"},
    "AZ": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 8000, "notes": "TBD"},
    "AR": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 3000, "notes": "TBD"},
    "CO": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 7000, "notes": "TBD"},
    "CT": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 5000, "notes": "TBD"},
    "DE": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 2000, "notes": "TBD"},
    "DC": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 1500, "notes": "TBD"},
    "GA": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 10000, "notes": "TBD"},
    "HI": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 2000, "notes": "TBD"},
    "ID": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 2000, "notes": "TBD"},
    "IN": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 6000, "notes": "TBD"},
    "IA": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 3000, "notes": "TBD"},
    "KS": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 3000, "notes": "TBD"},
    "KY": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 4000, "notes": "TBD"},
    "LA": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 5000, "notes": "TBD"},
    "ME": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 2000, "notes": "TBD"},
    "MD": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 7000, "notes": "TBD"},
    "MI": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 10000, "notes": "TBD"},
    "MN": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 6000, "notes": "TBD"},
    "MS": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 3000, "notes": "TBD"},
    "MO": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 6000, "notes": "TBD"},
    "MT": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 1500, "notes": "TBD"},
    "NE": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 2000, "notes": "TBD"},
    "NV": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 5000, "notes": "TBD"},
    "NH": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 2000, "notes": "TBD"},
    "NM": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 2000, "notes": "TBD"},
    "NC": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 10000, "notes": "TBD"},
    "ND": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 1000, "notes": "TBD"},
    "OH": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 12000, "notes": "TBD"},
    "OK": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 4000, "notes": "TBD"},
    "OR": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 5000, "notes": "TBD"},
    "RI": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 1500, "notes": "TBD"},
    "SC": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 5000, "notes": "TBD"},
    "SD": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 1000, "notes": "TBD"},
    "TN": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 6000, "notes": "TBD"},
    "UT": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 3000, "notes": "TBD"},
    "VT": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 1000, "notes": "TBD"},
    "VA": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 8000, "notes": "TBD"},
    "WA": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 8000, "notes": "TBD"},
    "WV": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 2000, "notes": "TBD"},
    "WI": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 6000, "notes": "TBD"},
    "WY": {"tier": "SCRAPER", "search_url": "TBD", "license_types": {}, "estimated_volume": 1000, "notes": "TBD"},
}

def get_state_config(state_code: str) -> dict:
    """
    Get configuration for a specific state.

    Args:
        state_code: Two-letter state code (e.g., "CA", "TX")

    Returns:
        State configuration dict

    Raises:
        KeyError: If state_code is invalid
    """
    return STATE_CONFIGS[state_code]

def get_states_by_tier(tier: str) -> list:
    """
    Get all states for a specific tier.

    Args:
        tier: "BULK", "API", or "SCRAPER"

    Returns:
        List of state codes in that tier
    """
    return [code for code, config in STATE_CONFIGS.items() if config["tier"] == tier]
