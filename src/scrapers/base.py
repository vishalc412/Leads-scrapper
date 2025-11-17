"""
Base scraper class for all lead scrapers.
Provides common functionality and interface.
"""

import time
import logging
import hashlib
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..utils.models import SearchQuery, JobLead, ScraperResult, LeadStatus
from ..config import get_config


logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    def __init__(self, source_name: str):
        """
        Initialize the scraper.

        Args:
            source_name: Name of the scraping source (e.g., "indeed", "linkedin")
        """
        self.source_name = source_name
        self.config = get_config().scraper
        self.session = self._create_session()
        self.last_request_time = 0.0

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set headers
        session.headers.update({
            'User-Agent': self.config.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

        return session

    def _rate_limit(self):
        """Apply rate limiting between requests."""
        if self.config.rate_limit > 0:
            time_since_last = time.time() - self.last_request_time
            min_interval = 1.0 / self.config.rate_limit

            if time_since_last < min_interval:
                time.sleep(min_interval - time_since_last)

        self.last_request_time = time.time()

    def _generate_lead_id(self, url: str, title: str) -> str:
        """
        Generate a unique ID for a lead.

        Args:
            url: Job posting URL
            title: Job title

        Returns:
            Unique identifier string
        """
        unique_string = f"{self.source_name}:{url}:{title}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:16]

    def _make_request(self, url: str, method: str = "GET", **kwargs) -> Optional[requests.Response]:
        """
        Make an HTTP request with rate limiting and error handling.

        Args:
            url: URL to request
            method: HTTP method
            **kwargs: Additional arguments for requests

        Returns:
            Response object or None if failed
        """
        self._rate_limit()

        try:
            kwargs.setdefault('timeout', self.config.timeout)
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {str(e)}")
            return None

    @abstractmethod
    def search(self, query: SearchQuery) -> ScraperResult:
        """
        Search for leads based on query parameters.

        Args:
            query: Search query parameters

        Returns:
            ScraperResult containing found leads
        """
        pass

    @abstractmethod
    def _build_search_url(self, query: SearchQuery) -> str:
        """
        Build the search URL for the specific platform.

        Args:
            query: Search query parameters

        Returns:
            Formatted search URL
        """
        pass

    @abstractmethod
    def _parse_listing(self, listing_data: Any) -> Optional[JobLead]:
        """
        Parse a single listing into a JobLead.

        Args:
            listing_data: Raw listing data (HTML element, JSON, etc.)

        Returns:
            Parsed JobLead or None if parsing failed
        """
        pass

    def scrape(self, query: SearchQuery) -> ScraperResult:
        """
        Main scraping method with error handling and timing.

        Args:
            query: Search query parameters

        Returns:
            ScraperResult with leads and metadata
        """
        start_time = time.time()
        logger.info(f"Starting scrape for {self.source_name} with query: {query.keywords}")

        try:
            result = self.search(query)
            result.execution_time = time.time() - start_time
            logger.info(
                f"Completed scrape for {self.source_name}: "
                f"{result.total_scraped} leads in {result.execution_time:.2f}s"
            )
            return result

        except Exception as e:
            logger.error(f"Scraping failed for {self.source_name}: {str(e)}", exc_info=True)
            return ScraperResult(
                source=self.source_name,
                query=query,
                errors=[str(e)],
                execution_time=time.time() - start_time
            )

    def close(self):
        """Clean up resources."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class MockScraper(BaseScraper):
    """Mock scraper for testing purposes."""

    def __init__(self):
        super().__init__("mock")

    def _build_search_url(self, query: SearchQuery) -> str:
        return "https://example.com/mock"

    def _parse_listing(self, listing_data: Any) -> Optional[JobLead]:
        return listing_data

    def search(self, query: SearchQuery) -> ScraperResult:
        """Return mock data for testing."""
        from ..utils.models import Company, Location

        mock_leads = []
        for i in range(min(3, query.max_results)):
            lead = JobLead(
                id=self._generate_lead_id(f"https://example.com/job/{i}", f"Mock Job {i}"),
                source=self.source_name,
                url=f"https://example.com/job/{i}",
                title=f"Mock {query.keywords[0] if query.keywords else 'Generic'} Position {i}",
                description=f"This is a mock job description for testing purposes. "
                           f"Skills required: {', '.join(query.keywords)}",
                company=Company(
                    name=f"Mock Company {i}",
                    industry=query.industry or "Technology"
                ),
                location=query.location,
                required_skills=query.keywords,
                status=LeadStatus.NEW,
                posted_date=datetime.utcnow()
            )
            mock_leads.append(lead)

        return ScraperResult(
            source=self.source_name,
            query=query,
            leads=mock_leads,
            total_found=len(mock_leads),
            total_scraped=len(mock_leads)
        )
