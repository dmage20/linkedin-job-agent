"""Tests for application repository."""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import IntegrityError

from src.applicator.repository import ApplicationRepository, ApplicationRepositoryError
from src.applicator.models import (
    ApplicationStatus,
    JobApplicationModel,
    ContentType,
    GeneratedContentModel,
    SafetyEventType,
    SafetyEventModel
)


class TestApplicationRepository:
    """Test cases for ApplicationRepository."""

    @pytest.fixture
    def app_repo(self, test_session):
        """Create application repository instance."""
        return ApplicationRepository(test_session)

    # Job Application tests
    def test_create_application(self, app_repo, sample_job, sample_user_profile):
        """Test creating a job application."""
        application = app_repo.create_application(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id,
            application_method="linkedin",
            cover_letter_content="Test cover letter"
        )

        assert application.id is not None
        assert application.job_id == sample_job.id
        assert application.user_profile_id == sample_user_profile.id
        assert application.status == ApplicationStatus.ELIGIBLE
        assert application.application_method == "linkedin"
        assert application.cover_letter_content == "Test cover letter"

    def test_create_duplicate_application_fails(self, app_repo, sample_job, sample_user_profile):
        """Test that creating duplicate application fails."""
        # Create first application
        app_repo.create_application(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id
        )

        # Try to create duplicate
        with pytest.raises(Exception):  # Should raise integrity error
            app_repo.create_application(
                job_id=sample_job.id,
                user_profile_id=sample_user_profile.id
            )

    def test_get_application_by_id(self, app_repo, sample_job, sample_user_profile):
        """Test getting application by ID."""
        created_app = app_repo.create_application(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id,
            custom_message="Test message"
        )

        retrieved_app = app_repo.get_application_by_id(created_app.id)

        assert retrieved_app is not None
        assert retrieved_app.id == created_app.id
        assert retrieved_app.custom_message == "Test message"

    def test_get_application_by_id_not_found(self, app_repo):
        """Test getting non-existent application returns None."""
        result = app_repo.get_application_by_id(999)
        assert result is None

    def test_get_application_by_job_and_user(self, app_repo, sample_job, sample_user_profile):
        """Test getting application by job and user."""
        created_app = app_repo.create_application(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id,
            automation_session_id="test_session"
        )

        retrieved_app = app_repo.get_application_by_job_and_user(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id
        )

        assert retrieved_app is not None
        assert retrieved_app.id == created_app.id
        assert retrieved_app.automation_session_id == "test_session"

    def test_update_application_status(self, app_repo, sample_job, sample_user_profile):
        """Test updating application status."""
        application = app_repo.create_application(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id
        )

        success = app_repo.update_application_status(
            application_id=application.id,
            status=ApplicationStatus.SUBMITTED,
            automation_success=True,
            automation_session_id="session_123"
        )

        assert success is True

        # Verify the update
        updated_app = app_repo.get_application_by_id(application.id)
        assert updated_app.status == ApplicationStatus.SUBMITTED
        assert updated_app.automation_success is True
        assert updated_app.automation_session_id == "session_123"
        assert updated_app.last_status_update is not None

    def test_update_application_status_not_found(self, app_repo):
        """Test updating non-existent application returns False."""
        success = app_repo.update_application_status(
            application_id=999,
            status=ApplicationStatus.SUBMITTED
        )
        assert success is False

    def test_get_user_applications(self, app_repo, sample_job, sample_user_profile, test_session):
        """Test getting user applications."""
        # Create multiple applications with different statuses
        app1 = app_repo.create_application(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id,
            status=ApplicationStatus.ELIGIBLE
        )

        # Create another job for second application
        from src.database.models import JobModel
        job2 = JobModel(
            title="Backend Engineer",
            company="Another Corp",
            location="Remote",
            description="Remote backend position",
            url="https://linkedin.com/jobs/67890",
            linkedin_job_id="67890"
        )
        test_session.add(job2)
        test_session.commit()

        app2 = app_repo.create_application(
            job_id=job2.id,
            user_profile_id=sample_user_profile.id,
            status=ApplicationStatus.SUBMITTED
        )

        # Get all applications for user
        all_apps = app_repo.get_user_applications(sample_user_profile.id)
        assert len(all_apps) == 2

        # Get only submitted applications
        submitted_apps = app_repo.get_user_applications(
            sample_user_profile.id,
            status=ApplicationStatus.SUBMITTED
        )
        assert len(submitted_apps) == 1
        assert submitted_apps[0].id == app2.id

        # Test limit
        limited_apps = app_repo.get_user_applications(sample_user_profile.id, limit=1)
        assert len(limited_apps) == 1

    def test_get_applications_by_status(self, app_repo, sample_job, sample_user_profile, test_session):
        """Test getting applications by status."""
        app1 = app_repo.create_application(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id,
            status=ApplicationStatus.ELIGIBLE
        )

        # Create another job for second application to avoid unique constraint
        from src.database.models import JobModel
        job2 = JobModel(
            title="Frontend Engineer",
            company="Frontend Corp",
            location="Remote",
            description="Frontend position",
            url="https://linkedin.com/jobs/54321",
            linkedin_job_id="54321"
        )
        test_session.add(job2)
        test_session.commit()

        app2 = app_repo.create_application(
            job_id=job2.id,
            user_profile_id=sample_user_profile.id,
            status=ApplicationStatus.PENDING
        )

        pending_apps = app_repo.get_applications_by_status(ApplicationStatus.PENDING)
        assert len(pending_apps) == 1
        assert pending_apps[0].id == app2.id

        eligible_apps = app_repo.get_applications_by_status(ApplicationStatus.ELIGIBLE)
        assert len(eligible_apps) == 1
        assert eligible_apps[0].id == app1.id

    def test_get_applications_by_session_id(self, app_repo, sample_job, sample_user_profile):
        """Test getting applications by session ID."""
        session_id = "test_session_456"

        application = app_repo.create_application(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id,
            automation_session_id=session_id
        )

        session_apps = app_repo.get_applications_by_session_id(session_id)
        assert len(session_apps) == 1
        assert session_apps[0].id == application.id
        assert session_apps[0].automation_session_id == session_id

    def test_get_pending_applications(self, app_repo, sample_job, sample_user_profile):
        """Test getting pending applications."""
        # Create applications with different statuses
        eligible_app = app_repo.create_application(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id,
            status=ApplicationStatus.ELIGIBLE
        )

        # Update to pending
        app_repo.update_application_status(eligible_app.id, ApplicationStatus.PENDING)

        pending_apps = app_repo.get_pending_applications()
        assert len(pending_apps) == 1
        assert pending_apps[0].id == eligible_app.id


