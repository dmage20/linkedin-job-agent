"""Tests for error handling and recovery systems."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import json

from src.scraper.error_handler import (
    ErrorHandler,
    RetryManager,
    ErrorClassifier,
    ErrorType,
    RecoveryStrategy,
    CircuitBreaker,
    ErrorMetrics,
    ExponentialBackoff
)
from src.scraper.linkedin_scraper import (
    ScrapingError,
    RateLimitError,
    CaptchaError,
    BlockedError
)


class TestErrorClassifier:
    """Test error classification system."""

    def test_classify_rate_limit_error(self):
        """Test classification of rate limit errors."""
        classifier = ErrorClassifier()

        # Test rate limit error
        rate_error = RateLimitError("Session job limit exceeded")
        error_type = classifier.classify_error(rate_error)
        assert error_type == ErrorType.RATE_LIMIT

    def test_classify_captcha_error(self):
        """Test classification of CAPTCHA errors."""
        classifier = ErrorClassifier()

        captcha_error = CaptchaError("CAPTCHA detected on page")
        error_type = classifier.classify_error(captcha_error)
        assert error_type == ErrorType.CAPTCHA

    def test_classify_blocked_error(self):
        """Test classification of blocking errors."""
        classifier = ErrorClassifier()

        blocked_error = BlockedError("Access appears to be blocked")
        error_type = classifier.classify_error(blocked_error)
        assert error_type == ErrorType.BLOCKED

    def test_classify_network_error(self):
        """Test classification of network errors."""
        classifier = ErrorClassifier()

        network_error = ConnectionError("Connection timeout")
        error_type = classifier.classify_error(network_error)
        assert error_type == ErrorType.NETWORK

    def test_classify_unknown_error(self):
        """Test classification of unknown errors."""
        classifier = ErrorClassifier()

        unknown_error = ValueError("Some unexpected error")
        error_type = classifier.classify_error(unknown_error)
        assert error_type == ErrorType.UNKNOWN

    def test_get_recovery_strategy_for_rate_limit(self):
        """Test getting recovery strategy for rate limit errors."""
        classifier = ErrorClassifier()

        strategy = classifier.get_recovery_strategy(ErrorType.RATE_LIMIT)
        assert strategy == RecoveryStrategy.WAIT_AND_RETRY

    def test_get_recovery_strategy_for_captcha(self):
        """Test getting recovery strategy for CAPTCHA errors."""
        classifier = ErrorClassifier()

        strategy = classifier.get_recovery_strategy(ErrorType.CAPTCHA)
        assert strategy == RecoveryStrategy.STOP_SESSION

    def test_get_recovery_strategy_for_network(self):
        """Test getting recovery strategy for network errors."""
        classifier = ErrorClassifier()

        strategy = classifier.get_recovery_strategy(ErrorType.NETWORK)
        assert strategy == RecoveryStrategy.RETRY_WITH_BACKOFF


class TestExponentialBackoff:
    """Test exponential backoff implementation."""

    def test_backoff_initialization(self):
        """Test exponential backoff initialization."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=60.0,
            multiplier=2.0,
            jitter=True
        )

        assert backoff.initial_delay == 1.0
        assert backoff.max_delay == 60.0
        assert backoff.multiplier == 2.0
        assert backoff.jitter is True
        assert backoff.current_delay == 1.0

    def test_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=16.0,
            multiplier=2.0,
            jitter=False
        )

        # First attempt
        delay = backoff.get_delay()
        assert delay == 1.0

        # Second attempt
        delay = backoff.get_delay()
        assert delay == 2.0

        # Third attempt
        delay = backoff.get_delay()
        assert delay == 4.0

        # Fourth attempt
        delay = backoff.get_delay()
        assert delay == 8.0

        # Fifth attempt (should cap at max_delay)
        delay = backoff.get_delay()
        assert delay == 16.0

        # Sixth attempt (should stay at max_delay)
        delay = backoff.get_delay()
        assert delay == 16.0

    def test_backoff_with_jitter(self):
        """Test exponential backoff with jitter."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=60.0,
            multiplier=2.0,
            jitter=True
        )

        # Test multiple delays to ensure jitter varies
        delays = [backoff.get_delay() for _ in range(10)]

        # Should have some variation due to jitter
        assert len(set(delays)) > 1

    def test_backoff_reset(self):
        """Test backoff reset functionality."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=60.0,
            multiplier=2.0,
            jitter=False
        )

        # Advance the backoff
        backoff.get_delay()  # 1.0
        backoff.get_delay()  # 2.0
        backoff.get_delay()  # 4.0

        # Reset
        backoff.reset()

        # Should be back to initial delay
        delay = backoff.get_delay()
        assert delay == 1.0


