# 🚀 QUICKSTART - Get Coperniq Leads TODAY

**5-minute setup to generate scored contractor leads for SREC states**

---

## Prerequisites

✅ Python 3.8+  
✅ RunPod account (for automated cloud scraping)  
✅ 10 minutes

---

## Step 1: Install Dependencies

```bash
cd dealer-scraper-mvp
pip install -r requirements.txt
```

---

## Step 2: Add Your RunPod API Key

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Get your RunPod credentials:
   - Go to https://www.runpod.io/console/serverless
   - Copy your **API Key**
   - Copy your **Endpoint ID** (from the deployed playwright-api endpoint)

3. Edit `.env` and add your credentials:
   ```bash
   RUNPOD_API_KEY=your_actual_api_key_here
   RUNPOD_ENDPOINT_ID=your_actual_endpoint_id_here
   ```

---

## Step 3: Generate Leads (MVP - Generac Only)

Run the lead generation script for California:

```bash
python scripts/generate_leads.py --mode runpod --states CA --limit-zips 5
```

**What this does:**
1. ✅ Scrapes 5 California ZIPs for Generac dealers via RunPod cloud API
2. ✅ Filters to SREC states only
3. ✅ Scores with Coperniq algorithm (multi-OEM, SREC priority, commercial capability, geography, ITC urgency)
4. ✅ Exports CSV sorted by score (HIGH priority first)

**Output:**
- `output/coperniq_leads_YYYYMMDD_HHMMSS.csv` ← **START HERE** (scored, sorted)
- `output/coperniq_leads_YYYYMMDD_HHMMSS.json` (full data)
- `output/generac_dealers_raw_YYYYMMDD_HHMMSS.csv` (unscored raw data)

---

## Step 4: Call Your Leads!

Open the CSV in Excel/Google Sheets:

```
priority_tier | total_score | contractor_name | phone | ...
HIGH          | 85          | ACME ELECTRIC   | (555) 555-5555
HIGH          | 82          | XYZ CONTRACTORS | (555) 555-1234
MEDIUM        | 65          | ...
```

**Prioritization:**
- **HIGH (80-100)**: Call first - multi-brand contractors in prime SREC states
- **MEDIUM (50-79)**: Call second - solid prospects
- **LOW (<50)**: Call last or skip

---

## Full Production Run (All SREC States)

Once you've tested with CA, run all 6 SREC states:

```bash
python scripts/generate_leads.py --mode runpod --states CA TX PA MA NJ FL
```

**Scrapes ~70-90 ZIPs across:**
- California (SGIP + NEM 3.0)
- Texas (deregulated market + ERCOT)
- Pennsylvania (PA SREC)
- Massachusetts (SREC II + SMART)
- New Jersey (NJ TREC)
- Florida (net metering + tax exemptions)

**Estimated time:** ~10-15 minutes  
**Estimated cost:** ~$0.50 (RunPod serverless)

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

---

## Advanced Workflow: Full Enrichment Pipeline

Once you have the basic leads, enrich them for better targeting:

### Step 5: Enrich with Apollo.io (Employee Count, Revenue, Emails)

**What it does:** Adds company data + decision-maker contacts for accurate scoring

```bash
# 1. Get Apollo API key from https://app.apollo.io/#/settings/integrations/api
# 2. Add to .env:
echo "APOLLO_API_KEY=your_apollo_key" >> .env

# 3. Enrich your leads
python scripts/enrich_with_apollo.py --input output/generac_master_list.json
```

**Output:** `output/generac_master_list_apollo.json`

**What's added:**
- Employee count (accurate commercial capability scoring - 20 pts)
- Revenue estimate
- Decision-maker emails (Owner, GM, Operations Manager)
- LinkedIn profiles (company + contacts)

---

### Step 6: Enrich with Clay.com (Waterfall Enrichment) [OPTIONAL]

**What it does:** Adds additional data via waterfall enrichment

```bash
# 1. Create Clay table at https://clay.com
# 2. Add Webhook integration → Copy URL to .env:
echo "CLAY_WEBHOOK_URL=https://clay.com/webhooks/..." >> .env

# 3. Send leads to Clay
python scripts/enrich_with_clay.py --input output/generac_master_list_apollo.json

# 4. Wait 1-5 minutes for Clay processing
# 5. Export enriched CSV from Clay table
```

**What Clay adds:**
- Additional emails (Apollo → Hunter → Snov.io waterfall)
- Phone validation
- Tech stack (BuiltWith)
- Social profiles (Facebook, Twitter)

---

### Step 7: Upload to Close CRM (Automated Outreach)

**What it does:** Imports leads with Smart Views for organized calling

```bash
# 1. Get Close CRM API key from https://app.close.com/settings/api/
# 2. Add to .env:
echo "CLOSE_API_KEY=your_close_key" >> .env

# 3. Create custom fields in Close CRM UI (see scripts/upload_to_close.py docstring)

# 4. Upload leads
python scripts/upload_to_close.py --input output/generac_master_list_apollo.json
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
# 2. Add to .env:
echo "BROWSERBASE_API_KEY=your_key" >> .env
echo "BROWSERBASE_PROJECT_ID=your_project_id" >> .env

# 3. Install Playwright (required for Browserbase mode)
pip install playwright && playwright install chromium

# 4. Run with Browserbase
python scripts/generate_leads.py --mode browserbase --states CA --limit-zips 5
```

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

## Troubleshooting

### "Missing RunPod credentials"
- Make sure you copied `.env.example` to `.env`
- Verify `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` are set
- Check no extra spaces or quotes around values

### "RunPod API timeout"
- Your endpoint might be scaling up from 0 workers (first request takes ~30s)
- Retry - subsequent requests will be faster

### "Empty results"
- Check RunPod logs: https://www.runpod.io/console/serverless
- Verify your endpoint is deployed and active
- Test with `--limit-zips 1` first

### "No module named 'scrapers'"
- Run from project root: `cd dealer-scraper-mvp`
- Verify you installed requirements: `pip install -r requirements.txt`

---

## Support

Questions? Check:
- **Full docs**: README.md
- **Architecture**: CLAUDE.md
- **RunPod deployment**: runpod-playwright-api/README.md

---

**🎯 Goal:** Get 50-100 HIGH-priority leads you can start calling TODAY

**💰 Cost:** ~$0.50-1.00 for 100 locations

**⏱️ Time:** 5 min setup + 10 min scraping = leads in 15 minutes

---

*Built for Coperniq's partner prospecting system - targeting multi-brand contractors who need unified monitoring*
