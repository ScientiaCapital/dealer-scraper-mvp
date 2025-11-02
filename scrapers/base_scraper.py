"""
Base Scraper for Multi-OEM Dealer Networks

Abstract base class that standardizes scraping across different OEM dealer locators.
Each OEM-specific scraper inherits from this and implements custom extraction logic.

Supports Coperniq's partner prospecting system targeting multi-brand contractors.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from difflib import SequenceMatcher
import re
import json
import logging
from datetime import datetime
from pathlib import Path


class ScraperMode(Enum):
    """Execution mode for dealer scraping"""
    PLAYWRIGHT = "playwright"  # Local MCP Playwright
    RUNPOD = "runpod"         # RunPod serverless API
    BROWSERBASE = "browserbase"  # Browserbase cloud
    PATCHRIGHT = "patchright"  # Patchright stealth (bot detection bypass)


class DealerCapabilities:
    """Tracks contractor capabilities across multiple dimensions"""
    
    # Product installation capabilities
    has_generator: bool = False
    has_solar: bool = False
    has_battery: bool = False
    has_microinverters: bool = False
    has_inverters: bool = False
    
    # Trade capabilities
    has_electrical: bool = False
    has_hvac: bool = False
    has_roofing: bool = False
    has_plumbing: bool = False
    
    # Business characteristics
    is_commercial: bool = False
    is_residential: bool = False
    is_gc: bool = False  # General contractor
    is_sub: bool = False  # Specialized sub-contractor

    # High-value contractor types (Coperniq priority targets)
    has_om_capability: bool = False  # Operations & Maintenance (manages complex energy portfolios)
    is_mep_r_contractor: bool = False  # MEP+R self-performing (Mechanical, Electrical, Plumbing, Roofing)

    # OEM certifications (populated by multi-OEM detector)
    oem_certifications: Set[str] = field(default_factory=set)

    # OEM-specific product capabilities (Coperniq's key value prop)
    # Tracks which specific OEM brands this dealer is certified to install
    generator_oems: Set[str] = field(default_factory=set)  # Generac, Kohler, Cummins
    battery_oems: Set[str] = field(default_factory=set)     # Tesla, Generac, Enphase, LG, SolarEdge
    microinverter_oems: Set[str] = field(default_factory=set)  # Enphase, APsystems
    inverter_oems: Set[str] = field(default_factory=set)    # SolarEdge, SMA, Fronius

    def __init__(self):
        self.has_generator = False
        self.has_solar = False
        self.has_battery = False
        self.has_microinverters = False
        self.has_inverters = False
        self.has_electrical = False
        self.has_hvac = False
        self.has_roofing = False
        self.has_plumbing = False
        self.is_commercial = False
        self.is_residential = False
        self.is_gc = False
        self.is_sub = False
        self.has_om_capability = False
        self.is_mep_r_contractor = False
        self.oem_certifications = set()
        self.generator_oems = set()
        self.battery_oems = set()
        self.microinverter_oems = set()
        self.inverter_oems = set()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export"""
        return {
            "has_generator": self.has_generator,
            "has_solar": self.has_solar,
            "has_battery": self.has_battery,
            "has_microinverters": self.has_microinverters,
            "has_inverters": self.has_inverters,
            "has_electrical": self.has_electrical,
            "has_hvac": self.has_hvac,
            "has_roofing": self.has_roofing,
            "has_plumbing": self.has_plumbing,
            "is_commercial": self.is_commercial,
            "is_residential": self.is_residential,
            "is_gc": self.is_gc,
            "is_sub": self.is_sub,
            "has_om_capability": self.has_om_capability,
            "is_mep_r_contractor": self.is_mep_r_contractor,
            "oem_certifications": list(self.oem_certifications),
            "generator_oems": list(self.generator_oems),
            "battery_oems": list(self.battery_oems),
            "microinverter_oems": list(self.microinverter_oems),
            "inverter_oems": list(self.inverter_oems),
            "capability_count": self.get_capability_count(),
        }
    
    def get_capability_count(self) -> int:
        """Count total number of capabilities (for scoring)"""
        capabilities = [
            self.has_generator, self.has_solar, self.has_battery,
            self.has_microinverters, self.has_inverters,
            self.has_electrical, self.has_hvac, self.has_roofing,
            self.has_plumbing
        ]
        return sum(1 for cap in capabilities if cap)
    
    def get_product_capabilities(self) -> List[str]:
        """Get list of product installation capabilities"""
        products = []
        if self.has_generator: products.append("Generator")
        if self.has_solar: products.append("Solar")
        if self.has_battery: products.append("Battery")
        if self.has_microinverters: products.append("Microinverters")
        if self.has_inverters: products.append("Inverters")
        return products
    
    def get_trade_capabilities(self) -> List[str]:
        """Get list of trade capabilities"""
        trades = []
        if self.has_electrical: trades.append("Electrical")
        if self.has_hvac: trades.append("HVAC")
        if self.has_roofing: trades.append("Roofing")
        if self.has_plumbing: trades.append("Plumbing")
        return trades

    def detect_high_value_contractor_types(self, dealer_name: str, certifications: List[str], tier: str) -> None:
        """
        Detect O&M and MEP+R contractor types from dealer data.

        **O&M (Operations & Maintenance)** contractors manage complex energy portfolios:
        - Keywords: "operations", "maintenance", "service", "monitoring", "O&M"
        - High value: They manage ongoing systems, perfect for Coperniq's monitoring platform

        **MEP+R (Mechanical, Electrical, Plumbing, Roofing)** self-performing contractors:
        - Have ALL four trade capabilities: electrical + HVAC + plumbing + roofing
        - OR keywords: "MEP", "mechanical contractor", "full-service"
        - 10x value: Can handle complex installations end-to-end without subcontractors

        Args:
            dealer_name: Company name
            certifications: List of certifications
            tier: OEM tier (Premier, Platinum, etc.)
        """
        # Convert to lowercase for case-insensitive matching
        search_text = f"{dealer_name} {' '.join(certifications)} {tier}".lower()

        # O&M Detection
        om_keywords = ["operations", "maintenance", "service", "monitoring", "o&m", "o & m"]
        self.has_om_capability = any(keyword in search_text for keyword in om_keywords)

        # MEP+R Detection (two methods)
        # Method 1: Has all four trade capabilities
        has_all_mep_r_trades = (
            self.has_electrical and
            self.has_hvac and
            self.has_plumbing and
            self.has_roofing
        )

        # Method 2: Has MEP keywords
        mep_keywords = ["mep", "mechanical contractor", "full-service", "multi-trade"]
        has_mep_keywords = any(keyword in search_text for keyword in mep_keywords)

        self.is_mep_r_contractor = has_all_mep_r_trades or has_mep_keywords


