# RunPod Deployment Troubleshooting Guide

## 🎯 Quick Diagnosis Checklist

### ✅ What's Working
- Docker image built locally successfully
- Image pushed to Docker Hub: `tmk74/dealer-scraper:latest`
- SHA256: `499d9ae35c38adcebf4e027ce6a4602f48db30e39e7b75384b5a7f70afd30e1d`

### ⚠️ Common Build Failure Causes

#### 1. **Dockerfile Path Issues** (MOST COMMON)

**Problem**: Dockerfile uses relative paths that work locally but fail in RunPod

**Current Dockerfile (lines 12-17):**
```dockerfile
# Copy scraper modules and analysis logic
COPY scrapers/ ./scrapers/
COPY analysis/ ./analysis/
COPY config.py ./

# Copy RunPod handler and Playwright service
COPY runpod-playwright-api/handler.py runpod-playwright-api/playwright_service.py ./
```

**Issue**:
- Dockerfile is in `runpod-playwright-api/` subdirectory
- COPY commands reference parent directory files
- RunPod may build from different context than local Docker

**Solution**: Build context must be project root, not `runpod-playwright-api/` directory

---

#### 2. **Unnecessary Dependencies** (CAUSING IMPORT ERRORS)

**Critical Insight**: The RunPod handler is a **generic Playwright executor**. It does NOT need:
- ❌ `scrapers/` modules (generac_scraper.py, tesla_scraper.py, etc.)
- ❌ `analysis/` modules (multi_oem_detector.py, etc.)
- ❌ `config.py`

**Why**: Scrapers call RunPod via HTTP, they don't run inside it!

**What RunPod Actually Needs**:
- ✅ `handler.py` - Entry point
- ✅ `playwright_service.py` - Browser automation
- ✅ `requirements.txt` - Python dependencies
- ✅ Playwright Chromium (pre-installed in base image)

---

## 🔧 Recommended Fix: Simplified Dockerfile

Create a **minimal Dockerfile** that only includes what's actually needed:

**New `runpod-playwright-api/Dockerfile`:**
```dockerfile
# Use official Microsoft Playwright Python image (includes Chromium)
FROM mcr.microsoft.com/playwright/python:v1.48.0

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
# Only need: playwright, runpod
COPY requirements.txt .
RUN pip install --no-cache-dir playwright runpod

# Copy ONLY the handler and service (no scrapers needed!)
COPY handler.py playwright_service.py ./

# RunPod expects Python script as entry point
CMD ["python", "handler.py"]
```

**Why This Works**:
1. **Simpler COPY commands** - No parent directory references
2. **Fewer dependencies** - Only install what handler.py actually imports
3. **Faster builds** - Less to copy, less to break
4. **Clear separation** - Scrapers live in main app, handler is pure Playwright

---

## 🚀 Deployment Steps for Tomorrow's Team

### Option A: Use Existing Image (Fastest - 2 minutes)

Your current image is already on Docker Hub and should work:

1. **Go to RunPod Console**: https://www.runpod.io/console/serverless
2. **Create New Endpoint** with these exact settings:
   - **Docker Image**: `tmk74/dealer-scraper:latest`
   - **Container Disk**: `10 GB`
   - **Min Workers**: `0`
   - **Max Workers**: `3`
   - **GPU Type**: `None` or `CPU`
   - **Idle Timeout**: `5 seconds`
   - **Execution Timeout**: `120 seconds` ← **IMPORTANT**: Increase from default
3. **Copy Endpoint ID** (looks like `abc123xyz456`)
4. **Add to .env**:
   ```bash
   echo 'RUNPOD_ENDPOINT_ID=your_endpoint_id_here' >> .env
   ```
5. **Test it**:
   ```bash
   python test_runpod_endpoint.py
   ```

### Option B: Rebuild with Simplified Dockerfile (5 minutes)

If Option A fails, rebuild with minimal dependencies:

1. **Create simplified Dockerfile** (see above)
2. **Build from project root** (CRITICAL):
   ```bash
   cd /Users/tmkipper/Desktop/dealer-scraper-mvp
   docker build -f runpod-playwright-api/Dockerfile -t tmk74/dealer-scraper:v2 .
   ```
   Note the `.` at the end - builds from current directory (project root)
