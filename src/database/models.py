"""Database models for the LinkedIn Job Agent application."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Index,
    UniqueConstraint,
    create_engine
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func


# Create base class for all models
Base = declarative_base()


class BaseModel(Base):
    """Base model with common fields for all database models."""

    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc)
    )


class JobModel(BaseModel):
    """Model for storing job posting information from LinkedIn."""

    __tablename__ = "jobs"

    # Core job information
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    url = Column(String(500), nullable=False)

    # LinkedIn-specific fields
    linkedin_job_id = Column(String(50), nullable=False, unique=True, index=True)

    # Optional fields for enhanced data
    employment_type = Column(String(50), nullable=True, index=True)  # Full-time, Part-time, Contract, etc.
    experience_level = Column(String(50), nullable=True, index=True)  # Entry, Mid, Senior, etc.
    industry = Column(String(100), nullable=True, index=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(String(3), nullable=True, default="USD")

    # Metadata
    date_posted = Column(DateTime(timezone=True), nullable=True)
    is_remote = Column(String(20), nullable=True, index=True)  # Remote, Hybrid, On-site
    company_size = Column(String(50), nullable=True)
    applicant_count = Column(Integer, nullable=True, index=True)  # Number of applicants who applied

    # Performance indexes
    __table_args__ = (
        Index('idx_job_search', 'title', 'company', 'location'),
        Index('idx_job_date_posted', 'date_posted'),
        Index('idx_job_employment_type', 'employment_type'),
        Index('idx_job_experience_level', 'experience_level'),
        Index('idx_job_created_at', 'created_at'),
        Index('idx_job_applicant_count', 'applicant_count'),
        UniqueConstraint('linkedin_job_id', name='uq_job_linkedin_id'),
    )

    def __repr__(self) -> str:
        """String representation of the job model."""
        return f"<JobModel(id={self.id}, title='{self.title}', company='{self.company}')>"

    def to_dict(self) -> dict:
        """Convert job model to dictionary for serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'description': self.description,
            'url': self.url,
            'linkedin_job_id': self.linkedin_job_id,
            'employment_type': self.employment_type,
            'experience_level': self.experience_level,
            'industry': self.industry,
            'salary_min': self.salary_min,
            'salary_max': self.salary_max,
            'salary_currency': self.salary_currency,
            'date_posted': self.date_posted.isoformat() if self.date_posted else None,
            'is_remote': self.is_remote,
            'company_size': self.company_size,
            'applicant_count': self.applicant_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# Expose Base for external use (needed for tests)
__all__ = ['Base', 'BaseModel', 'JobModel']