@dataclass
class StandardizedDealer:
    """
    Standardized dealer data structure across all OEM networks.
    
    This ensures consistent data format regardless of which OEM scraper extracted it.
    Used by multi-OEM cross-reference detector and lead scoring system.
    """
    # Core identification
    name: str
    phone: str
    domain: str
    website: str
    
    # Location
    street: str
    city: str
    state: str
    zip: str
    address_full: str
    
    # Quality signals
    rating: float = 0.0
    review_count: int = 0
    
    # OEM-specific tier/designation
    tier: str = "Standard"
    certifications: List[str] = field(default_factory=list)
    
    # Distance from search ZIP
    distance: str = ""
    distance_miles: float = 0.0
    
    # Capabilities (detected from OEM data)
    capabilities: DealerCapabilities = field(default_factory=DealerCapabilities)
    
    # OEM source
    oem_source: str = ""  # "Generac", "Tesla", "Enphase"
    scraped_from_zip: str = ""
    
    # Enrichment fields (populated later)
    apollo_enriched: bool = False
    employee_count: Optional[int] = None
    estimated_revenue: Optional[str] = None
    linkedin_url: Optional[str] = None
    
    # Coperniq scoring fields (populated by lead scorer)
    coperniq_score: Optional[int] = None
    multi_oem_score: Optional[int] = None
    srec_state_priority: Optional[str] = None
    itc_urgency: Optional[str] = None

    # GTM/Marketing fields for targeted campaigns
    seo_keywords: str = ""            # SEO keywords for organic search targeting
    adwords_keywords: str = ""        # Google AdWords keywords for PPC campaigns
    linkedin_search_query: str = ""   # LinkedIn Sales Navigator search query
    meta_ads_targeting: str = ""      # Meta (Facebook/Instagram) ads targeting parameters
    meta_custom_audience: str = ""    # Meta custom audience category for upload

    # MEP+R (Mechanical, Electrical, Plumbing + Renewables) tracking
    is_mep_contractor: bool = False   # Has MEP capabilities
    is_self_performing: bool = False  # Actually does the work (not just sales)
    mep_score: int = 0                # 0-100 score for MEP+R capabilities

    # O&M and Resimercial tracking (high-value targets)
    has_ops_maintenance: bool = False # Offers O&M services (recurring revenue)
    is_resimercial: bool = False     # Does both residential AND commercial (diverse portfolio)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export"""
        return {
            "name": self.name,
            "phone": self.phone,
            "domain": self.domain,
            "website": self.website,
            "street": self.street,
            "city": self.city,
            "state": self.state,
            "zip": self.zip,
            "address_full": self.address_full,
            "rating": self.rating,
            "review_count": self.review_count,
            "tier": self.tier,
            "certifications": self.certifications,
            "distance": self.distance,
            "distance_miles": self.distance_miles,
            "capabilities": self.capabilities.to_dict() if hasattr(self.capabilities, 'to_dict') else self.capabilities,
            "oem_source": self.oem_source,
            "scraped_from_zip": self.scraped_from_zip,
            "apollo_enriched": self.apollo_enriched,
            "employee_count": self.employee_count,
            "estimated_revenue": self.estimated_revenue,
            "linkedin_url": self.linkedin_url,
            "coperniq_score": self.coperniq_score,
            "multi_oem_score": self.multi_oem_score,
            "srec_state_priority": self.srec_state_priority,
            "itc_urgency": self.itc_urgency,
            "seo_keywords": self.seo_keywords,
            "adwords_keywords": self.adwords_keywords,
            "linkedin_search_query": self.linkedin_search_query,
            "meta_ads_targeting": self.meta_ads_targeting,
            "meta_custom_audience": self.meta_custom_audience,
            "is_mep_contractor": self.is_mep_contractor,
            "is_self_performing": self.is_self_performing,
            "mep_score": self.mep_score,
            "has_ops_maintenance": self.has_ops_maintenance,
            "is_resimercial": self.is_resimercial,
        }


