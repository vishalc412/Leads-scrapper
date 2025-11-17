#!/bin/bash
# Docker deployment script for Leads Scraper

set -e

echo "======================================"
echo "Leads Scraper - Docker Deployment"
echo "======================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and configure your settings."
    exit 1
fi

# Load environment variables
source .env

# Verify API keys are set
if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "Warning: No AI API keys configured!"
    echo "Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env file."
fi

# Build Docker image
echo ""
echo "Building Docker image..."
docker build -t leads-scraper:latest .

# Create data directory if it doesn't exist
mkdir -p ./data ./logs

# Stop existing container if running
if [ "$(docker ps -q -f name=leads-scraper)" ]; then
    echo ""
    echo "Stopping existing container..."
    docker stop leads-scraper
    docker rm leads-scraper
fi

# Run container
echo ""
echo "Starting container..."
docker run -d \
    --name leads-scraper \
    -p 8000:8000 \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/logs:/app/logs \
    --env-file .env \
    leads-scraper:latest

echo ""
echo "======================================"
echo "Deployment complete!"
echo "======================================"
echo "API URL: http://localhost:8000"
echo "Health check: http://localhost:8000/health"
echo ""
echo "View logs: docker logs -f leads-scraper"
echo "Stop: docker stop leads-scraper"
echo ""
