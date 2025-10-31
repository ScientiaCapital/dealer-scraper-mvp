# 🚀 QUICKSTART Guide

**Get Coperniq leads in 15 minutes - Scrape contractor networks, score leads, and start calling**

---

## Prerequisites

✅ Python 3.8+  
✅ RunPod account (for automated cloud scraping) or Browserbase account  
✅ 15 minutes

---

## Quick Start (5 minutes)

### Step 1: Install Dependencies

```bash
cd dealer-scraper-mvp
pip install -r requirements.txt
```

### Step 2: Configure API Keys

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. **For RunPod** (Recommended):
   - Go to https://www.runpod.io/console/serverless
   - Copy your **API Key**
   - Copy your **Endpoint ID** (deploy playwright-api endpoint first, see [RunPod Setup](#runpod-setup))
   - Add to `.env`:
     ```bash
     RUNPOD_API_KEY=your_actual_api_key_here
     RUNPOD_ENDPOINT_ID=your_actual_endpoint_id_here
     ```

3. **For Browserbase** (Alternative):
   - Get credentials from https://www.browserbase.com/dashboard
   - Add to `.env`:
     ```bash
     BROWSERBASE_API_KEY=your_key
     BROWSERBASE_PROJECT_ID=your_project_id
     ```

### Step 3: Test Run (Single State, 3 ZIPs)

Verify everything works before full production:

```bash
python scripts/generate_leads.py --mode runpod --states CA --limit-zips 3
```

**Expected Output:**
- `output/coperniq_leads_YYYYMMDD_HHMMSS.csv` ← **Scored leads ready to call**
- ~50-150 dealers from 3 California ZIPs
- HIGH priority leads (80-100 score) at top of CSV

---

## RunPod Setup

### Option A: Use Existing Docker Image (2 minutes)

Your Docker image is already on Docker Hub:

1. **Deploy to RunPod:**
   - Go to https://www.runpod.io/console/serverless
   - Click **"+ New Endpoint"** with these settings:
     ```
     Docker Image:        tmk74/dealer-scraper:latest
     Container Disk:      10 GB
     Min Workers:         0
     Max Workers:         3
     GPU Type:            None (or CPU)
     Idle Timeout:        5 seconds
     Execution Timeout:   120 seconds    ← CRITICAL: Must be 120s, not 60s
     ```

2. **Add Endpoint ID to .env:**
   ```bash
   echo 'RUNPOD_ENDPOINT_ID=your_endpoint_id_here' >> .env
   ```

3. **Test It:**
   ```bash
   python tests/integration/test_runpod_endpoint.py
   ```
   
   **Expected**: ✅ Status: COMPLETED, Found ~50-60 dealers

### Option B: Rebuild Docker Image (5 minutes)

If Option A fails, rebuild with simplified dependencies:

```bash
cd dealer-scraper-mvp
docker build -f runpod-playwright-api/Dockerfile.minimal \
  -t tmk74/dealer-scraper:minimal .
docker push tmk74/dealer-scraper:minimal
```

Then deploy using `tmk74/dealer-scraper:minimal` as Docker image.

See [Troubleshooting](#troubleshooting) or `docs/troubleshooting/RUNPOD_TROUBLESHOOTING.md` for more help.

---

## Production Run (All SREC States)

Once test run succeeds, scrape all SREC states:

```bash
python scripts/generate_leads.py --mode runpod --states CA TX PA MA NJ FL
```

**What this does:**
1. ✅ Scrapes ~140 wealthy ZIPs across 6 SREC states
2. ✅ Filters to SREC states only (sustainable markets post-ITC)
3. ✅ Scores with Coperniq algorithm (multi-OEM, SREC priority, commercial capability, geography, ITC urgency)
4. ✅ Exports CSV sorted by score (HIGH priority first)

**Estimated time:** ~10-15 minutes  
**Estimated cost:** ~$0.50 (RunPod serverless)  
**Expected output:** 3,000-5,000 leads with scores 0-100

---

## Scoring Breakdown

Each lead gets 0-100 score across 5 dimensions:

| Dimension | Max Points | What It Means |
|-----------|-----------|---------------|
| **Multi-OEM Presence** | 40 | 3+ OEMs = 40pts (desperately need unified platform)<br>2 OEMs = 25pts (strong prospect)<br>1 OEM = 10pts (lower priority) |
| **SREC State Priority** | 20 | HIGH state = 20pts (sustainable post-ITC)<br>MEDIUM state = 10pts |
| **Commercial Capability** | 20 | 50+ employees = 20pts<br>10-50 = 15pts<br>5-10 = 10pts<br><5 = 5pts |
| **Geographic Value** | 10 | Top 10 wealthy ZIPs = 10pts<br>Top 30 wealthy ZIPs = 7pts |
| **ITC Urgency** | 10 | CRITICAL (commercial Q2 2026) = 10pts<br>HIGH (residential Dec 2025) = 7pts |

**Prioritization:**
- **HIGH (80-100)**: Call first - multi-brand contractors in prime SREC states
- **MEDIUM (50-79)**: Call second - solid prospects
- **LOW (<50)**: Call last or skip

---

## Advanced Workflow: Full Enrichment Pipeline

### Step 5: Enrich with Apollo.io (Employee Count, Revenue, Emails)

**What it does:** Adds company data + decision-maker contacts for accurate scoring

```bash
# 1. Get Apollo API key from https://app.apollo.io/#/settings/integrations/api
# 2. Add to .env:
echo "APOLLO_API_KEY=your_apollo_key" >> .env

# 3. Enrich your leads
python scripts/enrichment/enrich_with_apollo.py --input output/generac_master_list.json
```

**Output:** `output/generac_master_list_apollo.json`

**What's added:**
- Employee count (accurate commercial capability scoring - 20 pts)
- Revenue estimate
- Decision-maker emails (Owner, GM, Operations Manager)
- LinkedIn profiles (company + contacts)

### Step 6: Enrich with Clay.com (Waterfall Enrichment) [OPTIONAL]

**What it does:** Adds additional data via waterfall enrichment

```bash
# 1. Create Clay table at https://clay.com
# 2. Add Webhook integration → Copy URL to .env:
echo "CLAY_WEBHOOK_URL=https://clay.com/webhooks/..." >> .env

# 3. Send leads to Clay
python scripts/enrichment/enrich_with_clay.py --input output/generac_master_list_apollo.json
```

**What Clay adds:**
- Additional emails (Apollo → Hunter → Snov.io waterfall)
- Phone validation
- Tech stack (BuiltWith)
- Social profiles (Facebook, Twitter)

### Step 7: Upload to Close CRM (Automated Outreach)

**What it does:** Imports leads with Smart Views for organized calling

```bash
# 1. Get Close CRM API key from https://app.close.com/settings/api/
# 2. Add to .env:
echo "CLOSE_API_KEY=your_close_key" >> .env

# 3. Create custom fields in Close CRM UI (see scripts/crm/close_importer.py docstring)

# 4. Upload leads
python scripts/crm/upload_to_close.py --input output/generac_master_list_apollo.json
```

**What's created:**
- ✅ All contractors imported as leads
- ✅ 6 state-based Smart Views (CA, TX, PA, MA, NJ, FL)
- ✅ Sorted by Coperniq Score (HIGH priority first)
- ✅ Decision-maker emails attached to each lead

**Next:** Go to https://app.close.com → Use Smart Views → Start calling HIGH priority (80-100) leads!

---

## Alternative: Browserbase Cloud Browser

If you prefer Browserbase over RunPod:

```bash
# 1. Get credentials from https://www.browserbase.com/dashboard
# 2. Add to .env (see Step 2 above)

# 3. Install Playwright (required for Browserbase mode)
pip install playwright && playwright install chromium

# 4. Run with Browserbase
python scripts/generate_leads.py --mode browserbase --states CA --limit-zips 5
```

---

## Troubleshooting

### "Missing RunPod credentials"
- Make sure you copied `.env.example` to `.env`
- Verify `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` are set
- Check no extra spaces or quotes around values

### "RunPod API timeout"
- Your endpoint might be scaling up from 0 workers (first request takes ~30s)
- Retry - subsequent requests will be faster
- Verify execution timeout is 120s, not 60s

### "Empty results"
- Check RunPod logs: https://www.runpod.io/console/serverless
- Verify your endpoint is deployed and active
- Test with `--limit-zips 1` first
- See `docs/troubleshooting/RUNPOD_TROUBLESHOOTING.md` for detailed debugging

### "No module named 'scrapers'"
- Run from project root: `cd dealer-scraper-mvp`
- Verify you installed requirements: `pip install -r requirements.txt`

### Test Script Fails
```bash
# Check credentials
cat .env | grep RUNPOD

# Verify endpoint ID is correct
curl https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/health
```

---

## Success Metrics

You'll know it's working when:

1. ✅ RunPod endpoint shows "Active" status
2. ✅ Test script returns ~50-60 dealers
3. ✅ Production script completes without errors
4. ✅ CSV file generated with 3,000-5,000 leads
5. ✅ HIGH priority leads (80-100 score) appear at top of CSV
6. ✅ Multi-OEM contractors identified (2-3 OEM certifications)

---

## Pro Tips

### Before Running Production
- [ ] Test with 1 ZIP first (`--limit-zips 1`)
- [ ] Verify RunPod endpoint is "Active" in console
- [ ] Check .env has both RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID
- [ ] Ensure execution timeout is 120s (not 60s)

### While Running
- Monitor RunPod console for errors
- Check terminal output for HTTP errors
- Watch for rate limiting (shouldn't happen with 0→3 auto-scaling)

### After Running
- Sort CSV by `coperniq_score` column (descending)
- Filter to HIGH priority (score >= 80) for first calls
- Check `multi_oem_count` column for contractors with 2-3 OEMs

---

## Where to Find Things

### Documentation
- `docs/troubleshooting/RUNPOD_TROUBLESHOOTING.md` - Detailed debugging guide
- `docs/guides/RUNPOD_SETUP_GUIDE.md` - Original setup instructions
- `docs/guides/API_KEYS_GUIDE.md` - API key configuration
- `CLAUDE.md` - Full project architecture

### Test Scripts
- `tests/integration/test_runpod_endpoint.py` - Test RunPod connectivity
- `tests/integration/test_all_scrapers.py` - Test all OEM scrapers
- `tests/unit/test_multi_oem_detector.py` - Test cross-reference logic

### Key Files
- `scripts/generate_leads.py` - Main lead generation script
- `scrapers/generac_scraper.py` - Production-ready scraper
- `targeting/coperniq_lead_scorer.py` - Scoring algorithm
- `analysis/multi_oem_detector.py` - Cross-reference logic

---

## Future Enhancements

### 1. **Multi-OEM Detection** (Find contractors in 2-3 OEM networks)
   - Add Tesla Powerwall scraper extraction logic (structure ready)
   - Add Enphase installer scraper extraction logic (structure ready)
   - Re-run to find contractors certified across multiple brands
   - **Value:** Multi-brand contractors NEED Coperniq (managing 3 platforms is painful)

### 2. **Outreach Automation** (10x BDR goal)
   - Email sequences (SendGrid/Mailgun)
   - SMS campaigns (Twilio)
   - AI agent testing

---

**🎯 Goal:** Get 50-100 HIGH-priority leads you can start calling TODAY

**💰 Cost:** ~$0.50-1.00 for 100 locations

**⏱️ Time:** 5 min setup + 10 min scraping = leads in 15 minutes

---

*Built for Coperniq's partner prospecting system - targeting multi-brand contractors who need unified monitoring*

