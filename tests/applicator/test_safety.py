"""Tests for safety framework and emergency controls."""

import pytest
import asyncio
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from src.applicator.safety import (
    SafetyConfig,
    SafetyManager,
    RateLimitManager,
    EmergencyStopSystem,
    SafetyException,
    EmergencyStopException,
    RateLimitException,
    CaptchaDetectedException,
    BlockedAccessException,
    CostLimitException
)
from src.applicator.models import SafetyEventType, ApplicationStatus
from src.applicator.repository import ApplicationRepository


class TestSafetyConfig:
    """Test cases for SafetyConfig."""

    def test_safety_config_creation(self):
        """Test creating safety config with default values."""
        config = SafetyConfig()

        assert config.applications_per_hour == 10
        assert config.applications_per_day == 50
        assert config.max_cost_per_hour == 10.0
        assert config.max_consecutive_failures == 3

    def test_safety_config_custom_values(self):
        """Test creating safety config with custom values."""
        config = SafetyConfig(
            applications_per_hour=5,
            applications_per_day=25,
            max_cost_per_hour=5.0
        )

        assert config.applications_per_hour == 5
        assert config.applications_per_day == 25
        assert config.max_cost_per_hour == 5.0

    def test_safety_config_validation(self):
        """Test safety config validation."""
        with pytest.raises(ValueError):
            SafetyConfig(applications_per_hour=0)

        with pytest.raises(ValueError):
            SafetyConfig(applications_per_day=-1)

        with pytest.raises(ValueError):
            SafetyConfig(max_cost_per_hour=0)


class TestSafetyExceptions:
    """Test cases for safety exceptions."""

    def test_safety_exception(self):
        """Test basic safety exception."""
        exception = SafetyException("Test error", SafetyEventType.USER_INTERVENTION, "medium")

        assert str(exception) == "Test error"
        assert exception.event_type == SafetyEventType.USER_INTERVENTION
        assert exception.severity == "medium"

    def test_emergency_stop_exception(self):
        """Test emergency stop exception."""
        exception = EmergencyStopException("System halted")

        assert str(exception) == "System halted"
        assert exception.event_type == SafetyEventType.EMERGENCY_STOP
        assert exception.severity == "critical"

    def test_rate_limit_exception(self):
        """Test rate limit exception."""
        exception = RateLimitException("Rate limit exceeded")

        assert str(exception) == "Rate limit exceeded"
        assert exception.event_type == SafetyEventType.RATE_LIMIT_HIT
        assert exception.severity == "high"

    def test_captcha_detected_exception(self):
        """Test CAPTCHA detected exception."""
        exception = CaptchaDetectedException("CAPTCHA challenge")

        assert str(exception) == "CAPTCHA challenge"
        assert exception.event_type == SafetyEventType.CAPTCHA_DETECTED
        assert exception.severity == "high"

    def test_blocked_access_exception(self):
        """Test blocked access exception."""
        exception = BlockedAccessException("Access denied")

        assert str(exception) == "Access denied"
        assert exception.event_type == SafetyEventType.BLOCKED_ACCESS
        assert exception.severity == "critical"

    def test_cost_limit_exception(self):
        """Test cost limit exception."""
        exception = CostLimitException("Cost limit reached")

        assert str(exception) == "Cost limit reached"
        assert exception.event_type == SafetyEventType.API_COST_LIMIT
        assert exception.severity == "high"


