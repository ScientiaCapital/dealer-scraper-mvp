# 🏗️ Multi-OEM Dealer Network Scraper

> **Automated lead generation system across 17 OEM dealer networks - showcasing Python, automation, and data engineering skills**

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/playwright-automated-green.svg)](https://playwright.dev/)
[![Streamlit](https://img.shields.io/badge/streamlit-dashboard-red.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 Overview

An automated web scraping system that aggregates contractor data across 17 OEM dealer networks (generators, solar, batteries) with intelligent deduplication, cross-referencing, and lead scoring capabilities.

### Key Features

- **17 OEM Integrations**: Generac, Tesla, Enphase, SolarEdge, Cummins, Briggs & Stratton, Kohler, and 10 more
- **National Coverage**: All 50 US states via 137 major metro ZIP codes
- **Smart Deduplication**: 97%+ duplicate removal via phone/domain/name matching  
- **Real-time Monitoring**: Streamlit dashboard with live progress tracking
- **Scalable Architecture**: Factory pattern + abstract base classes for easy OEM additions

---

## 📊 Live Scraping Demo

### National Run - All 50 States (137 Major Metro ZIPs)

```bash
======================================================================
CUMMINS RESIDENTIAL STANDBY - NATIONAL RUN (ALL 50 STATES)
======================================================================
Started: 2025-10-28 06:30:37
ZIP Codes: 137 (137 major metro ZIPs across 50 states)
Strategy: Save checkpoint every 10 ZIPs
======================================================================

📍 Scraping 137 ZIP codes...

[1/137] Scraping ZIP 02101...
  → Navigating to Cummins dealer locator...
  → Checking for cookie consent dialog...
  → Finding form iframe...
  → Filling form for ZIP 02101...
  → Submitting search...
  → Waiting for results...
  → Extracting dealer data...
  → Found 200 dealers
   ✓ Found 200 dealers (Total: 200)

[10/137] Scraping ZIP 12207...
   ✓ Found 200 dealers (Total: 2000)
      💾 Saved checkpoint: 2000 dealers

[137/137] Scraping ZIP 96720...
   ✓ Found 200 dealers (Total: 27200)

✅ Scraping complete!
   Total dealers found: 27,200

======================================================================
DEDUPLICATING DEALERS BY PHONE NUMBER
======================================================================
Removed 26,489 duplicate dealers (by phone)

📊 Deduplication Results:
   • Before: 27,200 dealers
   • After: 711 unique dealers
   • Removed: 26,489 duplicates (97.4%)
```

### Performance Metrics

| OEM | ZIPs Scraped | Raw Dealers | Unique Dealers | Dedup Rate | Runtime |
|-----|-------------|-------------|----------------|------------|---------|
| **Cummins** | 137 | 27,200 | 711 | 97.4% | ~60 min |
| **Briggs & Stratton** | 137 | ~1,370 | ~140 | ~90% | ~60 min |
| **Generac** | 137 | ~27,000 | ~700 | ~97% | ~60 min |
| **TOTAL** | 411 | ~55,000+ | **~1,500** | ~97% | ~3 hours |

---

## 🏗️ Architecture

### Multi-OEM Scraper Framework

```
┌─────────────────────────────────────────────────────────────┐
│                    ScraperFactory                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ OEM Registration (17 Total)                          │   │
│  │  • Generac          • Enphase        • GoodWe       │   │
│  │  • Tesla            • SolarEdge      • Growatt      │   │
│  │  • Cummins          • Fronius        • Sungrow      │   │
│  │  • Briggs & Stratton • SMA           • ABB          │   │
│  │  • Kohler           • Sol-Ark        • Delta        │   │
│  │  • SimpliPhi        • Tigo                          │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              BaseDealerScraper (Abstract)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Core Workflow (All OEMs)                            │   │
│  │  1. Navigate to dealer locator                      │   │
│  │  2. Handle cookie consent                           │   │
│  │  3. Fill ZIP code form                              │   │
│  │  4. Submit search                                   │   │
│  │  5. Wait for AJAX results                           │   │
│  │  6. Execute extraction script                       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Patterns

- **Abstract Base Class**: Extensible framework for adding new OEMs
- **Factory Pattern**: Dynamic scraper instantiation  
- **Singleton Pattern**: Optimized browser resource management
- **Standardized Data Models**: Type-safe dataclasses across all sources

---

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.13+
python --version

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Run Your First Scrape

**Single OEM:**
```bash
python3 scripts/run_generac_production.py

# Output: output/generac_dealers_YYYYMMDD.csv
```

**National Coverage (All 50 states):**
```bash
# Run all three OEMs
python3 scripts/run_cummins_national.py    # ~60 min
python3 scripts/run_briggs_national.py     # ~60 min
python3 scripts/run_generac_national.py    # ~60 min

# Combine into master list
python3 scripts/combine_national_oems.py

# Output: output/grand_master_national_YYYYMMDD.csv
```

### Real-time Dashboard

```bash
streamlit run streamlit_monitor.py
```

Opens live dashboard at http://localhost:8501 with:
- Real-time progress tracking
- Performance charts
- Recent activity logs
- Auto-refresh every 5 seconds

---

## 📁 Project Structure

```
dealer-scraper-mvp/
├── scrapers/
│   ├── base_scraper.py              # Abstract base class
│   ├── scraper_factory.py           # OEM registration & factory
│   ├── generac_scraper.py           # Generac (custom navigation)
│   ├── cummins_scraper.py           # Cummins (generic scraper)
│   └── [15 more OEM scrapers]       # All registered in factory
├── scripts/
│   ├── run_*_national.py            # National run scripts
│   ├── combine_national_oems.py     # Master list combiner
│   └── generate_gtm_deliverables.py # Marketing exports
├── analysis/
│   └── multi_oem_detector.py        # Cross-reference detection
├── targeting/
│   ├── srec_itc_filter.py           # Geographic filtering
│   └── icp_filter.py                # Lead scoring (0-100)
├── config.py                        # ZIP code lists
├── streamlit_monitor.py             # Real-time dashboard
└── README.md                        # This file
```

---

## 💡 Technical Highlights

### 1. Intelligent Deduplication

Multi-key matching algorithm:
- **Phone normalization**: Strip to digits only
- **Domain extraction**: Root domain matching  
- **Fuzzy name matching**: High-threshold similarity

Achieves **97.4% duplicate removal** rate across sources.

### 2. Cross-OEM Detection

Identifies contractors certified with multiple brands:
```python
# Example: Contractor in 3 networks
{
  "name": "ABC Electric",
  "oem_certifications": ["Generac", "Tesla", "Enphase"],
  "confidence": 100,  # All signals match
  "multi_oem_score": 100
}
```

### 3. Checkpoint-Based Progress

Auto-saves every 10 ZIPs to prevent data loss:
```
output/cummins_national_checkpoint_10_*.json  # 2,000 dealers
output/cummins_national_checkpoint_20_*.json  # 4,000 dealers
...
output/cummins_national_checkpoint_130_*.json # 26,000 dealers
```

### 4. Scalable Factory Pattern

Adding a new OEM requires only:
```python
# 1. Create scraper class
class NewOEMScraper(BaseDealerScraper):
    def get_extraction_script(self): ...

# 2. Register in factory
ScraperFactory.register("NewOEM", NewOEMScraper)

# 3. Use immediately
scraper = ScraperFactory.create("NewOEM")
```

---

## 📊 Results Summary

### National Run (137 ZIPs, 50 states)

| OEM | Raw Dealers | Unique Dealers | Dedup Rate |
|-----|-------------|----------------|------------|
| **Cummins** | 27,200 | 711 | 97.4% |
| **Briggs** | ~1,370 | ~140 | ~90% |
| **Generac** | ~27,000 | ~700 | ~97% |

**Grand Master List:** ~1,500 unique contractors nationwide

**Key Insight:** 97%+ duplication rate shows OEMs return same dealers across multiple ZIPs (broad geographic coverage per dealer).

---

## 🛠️ Technology Stack

### Core
- **Python 3.13** - Modern async/await support
- **Playwright** - Headless browser automation
- **Streamlit** - Real-time dashboard
- **Plotly** - Interactive charts

### Data Engineering
- **Pandas** - Data manipulation
- **JSON/CSV** - Standardized exports
- **Multi-key deduplication** - Phone/domain/name matching

### Architecture
- **Abstract Base Classes** - Extensible design
- **Factory Pattern** - Dynamic instantiation
- **Singleton Pattern** - Resource optimization
- **Dataclasses** - Type-safe models

---

## 🎓 Skills Demonstrated

### Python & Software Engineering
- ✅ Object-oriented design (ABC, Factory, Singleton patterns)
- ✅ Type safety with dataclasses
- ✅ Async/await for concurrency
- ✅ Error handling & retry logic
- ✅ Logging & monitoring

### Data Engineering
- ✅ Multi-source data aggregation
- ✅ Record linkage & fuzzy matching
- ✅ Deduplication algorithms (97%+ removal rate)
- ✅ Data normalization & standardization
- ✅ Checkpoint-based ETL pipeline

### Web Scraping & Automation
- ✅ Playwright browser automation
- ✅ Cookie/AJAX/iframe handling
- ✅ JavaScript extraction scripts
- ✅ Rate limiting & politeness
- ✅ Checkpoint-based progress tracking

### DevOps & Tools
- ✅ Git version control
- ✅ Virtual environments
- ✅ Requirements management
- ✅ Environment variables (.env)
- ✅ Real-time dashboards (Streamlit)

---

## 🔮 Roadmap

### ✅ Completed
- [x] 17 OEM scrapers with unified architecture
- [x] National coverage (all 50 states)
- [x] Multi-key deduplication (97%+ removal)
- [x] Real-time Streamlit dashboard
- [x] Cross-OEM detection
- [x] ICP lead scoring

### 🚧 Next Steps
- [ ] Cloud deployment (RunPod serverless)
- [ ] API enrichment (Apollo/Clay)
- [ ] CRM integration (Close/HubSpot)
- [ ] Email/SMS automation

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🤝 Contact

**Tim Kipper** - Sales Professional → Software Engineer

- GitHub: [@ScientiaCapital](https://github.com/ScientiaCapital)
- LinkedIn: [Your LinkedIn]
- Portfolio: [Your Portfolio]

---

**Built with ☕ and 🔥 - Showcasing Python automation & data engineering skills**
