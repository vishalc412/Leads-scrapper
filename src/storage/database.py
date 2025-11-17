"""
Database storage for leads and analysis results.
"""

import logging
import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from ..utils.models import JobLead, LeadAnalysis, LeadStatus
from ..config import get_config

logger = logging.getLogger(__name__)


class Database:
    """SQLite database for storing leads and analyses."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file. If None, uses config.
        """
        config = get_config().storage

        if db_path is None:
            # Use configured data directory
            data_dir = Path(config.data_dir)
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(data_dir / "leads.db")

        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._init_database()

    def _init_database(self):
        """Initialize database tables."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Create tables
        cursor = self.conn.cursor()

        # Leads table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                company_name TEXT,
                company_data TEXT,
                location_data TEXT,
                required_skills TEXT,
                preferred_skills TEXT,
                experience_level TEXT,
                education TEXT,
                salary_min INTEGER,
                salary_max INTEGER,
                salary_currency TEXT,
                benefits TEXT,
                job_type TEXT,
                remote_type TEXT,
                posted_date TEXT,
                scraped_date TEXT NOT NULL,
                expires_date TEXT,
                status TEXT NOT NULL,
                raw_data TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Analyses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id TEXT NOT NULL,
                model_used TEXT NOT NULL,
                relevance_score REAL NOT NULL,
                match_score REAL NOT NULL,
                quality_score REAL NOT NULL,
                summary TEXT,
                key_highlights TEXT,
                match_reasons TEXT,
                concerns TEXT,
                recommendations TEXT,
                matched_skills TEXT,
                missing_skills TEXT,
                analyzed_at TEXT NOT NULL,
                processing_time REAL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            )
        """)

        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_posted ON leads(posted_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_lead ON analyses(lead_id)")

        self.conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def save_lead(self, lead: JobLead) -> bool:
        """
        Save or update a lead.

        Args:
            lead: JobLead to save

        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            now = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT OR REPLACE INTO leads (
                    id, source, url, title, description,
                    company_name, company_data, location_data,
                    required_skills, preferred_skills,
                    experience_level, education,
                    salary_min, salary_max, salary_currency, benefits,
                    job_type, remote_type,
                    posted_date, scraped_date, expires_date,
                    status, raw_data, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lead.id,
                lead.source,
                str(lead.url),
                lead.title,
                lead.description,
                lead.company.name,
                json.dumps(lead.company.model_dump()),
                json.dumps(lead.location.model_dump()),
                json.dumps(lead.required_skills),
                json.dumps(lead.preferred_skills),
                lead.experience_level,
                lead.education,
                lead.salary_min,
                lead.salary_max,
                lead.salary_currency,
                json.dumps(lead.benefits),
                lead.job_type,
                lead.remote_type,
                lead.posted_date.isoformat() if lead.posted_date else None,
                lead.scraped_date.isoformat(),
                lead.expires_date.isoformat() if lead.expires_date else None,
                lead.status.value,
                json.dumps(lead.raw_data),
                now,
                now
            ))

            self.conn.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to save lead {lead.id}: {str(e)}")
            self.conn.rollback()
            return False

    def save_leads(self, leads: List[JobLead]) -> int:
        """
        Save multiple leads.

        Args:
            leads: List of JobLeads to save

        Returns:
            Number of successfully saved leads
        """
        saved = 0
        for lead in leads:
            if self.save_lead(lead):
                saved += 1
        return saved

    def get_lead(self, lead_id: str) -> Optional[JobLead]:
        """
        Get a lead by ID.

        Args:
            lead_id: Lead ID

        Returns:
            JobLead or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
        row = cursor.fetchone()

        if row:
            return self._row_to_lead(row)
        return None

    def get_leads(
        self,
        status: Optional[LeadStatus] = None,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[JobLead]:
        """
        Get leads with optional filtering.

        Args:
            status: Filter by status
            source: Filter by source
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of JobLeads
        """
        query = "SELECT * FROM leads WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if source:
            query += " AND source = ?"
            params.append(source)

        query += " ORDER BY posted_date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        return [self._row_to_lead(row) for row in cursor.fetchall()]

    def save_analysis(self, analysis: LeadAnalysis) -> bool:
        """
        Save an analysis.

        Args:
            analysis: LeadAnalysis to save

        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            now = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT INTO analyses (
                    lead_id, model_used,
                    relevance_score, match_score, quality_score,
                    summary, key_highlights, match_reasons,
                    concerns, recommendations,
                    matched_skills, missing_skills,
                    analyzed_at, processing_time, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis.lead_id,
                analysis.model_used,
                analysis.relevance_score,
                analysis.match_score,
                analysis.quality_score,
                analysis.summary,
                json.dumps(analysis.key_highlights),
                json.dumps(analysis.match_reasons),
                json.dumps(analysis.concerns),
                json.dumps(analysis.recommendations),
                json.dumps(analysis.matched_skills),
                json.dumps(analysis.missing_skills),
                analysis.analyzed_at.isoformat(),
                analysis.processing_time,
                now
            ))

            self.conn.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to save analysis for lead {analysis.lead_id}: {str(e)}")
            self.conn.rollback()
            return False

    def get_analysis(self, lead_id: str) -> Optional[LeadAnalysis]:
        """
        Get the most recent analysis for a lead.

        Args:
            lead_id: Lead ID

        Returns:
            LeadAnalysis or None
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM analyses
            WHERE lead_id = ?
            ORDER BY analyzed_at DESC
            LIMIT 1
        """, (lead_id,))

        row = cursor.fetchone()
        if row:
            return self._row_to_analysis(row)
        return None

    def _row_to_lead(self, row: sqlite3.Row) -> JobLead:
        """Convert database row to JobLead."""
        from ..utils.models import Company, Location

        return JobLead(
            id=row['id'],
            source=row['source'],
            url=row['url'],
            title=row['title'],
            description=row['description'] or '',
            company=Company(**json.loads(row['company_data'])),
            location=Location(**json.loads(row['location_data'])),
            required_skills=json.loads(row['required_skills']),
            preferred_skills=json.loads(row['preferred_skills']),
            experience_level=row['experience_level'],
            education=row['education'],
            salary_min=row['salary_min'],
            salary_max=row['salary_max'],
            salary_currency=row['salary_currency'],
            benefits=json.loads(row['benefits']),
            job_type=row['job_type'],
            remote_type=row['remote_type'],
            posted_date=datetime.fromisoformat(row['posted_date']) if row['posted_date'] else None,
            scraped_date=datetime.fromisoformat(row['scraped_date']),
            expires_date=datetime.fromisoformat(row['expires_date']) if row['expires_date'] else None,
            status=LeadStatus(row['status']),
            raw_data=json.loads(row['raw_data'])
        )

    def _row_to_analysis(self, row: sqlite3.Row) -> LeadAnalysis:
        """Convert database row to LeadAnalysis."""
        return LeadAnalysis(
            lead_id=row['lead_id'],
            model_used=row['model_used'],
            relevance_score=row['relevance_score'],
            match_score=row['match_score'],
            quality_score=row['quality_score'],
            summary=row['summary'],
            key_highlights=json.loads(row['key_highlights']),
            match_reasons=json.loads(row['match_reasons']),
            concerns=json.loads(row['concerns']),
            recommendations=json.loads(row['recommendations']),
            matched_skills=json.loads(row['matched_skills']),
            missing_skills=json.loads(row['missing_skills']),
            analyzed_at=datetime.fromisoformat(row['analyzed_at']),
            processing_time=row['processing_time']
        )

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
