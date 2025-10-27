# Enphase Platinum + Gold Collection Guide

## ✅ Validated Extraction (ZIP 94102)

Successfully extracted **11 platinum/gold installers** with full enrichment data.

## 📊 Data Structure

### Core Fields (from Tesla pattern)
- `name` - Company name
- `phone` - Primary phone number
- `website` - Full website URL
- `domain` - Root domain (e.g., "YourEnergySolutions.com")
- `email` - (empty for now, can add later)
- `tier` - "platinum" or "gold"
- `certifications` - Tier description
- `oem_source` - "Enphase"
- `scraped_from_zip` - ZIP code searched
- `state` - State abbreviation (parsed from address)
- `collection_date` - Date collected

### Enrichment Fields (NEW - Enphase bonus data)
- `address_full` - Complete street address
- `city` - City name (parsed from address)
- `rating` - Customer rating (0-5 scale)
- `years_experience` - Years in business (integer)
- `warranty_years` - Labor warranty years (integer)
- `has_solar` - Boolean: offers solar installation
- `has_storage` - Boolean: offers battery storage installation
- `has_commercial` - Boolean: offers commercial installation
- `has_ev_charger` - Boolean: offers EV charger installation
- `has_ops_maintenance` - Boolean: offers operations & maintenance

## 🎯 Example Record

```python
{
    "name": "Your Energy Solutions (California)",
    "phone": "925-380-9500",
    "website": "http://www.YourEnergySolutions.com",
    "domain": "YourEnergySolutions.com",
    "email": "",
    "tier": "platinum",
    "certifications": "Platinum Certified Installer",
    "oem_source": "Enphase",
    "scraped_from_zip": "94102",
    "state": "CA",
    "collection_date": "2025-10-26",
    "address_full": "290 Rickenbacker Circle, Livermore, CA 94551",
    "city": "Livermore",
    "rating": "4.7",
    "years_experience": 17,
    "warranty_years": 25,
    "has_solar": true,
    "has_storage": true,
    "has_commercial": true,
    "has_ev_charger": true,
    "has_ops_maintenance": true
}
```

## 🔧 Validated JavaScript Extraction

### Step 1: List View - Extract IDs & Tiers
```javascript
() => {
  const cards = Array.from(document.querySelectorAll('[data-installer-id]'));
  const installers = cards.map(card => {
    const id = card.getAttribute('data-installer-id');
    const tierImg = card.querySelector('img[alt="platinum"], img[alt="gold"], img[alt="silver"]');
    const tier = tierImg ? tierImg.getAttribute('alt') : '';
    return { id, tier };
  });
  return installers.filter(inst => inst.id && (inst.tier === 'platinum' || inst.tier === 'gold'));
}
```

### Step 2: Detail View - Extract Full Data
```javascript
() => {
  const phoneLink = document.querySelector('a[href^="tel:"]');
  const phone = phoneLink ? phoneLink.textContent.trim() : '';

  const websiteLink = Array.from(document.querySelectorAll('a')).find(a => a.textContent.trim() === 'Website');
  const website = websiteLink ? websiteLink.getAttribute('href') : '';

  const allDivs = Array.from(document.querySelectorAll('div, generic'));
  const addressDiv = allDivs.find(div => /\d{5}/.test(div.textContent) && div.textContent.includes(',') && div.children.length === 0 && /^\d/.test(div.textContent.trim()));
  const address = addressDiv ? addressDiv.textContent.trim() : '';

  const ratingMatch = document.body.textContent.match(/\((\d+\.\d+)\)/);
  const rating = ratingMatch ? ratingMatch[1] : '';

  const bodyText = document.body.textContent;
  const hasSolar = bodyText.includes('Solar installation');
  const hasStorage = bodyText.includes('Storage installation');
  const hasCommercial = bodyText.includes('Commercial installation');
  const hasEV = bodyText.includes('EV charger');
  const hasOM = bodyText.includes('Ops & Maintenance');

  const listItems = Array.from(document.querySelectorAll('li'));
  const experienceItem = listItems.find(li => li.textContent.includes('experience'));
  const expMatch = experienceItem ? experienceItem.textContent.match(/(\d+)\s*years?\s*experience/i) : null;
  const yearsExperience = expMatch ? parseInt(expMatch[1]) : 0;

  const warrantyItem = listItems.find(li => li.textContent.includes('warranty'));
  const warMatch = warrantyItem ? warrantyItem.textContent.match(/(\d+)\s*years?/i) : null;
  const warrantyYears = warMatch ? parseInt(warMatch[1]) : 0;

  return {
    phone,
    website,
    address,
    rating,
    years_experience: yearsExperience,
    warranty_years: warrantyYears,
    has_solar: hasSolar,
    has_storage: hasStorage,
    has_commercial: hasCommercial,
    has_ev_charger: hasEV,
    has_ops_maintenance: hasOM
  };
}
```

