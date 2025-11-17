#!/usr/bin/env python3
"""
Command-line interface for Leads Scraper.
"""

import argparse
import logging
import json
import sys
from typing import Optional

from src.config import get_config, load_config, set_config, AIModel
from src.scrapers import ScraperManager
from src.analyzers import AnalyzerFactory
from src.storage import Database
from src.utils.models import SearchQuery, Location

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_search_query(args) -> SearchQuery:
    """Build SearchQuery from CLI arguments."""
    keywords = args.keywords.split(',') if isinstance(args.keywords, str) else args.keywords

    location = Location(
        city=args.city,
        state=args.state,
        country=args.country,
        remote=args.remote
    )

    return SearchQuery(
        keywords=keywords,
        location=location,
        industry=args.industry,
        experience_level=args.experience_level,
        job_type=args.job_type,
        salary_min=args.salary_min,
        salary_max=args.salary_max,
        date_posted=args.date_posted,
        max_results=args.max_results
    )


def command_search(args):
    """Execute search command."""
    logger.info("Starting lead search...")

    # Build query
    query = setup_search_query(args)

    # Initialize scraper manager
    with ScraperManager() as scraper_manager:
        # Perform search
        result = scraper_manager.search(
            query,
            parallel=not args.sequential,
            deduplicate=not args.no_deduplicate
        )

        # Save to database if requested
        if args.save:
            with Database() as db:
                saved_count = db.save_leads(result.leads)
                logger.info(f"Saved {saved_count} leads to database")

        # Output results
        if args.output:
            output_data = {
                "query": query.model_dump(),
                "total_found": result.total_found,
                "total_scraped": result.total_scraped,
                "execution_time": result.execution_time,
                "leads": [lead.model_dump() for lead in result.leads]
            }

            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)
            logger.info(f"Results saved to {args.output}")

        # Print summary
        print(f"\n{'='*60}")
        print(f"Search Results")
        print(f"{'='*60}")
        print(f"Total found: {result.total_found}")
        print(f"Total scraped: {result.total_scraped}")
        print(f"Execution time: {result.execution_time:.2f}s")
        print(f"\nLeads ({len(result.leads)}):")
        print(f"{'-'*60}")

        for i, lead in enumerate(result.leads[:args.display_limit], 1):
            print(f"\n{i}. {lead.title}")
            print(f"   Company: {lead.company.name}")
            print(f"   Location: {lead.location.city}, {lead.location.state}")
            print(f"   Source: {lead.source}")
            print(f"   URL: {lead.url}")

        if len(result.leads) > args.display_limit:
            print(f"\n... and {len(result.leads) - args.display_limit} more")


def command_analyze(args):
    """Execute analyze command."""
    logger.info("Starting lead analysis...")

    with Database() as db:
        # Get leads from database
        if args.lead_ids:
            lead_ids = args.lead_ids.split(',')
            leads = [db.get_lead(lid.strip()) for lid in lead_ids]
            leads = [l for l in leads if l]
        else:
            # Get recent leads
            leads = db.get_leads(limit=args.limit)

        if not leads:
            logger.error("No leads found to analyze")
            sys.exit(1)

        logger.info(f"Analyzing {len(leads)} leads...")

        # Create analyzer
        model = AIModel(args.model) if args.model else None
        analyzer = AnalyzerFactory.create_analyzer(model)

        # Load user profile if provided
        user_profile = None
        if args.profile:
            with open(args.profile, 'r') as f:
                user_profile = json.load(f)

        # Analyze leads
        analyses = analyzer.analyze_batch(leads, user_profile=user_profile)

        # Save analyses
        for analysis in analyses:
            db.save_analysis(analysis)

        # Output results
        if args.output:
            output_data = {
                "analyses": [a.model_dump() for a in analyses]
            }
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)
            logger.info(f"Analysis saved to {args.output}")

        # Print summary
        print(f"\n{'='*60}")
        print(f"Analysis Results")
        print(f"{'='*60}")

        for analysis in analyses:
            lead = next((l for l in leads if l.id == analysis.lead_id), None)
            if not lead:
                continue

            print(f"\n{lead.title} - {lead.company.name}")
            print(f"{'-'*60}")
            print(f"Relevance Score: {analysis.relevance_score:.1f}/100")
            print(f"Match Score: {analysis.match_score:.1f}/100")
            print(f"Quality Score: {analysis.quality_score:.1f}/100")
            print(f"\nSummary: {analysis.summary}")

            if analysis.key_highlights:
                print(f"\nKey Highlights:")
                for highlight in analysis.key_highlights:
                    print(f"  • {highlight}")

            if analysis.concerns:
                print(f"\nConcerns:")
                for concern in analysis.concerns:
                    print(f"  • {concern}")


