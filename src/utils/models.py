"""
Data models for leads and search queries.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum


class LeadType(str, Enum):
    """Type of lead."""
    JOB = "job"
    SALES = "sales"
    PROJECT = "project"
    OTHER = "other"


class LeadStatus(str, Enum):
    """Status of a lead."""
    NEW = "new"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    CONTACTED = "contacted"
    CLOSED = "closed"


class Location(BaseModel):
    """Geographic location information."""
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None  # {"lat": x, "lon": y}
    remote: bool = False


class SearchQuery(BaseModel):
    """Search parameters for finding leads."""
    lead_type: LeadType = Field(default=LeadType.JOB)
    keywords: List[str] = Field(..., description="Skills, job titles, or search terms")
    location: Location = Field(..., description="Geographic location")
    industry: Optional[str] = Field(default=None, description="Industry sector")
    experience_level: Optional[str] = Field(default=None, description="Entry, Mid, Senior, etc.")
    job_type: Optional[str] = Field(default=None, description="Full-time, Contract, etc.")
    salary_min: Optional[int] = Field(default=None, description="Minimum salary")
    salary_max: Optional[int] = Field(default=None, description="Maximum salary")
    date_posted: Optional[int] = Field(default=None, description="Days since posted")
    max_results: int = Field(default=50, description="Maximum results to return")


class Company(BaseModel):
    """Company information."""
    name: str
    website: Optional[HttpUrl] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[HttpUrl] = None


class JobLead(BaseModel):
    """Job lead information."""
    # Identification
    id: str = Field(..., description="Unique identifier")
    source: str = Field(..., description="Source platform (e.g., LinkedIn, Indeed)")
    url: HttpUrl = Field(..., description="Original job posting URL")

    # Job details
    title: str
    description: str
    company: Company
    location: Location

    # Requirements
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    experience_level: Optional[str] = None
    education: Optional[str] = None

    # Compensation
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = Field(default="USD")
    benefits: List[str] = Field(default_factory=list)

    # Employment details
    job_type: Optional[str] = None  # Full-time, Part-time, Contract
    remote_type: Optional[str] = None  # Remote, Hybrid, On-site

    # Metadata
    posted_date: Optional[datetime] = None
    scraped_date: datetime = Field(default_factory=datetime.utcnow)
    expires_date: Optional[datetime] = None

    # Status
    status: LeadStatus = Field(default=LeadStatus.NEW)

    # Raw data
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class LeadAnalysis(BaseModel):
    """AI-generated analysis of a lead."""
    lead_id: str
    model_used: str

    # Scores (0-100)
    relevance_score: float = Field(..., ge=0, le=100)
    match_score: float = Field(..., ge=0, le=100)
    quality_score: float = Field(..., ge=0, le=100)

    # Analysis
    summary: str
    key_highlights: List[str] = Field(default_factory=list)
    match_reasons: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    # Skill matching
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)

    # Metadata
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time: Optional[float] = None  # seconds


class SalesLead(BaseModel):
    """Sales lead information (for future expansion)."""
    id: str
    source: str
    company: Company
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    lead_type: str = "sales"
    status: LeadStatus = Field(default=LeadStatus.NEW)
    scraped_date: datetime = Field(default_factory=datetime.utcnow)
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class ProjectLead(BaseModel):
    """Project requirement lead (for future expansion)."""
    id: str
    source: str
    title: str
    description: str
    client: Optional[str] = None
    budget: Optional[Dict[str, Any]] = None
    deadline: Optional[datetime] = None
    required_skills: List[str] = Field(default_factory=list)
    lead_type: str = "project"
    status: LeadStatus = Field(default=LeadStatus.NEW)
    scraped_date: datetime = Field(default_factory=datetime.utcnow)
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class ScraperResult(BaseModel):
    """Result from a scraper operation."""
    source: str
    query: SearchQuery
    leads: List[JobLead] = Field(default_factory=list)
    total_found: int = 0
    total_scraped: int = 0
    errors: List[str] = Field(default_factory=list)
    execution_time: float = 0.0  # seconds
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AnalysisRequest(BaseModel):
    """Request for analyzing leads."""
    lead_ids: List[str] = Field(..., description="List of lead IDs to analyze")
    search_query: Optional[SearchQuery] = Field(default=None)
    user_profile: Optional[Dict[str, Any]] = Field(
        default=None,
        description="User skills, experience, preferences"
    )


class AnalysisResponse(BaseModel):
    """Response from lead analysis."""
    analyses: List[LeadAnalysis] = Field(default_factory=list)
    total_analyzed: int = 0
    errors: List[str] = Field(default_factory=list)
    execution_time: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
