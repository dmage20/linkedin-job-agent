"""Tests for application automation database models."""

import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from src.applicator.models import (
    ApplicationStatus,
    JobApplicationModel,
    ContentType,
    GeneratedContentModel,
    SafetyEventType,
    SafetyEventModel
)
from src.database.models import JobModel
from src.analyzer.models import UserProfileModel


class TestJobApplicationModel:
    """Test cases for JobApplicationModel."""

    def test_application_model_creation(self, test_session, sample_job, sample_user_profile):
        """Test creating a job application model."""
        application = JobApplicationModel(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id,
            status=ApplicationStatus.ELIGIBLE,
            application_method="linkedin",
            cover_letter_content="Sample cover letter",
            custom_message="Sample message"
        )

        test_session.add(application)
        test_session.commit()

        assert application.id is not None
        assert application.job_id == sample_job.id
        assert application.user_profile_id == sample_user_profile.id
        assert application.status == ApplicationStatus.ELIGIBLE
        assert application.application_method == "linkedin"
        assert application.retry_count == 0
        assert application.created_at is not None

    def test_application_model_unique_constraint(self, test_session, sample_job, sample_user_profile):
        """Test unique constraint on job_id and user_profile_id."""
        # Create first application
        application1 = JobApplicationModel(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id,
            status=ApplicationStatus.ELIGIBLE
        )
        test_session.add(application1)
        test_session.commit()

        # Try to create duplicate application
        application2 = JobApplicationModel(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id,
            status=ApplicationStatus.PENDING
        )
        test_session.add(application2)

        with pytest.raises(IntegrityError):
            test_session.commit()

    def test_application_model_status_enum(self, test_session, sample_job, sample_user_profile):
        """Test application status enumeration values."""
        statuses = [
            ApplicationStatus.ELIGIBLE,
            ApplicationStatus.PENDING,
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.UNDER_REVIEW,
            ApplicationStatus.INTERVIEW_SCHEDULED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.OFFER_RECEIVED,
            ApplicationStatus.WITHDRAWN,
            ApplicationStatus.ERROR
        ]

        for status in statuses:
            application = JobApplicationModel(
                job_id=sample_job.id,
                user_profile_id=sample_user_profile.id,
                status=status
            )
            test_session.add(application)
            test_session.commit()

            assert application.status == status
            test_session.delete(application)
            test_session.commit()

    def test_application_model_to_dict(self, test_session, sample_job, sample_user_profile):
        """Test converting application model to dictionary."""
        now = datetime.now(timezone.utc)
        application = JobApplicationModel(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id,
            status=ApplicationStatus.SUBMITTED,
            application_method="linkedin",
            cover_letter_content="Test cover letter",
            custom_message="Test message",
            resume_version="v1.0",
            applied_at=now,
            automation_session_id="test_session_123",
            automation_success=True,
            retry_count=1
        )

        test_session.add(application)
        test_session.commit()

        result = application.to_dict()

        assert result['id'] == application.id
        assert result['job_id'] == sample_job.id
        assert result['user_profile_id'] == sample_user_profile.id
        assert result['status'] == 'submitted'
        assert result['application_method'] == 'linkedin'
        assert result['cover_letter_content'] == 'Test cover letter'
        assert result['custom_message'] == 'Test message'
        assert result['resume_version'] == 'v1.0'
        assert result['applied_at'] == now.replace(tzinfo=None).isoformat()
        assert result['automation_session_id'] == 'test_session_123'
        assert result['automation_success'] is True
        assert result['retry_count'] == 1


