"""
FastAPI backend for Leads Scraper.
Provides REST API for UI integration.
"""

import logging
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..utils.models import (
    SearchQuery, JobLead, LeadAnalysis, ScraperResult,
    AnalysisRequest, AnalysisResponse, LeadStatus
)
from ..scrapers import ScraperManager
from ..analyzers import AnalyzerFactory
from ..storage import Database
from ..config import get_config, AIModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
db: Optional[Database] = None
scraper_manager: Optional[ScraperManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    global db, scraper_manager

    # Startup
    logger.info("Starting Leads Scraper API...")
    db = Database()
    scraper_manager = ScraperManager()
    logger.info("API ready")

    yield

    # Shutdown
    logger.info("Shutting down...")
    if db:
        db.close()
    if scraper_manager:
        scraper_manager.close_all()


# Create FastAPI app
app = FastAPI(
    title="Leads Scraper API",
    description="API for scraping and analyzing job leads across multiple platforms",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class SearchRequest(BaseModel):
    """Request to search for leads."""
    query: SearchQuery
    parallel: bool = True
    deduplicate: bool = True
    save_results: bool = True


class AnalyzeRequest(BaseModel):
    """Request to analyze leads."""
    lead_ids: List[str]
    model: Optional[AIModel] = None
    user_profile: Optional[dict] = None


class LeadListResponse(BaseModel):
    """Response with list of leads."""
    leads: List[JobLead]
    total: int
    page: int
    page_size: int


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Leads Scraper API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database": "connected" if db else "disconnected",
        "scrapers": len(scraper_manager.scrapers) if scraper_manager else 0
    }


@app.post("/search", response_model=ScraperResult)
async def search_leads(request: SearchRequest, background_tasks: BackgroundTasks):
    """
    Search for leads across enabled scrapers.

    Args:
        request: Search parameters
        background_tasks: FastAPI background tasks

    Returns:
        Aggregated scraper results
    """
    try:
        logger.info(f"Starting search with keywords: {request.query.keywords}")

        # Perform search
        result = scraper_manager.search(
            request.query,
            parallel=request.parallel,
            deduplicate=request.deduplicate
        )

        # Save results to database in background
        if request.save_results and result.leads:
            background_tasks.add_task(db.save_leads, result.leads)

        logger.info(f"Search completed: {result.total_scraped} leads found")

        return result

    except Exception as e:
        logger.error(f"Search failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_leads(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Analyze leads using AI.

    Args:
        request: Analysis parameters
        background_tasks: FastAPI background tasks

    Returns:
        Analysis results
    """
    try:
        import time
        start_time = time.time()

        logger.info(f"Analyzing {len(request.lead_ids)} leads")

        # Get leads from database
        leads = [db.get_lead(lead_id) for lead_id in request.lead_ids]
        leads = [lead for lead in leads if lead]  # Filter None values

        if not leads:
            raise HTTPException(status_code=404, detail="No leads found")

        # Create analyzer
        analyzer = AnalyzerFactory.create_analyzer(request.model)

        # Analyze leads
        analyses = analyzer.analyze_batch(
            leads,
            user_profile=request.user_profile
        )

        # Save analyses in background
        for analysis in analyses:
            background_tasks.add_task(db.save_analysis, analysis)

        execution_time = time.time() - start_time
        logger.info(f"Analysis completed: {len(analyses)} leads in {execution_time:.2f}s")

        return AnalysisResponse(
            analyses=analyses,
            total_analyzed=len(analyses),
            execution_time=execution_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/leads", response_model=LeadListResponse)
async def get_leads(
    status: Optional[LeadStatus] = Query(None),
    source: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    Get leads from database with filtering and pagination.

    Args:
        status: Filter by lead status
        source: Filter by source platform
        page: Page number (1-indexed)
        page_size: Results per page

    Returns:
        Paginated list of leads
    """
    try:
        offset = (page - 1) * page_size

        leads = db.get_leads(
            status=status,
            source=source,
            limit=page_size,
            offset=offset
        )

        return LeadListResponse(
            leads=leads,
            total=len(leads),
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"Failed to get leads: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/leads/{lead_id}", response_model=JobLead)
async def get_lead(lead_id: str):
    """
    Get a specific lead by ID.

    Args:
        lead_id: Lead ID

    Returns:
        JobLead object
    """
    lead = db.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@app.get("/leads/{lead_id}/analysis", response_model=LeadAnalysis)
async def get_lead_analysis(lead_id: str):
    """
    Get analysis for a specific lead.

    Args:
        lead_id: Lead ID

    Returns:
        LeadAnalysis object
    """
    analysis = db.get_analysis(lead_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@app.get("/scrapers")
async def get_scrapers():
    """Get list of available scrapers."""
    return {
        "enabled": list(scraper_manager.scrapers.keys()),
        "total": len(scraper_manager.scrapers)
    }


@app.get("/models")
async def get_models():
    """Get list of supported AI models."""
    return {
        "models": [model.value for model in AIModel],
        "default": get_config().ai.model.value
    }


@app.get("/config")
async def get_api_config():
    """Get current configuration (non-sensitive data only)."""
    config = get_config()
    return {
        "environment": config.environment.value,
        "enabled_scrapers": config.enabled_job_boards,
        "ai_model": config.ai.model.value,
        "storage_backend": config.storage.backend
    }


# Error handlers

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    return {"error": "Resource not found", "detail": str(exc.detail)}


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors."""
    logger.error(f"Internal error: {exc}", exc_info=True)
    return {"error": "Internal server error", "detail": "An unexpected error occurred"}


if __name__ == "__main__":
    import uvicorn

    config = get_config().api

    uvicorn.run(
        "src.api.main:app",
        host=config.host,
        port=config.port,
        reload=config.reload,
        workers=config.workers,
        log_level=config.log_level
    )
