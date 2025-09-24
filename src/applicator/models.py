"""Database models for job application automation and tracking."""

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
    Boolean,
    Index,
    UniqueConstraint,
    CheckConstraint,
    Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database.models import Base, BaseModel


class ApplicationStatus(Enum):
    """Application status enumeration."""
    ELIGIBLE = "eligible"
    PENDING = "pending"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    REJECTED = "rejected"
    OFFER_RECEIVED = "offer_received"
    WITHDRAWN = "withdrawn"
    ERROR = "error"


class JobApplicationModel(BaseModel):
    """Model for tracking job applications."""

    __tablename__ = "job_applications"

    # Foreign keys
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    user_profile_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False, index=True)

    # Application metadata
    status = Column(SQLEnum(ApplicationStatus), nullable=False, default=ApplicationStatus.ELIGIBLE, index=True)
    application_method = Column(String(50), nullable=True)  # "linkedin", "company_website", "email"

    # Application content
    cover_letter_content = Column(Text, nullable=True)
    custom_message = Column(Text, nullable=True)
    resume_version = Column(String(100), nullable=True)

    # Timestamps
    applied_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_status_update = Column(DateTime(timezone=True), nullable=True)

    # Automation tracking
    automation_session_id = Column(String(100), nullable=True, index=True)
    automation_success = Column(Boolean, nullable=True)
    automation_error = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    # Application response tracking
    employer_response_date = Column(DateTime(timezone=True), nullable=True)
    interview_date = Column(DateTime(timezone=True), nullable=True)
    offer_details = Column(JSON, nullable=True)

    # Relationships - will be added after JobModel update
    # job = relationship("JobModel", back_populates="applications")
    # user_profile = relationship("UserProfileModel", back_populates="applications")

    # Constraints
    __table_args__ = (
        UniqueConstraint('job_id', 'user_profile_id', name='uq_job_user_application'),
        Index('idx_application_status', 'status'),
        Index('idx_application_applied_at', 'applied_at'),
        Index('idx_application_session', 'automation_session_id'),
        CheckConstraint('retry_count >= 0', name='retry_count_non_negative'),
    )

    def __repr__(self) -> str:
        """String representation of the application model."""
        return f"<JobApplicationModel(id={self.id}, job_id={self.job_id}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert application model to dictionary for serialization."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'user_profile_id': self.user_profile_id,
            'status': self.status.value if self.status else None,
            'application_method': self.application_method,
            'cover_letter_content': self.cover_letter_content,
            'custom_message': self.custom_message,
            'resume_version': self.resume_version,
            'applied_at': self.applied_at.replace(tzinfo=None).isoformat() if self.applied_at else None,
            'last_status_update': self.last_status_update.replace(tzinfo=None).isoformat() if self.last_status_update else None,
            'automation_session_id': self.automation_session_id,
            'automation_success': self.automation_success,
            'automation_error': self.automation_error,
            'retry_count': self.retry_count,
            'employer_response_date': self.employer_response_date.replace(tzinfo=None).isoformat() if self.employer_response_date else None,
            'interview_date': self.interview_date.replace(tzinfo=None).isoformat() if self.interview_date else None,
            'offer_details': self.offer_details,
            'created_at': self.created_at.replace(tzinfo=None).isoformat() if self.created_at else None,
            'updated_at': self.updated_at.replace(tzinfo=None).isoformat() if self.updated_at else None,
        }


class ContentType(Enum):
    """Types of generated content."""
    COVER_LETTER = "cover_letter"
    LINKEDIN_MESSAGE = "linkedin_message"
    EMAIL_SUBJECT = "email_subject"
    FOLLOW_UP_MESSAGE = "follow_up_message"


class GeneratedContentModel(BaseModel):
    """Model for storing generated application content."""

    __tablename__ = "generated_content"

    # Foreign keys
    application_id = Column(Integer, ForeignKey("job_applications.id"), nullable=False, index=True)

    # Content metadata
    content_type = Column(SQLEnum(ContentType), nullable=False, index=True)
    content_version = Column(Integer, nullable=False, default=1)

    # Generated content
    content_text = Column(Text, nullable=False)
    generation_prompt = Column(Text, nullable=True)

    # Generation metadata
    claude_model_used = Column(String(50), nullable=True)
    generation_cost = Column(Float, nullable=True, default=0.0)
    generation_time_seconds = Column(Float, nullable=True)

    # Quality metrics
    quality_score = Column(Integer, nullable=True)  # 0-100
    user_approved = Column(Boolean, nullable=True)
    user_edited = Column(Boolean, nullable=False, default=False)

    # Relationships - will be added after JobApplicationModel update
    # application = relationship("JobApplicationModel", back_populates="generated_content")

    # Constraints
    __table_args__ = (
        Index('idx_content_type', 'content_type'),
        Index('idx_content_version', 'content_version'),
        CheckConstraint('quality_score >= 0 AND quality_score <= 100', name='quality_score_range'),
        CheckConstraint('generation_cost >= 0', name='generation_cost_non_negative'),
        CheckConstraint('generation_time_seconds >= 0', name='generation_time_non_negative'),
        CheckConstraint('content_version >= 1', name='content_version_positive'),
    )

    def __repr__(self) -> str:
        """String representation of the generated content model."""
        return f"<GeneratedContentModel(id={self.id}, type={self.content_type}, application_id={self.application_id})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert generated content model to dictionary for serialization."""
        return {
            'id': self.id,
            'application_id': self.application_id,
            'content_type': self.content_type.value if self.content_type else None,
            'content_version': self.content_version,
            'content_text': self.content_text,
            'generation_prompt': self.generation_prompt,
            'claude_model_used': self.claude_model_used,
            'generation_cost': self.generation_cost,
            'generation_time_seconds': self.generation_time_seconds,
            'quality_score': self.quality_score,
            'user_approved': self.user_approved,
            'user_edited': self.user_edited,
            'created_at': self.created_at.replace(tzinfo=None).isoformat() if self.created_at else None,
            'updated_at': self.updated_at.replace(tzinfo=None).isoformat() if self.updated_at else None,
        }


