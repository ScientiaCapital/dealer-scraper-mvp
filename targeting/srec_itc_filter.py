"""
SREC State Filter & ITC Urgency Tagger

Filters contractors to SREC (Solar Renewable Energy Credit) states and tags with ITC urgency.

Business Context:
- SREC states have sustainable solar incentive programs (unlike federal ITC which is expiring)
- Federal ITC deadlines creating time-sensitive sales opportunities:
  * Residential ITC: Ends December 31, 2025
  * Commercial Safe Harbor: Projects must start by June 30, 2026
- SREC programs continue after federal ITC expires = long-term sustainable market

Priority States:
- HIGH: CA, TX, PA, MA, NJ, FL (primary focus - large markets + strong SREC programs)
- MEDIUM: Other states with SREC or similar programs (OH, MD, DC, etc.)

This creates urgency-based messaging for Coperniq's sales outreach targeting contractors
in high-value territories with time-sensitive ITC opportunities.
"""

from typing import List, Dict, Optional
from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass
from scrapers.base_scraper import StandardizedDealer
from analysis.multi_oem_detector import MultiOEMMatch


class SRECPriority(Enum):
    """Priority level for SREC state markets"""
    HIGH = "HIGH"      # Primary focus states (large market + strong SREC)
    MEDIUM = "MEDIUM"  # Secondary states (smaller market or developing SREC)
    LOW = "LOW"        # Minimal/no SREC program


class ITCUrgency(Enum):
    """ITC deadline urgency level"""
    CRITICAL = "CRITICAL"  # Commercial projects - must start by June 2026
    HIGH = "HIGH"          # Residential projects - ends Dec 2025
    MEDIUM = "MEDIUM"      # SREC states - sustainable post-ITC
    LOW = "LOW"            # Non-SREC states - lower priority post-ITC


# SREC State Database
# Source: DSIRE (Database of State Incentives for Renewables & Efficiency)
SREC_STATES = {
    # HIGH PRIORITY - Primary focus for Coperniq
    "CA": {
        "name": "California",
        "program": "SGIP + NEM 3.0",
        "description": "Self-Generation Incentive Program for batteries, Net Energy Metering 3.0 for solar",
        "priority": SRECPriority.HIGH,
        "notes": "Largest market, storage incentives remain strong, high permit volume",
    },
    "TX": {
        "name": "Texas",
        "program": "Deregulated Market + ERCOT",
        "description": "Deregulated energy market with ERCOT arbitrage opportunities",
        "priority": SRECPriority.HIGH,
        "notes": "Huge commercial market, energy reliability concerns drive demand",
    },
    "PA": {
        "name": "Pennsylvania",
        "program": "PA Solar Renewable Energy Credits (SRECs)",
        "description": "Active SREC trading market for solar production",
        "priority": SRECPriority.HIGH,
        "notes": "Established SREC market, strong commercial opportunities",
    },
    "MA": {
        "name": "Massachusetts",
        "program": "SREC II + SMART Program",
        "description": "Solar Massachusetts Renewable Target (SMART) incentive program",
        "priority": SRECPriority.HIGH,
        "notes": "Wealthy market, high electricity rates, strong residential + commercial",
    },
    "NJ": {
        "name": "New Jersey",
        "program": "NJ Transition Renewable Energy Certificates (TRECs)",
        "description": "Successor to SREC program, strong battery incentives",
        "priority": SRECPriority.HIGH,
        "notes": "High electricity costs, aggressive clean energy goals",
    },
    "FL": {
        "name": "Florida",
        "program": "Net Metering + Property Tax Exemptions",
        "description": "Net metering for solar, property tax exemptions for solar installations",
        "priority": SRECPriority.HIGH,
        "notes": "Large population, hurricane backup power demand, no state income tax",
    },
    
    # MEDIUM PRIORITY - Secondary focus
    "OH": {
        "name": "Ohio",
        "program": "OH Solar Renewable Energy Credits",
        "description": "SREC program for solar generation",
        "priority": SRECPriority.MEDIUM,
        "notes": "Established market, moderate incentives",
    },
    "MD": {
        "name": "Maryland",
        "program": "MD Solar Renewable Energy Credits",
        "description": "Active SREC trading market",
        "priority": SRECPriority.MEDIUM,
        "notes": "Strong residential market, proximity to DC",
    },
    "DC": {
        "name": "District of Columbia",
        "program": "DC Solar Renewable Energy Credits",
        "description": "High-value SREC market",
        "priority": SRECPriority.MEDIUM,
        "notes": "Wealthy market, high SREC values",
    },
    "DE": {
        "name": "Delaware",
        "program": "DE Solar Renewable Energy Credits",
        "description": "SREC program for solar",
        "priority": SRECPriority.MEDIUM,
        "notes": "Small but established market",
    },
    "NH": {
        "name": "New Hampshire",
        "program": "NH Renewable Energy Fund",
        "description": "Rebates for solar + storage",
        "priority": SRECPriority.MEDIUM,
        "notes": "Growing market, high electricity rates",
    },
    "RI": {
        "name": "Rhode Island",
        "program": "RI Renewable Energy Growth Program",
        "description": "Performance-based incentives for solar",
        "priority": SRECPriority.MEDIUM,
        "notes": "Small but strong market",
    },
    "CT": {
        "name": "Connecticut",
        "program": "CT Zonal Solar Renewable Energy Credits",
        "description": "Zonal SREC program",
        "priority": SRECPriority.MEDIUM,
        "notes": "Wealthy market, high electricity rates",
    },
    "IL": {
        "name": "Illinois",
        "program": "IL Adjustable Block Program",
        "description": "Performance-based incentives through Adjustable Block Program",
        "priority": SRECPriority.MEDIUM,
        "notes": "Large market, strong commercial opportunities",
    },
}