class TestRateLimitManager:
    """Test cases for RateLimitManager."""

    @pytest.fixture
    def safety_config(self):
        """Create safety config for testing."""
        return SafetyConfig(
            applications_per_hour=2,
            applications_per_day=5
        )

    @pytest.fixture
    def app_repo(self, test_session):
        """Create application repository."""
        return ApplicationRepository(test_session)

    @pytest.fixture
    def rate_limiter(self, safety_config, app_repo):
        """Create rate limit manager."""
        return RateLimitManager(safety_config, app_repo)

    @pytest.mark.asyncio
    async def test_check_rate_limits_within_limits(self, rate_limiter, sample_user_profile):
        """Test rate limit check when within limits."""
        # No applications yet, should be within limits
        result = await rate_limiter.check_rate_limits(sample_user_profile.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_rate_limits_hourly_exceeded(self, rate_limiter, app_repo, sample_job, sample_user_profile, test_session):
        """Test rate limit check when hourly limit is exceeded."""
        # Create applications that exceed hourly limit
        now = datetime.now(timezone.utc)

        # Create different jobs to avoid unique constraint
        from src.database.models import JobModel

        for i in range(3):  # Exceeds limit of 2
            job = JobModel(
                title=f"Job {i}",
                company=f"Company {i}",
                location="Test Location",
                description="Test job",
                url=f"https://test.com/job{i}",
                linkedin_job_id=f"job{i}"
            )
            test_session.add(job)
            test_session.commit()

            application = app_repo.create_application(
                job_id=job.id,
                user_profile_id=sample_user_profile.id,
                applied_at=now - timedelta(minutes=30)
            )

        # This should now fail
        result = await rate_limiter.check_rate_limits(sample_user_profile.id)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_rate_limit_status(self, rate_limiter, app_repo, sample_job, sample_user_profile):
        """Test getting rate limit status."""
        # Create one application
        app_repo.create_application(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id,
            applied_at=datetime.now(timezone.utc) - timedelta(minutes=30)
        )

        status = await rate_limiter.get_rate_limit_status(sample_user_profile.id)

        assert status["hourly_count"] == 1
        assert status["hourly_limit"] == 2
        assert status["hourly_remaining"] == 1
        assert status["daily_count"] == 1
        assert status["daily_limit"] == 5
        assert status["daily_remaining"] == 4
        assert status["can_apply"] is True


class TestEmergencyStopSystem:
    """Test cases for EmergencyStopSystem."""

    @pytest.fixture
    def safety_config(self):
        """Create safety config with temporary stop file."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            return SafetyConfig(emergency_stop_file=tmp.name)

    @pytest.fixture
    def app_repo(self, test_session):
        """Create application repository."""
        return ApplicationRepository(test_session)

    @pytest.fixture
    def emergency_stop(self, safety_config, app_repo):
        """Create emergency stop system."""
        system = EmergencyStopSystem(safety_config, app_repo)
        # Ensure clean state
        system._stop_active = False
        system.remove_stop_file()
        return system

    def test_activate_emergency_stop(self, emergency_stop):
        """Test activating emergency stop."""
        emergency_stop.activate_emergency_stop("Test emergency", "test_user")

        assert emergency_stop.is_emergency_stop_active() is True
        assert emergency_stop.check_stop_file() is True

    def test_deactivate_emergency_stop(self, emergency_stop):
        """Test deactivating emergency stop."""
        emergency_stop.activate_emergency_stop("Test emergency", "test_user")
        assert emergency_stop.is_emergency_stop_active() is True

        # Resolve unresolved emergency stop events
        unresolved_events = emergency_stop.repository.get_unresolved_safety_events(
            event_type=SafetyEventType.EMERGENCY_STOP
        )
        for event in unresolved_events:
            emergency_stop.repository.resolve_safety_event(
                event.id, "Test resolution", "test_user"
            )

        emergency_stop.deactivate_emergency_stop("test_user")

        assert emergency_stop.is_emergency_stop_active() is False
        assert emergency_stop.check_stop_file() is False

    def test_check_stop_file_detection(self, emergency_stop):
        """Test stop file detection."""
        # Initially no stop file
        assert emergency_stop.check_stop_file() is False
        assert emergency_stop.is_emergency_stop_active() is False

        # Create stop file
        emergency_stop.create_stop_file("External stop")
        assert emergency_stop.check_stop_file() is True

        # Reset internal state to test file detection
        emergency_stop._stop_active = False
        assert emergency_stop.is_emergency_stop_active() is True  # Should detect from file

        # Remove stop file
        emergency_stop.remove_stop_file()
        emergency_stop._stop_active = False
        assert emergency_stop.check_stop_file() is False

    @pytest.mark.asyncio
    async def test_emergency_monitoring(self, emergency_stop):
        """Test emergency monitoring task."""
        await emergency_stop.start_monitoring()
        assert emergency_stop._monitoring_task is not None

        # Create stop file externally
        emergency_stop.create_stop_file("External stop test")

        # Wait a moment for monitoring to detect
        await asyncio.sleep(0.1)

        assert emergency_stop.is_emergency_stop_active() is True

        await emergency_stop.stop_monitoring()
        assert emergency_stop._monitoring_task is None


class TestSafetyManager:
    """Test cases for SafetyManager."""

    @pytest.fixture
    def safety_config(self):
        """Create safety config for testing."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            return SafetyConfig(
                applications_per_hour=2,
                applications_per_day=5,
                max_cost_per_hour=1.0,
                max_consecutive_failures=2,
                emergency_stop_file=tmp.name
            )

    @pytest.fixture
    def app_repo(self, test_session):
        """Create application repository."""
        return ApplicationRepository(test_session)

    @pytest.fixture
    def safety_manager(self, safety_config, app_repo):
        """Create safety manager."""
        manager = SafetyManager(safety_config, app_repo)
        # Ensure clean state
        manager.emergency_stop._stop_active = False
        manager.emergency_stop.remove_stop_file()
        manager._consecutive_failures = 0
        manager._last_failure_time = None
        return manager

    @pytest.mark.asyncio
    async def test_pre_application_check_success(self, safety_manager, sample_job, sample_user_profile):
        """Test successful pre-application check."""
        # Should pass all checks
        await safety_manager.pre_application_check(sample_job.id, sample_user_profile.id)

    @pytest.mark.asyncio
    async def test_pre_application_check_emergency_stop(self, safety_manager, sample_job, sample_user_profile):
        """Test pre-application check with emergency stop active."""
        safety_manager.emergency_stop.activate_emergency_stop("Test stop", "test")

        with pytest.raises(EmergencyStopException):
            await safety_manager.pre_application_check(sample_job.id, sample_user_profile.id)

    @pytest.mark.asyncio
    async def test_pre_application_check_duplicate(self, safety_manager, app_repo, sample_job, sample_user_profile):
        """Test pre-application check with duplicate application."""
        # Create existing application
        app_repo.create_application(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id
        )

        with pytest.raises(SafetyException) as exc_info:
            await safety_manager.pre_application_check(sample_job.id, sample_user_profile.id)

        assert exc_info.value.event_type == SafetyEventType.DUPLICATE_APPLICATION

    @pytest.mark.asyncio
    async def test_handle_safety_event(self, safety_manager):
        """Test handling safety events."""
        session_id = "test_session_123"
        event = RateLimitException("Rate limit hit")

        await safety_manager.handle_safety_event(session_id, event, job_id=1, user_profile_id=1)

        # Check that consecutive failures is tracked
        assert safety_manager._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_handle_critical_safety_event(self, safety_manager):
        """Test handling critical safety events triggers emergency stop."""
        session_id = "test_session_456"
        event = BlockedAccessException("Access blocked")

        await safety_manager.handle_safety_event(session_id, event)

        # Critical event should trigger emergency stop
        assert safety_manager.emergency_stop.is_emergency_stop_active() is True

    @pytest.mark.asyncio
    async def test_consecutive_failures_trigger_emergency_stop(self, safety_manager):
        """Test that consecutive failures trigger emergency stop."""
        session_id = "test_session_789"

        # Trigger multiple failures
        for i in range(2):  # Configured max is 2
            event = RateLimitException(f"Failure {i}")
            await safety_manager.handle_safety_event(session_id, event)

        # Should trigger emergency stop
        assert safety_manager.emergency_stop.is_emergency_stop_active() is True

    @pytest.mark.asyncio
    async def test_post_application_success_resets_failures(self, safety_manager):
        """Test that successful application resets failure count."""
        # First cause a failure
        event = RateLimitException("Test failure")
        await safety_manager.handle_safety_event("session", event)
        assert safety_manager._consecutive_failures == 1

        # Then have a success
        await safety_manager.post_application_success(cost=0.05)
        assert safety_manager._consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_cost_tracking(self, safety_manager):
        """Test cost tracking and limits."""
        # Track costs
        await safety_manager.post_application_success(cost=0.3)
        await safety_manager.post_application_success(cost=0.4)

        status = await safety_manager.get_safety_status()
        assert status["hourly_cost"] == 0.7
        assert status["daily_cost"] == 0.7

        # Exceed cost limit
        await safety_manager.post_application_success(cost=0.5)

        with pytest.raises(CostLimitException):
            await safety_manager._check_cost_limits()

    @pytest.mark.asyncio
    async def test_failure_cooldown(self, safety_manager):
        """Test failure cooldown mechanism."""
        # Trigger max failures
        for i in range(2):
            event = RateLimitException(f"Failure {i}")
            await safety_manager.handle_safety_event("session", event)

        # Emergency stop should be active
        assert safety_manager.emergency_stop.is_emergency_stop_active() is True

        # Deactivate emergency stop but failures remain
        safety_manager.emergency_stop.deactivate_emergency_stop()

        # Should still be in cooldown
        with pytest.raises(SafetyException) as exc_info:
            await safety_manager._check_failure_cooldown()

        assert exc_info.value.event_type == SafetyEventType.USER_INTERVENTION

    @pytest.mark.asyncio
    async def test_get_safety_status(self, safety_manager):
        """Test getting safety status."""
        status = await safety_manager.get_safety_status()

        assert "emergency_stop_active" in status
        assert "consecutive_failures" in status
        assert "hourly_cost" in status
        assert "daily_cost" in status
        assert "cost_limits" in status
        assert "rate_limits" in status
        assert "unresolved_events" in status

        assert status["emergency_stop_active"] is False
        assert status["consecutive_failures"] == 0
        assert status["hourly_cost"] == 0.0

    @pytest.mark.asyncio
    async def test_reset_failure_count(self, safety_manager):
        """Test manually resetting failure count."""
        # Create some failures
        event = RateLimitException("Test failure")
        await safety_manager.handle_safety_event("session", event)
        assert safety_manager._consecutive_failures == 1

        # Reset manually
        await safety_manager.reset_failure_count("manual intervention")
        assert safety_manager._consecutive_failures == 0
        assert safety_manager._last_failure_time is None

    @pytest.mark.asyncio
    async def test_monitoring_lifecycle(self, safety_manager):
        """Test starting and stopping monitoring."""
        await safety_manager.start_monitoring()
        assert safety_manager.emergency_stop._monitoring_task is not None

        await safety_manager.stop_monitoring()
        assert safety_manager.emergency_stop._monitoring_task is None


