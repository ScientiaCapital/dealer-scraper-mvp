# Dealer Scraper MVP

> **217K contractors** in database. **20 OEM scrapers** (Generac, Tesla, Carrier, etc.).
> B2B lead generation for MEP contractor prospecting with ICP scoring and deduplication.

---

## What It Does

- **20 OEM dealer locator scrapers** (generators, solar, HVAC)
- **217,523 contractors** in SQLite database
- **97.3% deduplication accuracy** (phone → email → domain → fuzzy name)
- **ICP scoring** with tier-based ranking (Platinum/Gold/Silver/Bronze)
- **Streamlit dashboard** for real-time monitoring

## Goals

Generate high-quality B2B leads for MEP SaaS sales by scraping OEM dealer networks and state license databases.

## Quick Start

```bash
cd dealer-scraper-mvp
pip install -r requirements.txt
playwright install chromium

# Run OEM scrapers
python3 scripts/run_all_oems_production.py

# Launch dashboard
streamlit run streamlit_monitor.py
```

## Current Status

| Component | Status |
|-----------|--------|
| SQLite database | 217,523 contractors |
| Supabase sync | 14,204 leads pushed |
| Working scrapers | ~5 (Carrier, Mitsubishi, Rheem, York, SMA) |
| Needs maintenance | ~15 (URL/selector changes) |
| Deduplication | 97.3% accuracy |
| ICP scoring | Working |

## Known Issues

- **15 scrapers need maintenance** - URL changes, selector updates
- **TX data**: 72K records are individuals, need filtering to businesses
- **Trane**: 0% direct contact (866 = call center) - use as enrichment leads
- **Browserbase session timeouts** - fixed in Cummins, Schneider, Tesla

## GTME Skills Developed

Building toward Go-To-Market Engineer through hands-on projects:

| Skill Area | What I Learned |
|------------|----------------|
| **Lead generation at scale** | Built 217K contractor database from 20+ sources |
| **Data quality engineering** | 97.3% deduplication accuracy across phone/email/domain/name |
| **ICP scoring models** | 4-dimension scoring: Resimercial (35%), Multi-OEM (25%), MEP+E (25%), O&M (15%) |
| **Multi-OEM pain detection** | Found 198 contractors managing 2+ platforms (highest conversion) |
| **Pipeline architecture** | Scrape → Dedupe → Score → Supabase → CRM flow |
| **Web scraping at scale** | Playwright automation, cookies, AJAX, rate limiting |

## Tech Stack

Python, Playwright, SQLite, Supabase, Streamlit, Plotly

## Data Flow

```
OEM Scrapers → SQLite (217K) → Dedup → ICP Score → Supabase → sales-agent → Close CRM
```

## Key Results

- **14,204 leads** in Supabase ready for sales-agent
- **198 multi-OEM contractors** (highest value - 2+ platforms)
- **7 triple-OEM unicorns** (managing 3+ platforms)
- **50 GOLD tier** ready for immediate outreach
