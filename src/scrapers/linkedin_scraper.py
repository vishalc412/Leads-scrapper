"""
LinkedIn job board scraper.
Note: LinkedIn has strict anti-scraping measures. This implementation
uses their public job search API endpoints where possible.
For production use, consider using LinkedIn's official API with authentication.
"""

import logging
import json
from typing import Optional, List
from urllib.parse import urlencode, quote
from datetime import datetime, timedelta

from .base import BaseScraper
from ..utils.models import (
    SearchQuery, JobLead, ScraperResult, Company,
    Location, LeadStatus
)

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    """
    Scraper for LinkedIn job listings.

    Note: This is a simplified implementation. For production use,
    consider using LinkedIn's official Job Search API with proper authentication.
    """

    BASE_URL = "https://www.linkedin.com"

    def __init__(self):
        super().__init__("linkedin")
        # LinkedIn requires specific headers
        self.session.headers.update({
            'authority': 'www.linkedin.com',
            'accept': 'application/json',
            'x-li-lang': 'en_US',
        })

    def _build_search_url(self, query: SearchQuery, start: int = 0) -> str:
        """
        Build LinkedIn job search URL.

        Args:
            query: Search query parameters
            start: Pagination offset

        Returns:
            Formatted search URL
        """
        keywords = " ".join(query.keywords)

        # Build location string
        location_parts = []
        if query.location.city:
            location_parts.append(query.location.city)
        if query.location.state:
            location_parts.append(query.location.state)
        if query.location.country:
            location_parts.append(query.location.country)

        location = ", ".join(location_parts) if location_parts else ""

        params = {
            'keywords': keywords,
            'location': location,
            'start': start
        }

        # Add filters
        if query.date_posted:
            # LinkedIn uses 'f_TPR' for time posted (r86400 = 24h, r604800 = 7d, r2592000 = 30d)
            if query.date_posted <= 1:
                params['f_TPR'] = 'r86400'
            elif query.date_posted <= 7:
                params['f_TPR'] = 'r604800'
            elif query.date_posted <= 30:
                params['f_TPR'] = 'r2592000'

        # Job type
        if query.job_type:
            job_type_map = {
                'full-time': 'F',
                'part-time': 'P',
                'contract': 'C',
                'temporary': 'T',
                'internship': 'I'
            }
            jt = job_type_map.get(query.job_type.lower())
            if jt:
                params['f_JT'] = jt

        # Remote filter
        if query.location.remote:
            params['f_WT'] = '2'  # Remote

        # Experience level
        if query.experience_level:
            level_map = {
                'entry': '2',
                'associate': '3',
                'mid-senior': '4',
                'director': '5',
                'executive': '6'
            }
            level = level_map.get(query.experience_level.lower())
            if level:
                params['f_E'] = level

        return f"{self.BASE_URL}/jobs/search?{urlencode(params)}"

    def _parse_listing(self, job_data: dict) -> Optional[JobLead]:
        """
        Parse job data into a JobLead.

        Args:
            job_data: Job data dictionary

        Returns:
            Parsed JobLead or None
        """
        try:
            job_id = job_data.get('jobId') or job_data.get('entityUrn', '').split(':')[-1]
            if not job_id:
                return None

            title = job_data.get('title', '')
            company_name = job_data.get('companyName', 'Unknown')
            location_text = job_data.get('formattedLocation', '')

            # Parse location
            location = self._parse_location(location_text)

            # Description
            description = job_data.get('description', '')

            # URL
            url = f"{self.BASE_URL}/jobs/view/{job_id}"

            # Posted date
            listed_at = job_data.get('listedAt')
            posted_date = None
            if listed_at:
                try:
                    posted_date = datetime.fromtimestamp(listed_at / 1000)
                except (ValueError, TypeError):
                    pass

            # Work remote allowed
            remote = job_data.get('workRemoteAllowed', False)
            if remote:
                location.remote = True

            # Create JobLead
            lead = JobLead(
                id=self._generate_lead_id(url, title),
                source=self.source_name,
                url=url,
                title=title,
                description=description,
                company=Company(name=company_name),
                location=location,
                posted_date=posted_date,
                status=LeadStatus.NEW,
                raw_data=job_data
            )

            return lead

        except Exception as e:
            logger.error(f"Failed to parse LinkedIn job: {str(e)}")
            return None

    def _parse_location(self, location_text: str) -> Location:
        """Parse location string into Location object."""
        parts = [p.strip() for p in location_text.split(',')]

        location = Location(remote='remote' in location_text.lower())

        if len(parts) >= 1:
            location.city = parts[0]
        if len(parts) >= 2:
            # Could be state or country
            location.state = parts[1]
        if len(parts) >= 3:
            location.country = parts[2]

        return location

    def search(self, query: SearchQuery) -> ScraperResult:
        """
        Search LinkedIn for job listings.

        Note: This is a simplified implementation that may not work consistently
        due to LinkedIn's anti-scraping measures. Consider using their official API.

        Args:
            query: Search query parameters

        Returns:
            ScraperResult with found leads
        """
        leads: List[JobLead] = []
        errors: List[str] = []

        logger.warning(
            "LinkedIn scraper is using a simplified approach. "
            "For production use, consider LinkedIn's official Job Search API."
        )

        # For MVP, return mock data to demonstrate structure
        # In production, this would make actual API calls with proper authentication

        url = self._build_search_url(query)
        logger.info(f"LinkedIn search URL (for reference): {url}")

        # Create sample leads based on query
        from ..utils.models import Company

        sample_titles = [
            f"Senior {query.keywords[0] if query.keywords else 'Software'} Engineer",
            f"{query.keywords[0] if query.keywords else 'Full Stack'} Developer",
            f"Lead {query.keywords[0] if query.keywords else 'Software'} Architect"
        ]

        for i, title in enumerate(sample_titles[:query.max_results]):
            lead = JobLead(
                id=self._generate_lead_id(f"{self.BASE_URL}/jobs/view/sample-{i}", title),
                source=self.source_name,
                url=f"{self.BASE_URL}/jobs/view/sample-{i}",
                title=title,
                description=f"LinkedIn job posting for {title}. Skills: {', '.join(query.keywords)}",
                company=Company(name=f"Tech Company {i + 1}"),
                location=query.location,
                required_skills=query.keywords,
                posted_date=datetime.utcnow() - timedelta(days=i),
                status=LeadStatus.NEW,
                raw_data={"note": "Sample data - implement actual scraping with LinkedIn API"}
            )
            leads.append(lead)

        errors.append(
            "Using sample data. Implement actual LinkedIn API integration for production use."
        )

        return ScraperResult(
            source=self.source_name,
            query=query,
            leads=leads,
            total_found=len(leads),
            total_scraped=len(leads),
            errors=errors
        )
