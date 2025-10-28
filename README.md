# 🏗️ Multi-OEM Dealer Network Scraper

> Automated lead generation across 17 OEM networks with 97% deduplication rate

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/playwright-automated-green.svg)](https://playwright.dev/)
[![Streamlit](https://img.shields.io/badge/streamlit-dashboard-red.svg)](https://streamlit.io/)

---

## Overview

Production-ready web scraper that aggregates contractor data across 17 OEM dealer networks (generators, solar, batteries). Processes 55,000+ records → 1,500 unique leads with intelligent multi-key deduplication.

**Key Features**: National coverage (50 states) • Real-time dashboard • 97% dedup rate • Factory pattern architecture

---

## Demo

```bash
[1/137] Scraping ZIP 02101... ✓ Found 200 dealers
[10/137] Scraping ZIP 12207... 💾 Saved checkpoint: 2,000 dealers
[137/137] Scraping ZIP 96720... ✅ Complete: 27,200 dealers

Deduplicating... Removed 26,489 duplicates (97.4%)
Final: 711 unique dealers
```

### Performance

| OEM | Raw → Unique | Dedup Rate | Runtime |
|-----|-------------|------------|---------|
| Cummins | 27,200 → 711 | 97.4% | 60 min |
| Briggs | 1,370 → 140 | 90% | 60 min |
| Generac | 27,000 → 700 | 97% | 60 min |
| **Total** | **55,000+ → 1,500** | **97%** | **3 hrs** |

---

## Architecture

```
ScraperFactory (17 OEMs)
    ↓
BaseDealerScraper (Abstract)
    ↓
1. Navigate → 2. Handle cookies → 3. Fill ZIP → 4. Extract → 5. Deduplicate
```

**Design Patterns**: Factory • Abstract Base Class • Singleton • Dataclasses

---

## Quick Start

```bash
# Install
pip install -r requirements.txt
playwright install chromium

# Run single OEM
python3 scripts/run_generac_production.py

# Run national (all 50 states)
python3 scripts/run_cummins_national.py
python3 scripts/run_briggs_national.py
python3 scripts/run_generac_national.py

# Combine results
python3 scripts/combine_national_oems.py

# Launch dashboard
streamlit run streamlit_monitor.py
```

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

**Data Engineering**: Multi-source aggregation • Record linkage • 97% dedup rate • ETL pipelines • Checkpoints

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

**National Run (137 ZIPs, 50 states)**:
- Raw: 55,000+ dealers collected
- Unique: 1,500 contractors (97% dedup)
- Multi-OEM: 547 contractors (3+ brands)
- Coverage: All 50 states via major metros

---

## Contact

**Tim Kipper** – Sales Professional → Software Engineer

Building technical skills for GTM Engineer roles in AI/Crypto/Fintech

GitHub: [@ScientiaCapital](https://github.com/ScientiaCapital)

---

**MIT License** • Built with Python, Playwright, Streamlit, Plotly
