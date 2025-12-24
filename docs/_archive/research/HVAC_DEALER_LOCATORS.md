# HVAC OEM Dealer Locator URLs

Research completed: 2025-10-28

## Summary

Adding 4 HVAC brands to detect MEP (Mechanical, Electrical, Plumbing) capabilities and commercial/resimercial signals for Coperniq ICP scoring.

## Dealer Locator URLs

### 1. Carrier
- **URL**: https://www.carrier.com/residential/en/us/find-a-dealer/
- **Market**: Residential + Commercial HVAC
- **Search**: ZIP code based
- **Dealer Badges**: Factory Authorized Dealer program
- **Notes**: One of the largest HVAC brands (owned by Carrier Global)

### 2. Trane
- **URL**: https://www.trane.com/residential/en/dealer-locator/
- **Market**: Residential + Commercial HVAC
- **Search**: ZIP code based
- **Dealer Tiers**:
  - Trane Comfort Specialist (standard)
  - Charter Member (original TCS dealers since 1998)
  - NATE Certified
  - 24/7 Emergency Service badge
  - Financing availability badge
- **Notes**: Premium HVAC brand, owned by Trane Technologies (formerly Ingersoll Rand)

### 3. Lennox
- **URLs**:
  - Residential: https://www.lennox.com/residential/locate/
  - Commercial: https://www.lennox.com/commercial/locate
- **Market**: Residential + Commercial HVAC
- **Search**: City or ZIP/postal code
- **Dealer Tiers**:
  - **Lennox Premier Dealers** (highest tier - similar to Generac PowerPro Premier)
  - Standard dealers
- **Network Size**: 6,000+ dealers across North America
- **Notes**: Independent dealers, prominently featured on ecommerce integration

### 4. Mitsubishi Electric
- **URLs**:
  - Residential: https://www.mitsubishicomfort.com/find-a-contractor
  - Commercial: https://www.mitsubishicomfort.com/find-a-commercial-contractor
  - **Diamond Commercial** (VRF specialists): https://www.mitsubishicomfort.com/find-a-diamond-commercial-contractor
- **Market**: Ductless mini-splits + VRF systems (Variable Refrigerant Flow)
- **Search**: ZIP code based
- **Dealer Tiers**:
  - **Diamond Commercial Contractor** 🏆 (TOP TIER - VRF/commercial specialists)
  - Diamond Contractor (residential ductless experts)
  - Elite Diamond Contractor
  - Standard contractors
- **Key Certifications**:
  - VRF system installation (commercial/multi-zone)
  - CITY MULTI® systems (commercial VRF product line)
  - 10-year extended warranty eligibility (Diamond Commercial only)
  - Priority technical support
- **Notes**: **Diamond Commercial = resimercial signal!** VRF contractors are doing large commercial + high-end residential projects ($5M-$50M revenue range)

## Why These 4 HVAC Brands Matter for Coperniq ICP

### MEP Capability Detection
- **HVAC presence = Mechanical trade capability**
- Cross-referencing HVAC + Solar + Generator = true MEP+R contractor
- Commercial HVAC (esp. VRF) = resimercial validation

### Commercial Signal Strength
| Brand | Commercial Indicator | Strength |
|-------|---------------------|----------|
| Carrier | Factory Authorized (commercial + resi) | Medium |
| Trane | Comfort Specialist (commercial + resi) | Medium-High |
| Lennox | Premier Dealer (commercial available) | Medium |
| **Mitsubishi** | **Diamond Commercial (VRF)** | **VERY HIGH** 🏆 |

### Target Contractor Profile
**Ideal Coperniq ICP with HVAC data:**
- Generator (Generac/Briggs/Cummins) + Solar (Enphase/Tesla/SMA) + **HVAC (Mitsubishi Diamond Commercial VRF)**
- Score breakdown:
  - Multi-product (40 pts): Gen + Solar + HVAC = 40 pts
  - Multi-OEM depth (30 pts): 4-5+ OEMs = 30 pts
  - Tier quality (20 pts): Diamond Commercial + Premier/Platinum = 20 pts
  - Market (10 pts): SREC states = 10 pts
  - **Total: 100/100 ICP score** 🎯

## Implementation Priority

1. **Mitsubishi Diamond Commercial** (HIGHEST PRIORITY)
   - VRF contractors = clear commercial signal
   - Smallest dataset (most selective tier) = fastest to scrape
   - Highest ICP value per lead

2. **Lennox Premier Dealers**
   - Similar tier structure to Generac (Premier = top tier)
   - Good mix of commercial + residential
   - Proven dealer locator pattern

3. **Trane Comfort Specialists**
   - Large national network
   - Multiple tier badges to track
   - Strong commercial presence

4. **Carrier Factory Authorized**
   - Largest HVAC brand by market share
   - Broad dealer network
   - Good baseline HVAC capability signal

## Next Steps

1. Inspect each dealer locator URL with Playwright to understand DOM structure
2. Write extraction scripts (similar to Generac/Briggs/Cummins pattern)
3. Test on 3 ZIPs per brand
4. Add to multi-OEM scraping workflow
5. Run national scrape (140 SREC state ZIPs × 4 HVAC brands = 560 scrapes, ~45-60 min total)

## Expected Dataset Sizes (Estimated)

- **Mitsubishi Diamond Commercial**: 50-150 contractors (highly selective VRF tier)
- **Lennox Premier**: 300-600 dealers
- **Trane Comfort Specialist**: 800-1,500 dealers
- **Carrier Factory Authorized**: 1,000-2,000 dealers

**Total HVAC contractors**: ~2,200-4,250 across 4 brands
**Multi-HVAC crossover expected**: 15-25% (contractors certified for 2+ HVAC brands)