class BaseDealerScraper(ABC):
    """
    Abstract base class for all OEM dealer network scrapers.
    
    Each OEM scraper (Generac, Tesla, Enphase, etc.) inherits from this
    and implements OEM-specific extraction logic while maintaining
    standardized data output format.
    
    Supports multiple execution modes:
    - PLAYWRIGHT: Local MCP Playwright tools (manual workflow)
    - RUNPOD: RunPod serverless Playwright API (automated)
    - BROWSERBASE: Browserbase cloud (future)
    """
    
    # OEM-specific constants (must be overridden by subclasses)
    OEM_NAME: str = None  # "Generac", "Tesla", "Enphase"
    DEALER_LOCATOR_URL: str = None
    PRODUCT_LINES: List[str] = []  # ["Generator", "Solar", "Battery"]
    
    def __init__(self, mode: ScraperMode = ScraperMode.PLAYWRIGHT):
        """
        Initialize scraper with execution mode.
        
        Args:
            mode: ScraperMode enum (PLAYWRIGHT, RUNPOD, or BROWSERBASE)
        """
        self.mode = mode
        self.dealers: List[StandardizedDealer] = []
        
        # Validate OEM-specific constants are set
        if self.OEM_NAME is None:
            raise ValueError(f"{self.__class__.__name__} must set OEM_NAME class variable")
        if self.DEALER_LOCATOR_URL is None:
            raise ValueError(f"{self.__class__.__name__} must set DEALER_LOCATOR_URL class variable")
    
    @abstractmethod
    def get_extraction_script(self) -> str:
        """
        Return JavaScript extraction script for browser evaluation.
        
        This is the core logic that runs in-browser to extract dealer data
        from the OEM's dealer locator page. Each OEM has different DOM structure.
        
        Returns:
            JavaScript function as string that returns array of dealer objects
        """
        pass
    
    @abstractmethod
    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect contractor capabilities from OEM dealer data.
        
        Each OEM provides different signals about what the dealer can do:
        - Generac: Generator tier (Premier = full service)
        - Tesla: Powerwall certified = battery + electrical
        - Enphase: Microinverter certified = solar + electrical
        
        Args:
            raw_dealer_data: Raw dealer dict from extraction script
        
        Returns:
            DealerCapabilities object with detected capabilities
        """
        pass
    
    @abstractmethod
    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw dealer data from extraction script to StandardizedDealer format.
        
        This normalizes different OEM data structures into consistent format
        for multi-OEM cross-referencing and scoring.
        
        Args:
            raw_dealer_data: Raw dealer dict from extraction script
            zip_code: ZIP code that was searched
        
        Returns:
            StandardizedDealer object
        """
        pass
    
    def scrape_zip_code(self, zip_code: str) -> List[StandardizedDealer]:
        """
        Scrape dealers for a single ZIP code.
        
        Execution varies by mode:
        - PLAYWRIGHT: Prints manual MCP instructions
        - RUNPOD: Makes HTTP request to serverless API
        - BROWSERBASE: Cloud browser automation
        - PATCHRIGHT: Stealth mode with bot detection bypass
        
        Args:
            zip_code: 5-digit ZIP code to search
        
        Returns:
            List of StandardizedDealer objects
        """
        if self.mode == ScraperMode.PLAYWRIGHT:
            return self._scrape_with_playwright(zip_code)
        elif self.mode == ScraperMode.RUNPOD:
            return self._scrape_with_runpod(zip_code)
        elif self.mode == ScraperMode.BROWSERBASE:
            return self._scrape_with_browserbase(zip_code)
        elif self.mode == ScraperMode.PATCHRIGHT:
            return self._scrape_with_patchright(zip_code)
        else:
            raise ValueError(f"Unknown scraper mode: {self.mode}")
    
    def scrape_multiple(
        self,
        zip_codes: List[str],
        verbose: bool = True,
        checkpoint_interval: int = 25,
        checkpoint_dir: Optional[str] = None
    ) -> List[StandardizedDealer]:
        """
        Scrape dealers from multiple ZIP codes with automatic checkpoint saving.

        Args:
            zip_codes: List of ZIP codes to scrape
            verbose: Print progress messages
            checkpoint_interval: Save checkpoint every N ZIP codes (default: 25)
            checkpoint_dir: Override default checkpoint directory

        Returns:
            List of all dealers collected
        """
        all_dealers = []
        failed_zips = []

        # Setup checkpoint directory
        if checkpoint_dir is None:
            oem_name_lower = self.OEM_NAME.lower().replace(" ", "_")
            checkpoint_dir = f"output/oem_data/{oem_name_lower}"

        Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)

        # Setup logging
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"{checkpoint_dir}/{oem_name_lower}_run_{timestamp}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

        logging.info(f"Starting {self.OEM_NAME} scraper with {len(zip_codes)} ZIP codes")

        # Main scraping loop
        for i, zip_code in enumerate(zip_codes, 1):
            if verbose:
                print(f"\n[{i}/{len(zip_codes)}] Scraping {self.OEM_NAME} dealers for ZIP {zip_code}...")

            logging.info(f"[{i}/{len(zip_codes)}] ZIP {zip_code}: Starting")

            try:
                dealers = self.scrape_zip_code(zip_code)
                all_dealers.extend(dealers)

                logging.info(f"[{i}/{len(zip_codes)}] ZIP {zip_code}: Found {len(dealers)} dealers")

                if verbose:
                    print(f"  ✓ Found {len(dealers)} dealers")

            except Exception as e:
                logging.error(f"[{i}/{len(zip_codes)}] ZIP {zip_code}: ERROR - {str(e)}")
                failed_zips.append(zip_code)

                if verbose:
                    print(f"  ✗ Error: {str(e)}")

            # Save checkpoint every N zips or at end
            if (i % checkpoint_interval == 0) or (i == len(zip_codes)):
                self._save_checkpoint(
                    checkpoint_dir=checkpoint_dir,
                    checkpoint_number=i,
                    all_dealers=all_dealers,
                    completed_zips=i,
                    total_zips=len(zip_codes),
                    failed_zips=failed_zips,
                    verbose=verbose
                )

        self.dealers = all_dealers
        logging.info(f"Completed: {len(all_dealers)} dealers total, {len(failed_zips)} failed ZIPs")

        return all_dealers

    def _save_checkpoint(
        self,
        checkpoint_dir: str,
        checkpoint_number: int,
        all_dealers: List[StandardizedDealer],
        completed_zips: int,
        total_zips: int,
        failed_zips: List[str],
        verbose: bool = True
    ) -> None:
        """
        Save checkpoint files (.json and .log) with dealer data and metadata.

        Args:
            checkpoint_dir: Directory to save checkpoint files
            checkpoint_number: Current ZIP index (for filename)
            all_dealers: List of StandardizedDealer objects collected so far
            completed_zips: Number of ZIPs processed
            total_zips: Total ZIPs to process
            failed_zips: List of ZIP codes that errored
            verbose: Whether to print status messages
        """
        # Track started_at timestamp (store as instance variable on first call)
        if not hasattr(self, '_scrape_started_at'):
            self._scrape_started_at = datetime.now().isoformat()

        # Deduplicate dealers before saving
        seen_phones = set()
        seen_domains = set()
        seen_names_by_state = {}
        unique_dealers = []

        for dealer in all_dealers:
            is_duplicate = False

            # Phone match
            if dealer.phone and dealer.phone in seen_phones:
                is_duplicate = True
            # Domain match
            elif dealer.domain and dealer.domain in seen_domains:
                is_duplicate = True
            # Fuzzy name + same state
            elif dealer.name and dealer.state:
                normalized_name = self._normalize_company_name(dealer.name)
                if dealer.state in seen_names_by_state:
                    for existing_norm_name, _ in seen_names_by_state[dealer.state]:
                        similarity = SequenceMatcher(None, normalized_name, existing_norm_name).ratio()
                        if similarity >= 0.85:
                            is_duplicate = True
                            break

            if not is_duplicate:
                unique_dealers.append(dealer)
                if dealer.phone:
                    seen_phones.add(dealer.phone)
                if dealer.domain:
                    seen_domains.add(dealer.domain)
                if dealer.name and dealer.state:
                    normalized_name = self._normalize_company_name(dealer.name)
                    if dealer.state not in seen_names_by_state:
                        seen_names_by_state[dealer.state] = []
                    seen_names_by_state[dealer.state].append((normalized_name, dealer))

        # Prepare checkpoint filename base
        oem_name_lower = self.OEM_NAME.lower().replace(" ", "_")
        checkpoint_base = f"{checkpoint_dir}/{oem_name_lower}_checkpoint_{checkpoint_number:04d}"

        # Save JSON checkpoint file
        json_file = f"{checkpoint_base}.json"
        checkpoint_data = {
            "oem_name": self.OEM_NAME,
            "started_at": self._scrape_started_at,
            "last_updated": datetime.now().isoformat(),
            "total_zips": total_zips,
            "completed_zips": completed_zips,
            "failed_zips": failed_zips,
            "total_dealers": len(all_dealers),
            "dealers_after_dedup": len(unique_dealers),
            "checkpoint_number": checkpoint_number,
            "status": "in_progress" if completed_zips < total_zips else "completed",
            "dealers": [dealer.to_dict() for dealer in unique_dealers]
        }

        try:
            # Save JSON checkpoint file
            with open(json_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)

            # Save checkpoint log file
            log_file = f"{checkpoint_base}.log"
            with open(log_file, 'w') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting {self.OEM_NAME} scraper with {total_zips} ZIP codes\n")
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] CHECKPOINT: Saved {checkpoint_number} zips, {len(all_dealers)} dealers total\n")
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checkpoint saved to: {oem_name_lower}_checkpoint_{checkpoint_number:04d}.json\n")
                f.write(f"\n")
                f.write(f"Progress: {completed_zips}/{total_zips} ZIPs ({100*completed_zips/total_zips:.1f}%)\n")
                f.write(f"Total dealers: {len(all_dealers)}\n")
                f.write(f"After dedup: {len(unique_dealers)}\n")
                f.write(f"Failed ZIPs: {len(failed_zips)}\n")
                if failed_zips:
                    f.write(f"Failed ZIP codes: {', '.join(failed_zips)}\n")

            # Log checkpoint confirmation
            logging.info(f"CHECKPOINT: Saved {checkpoint_number} zips, {len(all_dealers)} dealers total")
            logging.info(f"Checkpoint saved to: {json_file}")

            # Print if verbose
            if verbose:
                print(f"\n  Checkpoint saved: {checkpoint_number} zips, {len(all_dealers)} dealers ({len(unique_dealers)} after dedup)")
                print(f"     Saved to: {json_file}")

        except (IOError, OSError) as e:
            # Log error but don't crash - allow scraping to continue
            logging.error(f"CHECKPOINT FAILED: Unable to save checkpoint {checkpoint_number}: {str(e)}")
            if verbose:
                print(f"\n  Warning: Checkpoint save failed: {str(e)}")
            # Continue scraping - don't crash

    def deduplicate(self, key: str = "phone") -> None:
        """
        Remove duplicate dealers based on key field (usually phone number).
        
        Args:
            key: Field to use for deduplication (default: "phone")
        """
        seen = set()
        unique_dealers = []
        
        for dealer in self.dealers:
            key_value = getattr(dealer, key)
            if key_value and key_value not in seen:
                seen.add(key_value)
                unique_dealers.append(dealer)
        
        removed = len(self.dealers) - len(unique_dealers)
        print(f"Removed {removed} duplicate dealers (by {key})")
        self.dealers = unique_dealers

    @staticmethod
    def _normalize_company_name(name: str) -> str:
        """
        Normalize company name for fuzzy matching.
        Removes common suffixes (LLC, Inc, Corp, etc.), lowercases, strips whitespace.
        """
        if not name:
            return ""

        # Convert to lowercase
        normalized = name.lower().strip()

        # Remove common business suffixes
        suffixes = [
            r'\s+llc\s*$', r'\s+inc\.?\s*$', r'\s+corp\.?\s*$',
            r'\s+ltd\.?\s*$', r'\s+co\.?\s*$', r'\s+company\s*$',
            r'\s+incorporated\s*$', r'\s+corporation\s*$',
            r'\s+limited\s*$', r'\s+l\.?l\.?c\.?\s*$'
        ]

        for suffix in suffixes:
            normalized = re.sub(suffix, '', normalized)

        # Remove extra whitespace
        normalized = ' '.join(normalized.split())

        return normalized

    def deduplicate_by_phone(self) -> None:
        """
        Multi-signal deduplication using phone, name fuzzy matching, domain, and location.

        This catches duplicates missed by phone-only matching, like:
        - Same company with multiple locations/phone numbers
        - Name variations (e.g., "TRI-STATE POWER & PUMP" vs "TRI-STATE POWER & PUMP LLC")
        - Same domain but different phone numbers

        Deduplication signals (in order of precedence):
        1. Phone number (exact match after normalization)
        2. Domain (exact match)
        3. Fuzzy name match (>=85% similar) + same state
        """
        seen_phones = set()
        seen_domains = set()
        seen_names_by_state = {}  # {state: [(normalized_name, dealer), ...]}
        unique_dealers = []
        duplicates = []

        for dealer in self.dealers:
            is_duplicate = False
            duplicate_reason = ""

            # Signal 1: Phone match
            if dealer.phone and dealer.phone in seen_phones:
                is_duplicate = True
                duplicate_reason = f"phone={dealer.phone}"

            # Signal 2: Domain match (if not already marked duplicate)
            elif dealer.domain and dealer.domain in seen_domains:
                is_duplicate = True
                duplicate_reason = f"domain={dealer.domain}"

            # Signal 3: Fuzzy name + same state
            elif dealer.name and dealer.state:
                normalized_name = self._normalize_company_name(dealer.name)

                # Check against existing names in same state
                if dealer.state in seen_names_by_state:
                    for existing_norm_name, existing_dealer in seen_names_by_state[dealer.state]:
                        similarity = SequenceMatcher(None, normalized_name, existing_norm_name).ratio()

                        # 85% similarity threshold for same state
                        if similarity >= 0.85:
                            is_duplicate = True
                            duplicate_reason = f"fuzzy_name={similarity:.2f} ('{dealer.name}' ≈ '{existing_dealer.name}')"
                            break

            if is_duplicate:
                duplicates.append((dealer, duplicate_reason))
            else:
                # Add to unique list and tracking sets
                unique_dealers.append(dealer)

                if dealer.phone:
                    seen_phones.add(dealer.phone)

                if dealer.domain:
                    seen_domains.add(dealer.domain)

                if dealer.name and dealer.state:
                    normalized_name = self._normalize_company_name(dealer.name)
                    if dealer.state not in seen_names_by_state:
                        seen_names_by_state[dealer.state] = []
                    seen_names_by_state[dealer.state].append((normalized_name, dealer))

        removed = len(self.dealers) - len(unique_dealers)

        # Show breakdown of deduplication signals
        print(f"\nRemoved {removed} duplicate dealers (multi-signal deduplication):")
        phone_dupes = len([d for d, reason in duplicates if reason.startswith("phone=")])
        domain_dupes = len([d for d, reason in duplicates if reason.startswith("domain=")])
        fuzzy_dupes = len([d for d, reason in duplicates if reason.startswith("fuzzy_name=")])

        print(f"  • Phone matches: {phone_dupes}")
        print(f"  • Domain matches: {domain_dupes}")
        print(f"  • Fuzzy name + state matches: {fuzzy_dupes}")

        # Show examples of fuzzy matches (up to 5)
        if fuzzy_dupes > 0:
            print(f"\n  Examples of fuzzy name matches:")
            fuzzy_examples = [d for d, reason in duplicates if reason.startswith("fuzzy_name=")][:5]
            for dealer, reason in [(d, r) for d, r in duplicates if r.startswith("fuzzy_name=")][:5]:
                print(f"    - {reason}")

        self.dealers = unique_dealers

    def filter_by_state(self, states: List[str]) -> List[StandardizedDealer]:
        """
        Filter dealers to specific states (useful for SREC targeting).
        
        Args:
            states: List of 2-letter state codes (e.g., ["CA", "TX", "PA"])
        
        Returns:
            Filtered list of dealers
        """
        return [d for d in self.dealers if d.state in states]
    
    def get_top_rated(self, min_reviews: int = 5, limit: int = 10) -> List[StandardizedDealer]:
        """
        Get top-rated dealers with minimum review threshold.
        
        Args:
            min_reviews: Minimum number of reviews required
            limit: Maximum number of dealers to return
        
        Returns:
            List of top-rated dealers sorted by rating
        """
        qualified = [d for d in self.dealers if d.review_count >= min_reviews]
        sorted_dealers = sorted(qualified, key=lambda d: d.rating, reverse=True)
        return sorted_dealers[:limit]
    
    @abstractmethod
    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Print manual MCP tool instructions.
        
        Each OEM scraper must implement this with their specific workflow.
        """
        pass
    
    @abstractmethod
    def _scrape_with_runpod(self, zip_code: str) -> List[StandardizedDealer]:
        """
        RUNPOD mode: Make HTTP request to serverless API.
        
        Each OEM scraper must implement this with their specific workflow.
        """
        pass
    
    @abstractmethod
    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PATCHRIGHT mode: Stealth browser automation with bot detection bypass.
        
        Each OEM scraper must implement this with their specific workflow.
        Uses Patchright library for patched automation fingerprints.
        """
        pass
    
    def _scrape_with_browserbase(self, zip_code: str) -> List[StandardizedDealer]:
        """
        BROWSERBASE mode: Cloud browser automation (future implementation).
        """
        raise NotImplementedError("Browserbase mode not yet implemented")
    
    def save_json(self, filepath: str) -> None:
        """
        Save dealers to JSON file.
        
        Args:
            filepath: Path to output JSON file
        """
        import json
        import os
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        data = [d.to_dict() for d in self.dealers]
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved {len(self.dealers)} dealers to {filepath}")
    
    def save_csv(self, filepath: str) -> None:
        """
        Save dealers to CSV file.
        
        Args:
            filepath: Path to output CSV file
        """
        import csv
        import os
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        if not self.dealers:
            print("No dealers to save")
            return
        
        # Flatten nested capabilities into columns
        fieldnames = [
            "oem_source", "name", "phone", "website", "domain",
            "street", "city", "state", "zip", "address_full",
            "rating", "review_count", "tier", "certifications",
            "distance", "distance_miles", "scraped_from_zip",
            "has_generator", "has_solar", "has_battery",
            "has_microinverters", "has_inverters",
            "has_electrical", "has_hvac", "has_roofing", "has_plumbing",
            "is_commercial", "is_residential", "is_gc", "is_sub",
            "capability_count", "oem_certifications",
            "generator_oems", "battery_oems", "microinverter_oems", "inverter_oems",
            "apollo_enriched", "employee_count", "estimated_revenue", "linkedin_url",
            "coperniq_score", "multi_oem_score",
            "srec_state_priority", "itc_urgency",
            # ICP & Marketing enrichment fields
            "is_resimercial", "is_mep_contractor", "is_mep_r_contractor", "is_self_performing",
            "has_ops_maintenance", "has_om_capability", "mep_score",
            "linkedin_search_query", "meta_custom_audience", "meta_ads_targeting",
            "seo_keywords", "adwords_keywords",
        ]
        
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for dealer in self.dealers:
                row = dealer.to_dict()
                # Flatten capabilities
                caps = row.pop("capabilities")
                row.update(caps)
                # Convert lists to strings
                row["certifications"] = ", ".join(row.get("certifications", []))
                row["oem_certifications"] = ", ".join(row.get("oem_certifications", []))
                row["generator_oems"] = ", ".join(row.get("generator_oems", []))
                row["battery_oems"] = ", ".join(row.get("battery_oems", []))
                row["microinverter_oems"] = ", ".join(row.get("microinverter_oems", []))
                row["inverter_oems"] = ", ".join(row.get("inverter_oems", []))
                writer.writerow(row)
        
        print(f"Saved {len(self.dealers)} dealers to {filepath}")
