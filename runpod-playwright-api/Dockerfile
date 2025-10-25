# Use official Microsoft Playwright Python image (includes Chromium, Firefox, WebKit)
FROM mcr.microsoft.com/playwright/python:v1.48.0

# Set working directory
WORKDIR /app

# Copy and install Python dependencies from main project
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scraper modules and analysis logic
COPY scrapers/ ./scrapers/
COPY analysis/ ./analysis/
COPY config.py ./

# Copy RunPod handler and Playwright service
COPY runpod-playwright-api/handler.py runpod-playwright-api/playwright_service.py ./

# RunPod expects Python script as entry point
CMD ["python", "handler.py"]
