"""Comprehensive error handling and recovery system for LinkedIn scraping."""

import asyncio
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable, Tuple
from collections import defaultdict, Counter
from enum import Enum
import logging

from src.scraper.linkedin_scraper import (
    ScrapingError,
    RateLimitError,
    CaptchaError,
    BlockedError
)


class ErrorType(Enum):
    """Types of errors that can occur during scraping."""
    RATE_LIMIT = "rate_limit"
    CAPTCHA = "captcha"
    BLOCKED = "blocked"
    NETWORK = "network"
    TIMEOUT = "timeout"
    PARSE_ERROR = "parse_error"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types."""
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    WAIT_AND_RETRY = "wait_and_retry"
    STOP_SESSION = "stop_session"
    SKIP_AND_CONTINUE = "skip_and_continue"
    RESET_CONNECTION = "reset_connection"


class ErrorClassifier:
    """Classifies errors and determines appropriate recovery strategies."""

    def __init__(self):
        """Initialize error classifier with strategy mappings."""
        self.strategy_map = {
            ErrorType.RATE_LIMIT: RecoveryStrategy.WAIT_AND_RETRY,
            ErrorType.CAPTCHA: RecoveryStrategy.STOP_SESSION,
            ErrorType.BLOCKED: RecoveryStrategy.STOP_SESSION,
            ErrorType.NETWORK: RecoveryStrategy.RETRY_WITH_BACKOFF,
            ErrorType.TIMEOUT: RecoveryStrategy.RETRY_WITH_BACKOFF,
            ErrorType.PARSE_ERROR: RecoveryStrategy.SKIP_AND_CONTINUE,
            ErrorType.UNKNOWN: RecoveryStrategy.RETRY_WITH_BACKOFF
        }

    def classify_error(self, error: Exception) -> ErrorType:
        """Classify an error into one of the defined error types."""
        if isinstance(error, RateLimitError):
            return ErrorType.RATE_LIMIT
        elif isinstance(error, CaptchaError):
            return ErrorType.CAPTCHA
        elif isinstance(error, BlockedError):
            return ErrorType.BLOCKED
        elif isinstance(error, (ConnectionError, ConnectionResetError)):
            return ErrorType.NETWORK
        elif isinstance(error, asyncio.TimeoutError):
            return ErrorType.TIMEOUT
        elif isinstance(error, (ValueError, AttributeError)) and "parse" in str(error).lower():
            return ErrorType.PARSE_ERROR
        else:
            return ErrorType.UNKNOWN

    def get_recovery_strategy(self, error_type: ErrorType) -> RecoveryStrategy:
        """Get the appropriate recovery strategy for an error type."""
        return self.strategy_map.get(error_type, RecoveryStrategy.RETRY_WITH_BACKOFF)


class ExponentialBackoff:
    """Implements exponential backoff with jitter for retry delays."""

    def __init__(self, initial_delay: float = 1.0, max_delay: float = 60.0,
                 multiplier: float = 2.0, jitter: bool = True):
        """Initialize exponential backoff parameters."""
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self.current_delay = initial_delay

    def get_delay(self) -> float:
        """Get the next delay value with exponential backoff."""
        delay = min(self.current_delay, self.max_delay)

        if self.jitter:
            # Add jitter: ±20% of the delay
            jitter_range = delay * 0.2
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)  # Ensure non-negative

        # Prepare for next call
        self.current_delay = min(self.current_delay * self.multiplier, self.max_delay)

        return delay

    def reset(self):
        """Reset backoff to initial delay."""
        self.current_delay = self.initial_delay


class RetryManager:
    """Manages retry attempts with exponential backoff."""

    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0,
                 max_delay: float = 60.0, multiplier: float = 2.0):
        """Initialize retry manager."""
        self.max_retries = max_retries
        self.attempt_count = 0
        self.backoff = ExponentialBackoff(
            initial_delay=initial_delay,
            max_delay=max_delay,
            multiplier=multiplier
        )

    def can_retry(self) -> bool:
        """Check if more retries are allowed."""
        return self.attempt_count < self.max_retries

    def record_attempt(self):
        """Record a retry attempt."""
        self.attempt_count += 1

    async def wait_before_retry(self):
        """Wait before next retry using exponential backoff."""
        delay = self.backoff.get_delay()
        await asyncio.sleep(delay)

    def reset(self):
        """Reset retry count and backoff."""
        self.attempt_count = 0
        self.backoff.reset()


class CircuitBreaker:
    """Implements circuit breaker pattern to prevent cascading failures."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0,
                 success_threshold: int = 3):
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        """Check if execution is allowed based on circuit breaker state."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            # Check if recovery timeout has passed
            if (self.last_failure_time and
                time.time() - self.last_failure_time >= self.recovery_timeout):
                self.state = "HALF_OPEN"
                self.success_count = 0
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True

        return False

    def record_success(self):
        """Record a successful execution."""
        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = "CLOSED"
                self.failure_count = 0
        elif self.state == "CLOSED":
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
        elif self.state == "HALF_OPEN":
            self.state = "OPEN"


class ErrorMetrics:
    """Tracks error metrics and patterns for analysis."""

    def __init__(self):
        """Initialize error metrics tracking."""
        self.total_errors = 0
        self.errors_by_type = defaultdict(int)
        self.error_history = []
        self.recovery_attempts = defaultdict(int)

    def record_error(self, error_type: ErrorType, error_message: str):
        """Record an error occurrence."""
        self.total_errors += 1
        self.errors_by_type[error_type] += 1
        self.error_history.append({
            "timestamp": datetime.now(),
            "type": error_type,
            "message": error_message
        })

    def record_recovery_attempt(self, error_type: ErrorType, strategy: RecoveryStrategy):
        """Record a recovery attempt."""
        key = f"{error_type.value}_{strategy.value}"
        self.recovery_attempts[key] += 1

    def get_error_rate(self, minutes: int = None, hours: int = None) -> int:
        """Get error rate for a specific time period."""
        if minutes is not None:
            cutoff = datetime.now() - timedelta(minutes=minutes)
        elif hours is not None:
            cutoff = datetime.now() - timedelta(hours=hours)
        else:
            cutoff = datetime.now() - timedelta(hours=1)  # Default to 1 hour

        recent_errors = [e for e in self.error_history if e["timestamp"] >= cutoff]
        return len(recent_errors)

    def get_most_common_errors(self, limit: int = 5) -> List[Tuple[ErrorType, int]]:
        """Get the most common error types."""
        counter = Counter(self.errors_by_type)
        return counter.most_common(limit)

    def reset(self):
        """Reset all metrics."""
        self.total_errors = 0
        self.errors_by_type.clear()
        self.error_history.clear()
        self.recovery_attempts.clear()


class ErrorHandler:
    """Main error handler that orchestrates error recovery."""

    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0,
                 circuit_breaker_threshold: int = 5):
        """Initialize error handler with components."""
        self.retry_manager = RetryManager(
            max_retries=max_retries,
            initial_delay=initial_delay
        )
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_threshold
        )
        self.error_classifier = ErrorClassifier()
        self.metrics = ErrorMetrics()
        self.logger = logging.getLogger(__name__)

    async def handle_with_retry(self, operation: Callable, *args, **kwargs):
        """Execute an operation with comprehensive error handling and retry."""
        if not self.circuit_breaker.can_execute():
            raise Exception("Circuit breaker is open - operation rejected")

        self.retry_manager.reset()

        while True:
            try:
                # Execute the operation
                result = await operation(*args, **kwargs)
                self.circuit_breaker.record_success()
                return result

            except Exception as error:
                # Classify the error
                error_type = self.error_classifier.classify_error(error)
                self.metrics.record_error(error_type, str(error))
                self.circuit_breaker.record_failure()

                self.logger.warning(f"Error occurred: {error_type.value} - {error}")

                # Check if we should retry this error type
                if not self._should_retry(error_type):
                    self.logger.error(f"Non-retryable error: {error}")
                    raise error

                # Check if we can retry
                if not self.retry_manager.can_retry():
                    self.logger.error(f"Max retries exceeded for error: {error}")
                    raise error

                # Record retry attempt
                self.retry_manager.record_attempt()
                strategy = self.error_classifier.get_recovery_strategy(error_type)
                self.metrics.record_recovery_attempt(error_type, strategy)

                self.logger.info(f"Attempting recovery with strategy: {strategy.value}")

                # Execute recovery strategy
                try:
                    await self._execute_recovery_strategy(strategy, error_type)
                except Exception as recovery_error:
                    self.logger.error(f"Recovery strategy failed: {recovery_error}")
                    raise error

    def _should_retry(self, error_type: ErrorType) -> bool:
        """Determine if an error type should be retried."""
        non_retryable_errors = {
            ErrorType.CAPTCHA,
            ErrorType.BLOCKED
        }
        return error_type not in non_retryable_errors

    async def _execute_recovery_strategy(self, strategy: RecoveryStrategy, error_type: ErrorType):
        """Execute the appropriate recovery strategy."""
        if strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
            await self.retry_manager.wait_before_retry()

        elif strategy == RecoveryStrategy.WAIT_AND_RETRY:
            # For rate limits, wait longer
            if error_type == ErrorType.RATE_LIMIT:
                wait_time = random.uniform(30, 60)  # Wait 30-60 seconds
            else:
                wait_time = 5
            await asyncio.sleep(wait_time)

        elif strategy == RecoveryStrategy.STOP_SESSION:
            raise Exception("Session terminated due to non-recoverable error")

        elif strategy == RecoveryStrategy.SKIP_AND_CONTINUE:
            # Log and continue
            self.logger.warning(f"Skipping operation due to {error_type.value}")

        elif strategy == RecoveryStrategy.RESET_CONNECTION:
            # This would reset browser connection in actual implementation
            await asyncio.sleep(2)

    def get_error_summary(self) -> Dict[str, Any]:
        """Get comprehensive error summary."""
        return {
            "total_errors": self.metrics.total_errors,
            "errors_by_type": dict(self.metrics.errors_by_type),
            "circuit_breaker_state": self.circuit_breaker.state,
            "retry_attempts": self.retry_manager.attempt_count,
            "most_common_errors": self.metrics.get_most_common_errors(),
            "recent_error_rate": self.metrics.get_error_rate(hours=1)
        }

    def reset_all(self):
        """Reset all error tracking and recovery state."""
        self.retry_manager.reset()
        self.metrics.reset()
        self.circuit_breaker.failure_count = 0
        self.circuit_breaker.state = "CLOSED"