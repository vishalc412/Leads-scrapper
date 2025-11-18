# Docker Deployment Guide

This guide explains how to deploy the Leads Scraper application using Docker with separate containers for frontend and backend.

## Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ http://localhost
       ▼
┌─────────────────┐
│   Frontend      │ Nginx serving static files
│   (Port 80)     │ Proxies /api/* to backend
└────────┬────────┘
         │ Internal network
         ▼
┌─────────────────┐
│   Backend       │ FastAPI + Python
│   (Port 8000)   │ Leads scraping & AI analysis
└─────────────────┘
```

## Quick Start

### 1. Prerequisites

- Docker (20.10+)
- Docker Compose (1.29+)
- At least one AI API key (Anthropic or OpenAI)

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

Required environment variables:
```bash
# At least one AI API key
ANTHROPIC_API_KEY=your_anthropic_key_here
# OR
OPENAI_API_KEY=your_openai_key_here

# Optional: Choose AI model
AI_MODEL=claude-sonnet-4-5-20250929
```

### 3. Build and Run

```bash
# Build and start all containers
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 4. Access the Application

- **Frontend UI**: http://localhost
- **Backend API**: http://localhost/api (proxied through frontend)
- **API Documentation**: http://localhost/api/docs

## Services

### Frontend Container

- **Image**: Nginx Alpine
- **Port**: 80
- **Purpose**: Serves static HTML/CSS/JS and proxies API requests to backend
- **Build**: `frontend.Dockerfile`

### Backend Container

- **Image**: Python 3.11 Slim
- **Port**: 8000 (internal only)
- **Purpose**: FastAPI server with web scraping and AI analysis
- **Build**: `backend.Dockerfile`
- **Data**: Persisted to `./data` volume

## Docker Commands

### Start Services

```bash
# Start in background
docker-compose up -d

# Start and view logs
docker-compose up

# Start specific service
docker-compose up -d backend
```

### Stop Services

```bash
# Stop all containers
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove with volumes (deletes data!)
docker-compose down -v
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100
```

### Rebuild

```bash
# Rebuild all images
docker-compose build

# Rebuild specific service
docker-compose build backend

# Rebuild and restart
docker-compose up -d --build
```

### Execute Commands

```bash
# Run CLI command in backend container
docker-compose exec backend python cli.py search Python --city "SF" --save

# List saved leads
docker-compose exec backend python cli.py list --limit 10

# Access backend shell
docker-compose exec backend /bin/bash

# Access frontend shell
docker-compose exec frontend /bin/sh
```

## Development Mode

For development with hot-reload:

```bash
# Edit docker-compose.yml to mount source code
# Add under backend volumes:
volumes:
  - ./src:/app/src
  - ./data:/app/data

# Start with auto-reload
docker-compose exec backend python -m uvicorn src.api.main:app --host 0.0.0.0 --reload
```

## Troubleshooting

### Frontend can't reach backend

```bash
# Check if backend is running
docker-compose ps backend

# Check backend logs
docker-compose logs backend

# Test backend health
docker-compose exec backend curl http://localhost:8000/health
```

### Port already in use

```bash
# Change port in docker-compose.yml
ports:
  - "8080:80"  # Use port 8080 instead of 80
```

### Permission errors on data directory

```bash
# Fix permissions
chmod 777 ./data

# Or use specific user in docker-compose.yml
user: "1000:1000"
```

### Container keeps restarting

```bash
# Check logs
docker-compose logs --tail=50 backend

# Check health status
docker inspect leads-scraper-backend | grep -A 10 Health
```

### Clear everything and start fresh

```bash
# Stop and remove everything
docker-compose down -v

# Remove images
docker rmi leads-scraper-backend leads-scraper-frontend

# Remove data
rm -rf ./data/*

# Rebuild and start
docker-compose up -d --build
```

## Production Deployment

### Environment Variables

Set these in your production environment:

```bash
ENVIRONMENT=production
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
AI_MODEL=claude-sonnet-4-5-20250929
SCRAPER_MAX_RETRIES=3
SCRAPER_TIMEOUT=30
```

### Resource Limits

Add to docker-compose.yml:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 512M
```

### HTTPS/SSL

Use a reverse proxy (Nginx, Traefik, or Caddy):

```yaml
services:
  nginx-proxy:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
```

### Health Checks

Both containers have health checks configured. Monitor with:

```bash
docker-compose ps
# or
curl http://localhost/api/health
```

## Scaling

### Multiple Workers

```yaml
backend:
  deploy:
    replicas: 3
```

### Load Balancing

Add nginx upstream:

```nginx
upstream backend_servers {
    server backend:8000;
    server backend:8001;
    server backend:8002;
}
```

## Backup

### Backup Data

```bash
# Create backup
tar -czf backup-$(date +%Y%m%d).tar.gz ./data

# Restore from backup
tar -xzf backup-20250117.tar.gz
```

### Database Export

```bash
# Export SQLite database
docker-compose exec backend python -c "
from src.storage import Database
db = Database()
# Export logic here
"
```

## Monitoring

### View Resource Usage

```bash
docker stats

# Specific container
docker stats leads-scraper-backend
```

### Access Logs

Frontend logs: Nginx access logs in container
Backend logs: Python application logs via docker-compose logs

## Networks

Custom network `leads-network` allows:
- Frontend → Backend communication
- Isolated from host network
- Service discovery by name

## Volumes

- `./data`: Persistent SQLite database and cached data
- Survives container restarts
- Backed up separately from containers

## Support

For issues:
1. Check logs: `docker-compose logs`
2. Verify health: `docker-compose ps`
3. Review configuration: `.env` and `docker-compose.yml`
4. Check GitHub issues: https://github.com/vishalc412/Leads-scrapper/issues
