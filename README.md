# Leads Scraper

A comprehensive, production-ready framework for scraping and analyzing job leads across multiple platforms using AI-powered analysis.

## Features

- **Multi-Platform Scraping**: Support for Indeed, LinkedIn, Glassdoor, and more
- **AI-Powered Analysis**: Intelligent lead analysis using Claude (Anthropic) or GPT (OpenAI)
- **Flexible Architecture**: Easily extensible framework for adding new scrapers
- **RESTful API**: FastAPI backend for seamless UI integration
- **Multiple Deployment Options**: Run locally, Docker, AWS, or Azure
- **Data Persistence**: SQLite (default) with PostgreSQL support
- **Scalable Design**: Future-ready for sales leads, project requirements, and more

## Quick Start

### Prerequisites

- Python 3.9 or higher
- API key for Anthropic (Claude) or OpenAI (GPT)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/vishalc412/Leads-scrapper.git
cd Leads-scrapper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

4. Run a search:
```bash
python cli.py search "Python Developer" --city "San Francisco" --state "CA" --save
```

## Usage

### Command Line Interface

#### Search for Jobs

```bash
# Basic search
python cli.py search "Python Developer" --city "New York" --state "NY"

# Advanced search with filters
python cli.py search "Senior Software Engineer" \
  --city "Seattle" \
  --state "WA" \
  --remote \
  --salary-min 120000 \
  --experience-level "senior" \
  --max-results 50 \
  --save

# Search and save to JSON
python cli.py search "Data Scientist" \
  --city "Boston" \
  --state "MA" \
  --output results.json \
  --save
```

#### Analyze Leads

```bash
# Analyze recent leads
python cli.py analyze --limit 10

# Analyze specific leads
python cli.py analyze --lead-ids "abc123,def456,ghi789"

# Use specific AI model
python cli.py analyze --model "claude-sonnet-4-5-20250929"

# Analyze with user profile
python cli.py analyze --profile user_profile.json --output analysis.json
```

#### Start API Server

```bash
# Development server
python cli.py server --reload

# Production server
python cli.py server --workers 4 --host 0.0.0.0 --port 8000
```

#### List Saved Leads

```bash
python cli.py list --limit 20
```

### Python API

```python
from src.scrapers import ScraperManager
from src.analyzers import AnalyzerFactory
from src.utils.models import SearchQuery, Location
from src.storage import Database

# Create search query
query = SearchQuery(
    keywords=["Python", "Django", "FastAPI"],
    location=Location(
        city="San Francisco",
        state="CA",
        country="US",
        remote=False
    ),
    experience_level="mid-senior",
    max_results=50
)

# Search for leads
with ScraperManager() as scraper:
    results = scraper.search(query)
    print(f"Found {results.total_scraped} leads")

    # Save to database
    with Database() as db:
        db.save_leads(results.leads)

# Analyze leads
analyzer = AnalyzerFactory.create_analyzer()
analyses = analyzer.analyze_batch(results.leads[:10])

# Print top matches
for analysis in sorted(analyses, key=lambda x: x.match_score, reverse=True)[:5]:
    print(f"\nScore: {analysis.match_score:.1f}/100")
    print(f"Summary: {analysis.summary}")
```

### REST API

#### Start the API server:
```bash
python cli.py server
```

#### API Endpoints:

**Search for leads:**
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "keywords": ["Python", "Django"],
      "location": {"city": "Seattle", "state": "WA", "remote": false},
      "max_results": 20
    },
    "save_results": true
  }'
```

**Analyze leads:**
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "lead_ids": ["lead_id_1", "lead_id_2"],
    "model": "claude-sonnet-4-5-20250929"
  }'
```

**Get saved leads:**
```bash
curl http://localhost:8000/leads?page=1&page_size=20
```

**Health check:**
```bash
curl http://localhost:8000/health
```

## Deployment

### Docker

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or use the deployment script
chmod +x deployment/docker/deploy.sh
./deployment/docker/deploy.sh
```

### AWS (ECS Fargate)

```bash
# Deploy using CloudFormation
aws cloudformation create-stack \
  --stack-name leads-scraper \
  --template-body file://deployment/aws/cloudformation-template.yml \
  --parameters ParameterKey=AnthropicApiKey,ParameterValue=YOUR_KEY \
  --capabilities CAPABILITY_IAM
```

### Azure (Container Instances)

```bash
# Deploy using ARM template
az deployment group create \
  --resource-group leads-scraper-rg \
  --template-file deployment/azure/azure-deploy.json \
  --parameters anthropicApiKey=YOUR_KEY