class TestGeneratedContentRepository:
    """Test cases for generated content repository methods."""

    @pytest.fixture
    def app_repo(self, test_session):
        """Create application repository instance."""
        return ApplicationRepository(test_session)

    @pytest.fixture
    def sample_application(self, app_repo, sample_job, sample_user_profile):
        """Create a sample application for content tests."""
        return app_repo.create_application(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id
        )

    def test_create_generated_content(self, app_repo, sample_application):
        """Test creating generated content."""
        content = app_repo.create_generated_content(
            application_id=sample_application.id,
            content_type=ContentType.COVER_LETTER,
            content_text="Generated cover letter content",
            generation_prompt="Create a professional cover letter",
            quality_score=85,
            claude_model_used="claude-3-haiku-20240307"
        )

        assert content.id is not None
        assert content.application_id == sample_application.id
        assert content.content_type == ContentType.COVER_LETTER
        assert content.content_text == "Generated cover letter content"
        assert content.quality_score == 85
        assert content.claude_model_used == "claude-3-haiku-20240307"

    def test_get_application_content(self, app_repo, sample_application):
        """Test getting content for an application."""
        # Create multiple content types
        cover_letter = app_repo.create_generated_content(
            application_id=sample_application.id,
            content_type=ContentType.COVER_LETTER,
            content_text="Cover letter content"
        )

        linkedin_message = app_repo.create_generated_content(
            application_id=sample_application.id,
            content_type=ContentType.LINKEDIN_MESSAGE,
            content_text="LinkedIn message content"
        )

        # Get all content
        all_content = app_repo.get_application_content(sample_application.id)
        assert len(all_content) == 2

        # Get specific content type
        cover_letters = app_repo.get_application_content(
            sample_application.id,
            content_type=ContentType.COVER_LETTER
        )
        assert len(cover_letters) == 1
        assert cover_letters[0].id == cover_letter.id

    def test_get_latest_content(self, app_repo, sample_application):
        """Test getting latest version of content."""
        # Create multiple versions
        v1 = app_repo.create_generated_content(
            application_id=sample_application.id,
            content_type=ContentType.COVER_LETTER,
            content_text="Version 1",
            content_version=1
        )

        v2 = app_repo.create_generated_content(
            application_id=sample_application.id,
            content_type=ContentType.COVER_LETTER,
            content_text="Version 2",
            content_version=2
        )

        latest = app_repo.get_latest_content(
            sample_application.id,
            ContentType.COVER_LETTER
        )

        assert latest is not None
        assert latest.id == v2.id
        assert latest.content_text == "Version 2"
        assert latest.content_version == 2

    def test_update_content_approval(self, app_repo, sample_application):
        """Test updating content approval status."""
        content = app_repo.create_generated_content(
            application_id=sample_application.id,
            content_type=ContentType.COVER_LETTER,
            content_text="Test content"
        )

        success = app_repo.update_content_approval(
            content_id=content.id,
            user_approved=True,
            user_edited=True
        )

        assert success is True

        # Verify the update
        updated_content = app_repo.get_application_content(sample_application.id)[0]
        assert updated_content.user_approved is True
        assert updated_content.user_edited is True

    def test_update_content_approval_not_found(self, app_repo):
        """Test updating non-existent content approval returns False."""
        success = app_repo.update_content_approval(
            content_id=999,
            user_approved=True
        )
        assert success is False


