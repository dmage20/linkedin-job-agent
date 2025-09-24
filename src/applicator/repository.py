"""Repository for application automation database operations."""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    ApplicationStatus,
    JobApplicationModel,
    ContentType,
    GeneratedContentModel,
    SafetyEventType,
    SafetyEventModel
)
from ..database.models import JobModel
from ..analyzer.models import UserProfileModel


logger = logging.getLogger(__name__)


class ApplicationRepository:
    """Repository for application-related database operations."""

    def __init__(self, session: Session):
        """Initialize repository with database session."""
        self.session = session

    # Job Application CRUD operations
    def create_application(
        self,
        job_id: int,
        user_profile_id: int,
        status: ApplicationStatus = ApplicationStatus.ELIGIBLE,
        application_method: Optional[str] = None,
        **kwargs
    ) -> JobApplicationModel:
        """Create a new job application record."""
        try:
            application = JobApplicationModel(
                job_id=job_id,
                user_profile_id=user_profile_id,
                status=status,
                application_method=application_method,
                **kwargs
            )
            self.session.add(application)
            self.session.commit()
            logger.info(f"Created application {application.id} for job {job_id} and user {user_profile_id}")
            return application
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to create application: {e}")
            raise

    def get_application_by_id(self, application_id: int) -> Optional[JobApplicationModel]:
        """Get application by ID."""
        try:
            return self.session.query(JobApplicationModel).filter_by(id=application_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get application {application_id}: {e}")
            raise

    def get_application_by_job_and_user(
        self,
        job_id: int,
        user_profile_id: int
    ) -> Optional[JobApplicationModel]:
        """Get application by job and user profile IDs."""
        try:
            return self.session.query(JobApplicationModel).filter_by(
                job_id=job_id,
                user_profile_id=user_profile_id
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get application for job {job_id} and user {user_profile_id}: {e}")
            raise

    def update_application_status(
        self,
        application_id: int,
        status: ApplicationStatus,
        **kwargs
    ) -> bool:
        """Update application status with timestamp and additional fields."""
        try:
            application = self.session.query(JobApplicationModel).filter_by(id=application_id).first()
            if not application:
                logger.warning(f"Application {application_id} not found for status update")
                return False

            application.status = status
            application.last_status_update = datetime.now(timezone.utc)

            # Update additional fields if provided
            for key, value in kwargs.items():
                if hasattr(application, key):
                    setattr(application, key, value)

            self.session.commit()
            logger.info(f"Updated application {application_id} status to {status.value}")
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to update application {application_id} status: {e}")
            raise

    def get_user_applications(
        self,
        user_profile_id: int,
        status: Optional[ApplicationStatus] = None,
        limit: Optional[int] = None
    ) -> List[JobApplicationModel]:
        """Get user applications with optional status filter."""
        try:
            query = self.session.query(JobApplicationModel).filter_by(user_profile_id=user_profile_id)

            if status:
                query = query.filter_by(status=status)

            query = query.order_by(JobApplicationModel.created_at.desc())

            if limit:
                query = query.limit(limit)

            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get applications for user {user_profile_id}: {e}")
            raise

    def get_applications_by_status(
        self,
        status: ApplicationStatus,
        limit: Optional[int] = None
    ) -> List[JobApplicationModel]:
        """Get applications by status."""
        try:
            query = self.session.query(JobApplicationModel).filter_by(status=status)
            query = query.order_by(JobApplicationModel.created_at.desc())

            if limit:
                query = query.limit(limit)

            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get applications with status {status.value}: {e}")
            raise

    def get_applications_by_session_id(
        self,
        automation_session_id: str
    ) -> List[JobApplicationModel]:
        """Get applications by automation session ID."""
        try:
            return self.session.query(JobApplicationModel).filter_by(
                automation_session_id=automation_session_id
            ).all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get applications for session {automation_session_id}: {e}")
            raise

    def get_pending_applications(self, limit: Optional[int] = None) -> List[JobApplicationModel]:
        """Get applications that are eligible or pending automation."""
        try:
            query = self.session.query(JobApplicationModel).filter(
                JobApplicationModel.status.in_([ApplicationStatus.ELIGIBLE, ApplicationStatus.PENDING])
            ).order_by(JobApplicationModel.created_at.asc())

            if limit:
                query = query.limit(limit)

            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get pending applications: {e}")
            raise

    # Generated Content CRUD operations
    def create_generated_content(
        self,
        application_id: int,
        content_type: ContentType,
        content_text: str,
        **kwargs
    ) -> GeneratedContentModel:
        """Create generated content for an application."""
        try:
            content = GeneratedContentModel(
                application_id=application_id,
                content_type=content_type,
                content_text=content_text,
                **kwargs
            )
            self.session.add(content)
            self.session.commit()
            logger.info(f"Created {content_type.value} content for application {application_id}")
            return content
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to create content for application {application_id}: {e}")
            raise

    def get_application_content(
        self,
        application_id: int,
        content_type: Optional[ContentType] = None
    ) -> List[GeneratedContentModel]:
        """Get generated content for an application."""
        try:
            query = self.session.query(GeneratedContentModel).filter_by(application_id=application_id)

            if content_type:
                query = query.filter_by(content_type=content_type)

            return query.order_by(GeneratedContentModel.created_at.desc()).all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get content for application {application_id}: {e}")
            raise

    def get_latest_content(
        self,
        application_id: int,
        content_type: ContentType
    ) -> Optional[GeneratedContentModel]:
        """Get the latest version of specific content type for an application."""
        try:
            return self.session.query(GeneratedContentModel).filter_by(
                application_id=application_id,
                content_type=content_type
            ).order_by(GeneratedContentModel.content_version.desc()).first()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get latest {content_type.value} for application {application_id}: {e}")
            raise

    def update_content_approval(
        self,
        content_id: int,
        user_approved: bool,
        user_edited: bool = False
    ) -> bool:
        """Update content approval status."""
        try:
            content = self.session.query(GeneratedContentModel).filter_by(id=content_id).first()
            if not content:
                logger.warning(f"Content {content_id} not found for approval update")
                return False

            content.user_approved = user_approved
            content.user_edited = user_edited
            self.session.commit()
            logger.info(f"Updated content {content_id} approval to {user_approved}")
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to update content {content_id} approval: {e}")
            raise

    # Safety Event operations
    def create_safety_event(
        self,
        event_type: SafetyEventType,
        event_description: str,
        severity: str,
        automation_session_id: Optional[str] = None,
        job_id: Optional[int] = None,
        user_profile_id: Optional[int] = None,
        event_data: Optional[Dict[str, Any]] = None
    ) -> SafetyEventModel:
        """Create a safety event record."""
        try:
            event = SafetyEventModel(
                event_type=event_type,
                event_description=event_description,
                severity=severity,
                automation_session_id=automation_session_id,
                job_id=job_id,
                user_profile_id=user_profile_id,
                event_data=event_data
            )
            self.session.add(event)
            self.session.commit()
            logger.warning(f"Created safety event: {event_type.value} - {severity} - {event_description}")
            return event
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to create safety event: {e}")
            raise

    def resolve_safety_event(
        self,
        event_id: int,
        resolution_action: str,
        resolved_by: str
    ) -> bool:
        """Mark a safety event as resolved."""
        try:
            event = self.session.query(SafetyEventModel).filter_by(id=event_id).first()
            if not event:
                logger.warning(f"Safety event {event_id} not found for resolution")
                return False

            event.resolved_at = datetime.now(timezone.utc)
            event.resolution_action = resolution_action
            event.resolved_by = resolved_by
            self.session.commit()
            logger.info(f"Resolved safety event {event_id}")
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to resolve safety event {event_id}: {e}")
            raise

    def get_unresolved_safety_events(
        self,
        severity: Optional[str] = None,
        event_type: Optional[SafetyEventType] = None
    ) -> List[SafetyEventModel]:
        """Get unresolved safety events."""
        try:
            query = self.session.query(SafetyEventModel).filter(
                SafetyEventModel.resolved_at.is_(None)
            )

            if severity:
                query = query.filter_by(severity=severity)

            if event_type:
                query = query.filter_by(event_type=event_type)

            return query.order_by(SafetyEventModel.created_at.desc()).all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get unresolved safety events: {e}")
            raise

    def get_safety_events_by_session(
        self,
        automation_session_id: str
    ) -> List[SafetyEventModel]:
        """Get safety events for a specific automation session."""
        try:
            return self.session.query(SafetyEventModel).filter_by(
                automation_session_id=automation_session_id
            ).order_by(SafetyEventModel.created_at.asc()).all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get safety events for session {automation_session_id}: {e}")
            raise

    # Analytics and reporting methods
    def get_application_statistics(self, user_profile_id: Optional[int] = None) -> Dict[str, Any]:
        """Get application statistics."""
        try:
            query = self.session.query(JobApplicationModel)
            if user_profile_id:
                query = query.filter_by(user_profile_id=user_profile_id)

            total_applications = query.count()

            stats = {"total_applications": total_applications}

            # Count by status
            for status in ApplicationStatus:
                count = query.filter_by(status=status).count()
                stats[f"{status.value}_count"] = count

            # Success rate calculation
            submitted = query.filter_by(status=ApplicationStatus.SUBMITTED).count()
            stats["success_rate"] = (submitted / total_applications * 100) if total_applications > 0 else 0

            return stats
        except SQLAlchemyError as e:
            logger.error(f"Failed to get application statistics: {e}")
            raise

    def get_content_generation_stats(self) -> Dict[str, Any]:
        """Get content generation statistics."""
        try:
            total_content = self.session.query(GeneratedContentModel).count()
            approved_content = self.session.query(GeneratedContentModel).filter_by(user_approved=True).count()

            stats = {
                "total_content_generated": total_content,
                "approved_content": approved_content,
                "approval_rate": (approved_content / total_content * 100) if total_content > 0 else 0
            }

            # Stats by content type
            for content_type in ContentType:
                count = self.session.query(GeneratedContentModel).filter_by(content_type=content_type).count()
                stats[f"{content_type.value}_count"] = count

            return stats
        except SQLAlchemyError as e:
            logger.error(f"Failed to get content generation statistics: {e}")
            raise

    def cleanup_old_safety_events(self, days_old: int = 30) -> int:
        """Clean up resolved safety events older than specified days."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

            deleted_count = self.session.query(SafetyEventModel).filter(
                SafetyEventModel.resolved_at.isnot(None),
                SafetyEventModel.resolved_at < cutoff_date
            ).delete()

            self.session.commit()
            logger.info(f"Cleaned up {deleted_count} old safety events")
            return deleted_count
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to cleanup old safety events: {e}")
            raise


class ApplicationRepositoryError(Exception):
    """Custom exception for application repository errors."""
    pass