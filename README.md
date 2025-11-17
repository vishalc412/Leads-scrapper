# Leads Scraper

A Python framework for scraping and analyzing job leads using AI. Designed as an extensible MVP that can be adapted for sales leads, project requirements, and other lead types.

## Features

- **Multi-Platform Scraping**: Support for Indeed, LinkedIn (with mock scraper for testing)
- **AI-Powered Analysis**: Analyze leads using Anthropic Claude or OpenAI GPT models
- **RESTful API**: FastAPI backend for integration
- **CLI Tool**: Command-line interface for search and analysis
- **Multiple Deployment Options**: Run locally, Docker, AWS, or Azure
- **SQLite Database**: Stores leads and analyses (PostgreSQL support available)

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/vishalc412/Leads-scrapper.git
cd Leads-scrapper

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your API keys (ANTHROPIC_API_KEY or OPENAI_API_KEY)
```

### Usage

**Search for jobs:**
```bash
# Basic search
python cli.py search "Python Developer" --city "San Francisco" --state "CA"

# Search and save to database
python cli.py search "Software Engineer" --city "Seattle" --remote --save

# Advanced search with filters
python cli.py search "Data Scientist" \
  --city "Boston" \
  --state "MA" \
  --experience-level "senior" \
  --salary-min 120000 \
  --max-results 50 \
  --save
```

**Analyze leads with AI:**
```bash
# Analyze recent leads
python cli.py analyze --limit 10

# Analyze with specific model
python cli.py analyze --model "claude-sonnet-4-5-20250929" --limit 5

# Analyze with user profile matching
python cli.py analyze --profile examples/user_profile.json --output analysis.json
```

**List saved leads:**
```bash
python cli.py list --limit 20
```

**Start API server:**
```bash
python cli.py server --reload
```

### Python API

```python
from src import ScraperManager, AnalyzerFactory, SearchQuery, Location, Database

# Search for leads
query = SearchQuery(
    keywords=["Python", "Django"],
    location=Location(city="San Francisco", state="CA"),
    max_results=20
)

with ScraperManager() as manager:
    results = manager.search(query)
    print(f"Found {results.total_scraped} leads")

# Analyze with AI
analyzer = AnalyzerFactory.create_analyzer()
analyses = analyzer.analyze_batch(results.leads[:10])

# Save to database
with Database() as db:
    db.save_leads(results.leads)
    for analysis in analyses:
        db.save_analysis(analysis)
```

### REST API

Start the server:
```bash
python cli.py server
```

API endpoints:
- `POST /search` - Search for job leads
- `POST /analyze` - Analyze leads with AI
- `GET /leads` - Get saved leads (with pagination)
- `GET /leads/{id}` - Get specific lead
- `GET /leads/{id}/analysis` - Get lead analysis
- `GET /health` - Health check

Example:
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "keywords": ["Python"],
      "location": {"city": "SF", "state": "CA"},
      "max_results": 10
    },
    "save_results": true
  }'
```

## Configuration

Edit `.env` file:

```bash
# AI Configuration (at least one required for analysis)
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
AI_MODEL=claude-sonnet-4-5-20250929

# Scraper Configuration
SCRAPER_MAX_RETRIES=3
SCRAPER_TIMEOUT=30

# Storage
DATA_DIR=./data

# API
API_PORT=8000
```

## Deployment

### Docker

```bash
# Using Docker Compose
docker-compose up -d

# Or with deployment script
chmod +x deployment/docker/deploy.sh
./deployment/docker/deploy.sh
```

### AWS (ECS Fargate)

```bash
aws cloudformation create-stack \
  --stack-name leads-scraper \
  --template-body file://deployment/aws/cloudformation-template.yml \
  --parameters ParameterKey=AnthropicApiKey,ParameterValue=YOUR_KEY \
  --capabilities CAPABILITY_IAM
```

### Azure (Container Instances)

```bash
az deployment group create \
  --resource-group leads-scraper-rg \
  --template-file deployment/azure/azure-deploy.json \
  --parameters anthropicApiKey=YOUR_KEY
```

## Project Structure

```
Leads-scrapper/
├── src/
│   ├── scrapers/       # Web scrapers (Indeed, LinkedIn, base framework)
│   ├── analyzers/      # AI analyzers (Anthropic, OpenAI)
│   ├── api/           # FastAPI backend
│   ├── storage/       # Database layer
│   ├── config/        # Configuration management
│   └── utils/         # Data models
├── deployment/        # Docker, AWS, Azure configs
├── examples/         # Example scripts and profiles
├── cli.py           # Command-line interface
└── requirements.txt # Dependencies
```

## Supported AI Models

**Anthropic Claude:**
- `claude-sonnet-4-20250514`
- `claude-sonnet-4-5-20250929` (recommended)

**OpenAI:**
- `gpt-4-turbo-preview`
- `gpt-4o`
- `o1-preview`

## Extending the Framework

### Add a Custom Scraper

```python
from src.scrapers.base import BaseScraper
from src.utils.models import SearchQuery, JobLead, ScraperResult

class CustomScraper(BaseScraper):
    def __init__(self):
        super().__init__("custom")

    def _build_search_url(self, query: SearchQuery) -> str:
        return f"https://example.com/jobs?q={'+'.join(query.keywords)}"

    def _parse_listing(self, data) -> JobLead:
        # Parse job data into JobLead model
        pass

    def search(self, query: SearchQuery) -> ScraperResult:
        # Implement search logic
        pass

# Register with manager
from src.scrapers import ScraperManager
manager = ScraperManager()
manager.register_scraper("custom", CustomScraper)
```

## Important Notes

### Web Scraping Limitations

**Indeed Scraper**: May encounter HTTP 403 errors due to anti-scraping measures. For production use:
- Consider Indeed's official API (requires partnership)
- Implement proxy rotation
- Use authenticated sessions
- Respect rate limits and robots.txt

**LinkedIn Scraper**: Returns sample data by default. For real data:
- Use LinkedIn's Job Search API with authentication
- Implement proper OAuth flow
- Follow API rate limits

The scrapers are provided for educational purposes to demonstrate the framework architecture.

### MVP Scope

This is an MVP focused on job leads. The framework is designed to be extended for:
- Sales leads (B2B platforms)
- Project requirements (freelance platforms)
- Other lead types

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file

## Support

- **Issues**: [GitHub Issues](https://github.com/vishalc412/Leads-scrapper/issues)
- **Documentation**: See examples/ directory for sample code

---

**Built with:** Python, FastAPI, BeautifulSoup, Anthropic Claude, OpenAI
