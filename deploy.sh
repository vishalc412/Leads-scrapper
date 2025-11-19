#!/bin/bash
# Simple deployment script for Leads Scraper

set -e

echo "=========================================="
echo "Leads Scraper - Docker Deployment"
echo "=========================================="
echo ""

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "❗ IMPORTANT: Please edit .env and add your API keys:"
    echo "   - ANTHROPIC_API_KEY or OPENAI_API_KEY"
    echo ""
    read -p "Press Enter to continue after editing .env, or Ctrl+C to exit..."
fi

# Create data directory
mkdir -p ./data
echo "✓ Created data directory"

# Stop any running containers
echo ""
echo "Stopping any running containers..."
docker-compose down 2>/dev/null || true

# Build images
echo ""
echo "Building Docker images..."
docker-compose build

# Start containers
echo ""
echo "Starting containers..."
docker-compose up -d

# Wait for services to be ready
echo ""
echo "Waiting for services to start..."
sleep 5

# Check health
echo ""
echo "Checking service health..."
if docker-compose ps | grep -q "Up"; then
    echo "✓ Services are running"
else
    echo "❌ Services failed to start"
    echo "Check logs with: docker-compose logs"
    exit 1
fi

# Display status
echo ""
echo "=========================================="
echo "Deployment Complete! ✓"
echo "=========================================="
echo ""
echo "Access the application:"
echo "  Frontend UI:  http://localhost"
echo "  API Docs:     http://localhost/api/docs"
echo "  Health:       http://localhost/api/health"
echo ""
echo "Useful commands:"
echo "  View logs:    docker-compose logs -f"
echo "  Stop:         docker-compose stop"
echo "  Restart:      docker-compose restart"
echo "  Remove:       docker-compose down"
echo ""
echo "Documentation: See DOCKER.md for detailed instructions"
echo ""
