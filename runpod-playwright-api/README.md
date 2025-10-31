# RunPod Playwright API

**Cloud-hosted serverless Playwright browser automation API**

This is a RunPod serverless endpoint that provides browser automation via Playwright. It auto-scales from 0→N workers and runs headless Chromium in Docker containers.

## Overview

- **What**: HTTP API for Playwright browser automation workflows
- **Where**: Deployed on RunPod serverless infrastructure
- **Why**: Scalable, pay-per-second cloud alternative to local MCP Playwright
- **Cost**: ~$0.50-1.00 for 100 ZIP code scrapes (6 seconds per ZIP @ $0.00015/sec)

## Architecture

```
Python Scraper (scraper.py)
    ↓ HTTP POST
RunPod Serverless API (handler.py)
    ↓ Singleton Browser
Playwright Service (playwright_service.py)
    ↓ Context per Request
Chromium in Docker Container
    ↓ Web Automation
Target Website (dealer-locator)
```

**Key Design Decisions**:
- Singleton browser initialized once at worker startup (~2s startup cost)
- New context per request for clean state isolation
- `refresh_worker=False` keeps worker alive between jobs
- Returns JSON results array from JavaScript evaluation

## Prerequisites

1. **RunPod Account**: Sign up at [runpod.io](https://www.runpod.io)
2. **Docker**: Install from [docker.com](https://www.docker.com/get-started)
3. **RunPod CLI**: Required for deployment (see installation below)
4. **API Credentials**: Get from [RunPod Console → Serverless](https://www.runpod.io/console/serverless)

## Quick Start

### 1. Install RunPod CLI

**macOS/Linux**:
```bash
curl -sL https://runpod.io/install.sh | bash
```

**Windows (PowerShell)**:
```powershell
iwr -useb https://runpod.io/install.ps1 | iex
```

**Verify installation**:
```bash
runpodctl version
```

### 2. Configure RunPod CLI

```bash
# Login with your RunPod API key
runpodctl config --apiKey YOUR_API_KEY_HERE

# Verify configuration
runpodctl config --list
```

Get your API key from: https://www.runpod.io/console/user/settings

### 3. Build Docker Image

```bash
cd runpod-playwright-api

# Build the image
docker build -t runpod-playwright-api:latest .

# Verify build (optional)
docker images | grep runpod-playwright
```

**Build time**: ~2-3 minutes (downloads Playwright base image)

### 4. Test Locally (Optional)

Before deploying to RunPod, test locally:

```bash
# Run local test server
bash examples/test_local.sh

# In another terminal, test the API
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d @test_input.json
```

Expected output:
```json
{
  "status": "success",
  "results": [...],
  "execution_time": 5.234
}
```

### 5. Push to Docker Hub

RunPod pulls images from Docker registries (Docker Hub, GitHub Container Registry, etc.)

```bash
# Tag for Docker Hub (replace 'yourusername')
docker tag runpod-playwright-api:latest yourusername/runpod-playwright-api:latest

# Login to Docker Hub
docker login

# Push image
docker push yourusername/runpod-playwright-api:latest
```

### 6. Deploy to RunPod

**Option A: Web Console** (Recommended for first deployment)

1. Go to [RunPod Console → Serverless](https://www.runpod.io/console/serverless)
2. Click "Create Endpoint"
3. Fill in details:
   - **Name**: `playwright-api`
   - **Image**: `yourusername/runpod-playwright-api:latest`
   - **Container Disk**: 10 GB
   - **Min Workers**: 0 (auto-scale from zero)
   - **Max Workers**: 3
   - **GPU Type**: None (CPU only)
   - **Idle Timeout**: 5 seconds
4. Click "Deploy"
5. Copy your **Endpoint ID** (e.g., `abc123xyz`)

**Option B: CLI Deployment** (Advanced)

```bash
# Create endpoint via CLI
runpodctl endpoint create \
  --name playwright-api \
  --image yourusername/runpod-playwright-api:latest \
  --min-workers 0 \
  --max-workers 3 \
  --idle-timeout 5 \
  --container-disk 10

# List endpoints
runpodctl endpoint list
```

### 7. Configure Your Scraper

Copy `.env.example` to `.env` and add your credentials:

```bash
cp ../.env.example ../.env
```

Edit `.env`:
```bash
RUNPOD_API_KEY=your_runpod_api_key_here
RUNPOD_ENDPOINT_ID=abc123xyz  # From step 6
```

### 8. Test Cloud API

```bash
# Export credentials (or use .env)
export RUNPOD_API_KEY=your_key_here
export RUNPOD_ENDPOINT_ID=abc123xyz

# Run test script
bash examples/test_curl.sh
```

## Usage

### Python Integration (Recommended)

```python
# Note: Legacy scraper.py has been archived to docs/archive/legacy_code/
# Use scrapers/scraper_factory.py instead:
from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode
from config import ZIP_CODES_TEST

# Initialize with RunPod mode
scraper = ScraperFactory.create("Generac", mode=ScraperMode.RUNPOD)

# Scrape a single ZIP code
dealers = scraper.scrape_zip_code("53202")
print(f"Found {len(dealers)} dealers")

# Scrape multiple ZIP codes
all_dealers = scraper.scrape_multiple(ZIP_CODES_TEST)
scraper.deduplicate()
scraper.save_json("output/dealers.json")
scraper.save_csv("output/dealers.csv")
```

### Direct API Usage (curl)

```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "workflow": [
        {"action": "navigate", "url": "https://www.generac.com/dealer-locator/"},
        {"action": "click", "selector": "button:has-text(\"Accept Cookies\")"},
        {"action": "fill", "selector": "input[name*=\"zip\" i]", "text": "53202"},
        {"action": "click", "selector": "button:has-text(\"Search\")"},
        {"action": "wait", "timeout": 3000},
        {"action": "evaluate", "script": "() => { return [...]; }"}
      ]
    }
  }'
```

### Workflow Actions

The API supports these actions in sequence:

| Action | Parameters | Description |
|--------|-----------|-------------|
| `navigate` | `url` | Navigate to URL |
| `click` | `selector` | Click element |
| `fill` | `selector`, `text` | Fill input field |
| `wait` | `timeout` (ms) | Wait for specified time |
| `evaluate` | `script` (JavaScript) | Execute JavaScript and return result |

## Cost Breakdown

RunPod charges by the second when workers are active:

```
Single ZIP Scrape:
- Execution time: ~6 seconds
- Cost per second: $0.00015 (CPU worker)
- Cost per ZIP: $0.0009 (~$0.001)

100 ZIP Scrapes:
- Total time: ~600 seconds (10 minutes)
- Total cost: $0.09 - $0.15
- With overhead: ~$0.50 - $1.00

1000 ZIP Scrapes:
- Total cost: ~$5 - $10
```

**Pro tip**: Set `max_workers` based on your concurrency needs. 3 workers can handle ~1800 ZIPs/hour.

## Project Structure

```
runpod-playwright-api/
├── handler.py              # RunPod entry point
├── playwright_service.py   # Browser automation service
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container definition
├── .dockerignore          # Build exclusions
├── test_input.json        # Local test data
├── examples/
│   ├── test_local.sh      # Local development server
│   ├── test_curl.sh       # Cloud API testing
│   └── dealer_workflow.json  # Full dealer scraper workflow
└── README.md              # This file
```

## Performance Optimization

### Browser Singleton Pattern
- Browser initialized **once** at worker startup
- Saves ~2 seconds per request
- Contexts created per request for clean state

### Worker Keep-Alive
```python
runpod.serverless.start({
    "handler": handler,
    "refresh_worker": False  # Keep browser alive
})
```

### Auto-Scaling Strategy
- **Min workers: 0** → No idle costs
- **Max workers: 3** → Handles 3 concurrent requests
- **Idle timeout: 5s** → Quick shutdown after burst
- **Container disk: 10GB** → Enough for Chromium + cache

## Monitoring

### Check Endpoint Status
```bash
runpodctl endpoint list
runpodctl endpoint logs YOUR_ENDPOINT_ID
```

### View Execution Logs
Go to [RunPod Console → Serverless → Your Endpoint → Logs](https://www.runpod.io/console/serverless)

### Request Metrics
```python
result = scraper.scrape_zip_code("53202")
# Check execution_time in logs
```

## Troubleshooting

### Build Errors

**Problem**: `Docker build failed`
```bash
# Clear Docker cache and rebuild
docker system prune -a
docker build --no-cache -t runpod-playwright-api:latest .
```

### Deployment Errors

**Problem**: `Image pull failed`
- Verify image is pushed to Docker Hub
- Check image name matches exactly (case-sensitive)
- Ensure image is public or RunPod has registry credentials

**Problem**: `Worker timeout`
- Increase `timeout` in API call (default: 60s)
- Check RunPod worker logs for errors
- Verify website is accessible from RunPod infrastructure

### Runtime Errors

**Problem**: `Missing RUNPOD_API_KEY or RUNPOD_ENDPOINT_ID`
- Copy `.env.example` to `.env`
- Fill in credentials from RunPod console
- Restart scraper to load new environment variables

**Problem**: `Empty results array`
- Check RunPod logs for JavaScript evaluation errors
- Verify selectors match current website structure
- Test extraction script manually in browser console

**Problem**: `HTTP 401 Unauthorized`
- Verify `RUNPOD_API_KEY` is correct
- Check API key has serverless permissions
- Generate new API key if needed

## Security

- ✅ API keys stored in `.env` (git-ignored)
- ✅ No credentials in code or Docker image
- ✅ HTTPS-only API communication
- ✅ Stateless execution (no data persistence)

## Adapting for Other Websites

1. **Update selectors** in workflow:
```python
workflow = [
    {"action": "navigate", "url": "https://example.com"},
    {"action": "click", "selector": "YOUR_COOKIE_BUTTON"},
    {"action": "fill", "selector": "YOUR_INPUT_FIELD", "text": "search_term"},
    # ... rest of workflow
]
```

2. **Modify extraction script** (config.py):
```javascript
// Update EXTRACTION_SCRIPT with your DOM parsing logic
const data = document.querySelectorAll('.your-selector');
return Array.from(data).map(el => ({
    field1: el.querySelector('.field1').textContent,
    field2: el.querySelector('.field2').textContent,
}));
```

3. **Rebuild and redeploy**:
```bash
docker build -t runpod-playwright-api:latest .
docker push yourusername/runpod-playwright-api:latest
runpodctl endpoint update YOUR_ENDPOINT_ID --image yourusername/runpod-playwright-api:latest
```

## Resources

- [RunPod Documentation](https://docs.runpod.io/)
- [Playwright Python Docs](https://playwright.dev/python/docs/intro)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [RunPod CLI Reference](https://docs.runpod.io/cli/overview)

## License

MIT
