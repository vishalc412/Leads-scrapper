"""
Indeed job board scraper.
"""

import logging
from typing import Optional, List
from urllib.parse import urlencode
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..utils.models import (
    SearchQuery, JobLead, ScraperResult, Company,
    Location, LeadStatus
)

logger = logging.getLogger(__name__)


class IndeedScraper(BaseScraper):
    """Scraper for Indeed.com job listings."""

    BASE_URL = "https://www.indeed.com"

    def __init__(self):
        super().__init__("indeed")

    def _build_search_url(self, query: SearchQuery, start: int = 0) -> str:
        """
        Build Indeed search URL.

        Args:
            query: Search query parameters
            start: Pagination offset

        Returns:
            Formatted search URL
        """
        # Build query string
        q = " ".join(query.keywords)

        # Build location string
        location_parts = []
        if query.location.city:
            location_parts.append(query.location.city)
        if query.location.state:
            location_parts.append(query.location.state)
        if query.location.country:
            location_parts.append(query.location.country)

        l = ", ".join(location_parts) if location_parts else ""

        params = {
            'q': q,
            'l': l,
            'start': start
        }

        # Add remote filter
        if query.location.remote:
            params['sc'] = '0kf:attr(DSQF7);'

        # Add date filter
        if query.date_posted:
            params['fromage'] = query.date_posted

        # Add job type
        if query.job_type:
            job_type_map = {
                'full-time': 'fulltime',
                'part-time': 'parttime',
                'contract': 'contract',
                'temporary': 'temporary',
                'internship': 'internship'
            }
            jt = job_type_map.get(query.job_type.lower())
            if jt:
                params['jt'] = jt

        # Add salary filter
        if query.salary_min:
            params['salary'] = f"${query.salary_min}+"

        return f"{self.BASE_URL}/jobs?{urlencode(params)}"

    def _parse_listing(self, job_card) -> Optional[JobLead]:
        """
        Parse a job card element into a JobLead.

        Args:
            job_card: BeautifulSoup element containing job card

        Returns:
            Parsed JobLead or None
        """
        try:
            # Extract job key/ID
            job_key = job_card.get('data-jk')
            if not job_key:
                return None

            # Job title
            title_elem = job_card.find('h2', class_='jobTitle')
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)

            # Company name
            company_elem = job_card.find('span', class_='companyName')
            company_name = company_elem.get_text(strip=True) if company_elem else "Unknown"

            # Location
            location_elem = job_card.find('div', class_='companyLocation')
            location_text = location_elem.get_text(strip=True) if location_elem else ""
            location = self._parse_location(location_text)

            # Salary
            salary_elem = job_card.find('div', class_='salary-snippet')
            salary_min, salary_max = self._parse_salary(
                salary_elem.get_text(strip=True) if salary_elem else ""
            )

            # Job snippet (short description)
            snippet_elem = job_card.find('div', class_='job-snippet')
            description = snippet_elem.get_text(strip=True) if snippet_elem else ""

            # Posted date
            date_elem = job_card.find('span', class_='date')
            posted_date = self._parse_date(
                date_elem.get_text(strip=True) if date_elem else ""
            )

            # Build URL
            url = f"{self.BASE_URL}/viewjob?jk={job_key}"

            # Create JobLead
            lead = JobLead(
                id=self._generate_lead_id(url, title),
                source=self.source_name,
                url=url,
                title=title,
                description=description,
                company=Company(name=company_name),
                location=location,
                salary_min=salary_min,
                salary_max=salary_max,
                posted_date=posted_date,
                status=LeadStatus.NEW,
                raw_data={
                    'job_key': job_key,
                    'html': str(job_card)
                }
            )

            return lead

        except Exception as e:
            logger.error(f"Failed to parse job card: {str(e)}")
            return None

    def _parse_location(self, location_text: str) -> Location:
        """Parse location string into Location object."""
        parts = [p.strip() for p in location_text.split(',')]

        location = Location(remote=False)

        if 'remote' in location_text.lower():
            location.remote = True

        if len(parts) >= 1:
            location.city = parts[0]
        if len(parts) >= 2:
            location.state = parts[1]
        if len(parts) >= 3:
            location.country = parts[2]

        return location

    def _parse_salary(self, salary_text: str) -> tuple[Optional[int], Optional[int]]:
        """Parse salary string into min/max values."""
        if not salary_text:
            return None, None

        import re

        # Remove non-numeric characters except digits, dash, and period
        cleaned = re.sub(r'[^\d\-\.]', '', salary_text)

        # Look for range (e.g., "50000-80000")
        if '-' in cleaned:
            parts = cleaned.split('-')
            try:
                salary_min = int(float(parts[0]))
                salary_max = int(float(parts[1]))
                return salary_min, salary_max
            except (ValueError, IndexError):
                pass

        # Single value
        try:
            salary = int(float(cleaned))
            return salary, salary
        except ValueError:
            pass

        return None, None

    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """Parse relative date string (e.g., '2 days ago')."""
        if not date_text:
            return None

        import re

        # Extract number from text
        match = re.search(r'(\d+)', date_text)
        if not match:
            if 'today' in date_text.lower() or 'just posted' in date_text.lower():
                return datetime.utcnow()
            return None

        days_ago = int(match.group(1))

        if 'hour' in date_text.lower():
            return datetime.utcnow() - timedelta(hours=days_ago)
        elif 'day' in date_text.lower():
            return datetime.utcnow() - timedelta(days=days_ago)
        elif 'month' in date_text.lower():
            return datetime.utcnow() - timedelta(days=days_ago * 30)

        return None

    def search(self, query: SearchQuery) -> ScraperResult:
        """
        Search Indeed for job listings.

        Args:
            query: Search query parameters

        Returns:
            ScraperResult with found leads
        """
        leads: List[JobLead] = []
        errors: List[str] = []
        total_found = 0

        # Calculate pages needed
        results_per_page = 15  # Indeed typically shows 15 results per page
        max_pages = (query.max_results + results_per_page - 1) // results_per_page

        for page in range(max_pages):
            start = page * results_per_page

            # Build URL
            url = self._build_search_url(query, start=start)
            logger.info(f"Scraping Indeed page {page + 1}: {url}")

            # Make request
            response = self._make_request(url)
            if not response:
                errors.append(f"Failed to fetch page {page + 1}")
                continue

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find job cards
            job_cards = soup.find_all('div', class_='job_seen_beacon')

            if not job_cards and page == 0:
                # Try alternative selector
                job_cards = soup.find_all('td', class_='resultContent')

            if not job_cards:
                logger.warning(f"No job cards found on page {page + 1}")
                break

            # Update total found (first page only)
            if page == 0:
                count_elem = soup.find('div', class_='jobsearch-JobCountAndSortPane-jobCount')
                if count_elem:
                    import re
                    match = re.search(r'([\d,]+)', count_elem.get_text())
                    if match:
                        total_found = int(match.group(1).replace(',', ''))

            # Parse each job card
            for job_card in job_cards:
                if len(leads) >= query.max_results:
                    break

                lead = self._parse_listing(job_card)
                if lead:
                    leads.append(lead)

            # Check if we have enough results
            if len(leads) >= query.max_results:
                break

            # Check if there are more pages
            next_button = soup.find('a', {'aria-label': 'Next Page'})
            if not next_button:
                break

        return ScraperResult(
            source=self.source_name,
            query=query,
            leads=leads,
            total_found=total_found or len(leads),
            total_scraped=len(leads),
            errors=errors
        )
