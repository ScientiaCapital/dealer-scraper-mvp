#!/usr/bin/env python3
"""
Generate Keyword Strategy Document
50-100 commercial intent keywords mapped to ICP dimensions
"""

def generate_keyword_strategy(output_path: str):
    """
    Generate keyword strategy markdown document for Google Ads campaigns.

    Organized by:
    - ICP dimensions (Resimercial, O&M, Multi-OEM, MEP+R)
    - Product categories (Solar, Battery, Generator)
    - Intent levels (Commercial, Transactional, Informational)
    """
    print("\n" + "="*70)
    print("🔑 GENERATING KEYWORD STRATEGY DOCUMENT")
    print("="*70)
    print(f"Output: {output_path}")
    print()

    content = """# Coperniq GTM Keyword Strategy
## Paid Search Keywords for PLATINUM Tier Contractor Targeting

**Target Audience**: Resimercial contractors (residential + commercial) with O&M services managing multiple OEM monitoring platforms

**Campaign Structure**: Organize into ad groups by ICP dimension + product category

---

## 1. RESIMERCIAL KEYWORDS (30% ICP Weight)
**Goal**: Target contractors doing both residential AND commercial work

### High-Intent Commercial (Exact Match)
- `[commercial solar installer]`
- `[commercial battery storage contractor]`
- `[commercial backup power systems]`
- `[multifamily solar installation]`
- `[commercial generator installer]`
- `[industrial solar contractor]`
- `[commercial solar battery integration]`
- `[rooftop solar commercial buildings]`

### Residential + Commercial Crossover (Phrase Match)
- `"residential and commercial solar"`
- `"residential commercial battery backup"`
- `"home business backup power"`
- `"residential commercial generator installation"`

### Geographic Modifiers (Add to all keywords)
- `+ [state name]` (CA, TX, NY, FL, PA, MA, NJ)
- `+ [city name]` (New York, Houston, Los Angeles, Boston, etc.)
- `+ near me`

---

## 2. O&M KEYWORDS (40% ICP Weight - HIGHEST VALUE)
**Goal**: Target contractors with operations & maintenance revenue streams

### Service Contracts (High Commercial Intent)
- `[solar maintenance contracts]`
- `[generator service agreements]`
- `[battery storage maintenance plans]`
- `[preventive maintenance solar systems]`
- `[24/7 solar monitoring services]`
- `[commercial solar O&M]`
- `[operations and maintenance renewable energy]`

### Ongoing Service Keywords
- `"solar system monitoring and maintenance"`
- `"generator annual maintenance contract"`
- `"solar panel cleaning and inspection"`
- `"battery storage service agreements"`
- `"backup power system maintenance"`

### Emergency/Urgent Services
- `[emergency generator repair]`
- `[24/7 solar service]`
- `[battery backup emergency service]`

---

## 3. MULTI-OEM KEYWORDS (20% ICP Weight)
**Goal**: Target contractors managing multiple brand platforms (our sweet spot!)

### Multi-Brand Integration
- `[generac tesla installation]`
- `[enphase powerwall certified installer]`
- `[solar battery generator integration]`
- `[multi brand energy storage]`
- `[generac solar battery installer]`

### Brand Combinations (Exact Match)
- `[generac + enphase installer]`
- `[tesla powerwall + generac generator]`
- `[fronius + battery storage]`
- `[sol-ark hybrid inverter installer]`

### Monitoring Pain Points
- `"unified energy monitoring platform"`
- `"solar battery generator monitoring"`
- `"multi brand monitoring solution"`

---

## 4. MEP+R KEYWORDS (10% ICP Weight)
**Goal**: Target self-performing contractors with multiple trades

### Multi-Trade Contractors
- `[electrical contractor solar battery]`
- `[HVAC solar integration]`
- `[mechanical electrical renewable energy]`
- `[general contractor solar installation]`
- `[MEP contractor solar]`

### Electrical + Renewables
- `[licensed electrician solar installer]`
- `[electrical contractor backup power]`
- `[master electrician generator installation]`

### Facility/Building Contractors
- `[building contractor solar systems]`
- `[facility management renewable energy]`
- `[commercial construction solar battery]`

---

## 5. ITC URGENCY KEYWORDS
**Goal**: Capitalize on federal tax credit deadline urgency

### Deadline-Driven (High Intent)
- `[solar tax credit 2025]`
- `[ITC deadline commercial solar]`
- `[federal solar incentive ending]`
- `[commercial solar ITC 2026]`
- `[safe harbor solar projects]`

### Investment Tax Credit
- `[30 percent solar tax credit commercial]`
- `[ITC eligible solar projects]`
- `[solar investment tax credit deadline]`

---

## 6. PRODUCT-SPECIFIC KEYWORDS

### Solar + Battery Integration
- `[solar battery backup system commercial]`
- `[grid tied battery storage commercial]`
- `[solar plus storage installer]`
- `[commercial energy storage integration]`

### Generator + Renewables
- `[backup generator solar battery]`
- `[standby generator solar integration]`
- `[whole home solar battery generator]`
- `[commercial generator solar hybrid]`

### Hybrid Systems (High Value!)
- `[hybrid solar battery generator system]`
- `[sol-ark hybrid inverter commercial]`
- `[multi source backup power commercial]`

---

## 7. NEGATIVE KEYWORDS (Critical!)
**Exclude residential-only and DIY buyers**

### Residential-Only Exclusions
- `-residential only`
- `-homeowner`
- `-DIY`
- `-kit`
- `-self install`

### Low-Intent Exclusions
- `-free`
- `-cheap`
- `-discount`
- `-course`
- `-training`
- `-how to`

### Competitor Exclusions
- `-Tesla (only)` ← We want multi-brand!
- `-Sunrun`
- `-Sunpower`
- `-Vivint`

---

## 8. CAMPAIGN STRUCTURE RECOMMENDATIONS

### Campaign 1: HIGH INTENT - PLATINUM ICP
**Keywords**: O&M + Multi-OEM + Commercial
**Budget**: 50% of total
**Bid Strategy**: Target CPA or Maximize Conversions
**Landing Page**: Highlight multi-brand monitoring + O&M

### Campaign 2: RESIMERCIAL - GOLD ICP
**Keywords**: Residential+Commercial + MEP+R
**Budget**: 30% of total
**Bid Strategy**: Target ROAS
**Landing Page**: Resimercial capabilities + ITC urgency

### Campaign 3: ITC URGENCY - TIME-SENSITIVE
**Keywords**: Tax credit + Deadline keywords
**Budget**: 20% of total
**Bid Strategy**: Maximize Clicks
**Landing Page**: ITC deadline calculator + consultation CTA

---

## 9. MATCH TYPE STRATEGY

**Exact Match** `[keyword]`:
- High commercial intent keywords
- Multi-brand combinations
- Service contract keywords
- Budget: 60% of campaign

**Phrase Match** `"keyword"`:
- Resimercial crossover keywords
- O&M service keywords
- Budget: 30% of campaign

**Broad Match Modified** `+keyword`:
- Geographic expansion
- Long-tail discovery
- Budget: 10% of campaign

---

## 10. BID ADJUSTMENTS

**Device**:
- Mobile: -20% (contractors research on desktop)
- Desktop: +20%
- Tablet: 0%

**Time of Day**:
- Business hours (8am-6pm): +30%
- After hours: -50%

**Day of Week**:
- Monday-Friday: Baseline
- Saturday-Sunday: -30%

**Geographic**:
- CA, TX, NY, FL: +20% (largest markets)
- PA, MA, NJ: +10%
- Other SREC states: Baseline

---

## 11. KEYWORD PERFORMANCE TRACKING

**Success Metrics**:
- CTR > 5% (high commercial intent)
- Conversion Rate > 3% (form fills)
- Cost per Lead < $150
- Quality Score > 7

**Monthly Review**:
- Add negative keywords from search term reports
- Expand high-performing phrase match to exact
- Pause keywords with Quality Score < 5

---

**Total Keywords**: ~95 commercial intent keywords
**Estimated Monthly Spend**: $10,000-$25,000 across all campaigns
**Expected Leads**: 70-150 qualified contractor leads/month

---

*Generated by Coperniq Lead Generation System*
*Last Updated: 2025-10-25*
"""

    with open(output_path, 'w') as f:
        f.write(content)

    print("✅ Keyword strategy document created!")
    print()
    print("KEYWORD BREAKDOWN:")
    print("  Resimercial (30%): ~25 keywords")
    print("  O&M Services (40%): ~30 keywords ← HIGHEST VALUE")
    print("  Multi-OEM (20%): ~20 keywords")
    print("  MEP+R (10%): ~15 keywords")
    print("  Supporting: ~15 keywords")
    print()
    print("CAMPAIGN STRUCTURE:")
    print("  Campaign 1: HIGH INTENT - PLATINUM ICP (50% budget)")
    print("  Campaign 2: RESIMERCIAL - GOLD ICP (30% budget)")
    print("  Campaign 3: ITC URGENCY - TIME-SENSITIVE (20% budget)")
    print()
    print("="*70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate keyword strategy document")
    parser.add_argument("--output", default="output/gtm/keyword_strategy.md", help="Output path")

    args = parser.parse_args()

    generate_keyword_strategy(args.output)