def command_server(args):
    """Start API server."""
    import uvicorn
    from src.api.main import app

    logger.info(f"Starting API server on {args.host}:{args.port}")

    uvicorn.run(
        "src.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level=args.log_level
    )


def command_list(args):
    """List saved leads."""
    with Database() as db:
        leads = db.get_leads(limit=args.limit)

        print(f"\n{'='*60}")
        print(f"Saved Leads ({len(leads)})")
        print(f"{'='*60}")

        for i, lead in enumerate(leads, 1):
            print(f"\n{i}. {lead.title}")
            print(f"   Company: {lead.company.name}")
            print(f"   Location: {lead.location.city}, {lead.location.state}")
            print(f"   Source: {lead.source}")
            print(f"   Posted: {lead.posted_date}")
            print(f"   ID: {lead.id}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Leads Scraper - Search and analyze job leads",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Global options
    parser.add_argument(
        '--config',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search for job leads')
    search_parser.add_argument(
        'keywords',
        nargs='+',
        help='Search keywords (skills, job titles, etc.)'
    )
    search_parser.add_argument('--city', help='City')
    search_parser.add_argument('--state', help='State/Province')
    search_parser.add_argument('--country', default='US', help='Country')
    search_parser.add_argument('--remote', action='store_true', help='Remote jobs only')
    search_parser.add_argument('--industry', help='Industry sector')
    search_parser.add_argument('--experience-level', help='Experience level')
    search_parser.add_argument('--job-type', help='Job type (full-time, contract, etc.)')
    search_parser.add_argument('--salary-min', type=int, help='Minimum salary')
    search_parser.add_argument('--salary-max', type=int, help='Maximum salary')
    search_parser.add_argument('--date-posted', type=int, help='Days since posted')
    search_parser.add_argument('--max-results', type=int, default=50, help='Maximum results')
    search_parser.add_argument('--sequential', action='store_true', help='Run scrapers sequentially')
    search_parser.add_argument('--no-deduplicate', action='store_true', help='Disable deduplication')
    search_parser.add_argument('--save', action='store_true', help='Save results to database')
    search_parser.add_argument('--output', help='Output file (JSON)')
    search_parser.add_argument('--display-limit', type=int, default=10, help='Number of results to display')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze job leads')
    analyze_parser.add_argument('--lead-ids', help='Comma-separated lead IDs')
    analyze_parser.add_argument('--limit', type=int, default=10, help='Number of recent leads to analyze')
    analyze_parser.add_argument('--model', help='AI model to use')
    analyze_parser.add_argument('--profile', help='Path to user profile JSON')
    analyze_parser.add_argument('--output', help='Output file (JSON)')

    # Server command
    server_parser = subparsers.add_parser('server', help='Start API server')
    server_parser.add_argument('--host', default='0.0.0.0', help='Host')
    server_parser.add_argument('--port', type=int, default=8000, help='Port')
    server_parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
    server_parser.add_argument('--workers', type=int, default=4, help='Number of workers')
    server_parser.add_argument('--log-level', default='info', help='Log level')

    # List command
    list_parser = subparsers.add_parser('list', help='List saved leads')
    list_parser.add_argument('--limit', type=int, default=20, help='Number of leads to list')

    # Parse arguments
    args = parser.parse_args()

    # Configure logging
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Load configuration
    if args.config:
        config = load_config(args.config)
        set_config(config)

    # Execute command
    if args.command == 'search':
        command_search(args)
    elif args.command == 'analyze':
        command_analyze(args)
    elif args.command == 'server':
        command_server(args)
    elif args.command == 'list':
        command_list(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