class TestRetryManager:
    """Test retry management system."""

    def test_retry_manager_initialization(self):
        """Test retry manager initialization."""
        retry_manager = RetryManager(
            max_retries=3,
            initial_delay=1.0,
            max_delay=60.0
        )

        assert retry_manager.max_retries == 3
        assert retry_manager.attempt_count == 0
        assert retry_manager.backoff is not None

    def test_can_retry(self):
        """Test retry eligibility checking."""
        retry_manager = RetryManager(max_retries=3)

        # Should allow retries initially
        assert retry_manager.can_retry() is True

        # Simulate failed attempts
        retry_manager.record_attempt()
        assert retry_manager.can_retry() is True

        retry_manager.record_attempt()
        assert retry_manager.can_retry() is True

        retry_manager.record_attempt()
        assert retry_manager.can_retry() is False  # Max retries reached

    @pytest.mark.asyncio
    async def test_wait_before_retry(self):
        """Test waiting before retry with backoff."""
        retry_manager = RetryManager(
            max_retries=3,
            initial_delay=0.1,  # Small delay for testing
            max_delay=1.0
        )

        start_time = datetime.now()
        await retry_manager.wait_before_retry()
        end_time = datetime.now()

        elapsed = (end_time - start_time).total_seconds()
        assert elapsed >= 0.08  # Should wait close to initial delay (allowing for jitter)

    def test_reset_retry_count(self):
        """Test resetting retry count."""
        retry_manager = RetryManager(max_retries=3)

        # Exhaust retries
        retry_manager.record_attempt()
        retry_manager.record_attempt()
        retry_manager.record_attempt()
        assert retry_manager.can_retry() is False

        # Reset
        retry_manager.reset()
        assert retry_manager.can_retry() is True
        assert retry_manager.attempt_count == 0