3. **Push to Docker Hub**:
   ```bash
   docker push tmk74/dealer-scraper:v2
   ```
4. **Deploy to RunPod** using `tmk74/dealer-scraper:v2` as image name

---

## 🐛 Debugging Failed Deployments

### Check RunPod Logs

1. Go to: https://www.runpod.io/console/serverless
2. Click on your endpoint
3. Click **"Logs"** tab
4. Look for errors like:
   - `ModuleNotFoundError` → Missing dependency in requirements.txt
   - `FileNotFoundError` → COPY command failed (wrong build context)
   - `Permission denied` → Container disk too small (increase to 10GB)
   - `Timeout` → Increase Execution Timeout to 120 seconds

### Test Locally First

Before deploying to RunPod, test the Docker image locally:

```bash
# Run container locally
docker run -p 8080:8080 tmk74/dealer-scraper:latest

# In another terminal, test the handler
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "workflow": [
        {"action": "navigate", "url": "https://www.google.com"},
        {"action": "evaluate", "script": "() => document.title"}
      ]
    }
  }'
```

If this fails locally, it will fail on RunPod too.

---

## 📊 Expected Performance

Once working, you should see:

**Test Script** (`test_runpod_endpoint.py`):
- ✅ Status: 200
- ✅ Job Status: COMPLETED
- ✅ Found ~50-60 dealers (Generac, Milwaukee ZIP 53202)
- ⏱️ Response time: 5-8 seconds (includes cold start)

**Production Run** (`scripts/generate_leads.py --mode runpod --states CA TX PA MA NJ FL`):
- ⏱️ Total time: ~10-15 minutes (75 ZIPs × 5-8 seconds each)
- 💰 Total cost: ~$0.05 - $0.10 USD
- 📊 Output: CSV with ~3,000-5,000 dealers sorted by Coperniq score

---

## 🎯 Success Criteria

You'll know it's working when:

1. **Endpoint deploys** without errors (RunPod shows "Active")
2. **Test script passes** (`python test_runpod_endpoint.py` returns dealers)
3. **Production script runs** without HTTP errors
4. **CSV file generated** in `output/` directory with scored leads

---

## 💡 Key Insights for Team

### Architecture Clarity
```
┌─────────────────────────────────────────────────────┐
│ Local Machine (Scrapers)                            │
│  ├─ generac_scraper.py                             │
│  ├─ tesla_scraper.py                               │
│  └─ Uses ScraperMode.RUNPOD                        │
│     └─ Sends HTTP request to RunPod endpoint       │
└─────────────────────────────────────────────────────┘
                        │
                        │ HTTP POST (workflow JSON)
                        ▼
┌─────────────────────────────────────────────────────┐
│ RunPod Cloud (Generic Playwright Executor)          │
│  ├─ handler.py (receives workflow)                  │
│  └─ playwright_service.py (executes steps)          │
│     └─ Returns results (dealer JSON)                │
└─────────────────────────────────────────────────────┘
```

**Key Point**: RunPod doesn't need to know about Generac, Tesla, or Enphase. It just executes browser automation steps sent from local scrapers.

### Build Context Matters
- **Building from `runpod-playwright-api/`**: ❌ Can't access parent directory
- **Building from project root**: ✅ Can access all subdirectories
- **RunPod's build context**: Unknown - safest to minimize dependencies

### Less is More
- Simpler Dockerfile = fewer failure points
- Only copy what `handler.py` actually imports
- Let scrapers stay local, handler stays generic

---

## 📞 Next Steps if Still Failing

1. **Share the exact error** from RunPod logs
2. **Try the simplified Dockerfile** (Option B above)
3. **Test locally first** before deploying to RunPod
4. **Check execution timeout** - must be 120s minimum (60s is too short)

The team is set up with:
- ✅ Working local scrapers
- ✅ Docker image on Docker Hub
- ✅ Clear deployment instructions
- ✅ Fallback options if primary approach fails

Let's ship this! 🚀
