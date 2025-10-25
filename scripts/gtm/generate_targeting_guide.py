#!/usr/bin/env python3
"""
Generate Paid Ads Targeting Guide
Complete targeting criteria for Meta/Instagram + Google Ads
"""

def generate_targeting_guide(output_path: str):
    """
    Generate comprehensive paid ads targeting guide.

    Covers:
    - Meta/Instagram targeting (demographics, interests, behaviors)
    - Google Ads targeting (audiences, placements, topics)
    - Geographic targeting by SREC state
    - Exclusions and negative targeting
    """
    print("\n" + "="*70)
    print("🎯 GENERATING PAID ADS TARGETING GUIDE")
    print("="*70)
    print(f"Output: {output_path}")
    print()

    content = """# Coperniq Paid Ads Targeting Guide
## Complete Targeting Criteria for Meta/Instagram + Google Ads

**Last Updated**: 2025-10-25
**Target Audience**: PLATINUM tier resimercial contractors with O&M services

---

## 1. GEOGRAPHIC TARGETING

### PRIMARY MARKETS (High Priority - 70% of budget)
**CA, TX, FL, NY, PA, MA, NJ** - Largest SREC markets + ITC urgency

#### California
- **Metro Areas**: Los Angeles, San Francisco, San Diego, Sacramento
- **Zip Codes**: Focus on wealthy suburbs (Palo Alto, Beverly Hills, La Jolla)
- **Budget Allocation**: 25% (largest market)

#### Texas
- **Metro Areas**: Houston, Dallas, Austin, San Antonio
- **Zip Codes**: Memorial, Highland Park, Westlake Hills
- **Budget Allocation**: 20% (deregulated energy market)

#### New York
- **Metro Areas**: NYC, Westchester, Long Island (Hamptons)
- **Zip Codes**: Manhattan UES/UWS, Scarsdale, Southampton
- **Budget Allocation**: 12% (high property values)

#### Florida
- **Metro Areas**: Miami, Naples, Tampa, Palm Beach
- **Zip Codes**: Fisher Island, Old Naples, South Tampa
- **Budget Allocation**: 10%

#### Pennsylvania
- **Metro Areas**: Philadelphia, Pittsburgh, Main Line suburbs
- **Zip Codes**: Villanova, Wayne, Ardmore, Fox Chapel
- **Budget Allocation**: 5%

#### Massachusetts
- **Metro Areas**: Boston, Cambridge, wealthy suburbs
- **Zip Codes**: Back Bay, Chestnut Hill, Wellesley
- **Budget Allocation**: 5%

#### New Jersey
- **Metro Areas**: Northern NJ, Princeton, Shore
- **Zip Codes**: Short Hills, Alpine, Saddle River
- **Budget Allocation**: 3%

### SECONDARY MARKETS (Medium Priority - 30% of budget)
**OH, MD, DC, DE, NH, RI, CT, IL** - Medium SREC states

---

## 2. META/INSTAGRAM TARGETING

### Demographics

**Age**: 35-65
- 35-44: Business owners, younger contractors (20%)
- 45-54: Established contractors (40%)
- 55-65: Senior contractors, business buyers (40%)

**Gender**: All (slight male skew 70/30 but include all)

**Job Titles** (Employer targeting):
- Electrical Contractor
- General Contractor
- Facility Manager
- Property Manager
- Building Owner
- Construction Manager
- Mechanical Contractor
- HVAC Contractor
- MEP Engineer

**Education**:
- Bachelor's degree or higher (40%)
- Some college (30%)
- Trade school/vocational (30%)

**Income**:
- $100,000+ household income
- Top 10% of ZIP code

### Interests (Detailed Targeting)

**Business & Industry**:
- Small business owners
- Commercial real estate
- Facility management
- Construction
- Green building
- Sustainability
- Energy management

**Technology**:
- Solar energy
- Renewable energy
- Energy storage
- Battery technology
- Smart home technology
- Building automation

**Professional**:
- Electrical engineering
- Mechanical engineering
- HVAC systems
- Plumbing
- Commercial construction

### Behaviors

**Business**:
- Small business owners (10-49 employees)
- Business decision makers
- B2B purchase behavior
- High-value purchasers

**Technology Adoption**:
- Early adopters
- Technology enthusiasts
- Smart device users

### Lookalike Audiences
1. **1% Lookalike** from PLATINUM tier upload (highest precision)
2. **2-3% Lookalike** from GOLD tier upload (expansion)
3. **Engagement Lookalike** from website visitors

### Placement Strategy

**Recommended Placements**:
- ✅ Facebook Feed (primary)
- ✅ Instagram Feed
- ✅ Facebook Marketplace (B2B happens here!)
- ✅ Instagram Explore
- ❌ Audience Network (low quality for B2B)
- ❌ Instagram Stories (unless testing)

**Device Targeting**:
- Desktop: +30% bid adjustment (contractors research at office)
- Mobile: Baseline (checking during fieldwork)

---

## 3. GOOGLE ADS TARGETING

### Audience Segments

#### Custom Intent Audiences
Create audiences based on keyword research:
- Users searching for: "commercial solar installation"
- Users searching for: "generator service contracts"
- Users searching for: "solar battery maintenance"
- Users searching for: "multi-brand energy monitoring"

#### In-Market Audiences
- **Business Services** > Facility Management
- **Business Services** > Commercial Construction
- **Home & Garden** > Home Improvement (exclude residential-only)
- **Green Living & Sustainability** > Solar Energy

#### Affinity Audiences
- Business Professionals
- Technology Enthusiasts
- Green Living Enthusiasts
- Home Improvement Enthusiasts

#### Customer Match
- Upload PLATINUM tier list (from our CSV)
- Upload GOLD tier list (from our CSV)
- Create Similar Audiences at 1%, 2%, 5%

### Topic Targeting (Display Network)

**Commercial Construction**:
- Commercial building
- Green building
- LEED certification
- Energy efficiency

**Renewable Energy**:
- Solar power
- Energy storage
- Backup power systems
- Renewable energy

**Business Management**:
- Facility management
- Property management
- Business operations

### Placement Targeting

**Website Placements** (Managed Placements):
- `solarpower world.com`
- `greenbuildingadvisor.com`
- `facilitiesnet.com`
- `constructiondive.com`
- `electricalcontractor.net`

**YouTube Channels**:
- Solar installation how-tos
- Commercial construction channels
- Electrical contractor education

**Mobile Apps**:
- Exclude (low B2B intent)

---

## 4. EXCLUSIONS & NEGATIVE TARGETING

### Meta/Instagram Exclusions

**Interests to Exclude**:
- DIY home improvement
- Budget home improvement
- Discount shopping
- Students
- Retail workers

**Behaviors to Exclude**:
- Frequent international travelers (not our audience)
- Engaged shoppers (looking for deals, not B2B)

**Income to Exclude**:
- Bottom 25% of ZIP code

### Google Ads Exclusions

**Demographics**:
- Age: Under 25 (too young for business owners)
- Household income: Bottom 50% (not decision makers)

**Audiences**:
- Residential homeowners (exclude if possible without excluding contractors)
- Students
- Job seekers

**Placements**:
- Gaming apps
- Entertainment sites
- News sites (unless industry news)

---

## 5. DAYPARTING (TIME OF DAY TARGETING)

### Optimal Hours (All Days)
**8:00 AM - 6:00 PM** - Business hours (+30% bid adjustment)

Reasoning: Contractors are:
- In the office (desktop usage)
- Making business decisions
- Researching new products/services

### Low-Intent Hours
**6:00 PM - 8:00 AM** - After hours (-50% bid adjustment)

Reasoning:
- Personal browsing (not business)
- Lower conversion rates
- Higher CPA

### Weekend Strategy
**Saturday-Sunday** - Reduced bids (-30%)

Reasoning:
- Some contractors work weekends (construction)
- But lower business decision-making
- Test and adjust by industry segment

---

## 6. DEVICE TARGETING

### Desktop
**+20-30% bid adjustment** (MOST IMPORTANT)

Reasoning:
- Contractors research at office
- Fill out longer forms
- Higher conversion rate
- Better lead quality

### Mobile
**Baseline (0% adjustment)**

Reasoning:
- Contractors check during fieldwork
- Quick lookups
- Lower form completion
- But still valuable touchpoints

### Tablet
**-20% bid adjustment**

Reasoning:
- Lower volume
- Mixed intent
- Not primary device for business research

---

## 7. BUDGET ALLOCATION

### By Platform
- Google Ads Search: 50% (high commercial intent)
- Meta/Instagram Feed: 30% (targeting + lookalikes)
- Google Display: 15% (awareness + retargeting)
- LinkedIn (future): 5% (B2B premium)

### By Campaign Type
- HIGH INTENT (O&M + Multi-OEM): 50%
- RESIMERCIAL (Commercial + Residential): 30%
- ITC URGENCY (Deadline keywords): 20%

### By Geography
- Primary markets (CA, TX, NY, FL): 70%
- Secondary markets (PA, MA, NJ): 20%
- Test markets (other SREC states): 10%

---

## 8. RETARGETING STRATEGY

### Website Visitors
**Audience Segments**:
- All visitors (180 days) - Awareness
- 30-day visitors - Consideration
- 7-day visitors - High intent

**Exclusions**:
- Converted leads (don't waste budget)
- Current customers

### Engagement Audiences
- Video viewers (50%+ watched)
- Instagram post engagers
- Facebook page followers

### Cart Abandoners / Form Abandoners
- Visited contact/demo page but didn't submit
- +50% bid adjustment
- Specific messaging: "Still interested in Coperniq?"

---

## 9. CREATIVE RECOMMENDATIONS

### Meta/Instagram Ad Copy

**Headline Options**:
- "Managing 3+ Monitoring Platforms? There's a Better Way"
- "Unified Monitoring for Multi-Brand Contractors"
- "Stop Juggling Generac, Tesla, and Enphase Dashboards"

**Body Copy Focus**:
- Pain point: Multiple monitoring platforms
- Solution: One unified dashboard
- Benefit: Save time, better customer experience
- CTA: "See Demo" or "Schedule Consultation"

**Image/Video**:
- Split-screen: Multiple dashboards vs. Coperniq unified view
- Contractor testimonials
- Before/after monitoring screenshots

### Google Ads Copy

**Headline 1**: "Multi-Brand Energy Monitoring"
**Headline 2**: "Generac + Tesla + Enphase in One Dashboard"
**Headline 3**: "Built for Contractors with O&M Contracts"

**Description**:
"Stop managing 3+ monitoring platforms. Coperniq unifies Generac, Tesla, Enphase, and more into one contractor dashboard. Perfect for multi-OEM installers with service contracts."

**Extensions**:
- Sitelink: "See Demo" | "Pricing" | "Supported Brands" | "Contact Sales"
- Callout: "30-Day Free Trial" | "No Credit Card" | "Multi-OEM Support"
- Structured Snippet: Brands: Generac, Tesla, Enphase, Fronius, SolarEdge

---

## 10. CONVERSION TRACKING

### Primary Conversions
1. **Demo Request Form** - Most valuable (assign $500 value)
2. **Contact Form Submit** - High value (assign $300 value)
3. **Phone Call** - Medium value (assign $200 value)

### Secondary Conversions
4. **Pricing Page View** - Consideration (assign $50 value)
5. **Features Page View** - Interest (assign $25 value)
6. **Video Watch 75%** - Awareness (assign $10 value)

### Attribution Model
**Recommended**: Data-Driven Attribution

**Alternative**: Last Non-Direct Click
- Gives credit to last marketing touchpoint
- Good for understanding channel effectiveness

---

## 11. A/B TESTING ROADMAP

### Month 1: Audience Testing
- Test: PLATINUM tier lookalike (1%) vs. Custom Intent
- Budget: 50/50 split
- Decision metric: Cost per Lead

### Month 2: Creative Testing
- Test: Pain point messaging vs. Feature messaging
- Budget: 50/50 split
- Decision metric: Conversion Rate

### Month 3: Placement Testing
- Test: Feed only vs. Feed + Marketplace
- Budget: 70/30 split
- Decision metric: CPA

### Month 4: Geographic Testing
- Test: CA only vs. CA + TX + NY
- Budget: Based on performance
- Decision metric: ROAS

---

## 12. SUCCESS METRICS

### Campaign-Level KPIs
- **CTR**: > 3% (Search), > 1% (Display/Social)
- **Conversion Rate**: > 2%
- **Cost per Lead**: < $200
- **Lead Quality Score**: > 7/10 (sales team rating)

### Platform Benchmarks
- **Google Search**: CPC $15-30, CVR 3-5%
- **Google Display**: CPC $3-8, CVR 1-2%
- **Meta/Instagram**: CPC $8-15, CVR 1.5-3%

### Business-Level KPIs
- **SQL Rate**: > 30% (marketing qualified → sales qualified)
- **Close Rate**: > 10% (demo → customer)
- **Customer LTV**: > $50,000 (multi-year contracts)

---

**Total Estimated Reach**: 500,000-1,000,000 multi-brand contractors across 15 SREC states
**Expected Monthly Leads**: 75-150 qualified contractor leads
**Recommended Monthly Budget**: $15,000-$30,000 across all platforms

---

*Generated by Coperniq Lead Generation System*
*For Pakistan GTM Team - 2-Day Launch Ready*
"""

    with open(output_path, 'w') as f:
        f.write(content)

    print("✅ Targeting guide created!")
    print()
    print("GUIDE SECTIONS:")
    print("  1. Geographic Targeting (15 SREC states)")
    print("  2. Meta/Instagram Targeting (demographics, interests, behaviors)")
    print("  3. Google Ads Targeting (audiences, topics, placements)")
    print("  4. Exclusions & Negative Targeting")
    print("  5. Dayparting (time of day)")
    print("  6. Device Targeting")
    print("  7. Budget Allocation")
    print("  8. Retargeting Strategy")
    print("  9. Creative Recommendations")
    print("  10. Conversion Tracking")
    print("  11. A/B Testing Roadmap")
    print("  12. Success Metrics")
    print()
    print("RECOMMENDED BUDGET: $15,000-$30,000/month")
    print("EXPECTED LEADS: 75-150 qualified contractors/month")
    print("="*70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate paid ads targeting guide")
    parser.add_argument("--output", default="output/gtm/targeting_criteria.md", help="Output path")

    args = parser.parse_args()

    generate_targeting_guide(args.output)
