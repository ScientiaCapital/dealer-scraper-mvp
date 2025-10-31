# API Keys Setup Guide

This guide will help you gather all the necessary API keys for the Coperniq Partner Prospecting System.

## Quick Start

1. Open the `.env` file in your workspace
2. Follow the sections below to get each API key
3. Paste the keys into the corresponding variables in `.env`
4. Save the file

---

## Required for Testing (Choose One)

### Option 1: Playwright Mode (Local - No API Keys Needed)

**Best for:** Testing and development

**Setup:**
```bash
pip install playwright
playwright install chromium
```

**Usage:**
```python
from scrapers.generac_scraper import GeneracScraper
from scrapers.base_scraper import ScraperMode

scraper = GeneracScraper(mode=ScraperMode.PLAYWRIGHT)
scraper.scrape_zip_code("53202")  # Follow manual workflow instructions
```

**Pros:** Free, no API keys needed
**Cons:** Manual workflow, not automated

---

### Option 2: RunPod Mode (Cloud - Automated)

**Best for:** Production scraping at scale

**Get API Keys:**

1. **Sign up:** https://www.runpod.io/
2. **Get API Key:**
   - Go to: https://www.runpod.io/console/user/settings
   - Click "API Keys"
   - Create new API key
   - Copy the key → Paste into `.env` as `RUNPOD_API_KEY`

3. **Deploy Endpoint:**
   - Build Docker image from `runpod-playwright-api/`
   - Push to Docker Hub or RunPod registry
   - Create serverless endpoint
   - Copy endpoint ID → Paste into `.env` as `RUNPOD_ENDPOINT_ID`

**Detailed Deployment Guide:** See `runpod-playwright-api/README.md`

**Cost:** ~$0.001 per ZIP code (~$0.50 for full SREC state run)

**Usage:**
```python
from scrapers.generac_scraper import GeneracScraper
from scrapers.base_scraper import ScraperMode

scraper = GeneracScraper(mode=ScraperMode.RUNPOD)
dealers = scraper.scrape_multiple(["53202", "60601", "55401"])
```

---

### Option 3: Browserbase Mode (Cloud - Automated Alternative)

**Best for:** Alternative to RunPod with simpler setup

**Get API Keys:**

1. **Sign up:** https://www.browserbase.com/
2. **Get API Key:**
   - Go to dashboard
   - Navigate to Settings → API Keys
   - Create new API key
   - Copy the key → Paste into `.env` as `BROWSERBASE_API_KEY`

3. **Get Project ID:**
   - Go to Projects
   - Create or select a project
   - Copy project ID → Paste into `.env` as `BROWSERBASE_PROJECT_ID`

**Install Playwright:**
```bash
pip install playwright
playwright install chromium
```

**Cost:** Check Browserbase pricing (session-based)

**Usage:**
```python
from scrapers.generac_scraper import GeneracScraper
from scrapers.base_scraper import ScraperMode

scraper = GeneracScraper(mode=ScraperMode.BROWSERBASE)
dealers = scraper.scrape_multiple(["53202", "60601", "55401"])
```

---

## Future Integrations (Optional)

### Apollo.io (Contact Enrichment)

**Purpose:** Enrich leads with employee count, revenue estimates, LinkedIn URLs

**Get API Key:**
1. Sign up: https://www.apollo.io/
2. Go to: https://app.apollo.io/#/settings/integrations/api
3. Copy API key → Paste into `.env` as `APOLLO_API_KEY`

**Usage:**
```bash
python scripts/enrich_with_apollo.py --input output/leads.csv
```

---

### Clay (Advanced Enrichment)

**Purpose:** Advanced enrichment waterfall (email finding, social profiles, etc.)

**Get Webhook URL:**
1. Sign up: https://clay.com/
2. Create a new table
3. Add webhook trigger
4. Copy webhook URL → Paste into `.env` as `CLAY_WEBHOOK_URL`

**Usage:**
```bash
python scripts/enrich_with_clay.py --input output/leads.csv
```

---

### Close CRM (Lead Management)

**Purpose:** Import leads into Close CRM, create Smart Views, manage pipeline

**Get API Key:**
1. Sign up: https://close.com/
2. Go to: https://app.close.com/settings/api/
3. Create new API key
4. Copy key → Paste into `.env` as `CLOSE_API_KEY`

**Usage:**
```bash
python scripts/upload_to_close.py --input output/coperniq_leads.csv
```

---

## Testing Your Setup

### Test Playwright Mode (No API Keys)

```bash
python -c "
from scrapers.generac_scraper import GeneracScraper
from scrapers.base_scraper import ScraperMode

scraper = GeneracScraper(mode=ScraperMode.PLAYWRIGHT)
scraper.scrape_zip_code('53202')
"
```

### Test RunPod Mode

```bash
python -c "
from scrapers.generac_scraper import GeneracScraper
from scrapers.base_scraper import ScraperMode

scraper = GeneracScraper(mode=ScraperMode.RUNPOD)
dealers = scraper.scrape_zip_code('53202')
print(f'Found {len(dealers)} dealers')
"
```

### Test Browserbase Mode

```bash
python -c "
from scrapers.generac_scraper import GeneracScraper
from scrapers.base_scraper import ScraperMode

scraper = GeneracScraper(mode=ScraperMode.BROWSERBASE)
dealers = scraper.scrape_zip_code('53202')
print(f'Found {len(dealers)} dealers')
"
```

---

## Troubleshooting

### "Missing RunPod credentials" Error

**Solution:** Make sure you've added both `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` to `.env`

### "Missing Browserbase credentials" Error

**Solution:** Make sure you've added both `BROWSERBASE_API_KEY` and `BROWSERBASE_PROJECT_ID` to `.env`

### "playwright package not found" Error

**Solution:** 
```bash
pip install playwright
playwright install chromium
```

### Environment Variables Not Loading

**Solution:** Make sure `.env` file is in the project root directory:
```bash
ls -la /Users/tmkipper/Desktop/dealer-scraper-mvp/.env
```

---

## Security Reminders

- ✅ `.env` is in `.gitignore` (never commit API keys)
- ✅ `.env.example` is safe to commit (no real keys)
- ⚠️ Never share your `.env` file
- ⚠️ Never paste API keys in public channels
- ⚠️ Rotate keys if accidentally exposed

---

## Next Steps

Once you have your API keys configured:

1. **Test with a single ZIP:**
   ```bash
   python scripts/generate_leads.py --mode runpod --states CA --limit-zips 1
   ```

2. **Run a small batch:**
   ```bash
   python scripts/generate_leads.py --mode runpod --states CA --limit-zips 5
   ```

3. **Full production run:**
   ```bash
   python scripts/generate_leads.py --mode runpod --states CA TX PA MA NJ FL
   ```

4. **Review output:**
   - Check `output/coperniq_leads_YYYYMMDD_HHMMSS.csv`
   - HIGH priority (80-100) = call first
   - MEDIUM priority (50-79) = call second
   - LOW priority (<50) = call last or skip

---

## Support

- **Documentation:** See `CLAUDE.md`, `README.md`, `QUICKSTART.md`
- **RunPod Deployment:** See `runpod-playwright-api/README.md`
- **Issues:** Check `FINDINGS.md` for known issues


