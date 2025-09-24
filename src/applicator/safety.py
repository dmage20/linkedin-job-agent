"""Safety framework and emergency controls for application automation."""

import asyncio
import logging
import os
import signal
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .models import SafetyEventType, SafetyEventModel, ApplicationStatus, JobApplicationModel
from .repository import ApplicationRepository


logger = logging.getLogger(__name__)


class SafetyException(Exception):
    """Base exception for safety-related issues."""

    def __init__(self, message: str, event_type: SafetyEventType, severity: str = "medium"):
        super().__init__(message)
        self.event_type = event_type
        self.severity = severity


class EmergencyStopException(SafetyException):
    """Exception raised when emergency stop is active."""

    def __init__(self, message: str = "Emergency stop is active"):
        super().__init__(message, SafetyEventType.EMERGENCY_STOP, "critical")


class RateLimitException(SafetyException):
    """Exception raised when rate limits are exceeded."""

    def __init__(self, message: str):
        super().__init__(message, SafetyEventType.RATE_LIMIT_HIT, "high")


class CaptchaDetectedException(SafetyException):
    """Exception raised when CAPTCHA is detected."""

    def __init__(self, message: str):
        super().__init__(message, SafetyEventType.CAPTCHA_DETECTED, "high")


class BlockedAccessException(SafetyException):
    """Exception raised when access is blocked."""

    def __init__(self, message: str):
        super().__init__(message, SafetyEventType.BLOCKED_ACCESS, "critical")


class CostLimitException(SafetyException):
    """Exception raised when API cost limits are exceeded."""

    def __init__(self, message: str):
        super().__init__(message, SafetyEventType.API_COST_LIMIT, "high")


@dataclass
class SafetyConfig:
    """Configuration for safety controls."""

    # Rate limiting
    applications_per_hour: int = 10
    applications_per_day: int = 50
    linkedin_requests_per_minute: int = 5

    # Emergency stop
    emergency_stop_file: str = "/tmp/linkedin_agent_emergency_stop"

    # Cost limits
    max_cost_per_hour: float = 10.0
    max_cost_per_day: float = 50.0

    # Safety thresholds
    max_consecutive_failures: int = 3
    failure_cooldown_minutes: int = 30

    # Monitoring
    safety_check_interval_seconds: int = 30

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.applications_per_hour <= 0:
            raise ValueError("applications_per_hour must be positive")

        if self.applications_per_day <= 0:
            raise ValueError("applications_per_day must be positive")

        if self.max_cost_per_hour <= 0:
            raise ValueError("max_cost_per_hour must be positive")