# Federal ITC Deadlines
ITC_RESIDENTIAL_DEADLINE = date(2025, 12, 31)  # Residential ITC ends Dec 31, 2025
ITC_COMMERCIAL_SAFE_HARBOR = date(2026, 6, 30)  # Commercial must start by June 30, 2026


@dataclass
class SRECFilterResult:
    """Result of SREC state filtering with ITC urgency tagging"""
    
    # Filtered contractors
    contractors: List  # List[StandardizedDealer] or List[MultiOEMMatch]
    
    # SREC state priority distribution
    high_priority_count: int
    medium_priority_count: int
    
    # ITC urgency distribution
    critical_urgency_count: int
    high_urgency_count: int
    medium_urgency_count: int
    
    # Statistics
    total_count: int
    srec_states_represented: List[str]
    
    def summary(self) -> str:
        """Generate human-readable summary"""
        lines = [
            f"\nSREC State Filter Results:",
            f"="*60,
            f"Total contractors in SREC states: {self.total_count}",
            f"",
            f"Priority Distribution:",
            f"  HIGH priority states: {self.high_priority_count}",
            f"  MEDIUM priority states: {self.medium_priority_count}",
            f"",
            f"ITC Urgency Distribution:",
            f"  CRITICAL (commercial deadline Q2 2026): {self.critical_urgency_count}",
            f"  HIGH (residential deadline Dec 2025): {self.high_urgency_count}",
            f"  MEDIUM (SREC sustainable post-ITC): {self.medium_urgency_count}",
            f"",
            f"States Represented: {', '.join(sorted(self.srec_states_represented))}",
            f"="*60,
        ]
        return "\n".join(lines)


