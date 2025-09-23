"""Database models for job analysis and matching."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Float,
    Index,
    UniqueConstraint,
    CheckConstraint,
    Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database.models import Base, BaseModel


class AnalysisStatus(Enum):
    """Status of analysis operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisType(Enum):
    """Types of job analysis."""
    QUALITY = "quality"
    COMPETITION = "competition"
    MATCHING = "matching"


class JobAnalysisModel(BaseModel):
    """Model for storing job analysis results."""

    __tablename__ = "job_analyses"

    # Foreign key to job
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Analysis metadata
    analysis_type = Column(SQLEnum(AnalysisType), nullable=False, index=True)
    status = Column(SQLEnum(AnalysisStatus), nullable=False, default=AnalysisStatus.PENDING, index=True)

    # Analysis results
    quality_score = Column(Integer, nullable=True)  # 0-100 for quality analysis
    match_score = Column(Integer, nullable=True)    # 0-100 for matching analysis
    competition_score = Column(Integer, nullable=True)  # 0-100 for competition analysis

    # Detailed analysis data (JSON)
    analysis_data = Column(JSON, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    # Processing metadata
    processing_time_seconds = Column(Float, nullable=True)
    api_cost = Column(Float, nullable=True, default=0.0)

    # Relationships
    job = relationship("JobModel", back_populates="analyses")

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('quality_score >= 0 AND quality_score <= 100', name='quality_score_range'),
        CheckConstraint('match_score >= 0 AND match_score <= 100', name='match_score_range'),
        CheckConstraint('competition_score >= 0 AND competition_score <= 100', name='competition_score_range'),
        CheckConstraint('retry_count >= 0', name='retry_count_non_negative'),
        CheckConstraint('api_cost >= 0', name='api_cost_non_negative'),
        Index('idx_analysis_job_type', 'job_id', 'analysis_type'),
        Index('idx_analysis_status', 'status'),
        Index('idx_analysis_created', 'created_at'),
        Index('idx_analysis_quality_score', 'quality_score'),
    )

    def __repr__(self) -> str:
        return f"<JobAnalysisModel(id={self.id}, job_id={self.job_id}, type={self.analysis_type})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis to dictionary."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'analysis_type': self.analysis_type.value if self.analysis_type else None,
            'status': self.status.value if self.status else None,
            'quality_score': self.quality_score,
            'match_score': self.match_score,
            'competition_score': self.competition_score,
            'analysis_data': self.analysis_data,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'processing_time_seconds': self.processing_time_seconds,
            'api_cost': self.api_cost,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class CompetitionAnalysisModel(BaseModel):
    """Model for storing detailed competition analysis."""

    __tablename__ = "competition_analyses"

    # Foreign key to job
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Competition metrics
    applicant_count = Column(Integer, nullable=True)
    competition_level = Column(String(20), nullable=True, index=True)  # low, medium, high
    success_probability = Column(Integer, nullable=True)  # 0-100

    # Market analysis
    similar_jobs_count = Column(Integer, nullable=True)
    average_applicants_for_role = Column(Float, nullable=True)
    market_demand_score = Column(Integer, nullable=True)  # 0-100

    # Strategic insights
    best_application_time = Column(String(50), nullable=True)
    recommended_approach = Column(Text, nullable=True)

    # Analysis data (JSON)
    analysis_data = Column(JSON, nullable=True)

    # Relationships
    job = relationship("JobModel", back_populates="competition_analyses")

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('success_probability >= 0 AND success_probability <= 100',
                       name='success_probability_range'),
        CheckConstraint('market_demand_score >= 0 AND market_demand_score <= 100',
                       name='market_demand_range'),
        Index('idx_competition_level', 'competition_level'),
        Index('idx_competition_probability', 'success_probability'),
        UniqueConstraint('job_id', name='uq_competition_job_id'),
    )

    def __repr__(self) -> str:
        return f"<CompetitionAnalysisModel(id={self.id}, job_id={self.job_id}, level={self.competition_level})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert competition analysis to dictionary."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'applicant_count': self.applicant_count,
            'competition_level': self.competition_level,
            'success_probability': self.success_probability,
            'similar_jobs_count': self.similar_jobs_count,
            'average_applicants_for_role': self.average_applicants_for_role,
            'market_demand_score': self.market_demand_score,
            'best_application_time': self.best_application_time,
            'recommended_approach': self.recommended_approach,
            'analysis_data': self.analysis_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class UserProfileModel(BaseModel):
    """Model for storing user profiles for job matching."""

    __tablename__ = "user_profiles"

    # User identification
    user_id = Column(String(100), nullable=False, unique=True, index=True)

    # Professional information
    skills = Column(JSON, nullable=True)  # List of skills
    experience_years = Column(Integer, nullable=True)
    desired_roles = Column(JSON, nullable=True)  # List of desired job titles
    preferred_locations = Column(JSON, nullable=True)  # List of preferred locations

    # Preferences and requirements
    salary_expectations = Column(JSON, nullable=True)  # {min, max, currency}
    work_schedule_preference = Column(String(20), nullable=True)  # full-time, part-time, contract
    remote_preference = Column(String(20), nullable=True)  # remote, hybrid, on-site

    # Additional profile data
    education_level = Column(String(50), nullable=True)
    certifications = Column(JSON, nullable=True)  # List of certifications
    industry_preferences = Column(JSON, nullable=True)  # Preferred industries
    company_size_preference = Column(String(20), nullable=True)

    # Profile metadata
    profile_data = Column(JSON, nullable=True)  # Additional flexible profile data
    last_updated = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    job_matches = relationship("JobMatchModel", back_populates="user_profile", cascade="all, delete-orphan")

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('experience_years >= 0', name='experience_years_non_negative'),
        Index('idx_profile_user_id', 'user_id'),
        Index('idx_profile_experience', 'experience_years'),
        Index('idx_profile_updated', 'last_updated'),
    )

    def __repr__(self) -> str:
        return f"<UserProfileModel(id={self.id}, user_id='{self.user_id}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert user profile to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'skills': self.skills,
            'experience_years': self.experience_years,
            'desired_roles': self.desired_roles,
            'preferred_locations': self.preferred_locations,
            'salary_expectations': self.salary_expectations,
            'work_schedule_preference': self.work_schedule_preference,
            'remote_preference': self.remote_preference,
            'education_level': self.education_level,
            'certifications': self.certifications,
            'industry_preferences': self.industry_preferences,
            'company_size_preference': self.company_size_preference,
            'profile_data': self.profile_data,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class JobMatchModel(BaseModel):
    """Model for storing job-to-profile matching results."""

    __tablename__ = "job_matches"

    # Foreign keys
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_profile_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"),
                           nullable=False, index=True)

    # Matching results
    match_score = Column(Integer, nullable=False)  # 0-100
    recommendation = Column(String(20), nullable=True, index=True)  # apply, consider, skip, strong_match

    # Detailed matching analysis
    skill_match_score = Column(Integer, nullable=True)  # 0-100
    experience_match_score = Column(Integer, nullable=True)  # 0-100
    location_match_score = Column(Integer, nullable=True)  # 0-100
    salary_match_score = Column(Integer, nullable=True)  # 0-100

    # Match data (JSON)
    match_data = Column(JSON, nullable=True)  # Detailed matching breakdown

    # User interaction tracking
    user_viewed = Column(DateTime(timezone=True), nullable=True)
    user_applied = Column(DateTime(timezone=True), nullable=True)
    user_bookmarked = Column(DateTime(timezone=True), nullable=True)
    user_dismissed = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    job = relationship("JobModel", back_populates="job_matches")
    user_profile = relationship("UserProfileModel", back_populates="job_matches")

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('match_score >= 0 AND match_score <= 100', name='match_score_range'),
        CheckConstraint('skill_match_score >= 0 AND skill_match_score <= 100', name='skill_match_range'),
        CheckConstraint('experience_match_score >= 0 AND experience_match_score <= 100', name='experience_match_range'),
        CheckConstraint('location_match_score >= 0 AND location_match_score <= 100', name='location_match_range'),
        CheckConstraint('salary_match_score >= 0 AND salary_match_score <= 100', name='salary_match_range'),
        UniqueConstraint('job_id', 'user_profile_id', name='uq_job_profile_match'),
        Index('idx_match_score', 'match_score'),
        Index('idx_match_recommendation', 'recommendation'),
        Index('idx_match_user_viewed', 'user_viewed'),
        Index('idx_match_created', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<JobMatchModel(id={self.id}, job_id={self.job_id}, score={self.match_score})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert job match to dictionary."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'user_profile_id': self.user_profile_id,
            'match_score': self.match_score,
            'recommendation': self.recommendation,
            'skill_match_score': self.skill_match_score,
            'experience_match_score': self.experience_match_score,
            'location_match_score': self.location_match_score,
            'salary_match_score': self.salary_match_score,
            'match_data': self.match_data,
            'user_viewed': self.user_viewed.isoformat() if self.user_viewed else None,
            'user_applied': self.user_applied.isoformat() if self.user_applied else None,
            'user_bookmarked': self.user_bookmarked.isoformat() if self.user_bookmarked else None,
            'user_dismissed': self.user_dismissed.isoformat() if self.user_dismissed else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# Update existing JobModel to add relationships
def add_job_relationships():
    """Add relationships to JobModel for analysis models."""
    from sqlalchemy.orm import relationship
    from ..database.models import JobModel

    # Add relationships to JobModel
    if not hasattr(JobModel, 'analyses'):
        JobModel.analyses = relationship("JobAnalysisModel", back_populates="job", cascade="all, delete-orphan")

    if not hasattr(JobModel, 'competition_analyses'):
        JobModel.competition_analyses = relationship("CompetitionAnalysisModel", back_populates="job", cascade="all, delete-orphan")

    if not hasattr(JobModel, 'job_matches'):
        JobModel.job_matches = relationship("JobMatchModel", back_populates="job", cascade="all, delete-orphan")


# Call the function to add relationships
add_job_relationships()


# Export models for use
__all__ = [
    'JobAnalysisModel',
    'CompetitionAnalysisModel',
    'UserProfileModel',
    'JobMatchModel',
    'AnalysisStatus',
    'AnalysisType'
]