class TestSafetyEventRepository:
    """Test cases for safety event repository methods."""

    @pytest.fixture
    def app_repo(self, test_session):
        """Create application repository instance."""
        return ApplicationRepository(test_session)

    def test_create_safety_event(self, app_repo, sample_job, sample_user_profile):
        """Test creating a safety event."""
        event = app_repo.create_safety_event(
            event_type=SafetyEventType.EMERGENCY_STOP,
            event_description="User triggered emergency stop",
            severity="critical",
            automation_session_id="session_789",
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id,
            event_data={"reason": "User intervention required"}
        )

        assert event.id is not None
        assert event.event_type == SafetyEventType.EMERGENCY_STOP
        assert event.event_description == "User triggered emergency stop"
        assert event.severity == "critical"
        assert event.automation_session_id == "session_789"
        assert event.job_id == sample_job.id
        assert event.user_profile_id == sample_user_profile.id
        assert event.event_data["reason"] == "User intervention required"

    def test_resolve_safety_event(self, app_repo):
        """Test resolving a safety event."""
        event = app_repo.create_safety_event(
            event_type=SafetyEventType.RATE_LIMIT_HIT,
            event_description="Rate limit exceeded",
            severity="medium"
        )

        success = app_repo.resolve_safety_event(
            event_id=event.id,
            resolution_action="Reduced automation rate",
            resolved_by="system"
        )

        assert success is True

        # Verify the resolution
        resolved_event = app_repo.session.query(SafetyEventModel).filter_by(id=event.id).first()
        assert resolved_event.resolved_at is not None
        assert resolved_event.resolution_action == "Reduced automation rate"
        assert resolved_event.resolved_by == "system"

    def test_resolve_safety_event_not_found(self, app_repo):
        """Test resolving non-existent safety event returns False."""
        success = app_repo.resolve_safety_event(
            event_id=999,
            resolution_action="Test action",
            resolved_by="test"
        )
        assert success is False

    def test_get_unresolved_safety_events(self, app_repo):
        """Test getting unresolved safety events."""
        # Create resolved event
        resolved_event = app_repo.create_safety_event(
            event_type=SafetyEventType.CAPTCHA_DETECTED,
            event_description="CAPTCHA resolved",
            severity="medium"
        )
        app_repo.resolve_safety_event(resolved_event.id, "Manual intervention", "user")

        # Create unresolved event
        unresolved_event = app_repo.create_safety_event(
            event_type=SafetyEventType.BLOCKED_ACCESS,
            event_description="Access blocked",
            severity="high"
        )

        unresolved_events = app_repo.get_unresolved_safety_events()
        assert len(unresolved_events) == 1
        assert unresolved_events[0].id == unresolved_event.id

        # Test filtering by severity
        high_severity_events = app_repo.get_unresolved_safety_events(severity="high")
        assert len(high_severity_events) == 1
        assert high_severity_events[0].id == unresolved_event.id

        # Test filtering by event type
        blocked_events = app_repo.get_unresolved_safety_events(
            event_type=SafetyEventType.BLOCKED_ACCESS
        )
        assert len(blocked_events) == 1
        assert blocked_events[0].id == unresolved_event.id

    def test_get_safety_events_by_session(self, app_repo):
        """Test getting safety events by session ID."""
        session_id = "test_session_safety"

        event1 = app_repo.create_safety_event(
            event_type=SafetyEventType.USER_INTERVENTION,
            event_description="User paused automation",
            severity="low",
            automation_session_id=session_id
        )

        event2 = app_repo.create_safety_event(
            event_type=SafetyEventType.RATE_LIMIT_HIT,
            event_description="Hit rate limit",
            severity="medium",
            automation_session_id=session_id
        )

        session_events = app_repo.get_safety_events_by_session(session_id)
        assert len(session_events) == 2
        # Events should be ordered by creation time
        assert session_events[0].id == event1.id
        assert session_events[1].id == event2.id


