# 🚀 Quick Start Guide for Tomorrow's Team

**Goal**: Get RunPod working and run production scrape across all SREC states

---

## ⚡ Option A: Use Existing Image (2 minutes)

Your Docker image is already on Docker Hub and ready to use:

### 1. Deploy to RunPod

Go to: **https://www.runpod.io/console/serverless**

Click **"+ New Endpoint"** with these settings:

```
Docker Image:        tmk74/dealer-scraper:latest
Container Disk:      10 GB
Min Workers:         0
Max Workers:         3
GPU Type:            None (or CPU)
Idle Timeout:        5 seconds
Execution Timeout:   120 seconds    ← CRITICAL: Must be 120s, not 60s
```

### 2. Add Endpoint ID to .env

After deployment, copy the Endpoint ID (looks like `abc123xyz456`) and run:

```bash
echo 'RUNPOD_ENDPOINT_ID=your_endpoint_id_here' >> .env
```

### 3. Test It

```bash
python test_runpod_endpoint.py
```

**Expected**: ✅ Status: COMPLETED, Found ~50-60 dealers

**If it fails**: See [Option B](#option-b) or check `RUNPOD_TROUBLESHOOTING.md`

---

## 🔧 Option B: Rebuild with Minimal Dockerfile (5 minutes)

If Option A fails, rebuild with simplified dependencies:

### 1. Build Minimal Image

```bash
cd /Users/tmkipper/Desktop/dealer-scraper-mvp

docker build -f runpod-playwright-api/Dockerfile.minimal \
  -t tmk74/dealer-scraper:minimal .
```

Note: The `.` at the end is CRITICAL (builds from project root)

### 2. Push to Docker Hub

```bash
docker push tmk74/dealer-scraper:minimal
```

### 3. Deploy to RunPod

Same as Option A, but use: `tmk74/dealer-scraper:minimal`

---

## 🎯 Production Scrape (Once RunPod Works)

### Full SREC State Scrape

```bash
python scripts/generate_leads.py --mode runpod --states CA TX PA MA NJ FL
```

**What happens**:
- Scrapes ~75 wealthy ZIPs across 6 SREC states
- Finds dealers certified for Generac (Tesla/Enphase coming soon)
- Cross-references to find multi-OEM contractors
- Scores each lead 0-100 (Coperniq algorithm)
- Exports CSV sorted by score (HIGH priority first)

**Expected**:
- ⏱️ Time: 10-15 minutes
- 💰 Cost: ~$0.05 - $0.10
- 📊 Output: `output/coperniq_leads_YYYYMMDD_HHMMSS.csv`

### Quick Test (1 state, 3 ZIPs)

```bash
python scripts/generate_leads.py --mode runpod --states CA --limit-zips 3
```

**Use this first** to verify everything works before full run.

---

## 📊 Expected Results

### High-Priority Leads (Score 80-100)
- ✅ Multi-OEM certified (Generac + Tesla + Enphase)
- ✅ Located in SREC states (sustainable markets)
- ✅ Commercial capability (employee count)
- ✅ Wealthy ZIP proximity (top 10 ZIPs)
- ✅ ITC urgency (approaching deadlines)

**Call these first!**

### Medium-Priority Leads (Score 50-79)
- 2 OEM certifications
- SREC state location
- Residential focus

**Call these second**

### Low-Priority Leads (Score <50)
- 1 OEM certification
- May be outside SREC states

**Call last or skip**

---

## 🐛 If Something Breaks

### RunPod Deployment Fails
1. Check RunPod logs for exact error
2. Read `RUNPOD_TROUBLESHOOTING.md` for diagnosis
3. Try Option B (minimal Dockerfile)

### Test Script Fails
```bash
# Check credentials
cat .env | grep RUNPOD

# Verify endpoint ID is correct
curl https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/health

# Try increasing timeout in test_runpod_endpoint.py (line 67)
timeout=180  # 3 minutes instead of 2
```

### Production Script Fails
```bash
# Test with single ZIP first
python scripts/generate_leads.py --mode runpod --states CA --limit-zips 1

# Check for rate limiting (RunPod)
# Check for API key expiration
```

---

## 📁 Where to Find Things

### Documentation
- `RUNPOD_TROUBLESHOOTING.md` - Detailed debugging guide
- `RUNPOD_SETUP_GUIDE.md` - Original setup instructions
- `CLAUDE.md` - Full project architecture

### Test Scripts
- `test_runpod_endpoint.py` - Test RunPod connectivity
- `test_all_scrapers.py` - Test all 4 OEM scrapers locally
- `test_multi_oem_detection.py` - Test cross-reference logic

### Key Files
- `scripts/generate_leads.py` - Main lead generation script
- `scrapers/generac_scraper.py` - Production-ready scraper
- `targeting/coperniq_lead_scorer.py` - Scoring algorithm
- `analysis/multi_oem_detector.py` - Cross-reference logic

---

## 🎯 Success Metrics

You'll know it's working when:

1. ✅ RunPod endpoint shows "Active" status
2. ✅ `test_runpod_endpoint.py` returns ~50-60 dealers
3. ✅ Production script completes without errors
4. ✅ CSV file generated with 3,000-5,000 leads
5. ✅ HIGH priority leads (80-100 score) appear at top of CSV
6. ✅ Multi-OEM contractors identified (future: 2-3 OEM certifications)

---

## 💡 Pro Tips

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
- Check `multi_oem_count` column (future: contractors with 2-3 OEMs)

---

## 🤝 Team-First Mindset

This setup is designed to **protect the team's time** by:

1. **Clear documentation** - No guessing what to do
2. **Fallback options** - If Plan A fails, Plan B is ready
3. **Detailed troubleshooting** - Specific solutions for common errors
4. **Quick tests** - Validate before spending time on full run
5. **Expected outputs** - Know what success looks like

**Remember**: Great companies prioritize team success over individual heroics. 💪

Let's ship this! 🚀
