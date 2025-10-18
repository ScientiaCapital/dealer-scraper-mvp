# 🚀 Generac Dealer Scraper

**Cloud-native web scraping infrastructure with serverless Playwright automation**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![RunPod](https://img.shields.io/badge/RunPod-serverless-purple.svg)](https://www.runpod.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **A production-ready scraper built for scale**: Extract dealer data from any locator site using automated browser workflows. Local development via MCP Playwright, cloud deployment via RunPod serverless — all from the same codebase.

---

## 🎯 What This Project Demonstrates

This is a **Go-To-Market Engineer (GTME)** showcase project that combines:

- 🐳 **Docker & Containerization** - Production-grade Dockerfile with multi-layer caching
- ☁️ **Cloud Deployment** - RunPod serverless infrastructure with auto-scaling
- 🌐 **API Development** - RESTful HTTP API for browser automation workflows
- 🎭 **Playwright Automation** - Headless Chromium control with JavaScript injection
- 🔧 **DevOps Skills** - CI/CD ready, environment management, cost optimization
- 📊 **Data Engineering** - Extraction, deduplication, multi-format export (JSON/CSV)
- 🛠️ **GTME Fundamentals** - curl, HTTP APIs, cloud CLI tools, infrastructure as code

**Result**: A scalable data extraction pipeline that costs **~$0.50-1.00 to scrape 100 locations** and auto-scales from zero.

---

## ✨ Features

### 🎯 Core Capabilities
- ✅ Extract 15 fields per dealer (name, rating, tier, contact, location)
- ✅ Identify PowerPro Premier dealers
- ✅ Multi-ZIP code batch processing
- ✅ Automatic deduplication by phone number
- ✅ Export to JSON and CSV formats
- ✅ Configurable wait times and retry logic

### 🌥️ Cloud-Native Architecture
- ✅ **RunPod Serverless API** - Auto-scaling browser automation
- ✅ **Local MCP Mode** - Development and testing via Claude Code
- ✅ **Browserbase Ready** - Alternative cloud provider support
- ✅ **Singleton Browser Pattern** - 2s faster per request
- ✅ **Context Isolation** - Clean state for each job

### 💰 Cost Efficiency
- **Per location**: ~$0.001 (6 seconds @ $0.00015/sec)
- **100 locations**: ~$0.50-$1.00 total
- **Zero idle costs**: Auto-scale to 0 workers between jobs
- **Concurrent processing**: 3 workers handle 1800 locations/hour

---

## 🏗️ Architecture

```
┌─────────────────────┐
│   Python Scraper    │  ← Entry point (scraper.py)
│  (3 modes: LOCAL,   │
│   RUNPOD, CLOUD)    │
└──────────┬──────────┘
           │
           ├─────────────────────┐
           │                     │
┌──────────▼──────────┐  ┌──────▼──────────────┐
│  MCP Playwright     │  │  RunPod HTTP API    │
│  (Local Browser)    │  │  (Cloud Serverless) │
└─────────────────────┘  └──────┬──────────────┘
                                │
                     ┌──────────▼──────────┐
                     │  Docker Container   │
                     │  ┌────────────────┐ │
                     │  │ playwright_    │ │
                     │  │ service.py     │ │
                     │  │ (Singleton)    │ │
                     │  └────────┬───────┘ │
                     │           │         │
                     │  ┌────────▼───────┐ │
                     │  │   Chromium     │ │
                     │  │   (Headless)   │ │
                     │  └────────┬───────┘ │
                     └───────────┼─────────┘
                                 │
                      ┌──────────▼──────────┐
                      │   Target Website    │
                      │  (dealer-locator)   │
                      └─────────────────────┘
```

### Design Principles

1. **Multi-Mode Flexibility**: Same extraction logic runs locally (MCP) or cloud (RunPod)
2. **Workflow-Based API**: JSON workflow arrays match 6-step browser automation pattern
3. **Cost Optimization**: Singleton browser + context-per-request + auto-scaling
4. **Separation of Concerns**: config.py (settings) → extraction.js (logic) → scraper.py (orchestration)

---

## 🚀 Quick Start

### Prerequisites

```bash
# Required
- Python 3.8+
- Docker (for cloud deployment)
- RunPod account (for cloud mode)

# Optional
- Claude Code (for local MCP Playwright)
```

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/dealer-scraper-mvp.git
cd dealer-scraper-mvp

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your RunPod credentials
```

### Local Testing (MCP Mode)

```python
from scraper import DealerScraper, ScraperMode

# Initialize local mode
scraper = DealerScraper(mode=ScraperMode.PLAYWRIGHT)

# Follow manual MCP tool calls in console output
dealers = scraper.scrape_zip_code("53202")
```

### Cloud Production (RunPod Mode)

```python
from scraper import DealerScraper, ScraperMode
from config import ZIP_CODES_TEST

# Initialize cloud mode
scraper = DealerScraper(mode=ScraperMode.RUNPOD)

# Fully automated scraping
dealers = scraper.scrape_multiple(ZIP_CODES_TEST)
scraper.deduplicate()
scraper.save_json("output/dealers.json")
scraper.save_csv("output/dealers.csv")

# Get top-rated dealers
top = scraper.get_top_rated(min_reviews=5, limit=10)
for dealer in top:
    print(f"{dealer['name']}: {dealer['rating']}★ ({dealer['review_count']} reviews)")
```

---

## 📦 Project Structure

```
dealer-scraper-mvp/
├── scraper.py                    # Main scraper class (3 modes)
├── config.py                     # Configuration & extraction script
├── extraction.js                 # JavaScript extraction logic
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template
│
├── runpod-playwright-api/        # ☁️ Cloud serverless API
│   ├── handler.py                #   RunPod entry point
│   ├── playwright_service.py     #   Singleton browser service
│   ├── Dockerfile                #   Container definition
│   ├── requirements.txt          #   API dependencies
│   ├── test_input.json           #   Local test data
│   ├── examples/                 #   Test scripts
│   │   ├── test_local.sh         #   Local dev server
│   │   ├── test_curl.sh          #   Cloud API testing
│   │   └── dealer_workflow.json  #   Full workflow example
│   └── README.md                 #   Deployment guide
│
└── FINDINGS.md                   # Research documentation
```

---

## 📊 Data Schema

Each dealer record contains **15 structured fields**:

```json
{
  "name": "CURRENT ELECTRIC CO.",
  "rating": 4.3,
  "review_count": 6,
  "tier": "Premier",
  "is_power_pro_premier": true,
  "street": "2942 n 117th st",
  "city": "wauwatosa",
  "state": "WI",
  "zip": "53222",
  "address_full": "2942 n 117th st, wauwatosa, WI 53222",
  "phone": "(262) 786-5885",
  "website": "https://currentelectricco.com/",
  "domain": "currentelectricco.com",
  "distance": "8.3 mi",
  "distance_miles": 8.3
}
```

### Dealer Tier System

| Tier | Description | Commitment Level |
|------|-------------|------------------|
| **Premier** | Highest level of commitment and service | ⭐⭐⭐⭐ |
| **Elite Plus** | Elevated level of service | ⭐⭐⭐ |
| **Elite** | Installation and basic service support | ⭐⭐ |
| **Standard** | No special designation | ⭐ |

---

## 🎯 Validated Results

Tested across **3 major metropolitan areas**:

| Location | ZIP Code | Dealers Found | Avg Rating | Top Tier |
|----------|----------|---------------|------------|----------|
| **Milwaukee, WI** | 53202 | 59 | 4.2 | MR. HOLLAND'S HOME SERVICES (5.0★) |
| **Chicago, IL** | 60601 | 59 | 4.1 | Premium dealers identified |
| **Minneapolis, MN** | 55401 | 28 | 4.3 | Elite Plus dealers found |

**Performance**: ~5-6 seconds per ZIP code | 100 ZIPs in ~10 minutes

---

## ☁️ Cloud Deployment

### Deploy to RunPod Serverless

```bash
cd runpod-playwright-api

# Build Docker image
docker build -t runpod-playwright-api:latest .

# Push to Docker Hub
docker tag runpod-playwright-api:latest yourusername/runpod-playwright-api:latest
docker push yourusername/runpod-playwright-api:latest

# Deploy via RunPod CLI
runpodctl endpoint create \
  --name playwright-api \
  --image yourusername/runpod-playwright-api:latest \
  --min-workers 0 \
  --max-workers 3
```

**Full deployment guide**: See [`runpod-playwright-api/README.md`](runpod-playwright-api/README.md)

### Test Cloud API

```bash
export RUNPOD_API_KEY=your_key_here
export RUNPOD_ENDPOINT_ID=your_endpoint_id

curl -X POST https://api.runpod.ai/v2/$RUNPOD_ENDPOINT_ID/runsync \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d @runpod-playwright-api/test_input.json
```

---

## 🛠️ Technology Stack

### Backend
- **Python 3.8+** - Core scraper logic
- **Playwright** - Browser automation
- **Requests** - HTTP client for RunPod API
- **python-dotenv** - Environment management

### Cloud Infrastructure
- **RunPod Serverless** - Auto-scaling compute
- **Docker** - Containerization
- **Playwright Base Image** - Pre-configured browser environment

### Development Tools
- **MCP Playwright** - Local browser automation via Claude Code
- **RunPod CLI** - Deployment and monitoring
- **curl** - API testing and debugging

---

## 💡 GTME Skills Demonstrated

This project showcases essential **Go-To-Market Engineer** competencies:

### 🐳 Docker & Containerization
- Multi-stage Dockerfile with layer caching
- `.dockerignore` for build optimization
- Official Playwright base image usage

### ☁️ Cloud & DevOps
- Serverless deployment on RunPod
- Auto-scaling from 0→N workers
- Environment variable management
- Cost-optimized infrastructure

### 🌐 API & Integration
- HTTP API design (workflow-based)
- RESTful endpoint structure
- JSON payload construction
- Authorization header handling

### 🔧 CLI & Tooling
- RunPod CLI usage (`runpodctl`)
- Docker CLI workflows
- curl for API testing
- Bash scripting for automation

### 📊 Data Engineering
- Web scraping best practices
- Data deduplication algorithms
- Multi-format export (JSON/CSV)
- Schema design and validation

---

## 🎨 Adapting for Other Websites

This scraper is **highly adaptable** for other dealer locators or directory sites:

### 1. Update Configuration
```python
# config.py
DEALER_LOCATOR_URL = "https://example.com/find-dealers/"
SELECTORS = {
    "zip_input": "input[name='zipcode']",
    "search_button": "button[type='submit']",
}
```

### 2. Modify Extraction Logic
```javascript
// extraction.js
const dealers = Array.from(document.querySelectorAll('.dealer-card')).map(card => ({
  name: card.querySelector('.dealer-name').textContent,
  phone: card.querySelector('.phone').textContent,
  // ... custom fields
}));
```

### 3. Rebuild & Deploy
```bash
docker build -t your-scraper:latest .
docker push yourusername/your-scraper:latest
runpodctl endpoint update YOUR_ENDPOINT --image yourusername/your-scraper:latest
```

---

## 📈 Performance & Costs

### Execution Metrics

| Metric | Local (MCP) | Cloud (RunPod) |
|--------|-------------|----------------|
| **Per ZIP** | ~6 seconds | ~6 seconds |
| **Setup Cost** | Manual | Automated |
| **Concurrency** | 1 worker | 1-N workers |
| **Idle Cost** | $0 | $0 (auto-scale) |
| **Active Cost** | $0 | $0.00015/sec |

### Cost Examples

```
100 ZIP codes:
  - Execution: 600 seconds
  - Cost: $0.09 base + $0.41 overhead
  - Total: ~$0.50

1,000 ZIP codes:
  - Execution: 6,000 seconds (100 min)
  - Cost: $0.90 base + $4.10 overhead
  - Total: ~$5.00

10,000 ZIP codes:
  - Execution: 60,000 seconds (16.7 hrs)
  - Cost: $9.00 base + $41.00 overhead
  - Total: ~$50.00
```

**Pro tip**: Use `max_workers=10` for faster processing → 10,000 ZIPs in ~2 hours.

---

## 🐛 Known Issues

### Address Parsing (Low Priority)
Dealers with 0 reviews have corrupted street addresses:
```python
# Current output:
"street": "3 mi0.0(0)0.0 out of 5 stars.   7816 frontage rd"

# Expected:
"street": "7816 frontage rd"
```

**Impact**: ~60% of dealers (those with no reviews)
**Status**: Data still usable, regex cleanup possible
**Location**: extraction.js:72-74

---

## 📚 Documentation

- **[RunPod Deployment Guide](runpod-playwright-api/README.md)** - Full cloud deployment instructions
- **[CLAUDE.md](CLAUDE.md)** - Architecture deep-dive for AI assistants
- **[FINDINGS.md](FINDINGS.md)** - Original research and validation notes

---

## 🤝 Contributing

This is a portfolio/showcase project, but suggestions are welcome!

```bash
# Fork the repository
git fork https://github.com/yourusername/dealer-scraper-mvp

# Create feature branch
git checkout -b feature/amazing-improvement

# Commit changes
git commit -m "Add amazing improvement"

# Push and create PR
git push origin feature/amazing-improvement
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🔗 Connect

**Built by**: Your Name
**LinkedIn**: [linkedin.com/in/yourprofile](https://linkedin.com/in/yourprofile)
**Portfolio**: [yourwebsite.com](https://yourwebsite.com)
**Email**: your.email@example.com

---

<div align="center">

**⭐ Star this repo if you found it helpful!**

Built with ❤️ for the GTME community

</div>