class TestIntegratedSafetyWorkflow:
    """Integration tests for complete safety workflow."""

    @pytest.fixture
    def safety_config(self):
        """Create safety config for integration testing."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            return SafetyConfig(
                applications_per_hour=1,
                applications_per_day=2,
                max_cost_per_hour=0.5,
                max_consecutive_failures=1,
                emergency_stop_file=tmp.name
            )

    @pytest.fixture
    def app_repo(self, test_session):
        """Create application repository."""
        return ApplicationRepository(test_session)

    @pytest.fixture
    def safety_manager(self, safety_config, app_repo):
        """Create safety manager."""
        manager = SafetyManager(safety_config, app_repo)
        # Ensure clean state
        manager.emergency_stop._stop_active = False
        manager.emergency_stop.remove_stop_file()
        manager._consecutive_failures = 0
        manager._last_failure_time = None
        return manager

    @pytest.mark.asyncio
    async def test_complete_safety_workflow(self, safety_manager, app_repo, sample_job, sample_user_profile):
        """Test complete safety workflow from check to completion."""
        # 1. Pre-application check should pass
        await safety_manager.pre_application_check(sample_job.id, sample_user_profile.id)

        # 2. Create application
        application = app_repo.create_application(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id,
            automation_session_id="test_session",
            applied_at=datetime.now(timezone.utc)
        )

        # 3. Successful completion
        await safety_manager.post_application_success(cost=0.1)

        # 4. Check safety status
        status = await safety_manager.get_safety_status()
        assert status["consecutive_failures"] == 0
        assert status["hourly_cost"] == 0.1

    @pytest.mark.asyncio
    async def test_safety_workflow_with_failure_recovery(self, safety_manager, sample_job, sample_user_profile):
        """Test safety workflow with failure and recovery."""
        # 1. Start with successful check
        await safety_manager.pre_application_check(sample_job.id, sample_user_profile.id)

        # 2. Simulate a failure
        event = RateLimitException("Simulated failure")
        await safety_manager.handle_safety_event("session", event, sample_job.id, sample_user_profile.id)

        # 3. Emergency stop should be activated (max failures = 1)
        assert safety_manager.emergency_stop.is_emergency_stop_active() is True

        # 4. Pre-application check should now fail
        with pytest.raises(EmergencyStopException):
            await safety_manager.pre_application_check(sample_job.id, sample_user_profile.id)

        # 5. Resolve emergency stop and safety events
        unresolved_events = safety_manager.repository.get_unresolved_safety_events(
            event_type=SafetyEventType.EMERGENCY_STOP
        )
        for event in unresolved_events:
            safety_manager.repository.resolve_safety_event(
                event.id, "Test resolution", "admin"
            )

        safety_manager.emergency_stop.deactivate_emergency_stop("admin")
        await safety_manager.reset_failure_count("manual intervention")

        # 6. Pre-application check should now pass again
        from src.database.models import JobModel
        job2 = JobModel(
            title="Another Job",
            company="Another Corp",
            location="Remote",
            description="Another job",
            url="https://linkedin.com/jobs/another",
            linkedin_job_id="another123"
        )
        safety_manager.repository.session.add(job2)
        safety_manager.repository.session.commit()

        await safety_manager.pre_application_check(job2.id, sample_user_profile.id)