class TestGeneratedContentModel:
    """Test cases for GeneratedContentModel."""

    def test_content_model_creation(self, test_session, sample_application):
        """Test creating a generated content model."""
        content = GeneratedContentModel(
            application_id=sample_application.id,
            content_type=ContentType.COVER_LETTER,
            content_version=1,
            content_text="Generated cover letter content",
            generation_prompt="Generate a professional cover letter",
            claude_model_used="claude-3-haiku-20240307",
            generation_cost=0.05,
            generation_time_seconds=2.5,
            quality_score=85,
            user_approved=True
        )

        test_session.add(content)
        test_session.commit()

        assert content.id is not None
        assert content.application_id == sample_application.id
        assert content.content_type == ContentType.COVER_LETTER
        assert content.content_version == 1
        assert content.content_text == "Generated cover letter content"
        assert content.quality_score == 85
        assert content.user_approved is True
        assert content.user_edited is False

    def test_content_type_enum(self, test_session, sample_application):
        """Test content type enumeration values."""
        content_types = [
            ContentType.COVER_LETTER,
            ContentType.LINKEDIN_MESSAGE,
            ContentType.EMAIL_SUBJECT,
            ContentType.FOLLOW_UP_MESSAGE
        ]

        for content_type in content_types:
            content = GeneratedContentModel(
                application_id=sample_application.id,
                content_type=content_type,
                content_text=f"Test content for {content_type.value}"
            )
            test_session.add(content)
            test_session.commit()

            assert content.content_type == content_type
            test_session.delete(content)
            test_session.commit()

    def test_content_quality_score_constraint(self, test_session, sample_application):
        """Test quality score constraint (0-100)."""
        # Valid quality score
        content_valid = GeneratedContentModel(
            application_id=sample_application.id,
            content_type=ContentType.COVER_LETTER,
            content_text="Valid content",
            quality_score=75
        )
        test_session.add(content_valid)
        test_session.commit()
        assert content_valid.quality_score == 75

        # Invalid quality score (negative)
        content_invalid1 = GeneratedContentModel(
            application_id=sample_application.id,
            content_type=ContentType.LINKEDIN_MESSAGE,
            content_text="Invalid content",
            quality_score=-1
        )
        test_session.add(content_invalid1)

        with pytest.raises(IntegrityError):
            test_session.commit()

        test_session.rollback()

        # Invalid quality score (over 100)
        content_invalid2 = GeneratedContentModel(
            application_id=sample_application.id,
            content_type=ContentType.EMAIL_SUBJECT,
            content_text="Invalid content",
            quality_score=101
        )
        test_session.add(content_invalid2)

        with pytest.raises(IntegrityError):
            test_session.commit()

    def test_content_model_to_dict(self, test_session, sample_application):
        """Test converting content model to dictionary."""
        content = GeneratedContentModel(
            application_id=sample_application.id,
            content_type=ContentType.LINKEDIN_MESSAGE,
            content_version=2,
            content_text="Test LinkedIn message",
            generation_prompt="Create professional message",
            claude_model_used="claude-3-haiku-20240307",
            generation_cost=0.03,
            generation_time_seconds=1.8,
            quality_score=90,
            user_approved=True,
            user_edited=True
        )

        test_session.add(content)
        test_session.commit()

        result = content.to_dict()

        assert result['id'] == content.id
        assert result['application_id'] == sample_application.id
        assert result['content_type'] == 'linkedin_message'
        assert result['content_version'] == 2
        assert result['content_text'] == 'Test LinkedIn message'
        assert result['generation_prompt'] == 'Create professional message'
        assert result['claude_model_used'] == 'claude-3-haiku-20240307'
        assert result['generation_cost'] == 0.03
        assert result['generation_time_seconds'] == 1.8
        assert result['quality_score'] == 90
        assert result['user_approved'] is True
        assert result['user_edited'] is True


