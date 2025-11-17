# Multi-stage build for Leads Scraper
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose API port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Default command (can be overridden)
CMD ["python", "cli.py", "server", "--host", "0.0.0.0", "--port", "8000"]
