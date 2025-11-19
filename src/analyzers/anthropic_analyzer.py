"""
Anthropic Claude AI analyzer.
"""

import logging
from typing import Optional, Dict, Any
import time

from .base_analyzer import BaseAnalyzer
from ..utils.models import JobLead, LeadAnalysis, SearchQuery
from ..config import AIModel

logger = logging.getLogger(__name__)


class AnthropicAnalyzer(BaseAnalyzer):
    """Analyzer using Anthropic's Claude models."""

    def __init__(self, model: Optional[AIModel] = None):
        """
        Initialize Anthropic analyzer.

        Args:
            model: AI model to use (should be an Anthropic model)
        """
        super().__init__(model)

        if not self.api_key:
            logger.warning("No Anthropic API key found. Set ANTHROPIC_API_KEY environment variable.")

        # Import anthropic library
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            logger.error("anthropic library not installed. Run: pip install anthropic")
            self.client = None

    def analyze_lead(
        self,
        lead: JobLead,
        search_query: Optional[SearchQuery] = None,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> LeadAnalysis:
        """
        Analyze a job lead using Claude.

        Args:
            lead: Job lead to analyze
            search_query: Original search query for context
            user_profile: User's skills, experience, and preferences

        Returns:
            LeadAnalysis with scores and insights
        """
        start_time = time.time()

        if not self.client:
            logger.error("Anthropic client not initialized")
            return self._create_fallback_analysis(lead)

        try:
            # Build prompt
            prompt = self._build_analysis_prompt(lead, search_query, user_profile)

            # Call Claude API
            response = self.client.messages.create(
                model=self.model.value,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract response text
            response_text = response.content[0].text

            # Parse response into LeadAnalysis
            analysis = self._parse_analysis_response(response_text, lead)
            analysis.processing_time = time.time() - start_time

            logger.info(
                f"Analyzed lead {lead.id} with Claude "
                f"(relevance: {analysis.relevance_score:.1f}, "
                f"match: {analysis.match_score:.1f})"
            )

            return analysis

        except Exception as e:
            logger.error(f"Claude analysis failed for lead {lead.id}: {str(e)}")
            return self._create_fallback_analysis(lead)

    def _create_fallback_analysis(self, lead: JobLead) -> LeadAnalysis:
        """Create a basic fallback analysis when API fails."""
        return LeadAnalysis(
            lead_id=lead.id,
            model_used=self.model.value,
            relevance_score=50.0,
            match_score=50.0,
            quality_score=50.0,
            summary=f"Job posting for {lead.title} at {lead.company.name}. "
                   f"Analysis unavailable due to API error.",
            key_highlights=[
                f"Position: {lead.title}",
                f"Company: {lead.company.name}",
                f"Location: {self._format_location(lead.location)}"
            ],
            match_reasons=[],
            concerns=["AI analysis not available"],
            recommendations=["Review the job posting manually"],
            matched_skills=lead.required_skills[:3] if lead.required_skills else [],
            missing_skills=[]
        )