class TestCircuitBreaker:
    """Test circuit breaker implementation."""

    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            success_threshold=3
        )

        assert circuit_breaker.failure_threshold == 5
        assert circuit_breaker.recovery_timeout == 60.0
        assert circuit_breaker.success_threshold == 3
        assert circuit_breaker.state == "CLOSED"
        assert circuit_breaker.failure_count == 0

    def test_circuit_breaker_failure_tracking(self):
        """Test circuit breaker failure tracking."""
        circuit_breaker = CircuitBreaker(failure_threshold=3)

        # Initially closed
        assert circuit_breaker.can_execute() is True
        assert circuit_breaker.state == "CLOSED"

        # Record failures
        circuit_breaker.record_failure()
        assert circuit_breaker.state == "CLOSED"

        circuit_breaker.record_failure()
        assert circuit_breaker.state == "CLOSED"

        circuit_breaker.record_failure()
        assert circuit_breaker.state == "OPEN"  # Should open after threshold
        assert circuit_breaker.can_execute() is False

    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery mechanism."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,  # Short timeout for testing
            success_threshold=2
        )

        # Trip the circuit breaker
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.state == "OPEN"

        # Wait for recovery timeout
        import time
        time.sleep(0.2)

        # Should transition to HALF_OPEN
        assert circuit_breaker.can_execute() is True
        assert circuit_breaker.state == "HALF_OPEN"

        # Record successes to close the circuit
        circuit_breaker.record_success()
        circuit_breaker.record_success()
        assert circuit_breaker.state == "CLOSED"

    def test_circuit_breaker_half_open_failure(self):
        """Test circuit breaker behavior when failing in half-open state."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=0.1
        )

        # Trip the circuit breaker
        circuit_breaker.record_failure()
        assert circuit_breaker.state == "OPEN"

        # Wait for recovery
        import time
        time.sleep(0.2)
        circuit_breaker.can_execute()  # Transitions to HALF_OPEN

        # Fail again - should go back to OPEN
        circuit_breaker.record_failure()
        assert circuit_breaker.state == "OPEN"


class TestErrorMetrics:
    """Test error metrics tracking."""

    def test_error_metrics_initialization(self):
        """Test error metrics initialization."""
        metrics = ErrorMetrics()

        assert metrics.total_errors == 0
        assert metrics.errors_by_type == {}
        assert len(metrics.error_history) == 0

    def test_record_error(self):
        """Test recording errors in metrics."""
        metrics = ErrorMetrics()

        # Record different types of errors
        metrics.record_error(ErrorType.RATE_LIMIT, "Rate limit exceeded")
        metrics.record_error(ErrorType.NETWORK, "Connection timeout")
        metrics.record_error(ErrorType.RATE_LIMIT, "Another rate limit")

        assert metrics.total_errors == 3
        assert metrics.errors_by_type[ErrorType.RATE_LIMIT] == 2
        assert metrics.errors_by_type[ErrorType.NETWORK] == 1
        assert len(metrics.error_history) == 3

    def test_get_error_rate(self):
        """Test calculating error rate over time period."""
        metrics = ErrorMetrics()

        # Record some errors
        metrics.record_error(ErrorType.NETWORK, "Error 1")
        metrics.record_error(ErrorType.RATE_LIMIT, "Error 2")

        # Error rate in last hour (should include all errors since they're recent)
        rate = metrics.get_error_rate(hours=1)
        assert rate == 2

        # Error rate in last minute (should still include all)
        rate = metrics.get_error_rate(minutes=1)
        assert rate == 2

    def test_get_most_common_errors(self):
        """Test getting most common error types."""
        metrics = ErrorMetrics()

        # Record various errors
        for _ in range(5):
            metrics.record_error(ErrorType.NETWORK, "Network error")
        for _ in range(3):
            metrics.record_error(ErrorType.RATE_LIMIT, "Rate limit")
        for _ in range(1):
            metrics.record_error(ErrorType.CAPTCHA, "CAPTCHA")

        common_errors = metrics.get_most_common_errors(limit=2)
        assert len(common_errors) == 2
        assert common_errors[0][0] == ErrorType.NETWORK
        assert common_errors[0][1] == 5
        assert common_errors[1][0] == ErrorType.RATE_LIMIT
        assert common_errors[1][1] == 3

    def test_reset_metrics(self):
        """Test resetting error metrics."""
        metrics = ErrorMetrics()

        # Record some errors
        metrics.record_error(ErrorType.NETWORK, "Error")
        metrics.record_error(ErrorType.RATE_LIMIT, "Error")

        # Reset
        metrics.reset()

        assert metrics.total_errors == 0
        assert metrics.errors_by_type == {}
        assert len(metrics.error_history) == 0


class TestErrorHandler:
    """Test the main error handler orchestration."""

    def test_error_handler_initialization(self):
        """Test error handler initialization."""
        handler = ErrorHandler(
            max_retries=3,
            initial_delay=1.0,
            circuit_breaker_threshold=5
        )

        assert handler.retry_manager is not None
        assert handler.circuit_breaker is not None
        assert handler.error_classifier is not None
        assert handler.metrics is not None

    @pytest.mark.asyncio
    async def test_handle_error_with_retry(self):
        """Test error handling with retry strategy."""
        handler = ErrorHandler(max_retries=2, initial_delay=0.1)

        # Mock a function that fails then succeeds
        call_count = 0
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise ConnectionError("Network error")
            return "success"

        result = await handler.handle_with_retry(mock_operation)
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_handle_error_exhausted_retries(self):
        """Test error handling when retries are exhausted."""
        handler = ErrorHandler(max_retries=2, initial_delay=0.1)

        # Mock a function that always fails
        async def mock_operation():
            raise ConnectionError("Persistent network error")

        with pytest.raises(ConnectionError):
            await handler.handle_with_retry(mock_operation)

        # Should have recorded the errors
        assert handler.metrics.total_errors > 0

    @pytest.mark.asyncio
    async def test_handle_non_retryable_error(self):
        """Test handling non-retryable errors."""
        handler = ErrorHandler(max_retries=3)

        # Mock a function that raises a CAPTCHA error (non-retryable)
        async def mock_operation():
            raise CaptchaError("CAPTCHA detected")

        with pytest.raises(CaptchaError):
            await handler.handle_with_retry(mock_operation)

        # Should not have retried
        assert handler.retry_manager.attempt_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """Test circuit breaker integration with error handler."""
        handler = ErrorHandler(
            max_retries=0,  # No retries to simplify test
            circuit_breaker_threshold=2,
            initial_delay=0.1
        )

        # Function that always fails
        async def failing_operation():
            raise ConnectionError("Always fails")

        # First attempt should be tried
        with pytest.raises(ConnectionError):
            await handler.handle_with_retry(failing_operation)

        # Second attempt should also be tried
        with pytest.raises(ConnectionError):
            await handler.handle_with_retry(failing_operation)

        # Circuit breaker should now be open
        assert handler.circuit_breaker.state == "OPEN"

        # Next attempt should be rejected by circuit breaker
        with pytest.raises(Exception, match="Circuit breaker is open"):
            await handler.handle_with_retry(failing_operation)

    def test_get_error_summary(self):
        """Test getting error summary from handler."""
        handler = ErrorHandler()

        # Simulate some errors
        handler.metrics.record_error(ErrorType.NETWORK, "Network error 1")
        handler.metrics.record_error(ErrorType.NETWORK, "Network error 2")
        handler.metrics.record_error(ErrorType.RATE_LIMIT, "Rate limit error")

        summary = handler.get_error_summary()

        assert summary["total_errors"] == 3
        assert summary["circuit_breaker_state"] == "CLOSED"
        assert ErrorType.NETWORK in summary["errors_by_type"]
        assert summary["errors_by_type"][ErrorType.NETWORK] == 2

    @pytest.mark.asyncio
    async def test_recovery_strategy_execution(self):
        """Test execution of different recovery strategies."""
        handler = ErrorHandler()

        # Test WAIT_AND_RETRY strategy
        start_time = datetime.now()
        await handler._execute_recovery_strategy(
            RecoveryStrategy.WAIT_AND_RETRY,
            error_type=ErrorType.RATE_LIMIT
        )
        end_time = datetime.now()

        # Should have waited some time
        elapsed = (end_time - start_time).total_seconds()
        assert elapsed > 0

        # Test STOP_SESSION strategy
        with pytest.raises(Exception, match="Session terminated"):
            await handler._execute_recovery_strategy(
                RecoveryStrategy.STOP_SESSION,
                error_type=ErrorType.CAPTCHA
            )

    def test_should_retry_based_on_error_type(self):
        """Test retry decision based on error type."""
        handler = ErrorHandler()

        # Network errors should be retryable
        assert handler._should_retry(ErrorType.NETWORK) is True

        # Rate limit errors should be retryable
        assert handler._should_retry(ErrorType.RATE_LIMIT) is True

        # CAPTCHA errors should not be retryable
        assert handler._should_retry(ErrorType.CAPTCHA) is False

        # Blocked errors should not be retryable
        assert handler._should_retry(ErrorType.BLOCKED) is False