class TestRepositoryAnalytics:
    """Test cases for repository analytics methods."""

    @pytest.fixture
    def app_repo(self, test_session):
        """Create application repository instance."""
        return ApplicationRepository(test_session)

    def test_get_application_statistics(self, app_repo, sample_job, sample_user_profile):
        """Test getting application statistics."""
        # Create applications with different statuses
        app1 = app_repo.create_application(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id,
            status=ApplicationStatus.ELIGIBLE
        )

        app_repo.update_application_status(app1.id, ApplicationStatus.SUBMITTED)

        stats = app_repo.get_application_statistics(sample_user_profile.id)

        assert stats["total_applications"] == 1
        assert stats["submitted_count"] == 1
        assert stats["eligible_count"] == 0
        assert stats["success_rate"] == 100.0

    def test_get_application_statistics_all_users(self, app_repo, sample_job, sample_user_profile):
        """Test getting application statistics for all users."""
        app_repo.create_application(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id,
            status=ApplicationStatus.ELIGIBLE
        )

        stats = app_repo.get_application_statistics()  # No user_profile_id

        assert stats["total_applications"] == 1
        assert stats["eligible_count"] == 1

    def test_get_content_generation_stats(self, app_repo, sample_job, sample_user_profile):
        """Test getting content generation statistics."""
        application = app_repo.create_application(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id
        )

        # Create approved content
        approved_content = app_repo.create_generated_content(
            application_id=application.id,
            content_type=ContentType.COVER_LETTER,
            content_text="Approved content",
            user_approved=True
        )

        # Create non-approved content
        pending_content = app_repo.create_generated_content(
            application_id=application.id,
            content_type=ContentType.LINKEDIN_MESSAGE,
            content_text="Pending content"
        )

        stats = app_repo.get_content_generation_stats()

        assert stats["total_content_generated"] == 2
        assert stats["approved_content"] == 1
        assert stats["approval_rate"] == 50.0
        assert stats["cover_letter_count"] == 1
        assert stats["linkedin_message_count"] == 1

    def test_cleanup_old_safety_events(self, app_repo):
        """Test cleaning up old safety events."""
        # Create old resolved event
        old_event = app_repo.create_safety_event(
            event_type=SafetyEventType.RATE_LIMIT_HIT,
            event_description="Old resolved event",
            severity="low"
        )

        # Manually set old resolution date
        old_event.resolved_at = datetime.now(timezone.utc) - timedelta(days=35)
        app_repo.session.commit()

        # Create recent event
        recent_event = app_repo.create_safety_event(
            event_type=SafetyEventType.USER_INTERVENTION,
            event_description="Recent event",
            severity="medium"
        )

        deleted_count = app_repo.cleanup_old_safety_events(days_old=30)

        assert deleted_count == 1

        # Verify old event is gone, recent event remains
        remaining_events = app_repo.session.query(SafetyEventModel).all()
        assert len(remaining_events) == 1
        assert remaining_events[0].id == recent_event.id