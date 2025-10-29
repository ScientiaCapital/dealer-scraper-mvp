# Setup Guide

Complete installation and configuration guide for the Multi-OEM Dealer Network Scraper.

## Prerequisites

- **Python 3.13+** - [Download](https://www.python.org/downloads/)
- **Playwright** (with Chromium) - Installed via pip
- **Git** - [Download](https://git-scm.com/downloads)

## Installation

1. **Clone the repository:**
   ```bash
   git clone [repository-url]
   cd dealer-scraper-mvp
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browser:**
   ```bash
   playwright install chromium
   ```

## Environment Variables

The scraper works out of the box without any API keys. Optional enrichment features require additional setup.

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Required variables:** None (scraping works without API keys)

3. **Optional variables:** See API Key Setup sections below

## API Key Setup (Optional Enrichment)

### Apollo.io Enrichment

Enriches contractor records with employee count, revenue, and LinkedIn profiles.

1. **Sign up at [apollo.io](https://apollo.io)**
2. **Navigate to Settings → Integrations → API**
3. **Copy your API key**
4. **Add to `.env` file:**
   ```bash
   APOLLO_API_KEY=your_key_here
   ```
5. **Usage:** Automatically enriches contractor records during scraping

### Close CRM Integration

Enables bulk import of leads with Smart Views organized by ICP tier.

1. **Log into [Close CRM](https://close.com)**
2. **Navigate to Settings → API Keys → Create New Key**
3. **Copy your API key**
4. **Add to `.env` file:**
   ```bash
   CLOSE_API_KEY=your_key_here
   ```
5. **Usage:** Bulk import leads with Smart Views by ICP tier (GOLD, SILVER, BRONZE)

## Running the Scraper

### Single OEM Test

Test individual OEM scrapers:

```bash
# Test Generac scraper
python3 scripts/run_generac_production.py

# Test other OEMs
python3 scripts/run_briggs_production.py
python3 scripts/run_cummins_production.py
```

### Multi-OEM Production Run

Run all 10 production-tested OEMs across 140 ZIP codes:

```bash
python3 scripts/run_multi_oem_scraping.py \
  --oems Generac "Briggs & Stratton" Cummins Carrier \
         Mitsubishi Trane York SMA Enphase SolarEdge \
  --states CA TX PA MA NJ FL NY OH MD DC DE NH RI CT IL
```

**Parameters:**
- `--oems`: List of OEM names to scrape
- `--states`: Target states for ZIP code selection
- `--limit-zips`: Maximum ZIP codes to process (default: 140)
- `--output-dir`: Output directory (default: `output/`)

### Real-time Dashboard

Monitor scraping progress with live dashboard:

```bash
streamlit run streamlit_monitor.py
```

Access at: `http://localhost:8501`

## Output Files

The scraper generates several output files in the `output/` directory:

### Main Output Files

- **`grandmaster_list_expanded_YYYYMMDD.csv`** - Complete contractor database
  - All 8,277 unique contractors
  - Full contact information and OEM certifications
  - ICP scores and tier classifications

- **`gold_tier_prospects_YYYYMMDD.csv`** - Top 50 prospects
  - ICP score 60-79 (immediate outreach candidates)
  - Highest priority leads for sales team

- **`multi_oem_crossovers_YYYYMMDD.csv`** - Multi-OEM contractors
  - 198 contractors certified by 2+ OEMs
  - Highest value prospects (2.4% of database)

### Additional Files

- **`silver_tier_prospects_YYYYMMDD.csv`** - Nurture campaign targets
- **`bronze_tier_prospects_YYYYMMDD.csv`** - Long-term follow-up
- **`hvac_contractors_YYYYMMDD.csv`** - HVAC-focused contractors (5,035 records)

## Troubleshooting

### Common Issues

**Playwright Installation Errors:**
```bash
# Reinstall Playwright
pip uninstall playwright
pip install playwright
playwright install chromium
```

**Memory Issues:**
- Reduce `--limit-zips` parameter (try 50-100 ZIPs)
- Close other applications to free memory
- Use cloud scraping with RunPod (see Cloud Setup)

**Rate Limiting:**
- Scrapers include 3-5 second delays (already optimized)
- If blocked, wait 10-15 minutes before retrying
- Consider using different IP addresses

**Chrome/Chromium Issues:**
```bash
# Update Chromium
playwright install chromium --force

# Check browser version
playwright --version
```

### Cloud Setup (RunPod)

For large-scale scraping or to avoid local resource constraints:

1. **Set up RunPod API credentials:**
   ```bash
   # Add to .env file
   RUNPOD_API_KEY=your_runpod_key
   RUNPOD_ENDPOINT_ID=your_endpoint_id
   ```

2. **Deploy to RunPod:**
   ```bash
   python3 scripts/deploy_runpod.py
   ```

3. **Run cloud scraping:**
   ```bash
   python3 scripts/run_cloud_scraping.py
   ```

### Performance Optimization

**For Large Datasets:**
- Use `--limit-zips 50` for testing
- Increase to 140 for full production run
- Monitor memory usage with `htop` or Task Manager

**For Faster Scraping:**
- Reduce delays in scraper configs (not recommended)
- Use multiple machines with different IP addresses
- Consider cloud-based solutions

## Support

**Documentation:**
- [README.md](README.md) - Project overview and architecture
- [OEM_SCRAPER_STATUS.md](OEM_SCRAPER_STATUS.md) - Individual scraper status
- [SCRAPER_STATUS.md](docs/SCRAPER_STATUS.md) - Detailed scraper documentation

**Issues:**
- Check existing issues on GitHub
- Create new issue with error logs and system info
- Include Python version, OS, and Playwright version

**Contact:**
- GitHub: [@ScientiaCapital](https://github.com/ScientiaCapital)
- Email: [your-email@domain.com]

---

**MIT License** • Built with Python, Playwright, Streamlit, Plotly