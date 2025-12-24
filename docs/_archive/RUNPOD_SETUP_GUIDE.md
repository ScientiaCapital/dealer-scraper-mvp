# RunPod Endpoint Setup Guide

Follow these steps to deploy the dealer-scraper to RunPod serverless.

## Step 1: Navigate to RunPod Console

Go to: **https://www.runpod.io/console/serverless**

Login with your credentials.

## Step 2: Create New Endpoint

Click the **"+ New Endpoint"** button (or similar - UI may vary)

## Step 3: Fill in Endpoint Configuration

### Basic Settings:
- **Endpoint Name**: `dealer-scraper` (or any name you prefer)
- **Select Base Image**: Choose "Custom Image"

### Docker Image Settings:
**Important**: Use the local image SHA since Docker Hub push failed

- **Docker Image**: `tmk74/dealer-scraper@sha256:499d9ae35c38adcebf4e027ce6a4602f48db30e39e7b75384b5a7f70afd30e1d`

  _(This is your locally built image - RunPod can pull it if you're logged into Docker Hub)_

**Alternative**: If the above doesn't work, use:
- **Docker Image**: `tmk74/dealer-scraper:latest`

### Resource Configuration:
- **Container Disk**: `10 GB` (Chromium + dependencies need space)
- **Min Workers**: `0` (auto-scale from zero - no idle costs)
- **Max Workers**: `3` (adjust based on your needs)
- **GPU Type**: `None` or `CPU` (we don't need GPU for web scraping)
- **Idle Timeout**: `5 seconds` (worker shuts down quickly after job completes)

### Advanced Settings (Optional):
- **Environment Variables**: None needed (handler.py loads directly)
- **Max Concurrency**: `1` (one job per worker)
- **Execution Timeout**: `60 seconds` (adjust if you need longer scraping)

## Step 4: Deploy

Click **"Deploy"** or **"Create Endpoint"**

Wait for deployment to complete (~1-2 minutes)

## Step 5: Get Endpoint ID

After deployment, you'll see your endpoint listed.

Copy the **Endpoint ID** - it looks like: `abc123xyz456`

## Step 6: Add to .env File

Come back to terminal and run:

```bash
echo 'RUNPOD_ENDPOINT_ID=YOUR_ENDPOINT_ID_HERE' >> .env
```

Replace `YOUR_ENDPOINT_ID_HERE` with the actual ID you copied.

## Step 7: Test the Endpoint

Once you've added the Endpoint ID to .env, Claude will test it automatically with all 4 OEM scrapers.

---

## Troubleshooting

### "Image pull failed"
- Make sure you're logged into Docker Hub: `docker login`
- Try using the SHA256 digest instead of `:latest` tag
- Alternative: Push image to Docker Hub manually first

### "Worker timeout"
- Increase "Execution Timeout" to 120 seconds
- Check RunPod logs for specific errors

### "Can't find image"
- Verify image name is exactly `tmk74/dealer-scraper:latest`
- Check that image exists: `docker images | grep dealer-scraper`

### "Endpoint won't start"
- Check RunPod logs for handler.py errors
- Verify Dockerfile CMD is correct: `CMD ["python", "handler.py"]`

---

## Local Image SHA (Full)

```
Image: tmk74/dealer-scraper:latest
SHA256: 499d9ae35c38adcebf4e027ce6a4602f48db30e39e7b75384b5a7f70afd30e1d
```

Use this if RunPod asks for a full SHA256 digest.

---

## What Happens Next

Once you add the RUNPOD_ENDPOINT_ID to .env:
1. Claude will test all 4 scrapers (Tesla, Enphase, SolarEdge, Generac)
2. We'll run production scraping across wealthy ZIPs in SREC states
3. Generate master lead list sorted by Coperniq score

**Estimated Time**: ~10-15 minutes for 60 wealthy ZIPs across CA, TX, PA, MA, NJ, FL
**Estimated Cost**: ~$0.05 - $0.10 USD
