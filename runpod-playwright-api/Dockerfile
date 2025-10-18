# Use official Microsoft Playwright Python image (includes Chromium, Firefox, WebKit)
FROM mcr.microsoft.com/playwright/python:v1.48.0

# Set working directory
WORKDIR /app

# Copy and install Python dependencies (separate layer for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY handler.py playwright_service.py ./

# RunPod expects Python script as entry point
CMD ["python", "handler.py"]