```

## Configuration

### Environment Variables

```bash
# AI Configuration
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
AI_MODEL=claude-sonnet-4-5-20250929
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=4096

# Scraper Configuration
SCRAPER_MAX_RETRIES=3
SCRAPER_TIMEOUT=30
SCRAPER_RATE_LIMIT=1.0

# Storage Configuration
STORAGE_BACKEND=sqlite
DATA_DIR=./data

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
```

### Supported AI Models

**Anthropic Claude:**
- `claude-sonnet-4-20250514` (Claude Sonnet 4)
- `claude-sonnet-4-5-20250929` (Claude Sonnet 4.5) - **Recommended**

**OpenAI:**
- `gpt-4-turbo-preview`
- `gpt-4o`
- `o1-preview`

## Project Structure

```
Leads-scrapper/
├── src/
│   ├── scrapers/          # Web scrapers for different platforms
│   │   ├── base.py        # Base scraper class
│   │   ├── indeed_scraper.py
│   │   ├── linkedin_scraper.py
│   │   └── scraper_manager.py
│   ├── analyzers/         # AI analyzers
│   │   ├── base_analyzer.py
│   │   ├── anthropic_analyzer.py
│   │   ├── openai_analyzer.py
│   │   └── analyzer_factory.py
│   ├── api/              # FastAPI backend
│   │   └── main.py
│   ├── storage/          # Data persistence
│   │   └── database.py
│   ├── config/           # Configuration management
│   │   └── settings.py
│   └── utils/            # Data models and utilities
│       └── models.py
├── deployment/           # Deployment configurations
│   ├── docker/
│   ├── aws/
│   └── azure/
├── examples/            # Example scripts
├── tests/              # Test suite
├── cli.py             # Command-line interface
├── requirements.txt   # Python dependencies
├── setup.py          # Package setup
└── README.md         # This file
```

## Examples

### Example 1: Search and Analyze

```python
from src import ScraperManager, AnalyzerFactory, SearchQuery, Location, Database

# Search
query = SearchQuery(
    keywords=["Full Stack Developer"],
    location=Location(city="Austin", state="TX"),
    max_results=30
)

with ScraperManager() as scraper:
    results = scraper.search(query)

# Analyze top 10
analyzer = AnalyzerFactory.create_analyzer()
analyses = analyzer.analyze_batch(results.leads[:10])

# Save to database
with Database() as db:
    db.save_leads(results.leads)
    for analysis in analyses:
        db.save_analysis(analysis)
```

### Example 2: User Profile Matching

Create `user_profile.json`:
```json
{
  "skills": ["Python", "Django", "React", "PostgreSQL"],
  "experience_years": 5,
  "preferences": "Remote-first companies, focus on AI/ML projects"
}
```

Run analysis:
```bash
python cli.py search "ML Engineer" --remote --save
python cli.py analyze --profile user_profile.json --limit 10
```

## Extending the Framework

### Adding a New Scraper

```python
from src.scrapers.base import BaseScraper
from src.utils.models import SearchQuery, JobLead, ScraperResult

class CustomScraper(BaseScraper):
    def __init__(self):
        super().__init__("custom_source")

    def _build_search_url(self, query: SearchQuery) -> str:
        # Build URL from query
        return f"https://example.com/search?q={query.keywords}"

    def _parse_listing(self, listing_data) -> JobLead:
        # Parse listing data into JobLead
        pass

    def search(self, query: SearchQuery) -> ScraperResult:
        # Implement search logic
        pass

# Register with manager
from src.scrapers import ScraperManager
manager = ScraperManager()
manager.register_scraper("custom", CustomScraper)
```

### Future Enhancements

- **Sales Leads**: Extend framework for B2B sales lead generation
- **Project Requirements**: Scrape freelance platforms (Upwork, Freelancer)
- **Email Integration**: Automated lead notifications
- **CRM Integration**: Export to Salesforce, HubSpot
- **Advanced Filtering**: ML-based lead scoring

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_scrapers.py
```

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Support

- **Issues**: [GitHub Issues](https://github.com/vishalc412/Leads-scrapper/issues)
- **Documentation**: See `docs/` directory
- **Email**: [Contact](mailto:your.email@example.com)

## Acknowledgments

- Built with FastAPI, BeautifulSoup, Anthropic Claude, and OpenAI
- Inspired by the need for intelligent lead generation

---

**Note**: This is an MVP focused on job leads. The framework is designed to be extended for sales leads, project requirements, and other lead types in future versions.