class SafetyEventType(Enum):
    """Types of safety events."""
    EMERGENCY_STOP = "emergency_stop"
    RATE_LIMIT_HIT = "rate_limit_hit"
    CAPTCHA_DETECTED = "captcha_detected"
    BLOCKED_ACCESS = "blocked_access"
    API_COST_LIMIT = "api_cost_limit"
    USER_INTERVENTION = "user_intervention"
    AUTHENTICATION_FAILED = "authentication_failed"
    DUPLICATE_APPLICATION = "duplicate_application"


class SafetyEventModel(BaseModel):
    """Model for tracking safety events and interventions."""

    __tablename__ = "safety_events"

    # Event metadata
    event_type = Column(SQLEnum(SafetyEventType), nullable=False, index=True)
    event_description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, index=True)  # low, medium, high, critical

    # Context
    automation_session_id = Column(String(100), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    user_profile_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=True)

    # Additional event data
    event_data = Column(JSON, nullable=True)

    # Resolution
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_action = Column(Text, nullable=True)
    resolved_by = Column(String(50), nullable=True)  # "system", "user", "admin"

    # Constraints
    __table_args__ = (
        Index('idx_safety_event_type', 'event_type'),
        Index('idx_safety_severity', 'severity'),
        Index('idx_safety_session', 'automation_session_id'),
        Index('idx_safety_created_at', 'created_at'),
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name='severity_valid_values'),
    )

    def __repr__(self) -> str:
        """String representation of the safety event model."""
        return f"<SafetyEventModel(id={self.id}, type={self.event_type}, severity={self.severity})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert safety event model to dictionary for serialization."""
        return {
            'id': self.id,
            'event_type': self.event_type.value if self.event_type else None,
            'event_description': self.event_description,
            'severity': self.severity,
            'automation_session_id': self.automation_session_id,
            'job_id': self.job_id,
            'user_profile_id': self.user_profile_id,
            'event_data': self.event_data,
            'resolved_at': self.resolved_at.replace(tzinfo=None).isoformat() if self.resolved_at else None,
            'resolution_action': self.resolution_action,
            'resolved_by': self.resolved_by,
            'created_at': self.created_at.replace(tzinfo=None).isoformat() if self.created_at else None,
            'updated_at': self.updated_at.replace(tzinfo=None).isoformat() if self.updated_at else None,
        }


# Function to add relationships to existing models
def add_application_relationships():
    """Add relationships to existing models for application tracking."""
    from sqlalchemy.orm import relationship
    from ..database.models import JobModel
    from ..analyzer.models import UserProfileModel

    # Add relationships to JobModel
    if not hasattr(JobModel, 'applications'):
        JobModel.applications = relationship("JobApplicationModel", back_populates="job", cascade="all, delete-orphan")

    # Add relationships to UserProfileModel
    if not hasattr(UserProfileModel, 'applications'):
        UserProfileModel.applications = relationship("JobApplicationModel", back_populates="user_profile", cascade="all, delete-orphan")

    # Add relationships to JobApplicationModel
    if not hasattr(JobApplicationModel, 'job'):
        JobApplicationModel.job = relationship("JobModel", back_populates="applications")

    if not hasattr(JobApplicationModel, 'user_profile'):
        JobApplicationModel.user_profile = relationship("UserProfileModel", back_populates="applications")

    if not hasattr(JobApplicationModel, 'generated_content'):
        JobApplicationModel.generated_content = relationship("GeneratedContentModel", back_populates="application", cascade="all, delete-orphan")

    # Add relationships to GeneratedContentModel
    if not hasattr(GeneratedContentModel, 'application'):
        GeneratedContentModel.application = relationship("JobApplicationModel", back_populates="generated_content")


# Call the function to add relationships
add_application_relationships()


# Export models for use
__all__ = [
    'ApplicationStatus',
    'JobApplicationModel',
    'ContentType',
    'GeneratedContentModel',
    'SafetyEventType',
    'SafetyEventModel'
]