class TestSafetyEventModel:
    """Test cases for SafetyEventModel."""

    def test_safety_event_creation(self, test_session, sample_job, sample_user_profile):
        """Test creating a safety event model."""
        event = SafetyEventModel(
            event_type=SafetyEventType.EMERGENCY_STOP,
            event_description="Emergency stop activated by user",
            severity="critical",
            automation_session_id="session_123",
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id,
            event_data={"reason": "User requested stop", "action": "immediate"},
            resolution_action="System stopped successfully",
            resolved_by="user"
        )

        test_session.add(event)
        test_session.commit()

        assert event.id is not None
        assert event.event_type == SafetyEventType.EMERGENCY_STOP
        assert event.event_description == "Emergency stop activated by user"
        assert event.severity == "critical"
        assert event.automation_session_id == "session_123"
        assert event.job_id == sample_job.id
        assert event.user_profile_id == sample_user_profile.id
        assert event.event_data["reason"] == "User requested stop"
        assert event.resolution_action == "System stopped successfully"
        assert event.resolved_by == "user"

    def test_safety_event_type_enum(self, test_session):
        """Test safety event type enumeration values."""
        event_types = [
            SafetyEventType.EMERGENCY_STOP,
            SafetyEventType.RATE_LIMIT_HIT,
            SafetyEventType.CAPTCHA_DETECTED,
            SafetyEventType.BLOCKED_ACCESS,
            SafetyEventType.API_COST_LIMIT,
            SafetyEventType.USER_INTERVENTION,
            SafetyEventType.AUTHENTICATION_FAILED,
            SafetyEventType.DUPLICATE_APPLICATION
        ]

        for event_type in event_types:
            event = SafetyEventModel(
                event_type=event_type,
                event_description=f"Test event for {event_type.value}",
                severity="medium"
            )
            test_session.add(event)
            test_session.commit()

            assert event.event_type == event_type
            test_session.delete(event)
            test_session.commit()

    def test_safety_event_severity_constraint(self, test_session):
        """Test severity constraint validation."""
        # Valid severities
        valid_severities = ["low", "medium", "high", "critical"]

        for severity in valid_severities:
            event = SafetyEventModel(
                event_type=SafetyEventType.RATE_LIMIT_HIT,
                event_description=f"Test event with {severity} severity",
                severity=severity
            )
            test_session.add(event)
            test_session.commit()

            assert event.severity == severity
            test_session.delete(event)
            test_session.commit()

        # Invalid severity
        event_invalid = SafetyEventModel(
            event_type=SafetyEventType.USER_INTERVENTION,
            event_description="Test event with invalid severity",
            severity="invalid"
        )
        test_session.add(event_invalid)

        with pytest.raises(IntegrityError):
            test_session.commit()

    def test_safety_event_to_dict(self, test_session):
        """Test converting safety event model to dictionary."""
        now = datetime.now(timezone.utc)
        event = SafetyEventModel(
            event_type=SafetyEventType.CAPTCHA_DETECTED,
            event_description="CAPTCHA challenge appeared during automation",
            severity="high",
            automation_session_id="session_456",
            event_data={"url": "https://linkedin.com/jobs/123", "attempt": 3},
            resolved_at=now,
            resolution_action="Manual intervention required",
            resolved_by="admin"
        )

        test_session.add(event)
        test_session.commit()

        result = event.to_dict()

        assert result['id'] == event.id
        assert result['event_type'] == 'captcha_detected'
        assert result['event_description'] == 'CAPTCHA challenge appeared during automation'
        assert result['severity'] == 'high'
        assert result['automation_session_id'] == 'session_456'
        assert result['event_data']['url'] == 'https://linkedin.com/jobs/123'
        assert result['event_data']['attempt'] == 3
        assert result['resolved_at'] == now.replace(tzinfo=None).isoformat()
        assert result['resolution_action'] == 'Manual intervention required'
        assert result['resolved_by'] == 'admin'


# Test fixtures specific to application models
@pytest.fixture
def sample_application(test_session, sample_job, sample_user_profile):
    """Create a sample job application for testing."""
    application = JobApplicationModel(
        job_id=sample_job.id,
        user_profile_id=sample_user_profile.id,
        status=ApplicationStatus.ELIGIBLE,
        application_method="linkedin"
    )
    test_session.add(application)
    test_session.commit()
    return application