class RateLimitManager:
    """Manages application rate limiting across different dimensions."""

    def __init__(self, config: SafetyConfig, repository: ApplicationRepository):
        self.config = config
        self.repository = repository
        self.logger = logging.getLogger(__name__)

    async def check_rate_limits(self, user_profile_id: int) -> bool:
        """Check if user can submit another application within rate limits."""
        try:
            now = datetime.now(timezone.utc)

            # Check hourly limits
            hour_ago = now - timedelta(hours=1)
            hourly_applications = self.repository.session.query(JobApplicationModel).filter(
                JobApplicationModel.user_profile_id == user_profile_id,
                JobApplicationModel.applied_at >= hour_ago,
                JobApplicationModel.status != ApplicationStatus.ERROR
            ).count()

            if hourly_applications >= self.config.applications_per_hour:
                self.logger.warning(f"Hourly rate limit exceeded for user {user_profile_id}: {hourly_applications}")
                return False

            # Check daily limits
            day_ago = now - timedelta(days=1)
            daily_applications = self.repository.session.query(JobApplicationModel).filter(
                JobApplicationModel.user_profile_id == user_profile_id,
                JobApplicationModel.applied_at >= day_ago,
                JobApplicationModel.status != ApplicationStatus.ERROR
            ).count()

            if daily_applications >= self.config.applications_per_day:
                self.logger.warning(f"Daily rate limit exceeded for user {user_profile_id}: {daily_applications}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error checking rate limits: {e}")
            # Fail safe - deny if we can't check
            return False

    async def get_rate_limit_status(self, user_profile_id: int) -> Dict[str, Any]:
        """Get current rate limit status for a user."""
        try:
            now = datetime.now(timezone.utc)

            # Count applications in last hour
            hour_ago = now - timedelta(hours=1)
            hourly_count = self.repository.session.query(JobApplicationModel).filter(
                JobApplicationModel.user_profile_id == user_profile_id,
                JobApplicationModel.applied_at >= hour_ago,
                JobApplicationModel.status != ApplicationStatus.ERROR
            ).count()

            # Count applications in last day
            day_ago = now - timedelta(days=1)
            daily_count = self.repository.session.query(JobApplicationModel).filter(
                JobApplicationModel.user_profile_id == user_profile_id,
                JobApplicationModel.applied_at >= day_ago,
                JobApplicationModel.status != ApplicationStatus.ERROR
            ).count()

            return {
                "hourly_count": hourly_count,
                "hourly_limit": self.config.applications_per_hour,
                "hourly_remaining": max(0, self.config.applications_per_hour - hourly_count),
                "daily_count": daily_count,
                "daily_limit": self.config.applications_per_day,
                "daily_remaining": max(0, self.config.applications_per_day - daily_count),
                "can_apply": hourly_count < self.config.applications_per_hour and daily_count < self.config.applications_per_day
            }

        except Exception as e:
            self.logger.error(f"Error getting rate limit status: {e}")
            return {
                "error": str(e),
                "can_apply": False
            }


