"""
Scraper manager to orchestrate multiple scrapers.
"""

import logging
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from .base import BaseScraper, MockScraper
from .indeed_scraper import IndeedScraper
from .linkedin_scraper import LinkedInScraper
from ..utils.models import SearchQuery, ScraperResult, JobLead
from ..config import get_config

logger = logging.getLogger(__name__)


class ScraperManager:
    """Manages multiple scrapers and coordinates their execution."""

    def __init__(self, enabled_scrapers: Optional[List[str]] = None):
        """
        Initialize the scraper manager.

        Args:
            enabled_scrapers: List of scraper names to enable.
                            If None, uses config settings.
        """
        self.config = get_config()

        # Scraper registry
        self._scraper_classes = {
            'indeed': IndeedScraper,
            'linkedin': LinkedInScraper,
            'mock': MockScraper,
        }

        # Determine which scrapers to enable
        if enabled_scrapers is None:
            enabled_scrapers = self.config.enabled_job_boards

        # Initialize scrapers
        self.scrapers: Dict[str, BaseScraper] = {}
        for name in enabled_scrapers:
            if name in self._scraper_classes:
                try:
                    self.scrapers[name] = self._scraper_classes[name]()
                    logger.info(f"Initialized scraper: {name}")
                except Exception as e:
                    logger.error(f"Failed to initialize scraper {name}: {str(e)}")
            else:
                logger.warning(f"Unknown scraper: {name}")

        if not self.scrapers:
            logger.warning("No scrapers initialized, adding mock scraper")
            self.scrapers['mock'] = MockScraper()

    def register_scraper(self, name: str, scraper_class: type):
        """
        Register a new scraper class.

        Args:
            name: Scraper name
            scraper_class: Scraper class (must inherit from BaseScraper)
        """
        if not issubclass(scraper_class, BaseScraper):
            raise ValueError("Scraper must inherit from BaseScraper")

        self._scraper_classes[name] = scraper_class
        logger.info(f"Registered scraper class: {name}")

    def enable_scraper(self, name: str):
        """
        Enable a scraper.

        Args:
            name: Scraper name
        """
        if name in self._scraper_classes and name not in self.scrapers:
            try:
                self.scrapers[name] = self._scraper_classes[name]()
                logger.info(f"Enabled scraper: {name}")
            except Exception as e:
                logger.error(f"Failed to enable scraper {name}: {str(e)}")
        elif name in self.scrapers:
            logger.info(f"Scraper already enabled: {name}")
        else:
            logger.error(f"Unknown scraper: {name}")

    def disable_scraper(self, name: str):
        """
        Disable a scraper.

        Args:
            name: Scraper name
        """
        if name in self.scrapers:
            self.scrapers[name].close()
            del self.scrapers[name]
            logger.info(f"Disabled scraper: {name}")

    def search_all(
        self,
        query: SearchQuery,
        parallel: bool = True,
        max_workers: int = 4
    ) -> List[ScraperResult]:
        """
        Search across all enabled scrapers.

        Args:
            query: Search query parameters
            parallel: Whether to run scrapers in parallel
            max_workers: Maximum parallel workers

        Returns:
            List of ScraperResult from each scraper
        """
        if not self.scrapers:
            logger.warning("No scrapers enabled")
            return []

        results = []

        if parallel and len(self.scrapers) > 1:
            # Parallel execution
            logger.info(f"Running {len(self.scrapers)} scrapers in parallel")

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit tasks
                future_to_scraper = {
                    executor.submit(scraper.scrape, query): name
                    for name, scraper in self.scrapers.items()
                }

                # Collect results
                for future in as_completed(future_to_scraper):
                    scraper_name = future_to_scraper[future]
                    try:
                        result = future.result()
                        results.append(result)
                        logger.info(
                            f"Scraper {scraper_name} completed: "
                            f"{result.total_scraped} leads"
                        )
                    except Exception as e:
                        logger.error(f"Scraper {scraper_name} failed: {str(e)}")

        else:
            # Sequential execution
            logger.info(f"Running {len(self.scrapers)} scrapers sequentially")

            for name, scraper in self.scrapers.items():
                try:
                    result = scraper.scrape(query)
                    results.append(result)
                    logger.info(
                        f"Scraper {name} completed: {result.total_scraped} leads"
                    )
                except Exception as e:
                    logger.error(f"Scraper {name} failed: {str(e)}")

        return results

    def aggregate_results(
        self,
        results: List[ScraperResult],
        deduplicate: bool = True
    ) -> ScraperResult:
        """
        Aggregate results from multiple scrapers.

        Args:
            results: List of ScraperResult objects
            deduplicate: Whether to remove duplicate leads

        Returns:
            Aggregated ScraperResult
        """
        if not results:
            return ScraperResult(
                source="aggregated",
                query=SearchQuery(
                    keywords=[],
                    location=Location()
                ),
                leads=[],
                total_found=0,
                total_scraped=0
            )

        all_leads: List[JobLead] = []
        all_errors: List[str] = []
        total_found = 0
        total_time = 0.0

        for result in results:
            all_leads.extend(result.leads)
            all_errors.extend(result.errors)
            total_found += result.total_found
            total_time += result.execution_time

        # Deduplicate based on URL
        if deduplicate and all_leads:
            seen_urls = set()
            unique_leads = []

            for lead in all_leads:
                if lead.url not in seen_urls:
                    seen_urls.add(lead.url)
                    unique_leads.append(lead)

            logger.info(
                f"Deduplication: {len(all_leads)} -> {len(unique_leads)} leads"
            )
            all_leads = unique_leads

        return ScraperResult(
            source="aggregated",
            query=results[0].query if results else SearchQuery(keywords=[], location=Location()),
            leads=all_leads,
            total_found=total_found,
            total_scraped=len(all_leads),
            errors=all_errors,
            execution_time=total_time
        )

    def search(
        self,
        query: SearchQuery,
        parallel: bool = True,
        deduplicate: bool = True
    ) -> ScraperResult:
        """
        Search and return aggregated results.

        Args:
            query: Search query parameters
            parallel: Whether to run scrapers in parallel
            deduplicate: Whether to remove duplicates

        Returns:
            Aggregated ScraperResult
        """
        start_time = time.time()

        results = self.search_all(query, parallel=parallel)
        aggregated = self.aggregate_results(results, deduplicate=deduplicate)

        aggregated.execution_time = time.time() - start_time

        logger.info(
            f"Search completed: {aggregated.total_scraped} total leads "
            f"from {len(results)} sources in {aggregated.execution_time:.2f}s"
        )

        return aggregated

    def close_all(self):
        """Close all scrapers."""
        for scraper in self.scrapers.values():
            scraper.close()
        self.scrapers.clear()
        logger.info("All scrapers closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_all()