class SRECITCFilter:
    """
    Filters contractors to SREC states and tags with ITC urgency.
    
    Usage:
        filter = SRECITCFilter()
        result = filter.filter_contractors(all_contractors)
        print(result.summary())
        filter.export_results(result, "output/srec_contractors.csv")
    """
    
    def __init__(self):
        """Initialize filter with SREC state database"""
        self.srec_states = SREC_STATES
        self.residential_itc_deadline = ITC_RESIDENTIAL_DEADLINE
        self.commercial_safe_harbor = ITC_COMMERCIAL_SAFE_HARBOR
        self.today = date.today()
    
    def is_srec_state(self, state_code: str) -> bool:
        """
        Check if state has SREC or similar incentive program.
        
        Args:
            state_code: 2-letter state code (e.g., "CA", "TX")
        
        Returns:
            True if state has SREC/similar program
        """
        return state_code.upper() in self.srec_states
    
    def get_srec_priority(self, state_code: str) -> Optional[SRECPriority]:
        """
        Get SREC priority level for state.
        
        Args:
            state_code: 2-letter state code
        
        Returns:
            SRECPriority enum or None if not SREC state
        """
        state_info = self.srec_states.get(state_code.upper())
        return state_info["priority"] if state_info else None
    
    def calculate_itc_urgency(
        self,
        state_code: str,
        is_commercial: bool = False,
        reference_date: Optional[date] = None
    ) -> ITCUrgency:
        """
        Calculate ITC urgency based on deadlines and contractor type.
        
        Logic:
        - Commercial contractors + < 12 months to safe harbor deadline = CRITICAL
        - Residential contractors + < 6 months to residential deadline = HIGH
        - SREC state contractors (sustainable post-ITC) = MEDIUM
        - Non-SREC state contractors = LOW
        
        Args:
            state_code: 2-letter state code
            is_commercial: Whether contractor does commercial work
            reference_date: Date to calculate from (default: today)
        
        Returns:
            ITCUrgency enum
        """
        ref_date = reference_date or self.today
        
        # Check if SREC state
        is_srec = self.is_srec_state(state_code)
        
        # Calculate days until deadlines
        days_to_commercial = (self.commercial_safe_harbor - ref_date).days
        days_to_residential = (self.residential_itc_deadline - ref_date).days
        
        # Commercial contractors approaching safe harbor deadline
        if is_commercial and days_to_commercial <= 365 and days_to_commercial > 0:
            return ITCUrgency.CRITICAL
        
        # Residential contractors approaching ITC expiration
        if not is_commercial and days_to_residential <= 180 and days_to_residential > 0:
            return ITCUrgency.HIGH
        
        # SREC states = sustainable market post-ITC
        if is_srec:
            return ITCUrgency.MEDIUM
        
        # Non-SREC states = lower priority
        return ITCUrgency.LOW
    
    def get_urgency_messaging(self, urgency: ITCUrgency, state_code: str) -> str:
        """
        Generate urgency-based sales messaging for outreach.
        
        Args:
            urgency: ITCUrgency enum
            state_code: 2-letter state code
        
        Returns:
            Urgency messaging string for sales outreach
        """
        state_info = self.srec_states.get(state_code.upper(), {})
        state_name = state_info.get("name", state_code)
        program = state_info.get("program", "state incentives")
        
        if urgency == ITCUrgency.CRITICAL:
            return (
                f"⚠️ CRITICAL: Commercial ITC safe harbor deadline June 30, 2026. "
                f"Projects must start by Q2 2026 to claim 30% federal tax credit. "
                f"{state_name}'s {program} provides additional value beyond federal ITC."
            )
        
        elif urgency == ITCUrgency.HIGH:
            return (
                f"🔥 URGENT: Residential ITC expires December 31, 2025. "
                f"Your customers have <6 months to claim 30% federal tax credit. "
                f"{state_name}'s {program} continues post-ITC."
            )
        
        elif urgency == ITCUrgency.MEDIUM:
            return (
                f"✅ SUSTAINABLE: {state_name}'s {program} continues after federal ITC expires. "
                f"Your market remains strong post-2025/2026."
            )
        
        else:  # LOW
            return (
                f"Federal ITC is expiring. Consider expanding to SREC states for "
                f"sustainable post-ITC market opportunities."
            )
    
    def filter_contractors(
        self,
        contractors: List,
        min_priority: Optional[SRECPriority] = None,
        include_enrichment: bool = True
    ) -> SRECFilterResult:
        """
        Filter contractors to SREC states and tag with ITC urgency.
        
        Args:
            contractors: List of StandardizedDealer or MultiOEMMatch objects
            min_priority: Minimum SREC priority (default: None = all SREC states)
            include_enrichment: Add SREC/ITC fields to contractor objects
        
        Returns:
            SRECFilterResult with filtered contractors and statistics
        """
        print(f"\n{'='*60}")
        print("SREC State Filter & ITC Urgency Tagger")
        print(f"{'='*60}\n")
        
        # Filter to SREC states
        srec_contractors = []
        
        for contractor in contractors:
            # Extract state code (handle both StandardizedDealer and MultiOEMMatch)
            if hasattr(contractor, "primary_dealer"):
                state_code = contractor.primary_dealer.state
            else:
                state_code = contractor.state
            
            # Check if SREC state
            if not self.is_srec_state(state_code):
                continue
            
            # Check priority threshold
            priority = self.get_srec_priority(state_code)
            if min_priority and priority.value != min_priority.value:
                if min_priority == SRECPriority.HIGH and priority != SRECPriority.HIGH:
                    continue
            
            # Add SREC/ITC enrichment fields
            if include_enrichment:
                # Detect if commercial (will be enhanced by Apollo enrichment later)
                is_commercial = False
                if hasattr(contractor, "primary_dealer"):
                    is_commercial = contractor.primary_dealer.capabilities.is_commercial
                elif hasattr(contractor, "capabilities"):
                    is_commercial = contractor.capabilities.is_commercial
                
                # Calculate ITC urgency
                urgency = self.calculate_itc_urgency(state_code, is_commercial)
                
                # Get SREC state info
                state_info = self.srec_states.get(state_code.upper(), {})
                
                # Add enrichment fields to contractor object
                if hasattr(contractor, "primary_dealer"):
                    contractor.primary_dealer.srec_state_priority = priority.value
                    contractor.primary_dealer.itc_urgency = urgency.value
                else:
                    contractor.srec_state_priority = priority.value
                    contractor.itc_urgency = urgency.value
                
                # Store enrichment metadata
                if not hasattr(contractor, "srec_metadata"):
                    if hasattr(contractor, "primary_dealer"):
                        contractor.srec_metadata = {
                            "state_name": state_info.get("name"),
                            "program": state_info.get("program"),
                            "priority": priority.value,
                            "urgency": urgency.value,
                            "urgency_message": self.get_urgency_messaging(urgency, state_code),
                        }
                    else:
                        contractor.srec_metadata = {
                            "state_name": state_info.get("name"),
                            "program": state_info.get("program"),
                            "priority": priority.value,
                            "urgency": urgency.value,
                            "urgency_message": self.get_urgency_messaging(urgency, state_code),
                        }
            
            srec_contractors.append(contractor)
        
        # Calculate statistics
        high_priority = sum(
            1 for c in srec_contractors
            if self.get_srec_priority(
                c.primary_dealer.state if hasattr(c, "primary_dealer") else c.state
            ) == SRECPriority.HIGH
        )
        medium_priority = len(srec_contractors) - high_priority
        
        # ITC urgency distribution
        critical_urgency = sum(
            1 for c in srec_contractors
            if hasattr(c, "srec_metadata") and c.srec_metadata["urgency"] == ITCUrgency.CRITICAL.value
        )
        high_urgency = sum(
            1 for c in srec_contractors
            if hasattr(c, "srec_metadata") and c.srec_metadata["urgency"] == ITCUrgency.HIGH.value
        )
        medium_urgency = sum(
            1 for c in srec_contractors
            if hasattr(c, "srec_metadata") and c.srec_metadata["urgency"] == ITCUrgency.MEDIUM.value
        )
        
        # States represented
        states = set()
        for c in srec_contractors:
            state = c.primary_dealer.state if hasattr(c, "primary_dealer") else c.state
            states.add(state)
        
        result = SRECFilterResult(
            contractors=srec_contractors,
            high_priority_count=high_priority,
            medium_priority_count=medium_priority,
            critical_urgency_count=critical_urgency,
            high_urgency_count=high_urgency,
            medium_urgency_count=medium_urgency,
            total_count=len(srec_contractors),
            srec_states_represented=list(states),
        )
        
        print(result.summary())
        
        return result
    
    def export_results(self, result: SRECFilterResult, filepath: str) -> None:
        """
        Export filtered contractors to CSV with SREC/ITC enrichment.
        
        Args:
            result: SRECFilterResult object
            filepath: Path to output CSV file
        """
        import csv
        import os
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        fieldnames = [
            "name", "state", "city",
            "srec_priority", "srec_program",
            "itc_urgency", "urgency_message",
            "phone", "website", "domain",
            "oem_sources",  # For MultiOEMMatch
            "multi_oem_score",  # For MultiOEMMatch
        ]
        
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for contractor in result.contractors:
                # Handle both StandardizedDealer and MultiOEMMatch
                if hasattr(contractor, "primary_dealer"):
                    dealer = contractor.primary_dealer
                    oem_sources = ", ".join(sorted(contractor.oem_sources))
                    multi_oem_score = contractor.multi_oem_score
                else:
                    dealer = contractor
                    oem_sources = dealer.oem_source
                    multi_oem_score = ""
                
                # Get SREC metadata
                metadata = contractor.srec_metadata if hasattr(contractor, "srec_metadata") else {}
                
                writer.writerow({
                    "name": dealer.name,
                    "state": dealer.state,
                    "city": dealer.city,
                    "srec_priority": metadata.get("priority", ""),
                    "srec_program": metadata.get("program", ""),
                    "itc_urgency": metadata.get("urgency", ""),
                    "urgency_message": metadata.get("urgency_message", ""),
                    "phone": dealer.phone,
                    "website": dealer.website,
                    "domain": dealer.domain,
                    "oem_sources": oem_sources,
                    "multi_oem_score": multi_oem_score,
                })
        
        print(f"\nExported {result.total_count} SREC contractors to {filepath}")


# Example usage
if __name__ == "__main__":
    from analysis.multi_oem_detector import MultiOEMDetector
    from scrapers.scraper_factory import ScraperFactory
    from scrapers.base_scraper import ScraperMode
    from config import ZIP_CODES_TEST
    
    # Scrape dealers (using SREC state ZIPs)
    CA_ZIPS = ["94102", "90210", "92037"]  # SF, Beverly Hills, La Jolla
    
    generac = ScraperFactory.create("Generac", mode=ScraperMode.RUNPOD)
    generac_dealers = generac.scrape_multiple(CA_ZIPS)
    
    # Detect multi-OEM contractors
    detector = MultiOEMDetector()
    detector.add_dealers(generac_dealers, "Generac")
    multi_oem = detector.find_multi_oem_contractors()
    
    # Filter to SREC states and tag with ITC urgency
    filter = SRECITCFilter()
    result = filter.filter_contractors(multi_oem)
    
    print(result.summary())
    
    # Export for review
    filter.export_results(result, "output/srec_contractors.csv")
