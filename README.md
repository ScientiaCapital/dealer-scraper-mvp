# 🏗️ Multi-OEM Dealer Network Scraper

> 55,000+ records → 8,277 unique contractors across 10 OEM networks with 85% deduplication rate

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/playwright-automated-green.svg)](https://playwright.dev/)
[![Streamlit](https://img.shields.io/badge/streamlit-dashboard-red.svg)](https://streamlit.io/)

---

## Overview

Production-ready web scraper that aggregates contractor data across 10 OEM dealer networks (generators, solar, HVAC). Processes 55,000+ records → 8,277 unique contractors with intelligent multi-key deduplication and ICP scoring.

**Key Features**: 10 production-tested OEMs • Real-time dashboard • 85% dedup rate • Factory pattern architecture • ICP lead scoring

---

## Demo

```bash
[1/140] Scraping ZIP 02101... ✓ Found 200 dealers
[10/140] Scraping ZIP 12207... 💾 Saved checkpoint: 2,000 dealers
[140/140] Scraping ZIP 96720... ✅ Complete: 55,000+ dealers

Deduplicating... Removed 46,723 duplicates (85%)
Final: 8,277 unique contractors
```

### Performance

| Category | OEMs | Raw → Unique | Dedup Rate |
|----------|------|-------------|------------|
| Generator OEMs | Generac, Briggs & Stratton, Cummins, Carrier | 28,500 → 2,100 | 92.6% |
| Solar OEMs | Tesla, Enphase, SolarEdge | 15,200 → 1,800 | 88.2% |
| HVAC OEMs | Mitsubishi, Trane, York, SMA Solar | 11,300 → 4,377 | 61.3% |
| **Total** | **10 OEMs** | **55,000+ → 8,277** | **85%** |

---

## Key Results

**Production Run (Oct 29, 2025):**
- **8,277 unique contractors** (deduplicated across 10 OEMs)
- **198 multi-OEM contractors** (2.4% - highest value prospects)
- **50 GOLD tier prospects** (ICP score 60-79, ready for outreach)
- **5,035 HVAC contractors** (60.8% - resimercial signal)
- **15 SREC states covered** (CA, TX, PA, MA, NJ, FL + 9 more)

**ICP Scoring Tiers:**
- **GOLD (50 prospects)**: ICP score 60-79, immediate outreach candidates
- **SILVER (8,160 prospects)**: ICP score 40-59, nurture campaign targets
- **BRONZE (67 prospects)**: ICP score 20-39, long-term follow-up

---

## Architecture

```
ScraperFactory (10 production-tested OEMs)
    ↓
BaseDealerScraper (Abstract)
    ↓
1. Navigate → 2. Handle cookies → 3. Fill ZIP → 4. Extract → 5. Deduplicate → 6. ICP Score
```

**Design Patterns**: Factory • Abstract Base Class • Singleton • Dataclasses

**ICP Scoring Algorithm**: 4-dimension scoring (Resimercial 35%, Multi-OEM 25%, MEP+R 25%, O&M 15%)

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run multi-OEM production (10 OEMs, 140 ZIPs)
python3 scripts/run_multi_oem_scraping.py \
  --oems Generac "Briggs & Stratton" Cummins Carrier \
         Mitsubishi Trane York SMA Enphase SolarEdge \
  --states CA TX PA MA NJ FL NY OH MD DC DE NH RI CT IL

# Launch dashboard
streamlit run streamlit_monitor.py
```

**Setup Guide**: See [SETUP.md](SETUP.md) for detailed installation, API key configuration (Apollo, Close CRM), and troubleshooting.

---

## Technical Highlights

### 1. Multi-Key Deduplication (97.4% removal rate)
- Phone normalization (digits only)
- Root domain extraction
- Fuzzy name matching

### 2. Checkpoint-Based ETL
- Auto-save every 10 ZIPs
- Zero data loss on failures
- Resumable scraping

### 3. Cross-OEM Detection
```python
{
  "name": "ABC Electric",
  "oem_certifications": ["Generac", "Tesla", "Enphase"],
  "confidence": 100,
  "multi_oem_score": 100
}
```

### 4. Real-Time Monitoring
- Streamlit dashboard with auto-refresh
- Live progress tracking (all OEMs)
- Performance charts (Plotly)

---

## Skills Demonstrated

**Python & Engineering**: OOP (Factory, ABC, Singleton) • Type safety (dataclasses) • Error handling • Async/await

**Data Engineering**: Multi-source aggregation • Record linkage • 85% dedup rate at scale • ETL pipelines • Checkpoints

**Lead Scoring & Segmentation**: ICP algorithm • Multi-OEM detection • Tier-based prospect ranking

**Web Scraping**: Playwright automation • Cookie/AJAX/iframe handling • JavaScript extraction • Rate limiting

**Full Stack**: Backend (Python) • Frontend (Streamlit) • Data (Pandas) • Visualization (Plotly)

---

## Project Structure

```
dealer-scraper-mvp/
├── scrapers/
│   ├── base_scraper.py          # Abstract base
│   ├── scraper_factory.py       # Factory pattern
│   └── [17 OEM scrapers]        # Generac, Tesla, etc.
├── scripts/
│   ├── run_*_national.py        # National runners
│   └── combine_national_oems.py # Master combiner
├── streamlit_monitor.py         # Real-time dashboard
└── README.md
```

---

## Results

**Production Run (Oct 29, 2025 - 140 ZIPs, 15 SREC states)**:
- Raw: 55,000+ contractors collected
- Unique: 8,277 contractors (85% dedup)
- Multi-OEM: 198 contractors (2.4% - highest value prospects)
- Coverage: 15 SREC states via major metros (CA, TX, PA, MA, NJ, FL + 9 more)

---

## Contact

**Tim Kipper** – Sales Professional → Software Engineer

Building technical skills for GTM Engineer roles in AI/Crypto/Fintech

GitHub: [@ScientiaCapital](https://github.com/ScientiaCapital)

---

**MIT License** • Built with Python, Playwright, Streamlit, Plotly