class EmergencyStopSystem:
    """System for emergency stops and user control."""

    def __init__(self, config: SafetyConfig, repository: ApplicationRepository):
        self.config = config
        self.repository = repository
        self.logger = logging.getLogger(__name__)
        self._stop_active = False
        self._monitoring_task = None

    def activate_emergency_stop(self, reason: str, triggered_by: str = "system") -> None:
        """Activate emergency stop for all automation."""
        self._stop_active = True

        # Create stop file
        self.create_stop_file(reason)

        # Log safety event
        self.repository.create_safety_event(
            event_type=SafetyEventType.EMERGENCY_STOP,
            event_description=f"Emergency stop activated: {reason}",
            severity="critical",
            event_data={"triggered_by": triggered_by, "reason": reason}
        )

        self.logger.critical(f"EMERGENCY STOP ACTIVATED: {reason} (by {triggered_by})")

    def deactivate_emergency_stop(self, resolved_by: str = "user") -> None:
        """Deactivate emergency stop."""
        self._stop_active = False

        # Remove stop file
        self.remove_stop_file()

        self.logger.info(f"Emergency stop deactivated by {resolved_by}")

    def is_emergency_stop_active(self) -> bool:
        """Check if emergency stop is currently active."""
        # Check in-memory flag first
        if self._stop_active:
            return True

        # Check for stop file
        if self.check_stop_file():
            self._stop_active = True
            return True

        # Check for unresolved emergency stop events
        unresolved_stops = self.repository.get_unresolved_safety_events(
            event_type=SafetyEventType.EMERGENCY_STOP
        )
        if unresolved_stops:
            self._stop_active = True
            return True

        return False

    def create_stop_file(self, reason: str) -> None:
        """Create emergency stop file."""
        try:
            stop_path = Path(self.config.emergency_stop_file)
            stop_path.parent.mkdir(parents=True, exist_ok=True)

            with open(stop_path, 'w') as f:
                f.write(f"EMERGENCY_STOP: {reason} at {datetime.now()}\n")
                f.write(f"Process PID: {os.getpid()}\n")

            self.logger.info(f"Created emergency stop file: {stop_path}")
        except Exception as e:
            self.logger.error(f"Failed to create stop file: {e}")

    def remove_stop_file(self) -> None:
        """Remove emergency stop file."""
        try:
            stop_path = Path(self.config.emergency_stop_file)
            if stop_path.exists():
                stop_path.unlink()
                self.logger.info(f"Removed emergency stop file: {stop_path}")
        except Exception as e:
            self.logger.error(f"Failed to remove stop file: {e}")

    def check_stop_file(self) -> bool:
        """Check if emergency stop file exists."""
        return Path(self.config.emergency_stop_file).exists()

    async def start_monitoring(self) -> None:
        """Start background monitoring for emergency signals."""
        if self._monitoring_task:
            return

        self._monitoring_task = asyncio.create_task(self._monitor_emergency_signals())
        self.logger.info("Started emergency stop monitoring")

    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            self.logger.info("Stopped emergency stop monitoring")

    async def _monitor_emergency_signals(self) -> None:
        """Monitor for emergency stop signals."""
        while True:
            try:
                # Check for stop file
                if self.check_stop_file() and not self._stop_active:
                    self.activate_emergency_stop("Stop file detected", "external")

                await asyncio.sleep(self.config.safety_check_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in emergency monitoring: {e}")
                await asyncio.sleep(self.config.safety_check_interval_seconds)


class SafetyManager:
    """Central safety management system for application automation."""

    def __init__(self, config: SafetyConfig, repository: ApplicationRepository):
        self.config = config
        self.repository = repository
        self.rate_limiter = RateLimitManager(config, repository)
        self.emergency_stop = EmergencyStopSystem(config, repository)
        self.logger = logging.getLogger(__name__)

        # Cost tracking
        self._hourly_cost = 0.0
        self._daily_cost = 0.0
        self._last_cost_reset = datetime.now(timezone.utc)

        # Failure tracking
        self._consecutive_failures = 0
        self._last_failure_time = None

    async def pre_application_check(self, job_id: int, user_profile_id: int) -> None:
        """Comprehensive safety checks before application automation."""
        # 1. Check emergency stop status
        if self.emergency_stop.is_emergency_stop_active():
            raise EmergencyStopException("Emergency stop is active")

        # 2. Rate limiting checks
        can_apply = await self.rate_limiter.check_rate_limits(user_profile_id)
        if not can_apply:
            rate_status = await self.rate_limiter.get_rate_limit_status(user_profile_id)
            raise RateLimitException(f"Rate limit exceeded: {rate_status}")

        # 3. Cost limit verification
        await self._check_cost_limits()

        # 4. Duplicate application prevention
        existing_app = self.repository.get_application_by_job_and_user(job_id, user_profile_id)
        if existing_app:
            self.repository.create_safety_event(
                event_type=SafetyEventType.DUPLICATE_APPLICATION,
                event_description=f"Duplicate application attempt for job {job_id}",
                severity="medium",
                job_id=job_id,
                user_profile_id=user_profile_id
            )
            raise SafetyException(
                f"Application already exists for job {job_id}",
                SafetyEventType.DUPLICATE_APPLICATION,
                "medium"
            )

        # 5. Failure cooldown check
        await self._check_failure_cooldown()

        self.logger.info(f"Pre-application safety checks passed for job {job_id}, user {user_profile_id}")

    async def handle_safety_event(
        self,
        session_id: str,
        event: SafetyException,
        job_id: Optional[int] = None,
        user_profile_id: Optional[int] = None
    ) -> None:
        """Handle and log safety events."""
        # Create safety event record
        safety_event = self.repository.create_safety_event(
            event_type=event.event_type,
            event_description=str(event),
            severity=event.severity,
            automation_session_id=session_id,
            job_id=job_id,
            user_profile_id=user_profile_id
        )

        # Update failure tracking
        if event.severity in ["high", "critical"]:
            self._consecutive_failures += 1
            self._last_failure_time = datetime.now(timezone.utc)

        # Escalate critical events
        if event.severity == "critical":
            self.emergency_stop.activate_emergency_stop(str(event), "system")

        # Auto-trigger emergency stop on too many consecutive failures
        elif self._consecutive_failures >= self.config.max_consecutive_failures:
            self.emergency_stop.activate_emergency_stop(
                f"Too many consecutive failures: {self._consecutive_failures}",
                "system"
            )

        self.logger.error(f"Safety event handled: {event.event_type.value} - {event.severity} - {str(event)}")

    async def post_application_success(self, cost: float = 0.0) -> None:
        """Handle successful application completion."""
        # Reset failure counter on success
        self._consecutive_failures = 0

        # Track costs
        await self._track_cost(cost)

        self.logger.info(f"Application completed successfully, cost: ${cost:.4f}")

    async def _check_cost_limits(self) -> None:
        """Check API cost limits."""
        await self._update_cost_tracking()

        if self._hourly_cost >= self.config.max_cost_per_hour:
            raise CostLimitException(f"Hourly cost limit exceeded: ${self._hourly_cost:.2f}")

        if self._daily_cost >= self.config.max_cost_per_day:
            raise CostLimitException(f"Daily cost limit exceeded: ${self._daily_cost:.2f}")

    async def _check_failure_cooldown(self) -> None:
        """Check if we're in failure cooldown period."""
        if (self._consecutive_failures >= self.config.max_consecutive_failures and
            self._last_failure_time):

            cooldown_until = self._last_failure_time + timedelta(
                minutes=self.config.failure_cooldown_minutes
            )

            if datetime.now(timezone.utc) < cooldown_until:
                remaining = cooldown_until - datetime.now(timezone.utc)
                raise SafetyException(
                    f"In failure cooldown period. Wait {remaining.total_seconds():.0f} seconds",
                    SafetyEventType.USER_INTERVENTION,
                    "medium"
                )

    async def _track_cost(self, cost: float) -> None:
        """Track API costs."""
        await self._update_cost_tracking()
        self._hourly_cost += cost
        self._daily_cost += cost

    async def _update_cost_tracking(self) -> None:
        """Update cost tracking with time-based resets."""
        now = datetime.now(timezone.utc)

        # Reset hourly cost if hour has passed
        if now - self._last_cost_reset >= timedelta(hours=1):
            self._hourly_cost = 0.0

        # Reset daily cost if day has passed
        if now - self._last_cost_reset >= timedelta(days=1):
            self._daily_cost = 0.0
            self._last_cost_reset = now

    async def get_safety_status(self) -> Dict[str, Any]:
        """Get current safety system status."""
        await self._update_cost_tracking()

        return {
            "emergency_stop_active": self.emergency_stop.is_emergency_stop_active(),
            "consecutive_failures": self._consecutive_failures,
            "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None,
            "hourly_cost": self._hourly_cost,
            "daily_cost": self._daily_cost,
            "cost_limits": {
                "hourly_limit": self.config.max_cost_per_hour,
                "daily_limit": self.config.max_cost_per_day
            },
            "rate_limits": {
                "applications_per_hour": self.config.applications_per_hour,
                "applications_per_day": self.config.applications_per_day
            },
            "unresolved_events": len(self.repository.get_unresolved_safety_events())
        }

    async def reset_failure_count(self, reason: str = "manual_reset") -> None:
        """Reset consecutive failure count."""
        old_count = self._consecutive_failures
        self._consecutive_failures = 0
        self._last_failure_time = None

        self.repository.create_safety_event(
            event_type=SafetyEventType.USER_INTERVENTION,
            event_description=f"Failure count reset from {old_count} to 0: {reason}",
            severity="low"
        )

        self.logger.info(f"Reset failure count from {old_count} to 0: {reason}")

    async def start_monitoring(self) -> None:
        """Start safety monitoring systems."""
        await self.emergency_stop.start_monitoring()
        self.logger.info("Safety monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop safety monitoring systems."""
        await self.emergency_stop.stop_monitoring()
        self.logger.info("Safety monitoring stopped")


