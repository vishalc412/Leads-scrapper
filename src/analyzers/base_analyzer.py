"""
Base AI analyzer for lead analysis.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import time
import json

from ..utils.models import JobLead, LeadAnalysis, SearchQuery
from ..config import get_config, AIModel

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """Abstract base class for AI analyzers."""

    def __init__(self, model: Optional[AIModel] = None):
        """
        Initialize the analyzer.

        Args:
            model: AI model to use. If None, uses config default.
        """
        self.config = get_config().ai
        self.model = model or self.config.model
        self.api_key = self.config.get_api_key()

    @abstractmethod
    def analyze_lead(
        self,
        lead: JobLead,
        search_query: Optional[SearchQuery] = None,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> LeadAnalysis:
        """
        Analyze a single lead.

        Args:
            lead: Job lead to analyze
            search_query: Original search query for context
            user_profile: User's skills, experience, and preferences

        Returns:
            LeadAnalysis with scores and insights
        """
        pass

    def analyze_batch(
        self,
        leads: List[JobLead],
        search_query: Optional[SearchQuery] = None,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> List[LeadAnalysis]:
        """
        Analyze multiple leads.

        Args:
            leads: List of job leads to analyze
            search_query: Original search query for context
            user_profile: User's skills, experience, and preferences

        Returns:
            List of LeadAnalysis objects
        """
        analyses = []
        for lead in leads:
            try:
                analysis = self.analyze_lead(lead, search_query, user_profile)
                analyses.append(analysis)
            except Exception as e:
                logger.error(f"Failed to analyze lead {lead.id}: {str(e)}")

        return analyses

    def _build_analysis_prompt(
        self,
        lead: JobLead,
        search_query: Optional[SearchQuery] = None,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build the prompt for AI analysis.

        Args:
            lead: Job lead to analyze
            search_query: Original search query
            user_profile: User profile data

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            "You are an expert career advisor and job market analyst. Analyze the following job posting and provide detailed insights.\n",
            f"\n## Job Posting\n",
            f"**Title:** {lead.title}",
            f"**Company:** {lead.company.name}",
            f"**Location:** {self._format_location(lead.location)}",
            f"\n**Description:**\n{lead.description}\n"
        ]

        if lead.required_skills:
            prompt_parts.append(f"\n**Required Skills:** {', '.join(lead.required_skills)}")

        if lead.salary_min or lead.salary_max:
            salary_range = self._format_salary(lead.salary_min, lead.salary_max, lead.salary_currency)
            prompt_parts.append(f"\n**Salary:** {salary_range}")

        # Add user context
        if user_profile:
            prompt_parts.append("\n## Candidate Profile")
            if user_profile.get('skills'):
                prompt_parts.append(f"**Skills:** {', '.join(user_profile['skills'])}")
            if user_profile.get('experience_years'):
                prompt_parts.append(f"**Experience:** {user_profile['experience_years']} years")
            if user_profile.get('preferences'):
                prompt_parts.append(f"**Preferences:** {user_profile['preferences']}")

        # Add search query context
        if search_query:
            prompt_parts.append("\n## Search Criteria")
            prompt_parts.append(f"**Desired Skills:** {', '.join(search_query.keywords)}")
            if search_query.industry:
                prompt_parts.append(f"**Industry:** {search_query.industry}")

        # Analysis instructions
        prompt_parts.extend([
            "\n## Analysis Required",
            "\nPlease analyze this job posting and provide:",
            "1. **Relevance Score** (0-100): How well this job matches the search criteria and user profile",
            "2. **Match Score** (0-100): How well the candidate's skills align with requirements",
            "3. **Quality Score** (0-100): Overall quality of the opportunity (company, role, growth potential)",
            "4. **Summary**: A brief 2-3 sentence overview of the opportunity",
            "5. **Key Highlights**: 3-5 notable positive aspects of this role",
            "6. **Match Reasons**: Specific reasons why this is a good match",
            "7. **Concerns**: Any potential drawbacks or concerns",
            "8. **Recommendations**: Advice for the candidate regarding this opportunity",
            "9. **Skill Analysis**: Which required skills the candidate has and which are missing",
            "\nProvide your analysis in JSON format with the following structure:",
            "```json",
            "{",
            '  "relevance_score": <number>,',
            '  "match_score": <number>,',
            '  "quality_score": <number>,',
            '  "summary": "<text>",',
            '  "key_highlights": ["<item>", ...],',
            '  "match_reasons": ["<reason>", ...],',
            '  "concerns": ["<concern>", ...],',
            '  "recommendations": ["<recommendation>", ...],',
            '  "matched_skills": ["<skill>", ...],',
            '  "missing_skills": ["<skill>", ...]',
            "}",
            "```"
        ])

        return "\n".join(prompt_parts)

    def _format_location(self, location) -> str:
        """Format location object as string."""
        parts = []
        if location.city:
            parts.append(location.city)
        if location.state:
            parts.append(location.state)
        if location.country:
            parts.append(location.country)

        location_str = ", ".join(parts) if parts else "Not specified"

        if location.remote:
            location_str += " (Remote)"

        return location_str

    def _format_salary(
        self,
        salary_min: Optional[int],
        salary_max: Optional[int],
        currency: str = "USD"
    ) -> str:
        """Format salary range as string."""
        if salary_min and salary_max and salary_min != salary_max:
            return f"{currency} {salary_min:,} - {salary_max:,}"
        elif salary_min:
            return f"{currency} {salary_min:,}+"
        elif salary_max:
            return f"Up to {currency} {salary_max:,}"
        else:
            return "Not specified"

    def _parse_analysis_response(
        self,
        response_text: str,
        lead: JobLead
    ) -> LeadAnalysis:
        """
        Parse AI response into LeadAnalysis object.

        Args:
            response_text: Raw response from AI
            lead: The job lead being analyzed

        Returns:
            LeadAnalysis object
        """
        # Extract JSON from response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start == -1 or json_end == 0:
            # No JSON found, create basic analysis
            return LeadAnalysis(
                lead_id=lead.id,
                model_used=self.model.value,
                relevance_score=50.0,
                match_score=50.0,
                quality_score=50.0,
                summary="Unable to parse AI analysis response.",
                key_highlights=[],
                match_reasons=[],
                concerns=["Analysis parsing failed"],
                recommendations=[]
            )

        try:
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)

            return LeadAnalysis(
                lead_id=lead.id,
                model_used=self.model.value,
                relevance_score=float(data.get('relevance_score', 50)),
                match_score=float(data.get('match_score', 50)),
                quality_score=float(data.get('quality_score', 50)),
                summary=data.get('summary', ''),
                key_highlights=data.get('key_highlights', []),
                match_reasons=data.get('match_reasons', []),
                concerns=data.get('concerns', []),
                recommendations=data.get('recommendations', []),
                matched_skills=data.get('matched_skills', []),
                missing_skills=data.get('missing_skills', [])
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from AI response: {str(e)}")
            return LeadAnalysis(
                lead_id=lead.id,
                model_used=self.model.value,
                relevance_score=50.0,
                match_score=50.0,
                quality_score=50.0,
                summary="JSON parsing error in AI response.",
                key_highlights=[],
                match_reasons=[],
                concerns=["Response parsing failed"],
                recommendations=[]
            )