## 📈 Collection Results (ZIP 94102)

- **Total results**: 27 installers
- **Platinum**: 3 installers
- **Gold**: 8 installers
- **Target collected**: 11 platinum/gold installers

## 🎯 Production Collection Plan

### Scope
- **40 ZIPs** (same as Tesla Premier)
- **Expected**: ~10-15 platinum/gold per ZIP = **400-600 total installers**
- **Time estimate**: 40 ZIPs × 2-3 min = **80-120 minutes**

### Next Steps

1. ✅ **Extraction validated** (scripts work perfectly)
2. ⏳ **Manual collection required** (MCP Playwright browser)
3. ⏳ **Deduplication** (phone-based, like Tesla)
4. ⏳ **Cross-reference with Tesla** (find multi-OEM contractors)

### Collection Workflow

For each of 40 ZIPs:
1. Navigate to https://enphase.com/installer-locator
2. Enter ZIP code
3. Click "Find an installer"
4. Execute Step 1 JavaScript → get platinum/gold IDs
5. For each ID:
   - Navigate to `https://enphase.com/installer-locator?installer={ID}`
   - Execute Step 2 JavaScript → get full data
   - Extract name from page text
   - Parse city/state from address
   - Save to CSV
6. Mark ZIP complete in progress tracker

## 💎 Value of Enrichment Data

The extra click to detail pages gives us **GOLD intelligence**:

### ICP Scoring Inputs
- **Years experience**: Credibility signal (17+ years = established)
- **Warranty**: Customer confidence (25 years labor = premium)
- **Commercial flag**: Resimercial targeting (35% of ICP score)
- **Multi-trade**: Solar + Storage + EV = platform power users

### Lead Qualification
- **Phone + Website**: Direct outreach channels
- **Rating**: Social proof for email personalization
- **Service mix**: Pain point identification (more platforms = more pain)

### Competitive Intelligence
- **Platinum vs Gold**: Market positioning
- **O&M flag**: Existing service contracts (Year 2 Coperniq feature)
- **Address**: Geographic coverage analysis

## 📁 Output Files

1. **Raw data**: `output/enphase_platinum_gold_installers.csv`
2. **Deduped**: `output/enphase_platinum_gold_deduped_YYYYMMDD.csv`
3. **Report**: `output/enphase_deduplication_report_YYYYMMDD.txt`
4. **Progress tracker**: `output/enphase_progress.json`

## 🔄 Comparison to Tesla

| Metric | Tesla Premier | Enphase Platinum/Gold |
|--------|--------------|----------------------|
| Raw records | 254 | ~500 (est) |
| Unique (deduped) | 69 | ~150 (est) |
| Duplication rate | 72.8% | ~70% (est) |
| Enrichment data | Basic | **EXTENSIVE** |
| Time per ZIP | 2-3 min | 2-3 min |
| Total time | 2 hours | 2 hours |

## ✨ Key Advantage

Enphase data is **RICHER** than Tesla:
- Tesla: Name, phone, website, tier
- Enphase: **+ address, city, rating, experience, warranty, 5 service flags**

This enables **smarter ICP scoring** and **better lead qualification**.
