"""Leads Scraper - A comprehensive framework for scraping and analyzing job leads."""

__version__ = "1.0.0"
__author__ = "Leads Scraper Team"

from .config import get_config, load_config, AIModel, Environment
from .scrapers import ScraperManager, BaseScraper
from .analyzers import AnalyzerFactory
from .storage import Database
from .utils.models import SearchQuery, JobLead, LeadAnalysis, Location

__all__ = [
    "get_config",
    "load_config",
    "AIModel",
    "Environment",
    "ScraperManager",
    "BaseScraper",
    "AnalyzerFactory",
    "Database",
    "SearchQuery",
    "JobLead",
    "LeadAnalysis",
    "Location"
]
