# 🚀 GTM Prospecting System

**Automated contractor lead generation targeting multi-brand installers in SREC states**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![RunPod](https://img.shields.io/badge/RunPod-serverless-purple.svg)](https://www.runpod.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Business Goal**: 10x Sr. BDR productivity via automated prospecting for Coperniq's brand-agnostic monitoring platform

---

## 🎯 What This Does

**Problem**: Finding contractors who need Coperniq most (those managing 2-3 separate monitoring platforms)

**Solution**: Scrape OEM dealer networks → Cross-reference → Score → Prioritize

**Output**: Sorted CSV of scored leads ready for outreach (HIGH priority 80-100 first)

**Target Market**:
- Multi-brand contractors (Generac + Tesla + Enphase)
- SREC states (CA, TX, PA, MA, NJ, FL) - sustainable post-ITC markets
- Commercial capability (ITC deadline urgency: June 30, 2026 safe harbor)

**Unique Value**: Coperniq is the **only** brand-agnostic monitoring platform for microinverters + batteries + generators

---

## ⚡ Quick Start (5 Minutes)

### Prerequisites
- Python 3.8+
- RunPod account (get $10 free credit at [runpod.io](https://runpod.io))

### 1. Install
```bash
git clone https://github.com/ScientiaCapital/dealer-scraper-mvp.git
cd dealer-scraper-mvp
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env and add:
#   RUNPOD_API_KEY=your_key_here
#   RUNPOD_ENDPOINT_ID=your_endpoint_here
```

Get credentials from: https://www.runpod.io/console/serverless

### 3. Generate Leads (MVP - Generac Only)
```bash
python scripts/generate_leads.py --mode runpod --states CA --limit-zips 5
```

### 4. Review Output
```bash
# Open the scored CSV (sorted HIGH → MEDIUM → LOW)
open output/coperniq_leads_*.csv
```

**Call HIGH priority leads first (score 80-100)** ← Multi-brand contractors in prime SREC states

---

## 📊 Coperniq Lead Scoring (0-100)

Each contractor gets scored across 5 dimensions:

| Dimension | Weight | What It Means |
|-----------|--------|---------------|
| **Multi-OEM Presence** | 40 pts | 3+ OEMs = 40pts (desperately need unified platform)<br>2 OEMs = 25pts (strong prospect)<br>1 OEM = 10pts (lower priority) |
| **SREC State Priority** | 20 pts | HIGH states (CA, TX, PA, MA, NJ, FL) = 20pts<br>Sustainable market post-ITC expiration |
| **Commercial Capability** | 20 pts | 50+ employees = 20pts<br>10-50 = 15pts<br>5-10 = 10pts<br><5 = 5pts |
| **Geographic Value** | 10 pts | Top 10 wealthy ZIPs in state = 10pts<br>High-value territories |
| **ITC Urgency** | 10 pts | CRITICAL (commercial Q2 2026 deadline) = 10pts<br>HIGH (residential Dec 2025) = 7pts |

**Priority Tiers**:
- **HIGH (80-100)**: Call first - multi-brand contractors in prime markets
- **MEDIUM (50-79)**: Call second - solid prospects
- **LOW (<50)**: Call last or skip - lower priority

---

## 🏗️ Architecture

### Multi-OEM Scraper Framework

```
┌─────────────────────────────────────────────────────────────┐
│                    Lead Generation Pipeline                  │
└─────────────────────────────────────────────────────────────┘

Step 1: SCRAPE
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │   Generac    │  │    Tesla     │  │   Enphase    │
  │   Dealers    │  │  Powerwall   │  │  Installers  │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                 │
         └─────────────────┴─────────────────┘
                           │
Step 2: CROSS-REFERENCE    ▼
         ┌──────────────────────────────┐
         │  Multi-OEM Detector          │
         │  • Phone matching (primary)   │
         │  • Domain matching (secondary)│
         │  • Fuzzy name match (tertiary)│
         └──────────────┬───────────────┘
                        │
Step 3: FILTER TO SREC  ▼
         ┌──────────────────────────────┐
         │  SREC State Filter           │
         │  • CA, TX, PA, MA, NJ, FL     │
         │  • ITC urgency tagging        │
         └──────────────┬───────────────┘
                        │
Step 4: SCORE          ▼
         ┌──────────────────────────────┐
         │  Coperniq Lead Scorer        │
         │  • 5-dimension 0-100 score    │
         │  • Priority tier assignment   │
         └──────────────┬───────────────┘
                        │
Step 5: EXPORT         ▼
         ┌──────────────────────────────┐
         │  Sorted CSV (HIGH first)     │
         │  Ready for outreach          │
         └──────────────────────────────┘
```

### Key Components

**OEM Scrapers** (`scrapers/`):
- `GeneracScraper` - ✅ Production (tested extraction)
- `TeslaScraper` - ⏳ Structure ready (extraction TBD)
- `EnphaseScraper` - ⏳ Structure ready (extraction TBD)

**Analysis** (`analysis/`):
- `MultiOEMDetector` - Cross-reference contractors by phone/domain/name

**Targeting** (`targeting/`):
- `SRECITCFilter` - Filter to SREC states + ITC urgency tagging
- `CoperniqLeadScorer` - Multi-dimensional 0-100 scoring

**Orchestration** (`scripts/`):
- `generate_leads.py` - End-to-end pipeline (scrape → score → CSV)

---

## 💰 Cost & Performance

### MVP (Generac Only)

| Metric | Value |
|--------|-------|
| **Per ZIP** | ~6 seconds, $0.001 |
| **100 ZIPs** | ~10 min, $0.50-1.00 |
| **Full SREC Run** (~75 ZIPs) | ~10-15 min, $0.50 |
| **Idle Cost** | $0 (auto-scale to zero) |

### Multi-OEM (Future)

Once Tesla + Enphase scrapers are implemented:
- **3 OEM networks** × 75 ZIPs = ~225 scrapes
- **Time**: ~30-40 minutes
- **Cost**: ~$1.50-2.00
- **Output**: Contractors in 2-3 networks (highest value!)

---

## 🎯 Market Context

### Federal ITC Deadlines (Creates Urgency)

- **Residential ITC**: Expires December 31, 2025
- **Commercial Safe Harbor**: Projects must start by June 30, 2026
- Creates time-sensitive opportunities for contractor outreach

### SREC States (Sustainable Post-ITC)

States with Solar Renewable Energy Credit programs that continue after federal ITC expires:

| State | Program | Priority |
|-------|---------|----------|
| **California** | SGIP + NEM 3.0 | HIGH |
| **Texas** | Deregulated + ERCOT | HIGH |
| **Pennsylvania** | PA SREC | HIGH |
| **Massachusetts** | SREC II + SMART | HIGH |
| **New Jersey** | NJ TREC | HIGH |
| **Florida** | Net Metering + Tax Exemptions | HIGH |

### Coperniq's Unique Position

**Problem**: Contractors managing multiple brands need 3+ separate platforms:
- Enphase Enlighten (microinverters)
- Tesla app (Powerwall batteries)
- Generac Mobile Link (generators)

**Solution**: Coperniq = Only brand-agnostic monitoring platform
- Single dashboard for all brands
- Unified customer experience
- Production + consumption monitoring

**Target**: Multi-brand contractors (2-3 OEMs) = highest value prospects

---

## 📈 Usage Examples

### Test Run (5 California ZIPs)
```bash
python scripts/generate_leads.py --mode runpod --states CA --limit-zips 5
```

### Production Run (All SREC States)
```bash
python scripts/generate_leads.py --mode runpod --states CA TX PA MA NJ FL
```

### Multi-State Custom
```bash
python scripts/generate_leads.py --mode runpod --states CA TX --limit-zips 10
```

### Manual Mode (Local Development)
```bash
python scripts/generate_leads.py --mode playwright --states CA --limit-zips 1
# Follow MCP Playwright workflow printed to console
```

---

## 🛠️ Technology Stack

### Backend
- **Python 3.8+** - Core orchestration
- **Playwright** - Browser automation (headless Chromium)
- **Requests** - HTTP client for RunPod API
- **python-dotenv** - Environment management

### Cloud Infrastructure
- **RunPod Serverless** - Auto-scaling compute (~$0.001/ZIP)
- **Docker** - Containerization (Playwright base image)
- **Singleton Browser Pattern** - 2s faster per request

### Architecture Patterns
- **Abstract Base Classes** - Extensible OEM scraper framework
- **Factory Pattern** - Dynamic scraper instantiation
- **Multi-Key Matching** - Phone + domain + fuzzy name for cross-referencing
- **Priority Scoring** - Multi-dimensional 0-100 lead prioritization

---

## 📁 Project Structure

```
dealer-scraper-mvp/
├── scripts/
│   └── generate_leads.py          # 🎯 MVP orchestration script
│
├── scrapers/
│   ├── base_scraper.py            # Abstract base + data models
│   ├── generac_scraper.py         # ✅ Production (tested)
│   ├── tesla_scraper.py           # ⏳ Structure ready
│   ├── enphase_scraper.py         # ⏳ Structure ready
│   └── scraper_factory.py         # Factory pattern
│
├── analysis/
│   └── multi_oem_detector.py      # Cross-reference contractors
│
├── targeting/
│   ├── srec_itc_filter.py         # SREC states + ITC urgency
│   └── coperniq_lead_scorer.py    # 0-100 multi-dimensional scoring
│
├── runpod-playwright-api/         # ☁️ Serverless infrastructure
│   ├── handler.py
│   ├── playwright_service.py
│   └── Dockerfile
│
├── config.py                      # ZIP codes + configuration
├── .env.example                   # API key template
├── QUICKSTART.md                  # 5-min setup guide
├── CLAUDE.md                      # Technical docs for AI
└── README.md                      # This file
```

---

## 🔮 Roadmap

### ✅ MVP Complete (Generac Only)
- [x] Multi-OEM scraper framework
- [x] Generac dealer scraper (production-ready)
- [x] SREC state filtering + ITC urgency
- [x] Coperniq lead scoring (0-100)
- [x] Lead generation script
- [x] RunPod serverless deployment

### ⏳ Phase 2: Multi-OEM Detection
- [ ] Tesla Powerwall scraper extraction logic
- [ ] Enphase installer scraper extraction logic
- [ ] Cross-reference contractors (2-3 OEM networks)
- [ ] Multi-OEM score boost (100pts for 3+ brands)

### 🔜 Phase 3: Enrichment & CRM
- [ ] Apollo.io integration (employee count, revenue, LinkedIn)
- [ ] Commercial capability scoring (20 pts)
- [ ] Close CRM bulk import
- [ ] Auto-generated Smart Views by OEM/state/priority

### 🌟 Phase 4: Outreach Automation (10x BDR Goal)
- [ ] Email sequences (SendGrid/Mailgun)
- [ ] SMS campaigns (Twilio)
- [ ] Automated outbound calls
- [ ] AI agent testing

---

## 🔧 Development

### Adding New OEM Scrapers

1. **Inherit from BaseDealerScraper**:
   ```python
   from scrapers.base_scraper import BaseDealerScraper

   class NewOEMScraper(BaseDealerScraper):
       OEM_NAME = "NewOEM"
       DEALER_LOCATOR_URL = "https://..."
       PRODUCT_LINES = ["Solar", "Battery"]
   ```

2. **Implement required methods**:
   - `get_extraction_script()` - JavaScript to extract dealer data
   - `detect_capabilities()` - Map OEM data to capabilities
   - `parse_dealer_data()` - Convert to StandardizedDealer format

3. **Register with factory**:
   ```python
   ScraperFactory.register("NewOEM", NewOEMScraper)
   ```

4. **Use immediately**:
   ```python
   scraper = ScraperFactory.create("NewOEM", mode=ScraperMode.RUNPOD)
   ```

### Testing Changes
```bash
# Test with 1 ZIP
python scripts/generate_leads.py --mode runpod --states CA --limit-zips 1

# Test with 3 ZIPs
python scripts/generate_leads.py --mode runpod --states CA --limit-zips 3
```

---

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get leads in 5 minutes
- **[CLAUDE.md](CLAUDE.md)** - Technical architecture (for AI assistants)
- **[runpod-playwright-api/README.md](runpod-playwright-api/README.md)** - Cloud deployment guide
- **[FINDINGS.md](FINDINGS.md)** - Original research notes (Generac scraper)

---

## 🤝 Contributing

This is a portfolio/showcase project for GTME skills, but suggestions are welcome!

```bash
# Fork & clone
git clone https://github.com/ScientiaCapital/dealer-scraper-mvp.git

# Create feature branch
git checkout -b feature/amazing-improvement

# Commit with detailed message (include business context)
git commit -m "Add XYZ feature for ABC use case"

# Push & create PR
git push origin feature/amazing-improvement
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🔗 Connect

**Built for**: Coperniq.io - Brand-agnostic monitoring platform

**Use Case**: Partner prospecting for multi-brand contractors

**Author**: Sr. BDR leveraging GTME skills to 10x productivity

**Goal**: Automate contractor discovery → enrichment → scoring → outreach

---

<div align="center">

**⭐ Star this repo if you're building GTM automation tools!**

*Showcasing: Web scraping • Cloud automation • Lead scoring • Multi-dimensional prioritization • GTM engineering*

</div>

---

## 🎓 Skills Demonstrated

### 🐳 Docker & Cloud
- Serverless deployment (RunPod)
- Container optimization (Playwright base image)
- Auto-scaling (0→N workers)
- Cost optimization (~$0.001/ZIP)

### 🌐 API & Integration
- HTTP API design (workflow-based)
- RESTful endpoint structure
- Multi-service integration (RunPod, Apollo, Clay, Close)
- API key management (.env patterns)

### 📊 Data Engineering
- Web scraping (Playwright automation)
- Cross-referencing (phone/domain/name matching)
- Fuzzy matching algorithms
- Multi-dimensional scoring
- Deduplication strategies

### 🎯 GTM Engineering
- Lead generation pipeline
- Prioritization algorithms
- SREC market analysis
- ITC deadline awareness
- Territory scoring (wealthy ZIP proximity)

### 🔧 Software Architecture
- Abstract base classes
- Factory pattern
- Singleton pattern
- Workflow orchestration
- Mode switching (PLAYWRIGHT/RUNPOD/BROWSERBASE)

---

**Built with ❤️ for the GTME community**
