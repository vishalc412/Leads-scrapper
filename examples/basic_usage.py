#!/usr/bin/env python3
"""
Basic usage example for Leads Scraper.
This script demonstrates how to search for job leads and analyze them.
"""

import json
from src.scrapers import ScraperManager
from src.analyzers import AnalyzerFactory
from src.utils.models import SearchQuery, Location
from src.storage import Database
from src.config import get_config


def main():
    print("=" * 60)
    print("Leads Scraper - Basic Usage Example")
    print("=" * 60)

    # 1. Create a search query
    print("\n1. Creating search query...")
    query = SearchQuery(
        keywords=["Python", "Django", "FastAPI"],
        location=Location(
            city="San Francisco",
            state="CA",
            country="US",
            remote=False
        ),
        experience_level="mid-senior",
        job_type="full-time",
        max_results=10  # Limit to 10 for demo
    )
    print(f"   Searching for: {', '.join(query.keywords)}")
    print(f"   Location: {query.location.city}, {query.location.state}")

    # 2. Search for leads
    print("\n2. Searching for job leads...")
    with ScraperManager() as scraper_manager:
        results = scraper_manager.search(query, parallel=True, deduplicate=True)

    print(f"   Found {results.total_scraped} leads in {results.execution_time:.2f}s")

    if not results.leads:
        print("\n   No leads found. Try adjusting your search criteria.")
        return

    # 3. Display results
    print("\n3. Search Results:")
    print("-" * 60)
    for i, lead in enumerate(results.leads, 1):
        print(f"\n   {i}. {lead.title}")
        print(f"      Company: {lead.company.name}")
        print(f"      Location: {lead.location.city}, {lead.location.state}")
        print(f"      Source: {lead.source}")
        print(f"      URL: {lead.url}")
        if lead.salary_min or lead.salary_max:
            salary_range = f"${lead.salary_min:,}" if lead.salary_min else ""
            if lead.salary_max and lead.salary_max != lead.salary_min:
                salary_range += f" - ${lead.salary_max:,}"
            if salary_range:
                print(f"      Salary: {salary_range}")

    # 4. Save to database
    print("\n4. Saving leads to database...")
    with Database() as db:
        saved_count = db.save_leads(results.leads)
    print(f"   Saved {saved_count} leads to database")

    # 5. Analyze leads (if API key is configured)
    config = get_config()
    if config.ai.get_api_key():
        print("\n5. Analyzing leads with AI...")

        # Load user profile if exists
        user_profile = None
        try:
            with open('examples/user_profile.json', 'r') as f:
                user_profile = json.load(f)
            print("   Loaded user profile for personalized analysis")
        except FileNotFoundError:
            print("   No user profile found, using generic analysis")

        # Create analyzer
        analyzer = AnalyzerFactory.create_analyzer()

        # Analyze first 5 leads
        leads_to_analyze = results.leads[:5]
        print(f"   Analyzing {len(leads_to_analyze)} leads...")

        analyses = analyzer.analyze_batch(
            leads_to_analyze,
            search_query=query,
            user_profile=user_profile
        )

        # Save analyses
        with Database() as db:
            for analysis in analyses:
                db.save_analysis(analysis)

        # Display top matches
        print("\n   Top Matches (by match score):")
        print("-" * 60)

        sorted_analyses = sorted(
            analyses,
            key=lambda x: x.match_score,
            reverse=True
        )

        for i, analysis in enumerate(sorted_analyses[:3], 1):
            lead = next(l for l in leads_to_analyze if l.id == analysis.lead_id)

            print(f"\n   {i}. {lead.title} - {lead.company.name}")
            print(f"      Relevance: {analysis.relevance_score:.1f}/100")
            print(f"      Match: {analysis.match_score:.1f}/100")
            print(f"      Quality: {analysis.quality_score:.1f}/100")
            print(f"\n      Summary: {analysis.summary}")

            if analysis.key_highlights:
                print(f"\n      Highlights:")
                for highlight in analysis.key_highlights[:3]:
                    print(f"      • {highlight}")

            if analysis.concerns:
                print(f"\n      Concerns:")
                for concern in analysis.concerns[:2]:
                    print(f"      • {concern}")

    else:
        print("\n5. Skipping AI analysis (no API key configured)")
        print("   Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env to enable")

    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("  - View saved leads: python cli.py list")
    print("  - Run analysis: python cli.py analyze --limit 10")
    print("  - Start API server: python cli.py server")
    print()


if __name__ == "__main__":
    main()
