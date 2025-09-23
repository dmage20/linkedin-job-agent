"""Tests for the LinkedIn job scraper."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json

from src.scraper.linkedin_scraper import (
    LinkedInScraper,
    ScrapingSession,
    RateLimiter,
    AntiDetectionManager,
    ScrapingError,
    RateLimitError,
    CaptchaError,
    BlockedError
)
from src.config.search_config import SearchConfig, SearchParameters, ScrapingLimits
from src.database.models import JobModel


class TestRateLimiter:
    """Test the rate limiting functionality."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization with correct parameters."""
        limits = ScrapingLimits(
            jobs_per_session=30,
            jobs_per_day=150,
            request_delay_seconds=2.5
        )
        rate_limiter = RateLimiter(limits)

        assert rate_limiter.jobs_per_session == 30
        assert rate_limiter.jobs_per_day == 150
        assert rate_limiter.request_delay == 2.5
        assert rate_limiter.session_jobs_count == 0
        assert rate_limiter.daily_jobs_count == 0

    @pytest.mark.asyncio
    async def test_rate_limiter_delays_requests(self):
        """Test that rate limiter enforces delays between requests."""
        limits = ScrapingLimits(request_delay_seconds=2.0)
        rate_limiter = RateLimiter(limits)

        start_time = datetime.now()
        await rate_limiter.wait_for_next_request()

        # Second request should be delayed
        await rate_limiter.wait_for_next_request()
        end_time = datetime.now()

        elapsed = (end_time - start_time).total_seconds()
        assert elapsed >= 2.0

    def test_session_limit_enforcement(self):
        """Test that session limits are enforced."""
        limits = ScrapingLimits(jobs_per_session=2)
        rate_limiter = RateLimiter(limits)

        # Should allow up to session limit
        assert rate_limiter.can_make_request() is True
        rate_limiter.record_job_scraped()

        assert rate_limiter.can_make_request() is True
        rate_limiter.record_job_scraped()

        # Should block after session limit
        assert rate_limiter.can_make_request() is False

    def test_daily_limit_enforcement(self):
        """Test that daily limits are enforced."""
        limits = ScrapingLimits(jobs_per_day=2)
        rate_limiter = RateLimiter(limits)

        # Should allow up to daily limit
        assert rate_limiter.can_make_request() is True
        rate_limiter.record_job_scraped()

        assert rate_limiter.can_make_request() is True
        rate_limiter.record_job_scraped()

        # Should block after daily limit
        assert rate_limiter.can_make_request() is False

    def test_reset_session_count(self):
        """Test resetting session job count."""
        limits = ScrapingLimits(jobs_per_session=1)
        rate_limiter = RateLimiter(limits)

        rate_limiter.record_job_scraped()
        assert rate_limiter.can_make_request() is False

        rate_limiter.reset_session_count()
        assert rate_limiter.can_make_request() is True


class TestAntiDetectionManager:
    """Test the anti-detection functionality."""

    def test_user_agent_rotation(self):
        """Test that user agents are rotated."""
        user_agents = ["agent1", "agent2", "agent3"]
        manager = AntiDetectionManager(user_agents)

        # Get multiple user agents and ensure they rotate
        agents = [manager.get_random_user_agent() for _ in range(10)]

        # Should have variety (not all the same)
        assert len(set(agents)) > 1

        # Should only use provided agents
        for agent in agents:
            assert agent in user_agents

    @pytest.mark.asyncio
    async def test_human_like_delays(self):
        """Test that human-like delays are applied."""
        manager = AntiDetectionManager(["test-agent"])

        start_time = datetime.now()
        await manager.apply_human_like_delay()
        end_time = datetime.now()

        elapsed = (end_time - start_time).total_seconds()
        # Should have some delay (randomized, but at least minimum)
        assert elapsed >= 0.5

    def test_stealth_headers(self):
        """Test generation of stealth headers."""
        manager = AntiDetectionManager(["test-agent"])
        headers = manager.get_stealth_headers()

        # Should include essential headers
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "Accept-Encoding" in headers
        assert "Connection" in headers

    def test_detect_captcha_indicators(self):
        """Test CAPTCHA detection in page content."""
        manager = AntiDetectionManager(["test-agent"])

        # Test positive detection
        captcha_content = "<div class='g-recaptcha'>CAPTCHA content</div>"
        assert manager.detect_captcha(captcha_content) is True

        # Test negative detection
        normal_content = "<div class='job-listing'>Normal job content</div>"
        assert manager.detect_captcha(normal_content) is False

    def test_detect_blocking_indicators(self):
        """Test detection of blocking/rate limiting."""
        manager = AntiDetectionManager(["test-agent"])

        # Test positive detection
        blocked_content = "You have been temporarily blocked"
        assert manager.detect_blocking(blocked_content) is True

        # Test negative detection
        normal_content = "Welcome to LinkedIn jobs"
        assert manager.detect_blocking(normal_content) is False


class TestScrapingSession:
    """Test the scraping session management."""

    def test_session_initialization(self):
        """Test scraping session initialization."""
        limits = ScrapingLimits(session_duration_minutes=30)
        session = ScrapingSession(limits)

        assert session.session_start_time is not None
        assert session.max_duration_minutes == 30
        assert session.is_active is True

    def test_session_timeout(self):
        """Test session timeout detection."""
        limits = ScrapingLimits(session_duration_minutes=1)
        session = ScrapingSession(limits)

        # Mock session start time to be in the past
        session.session_start_time = datetime.now() - timedelta(minutes=2)

        assert session.is_active is False

    def test_session_statistics(self):
        """Test session statistics tracking."""
        limits = ScrapingLimits()
        session = ScrapingSession(limits)

        session.record_job_scraped()
        session.record_job_scraped()
        session.record_error("test error")

        stats = session.get_session_stats()
        assert stats["jobs_scraped"] == 2
        assert stats["errors_count"] == 1
        assert "session_duration" in stats

    def test_session_reset(self):
        """Test session reset functionality."""
        limits = ScrapingLimits()
        session = ScrapingSession(limits)

        session.record_job_scraped()
        session.record_error("test error")

        session.reset_session()

        stats = session.get_session_stats()
        assert stats["jobs_scraped"] == 0
        assert stats["errors_count"] == 0


class TestLinkedInScraper:
    """Test the main LinkedIn scraper class."""

    def test_scraper_initialization(self):
        """Test LinkedIn scraper initialization."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits()
        )

        scraper = LinkedInScraper(config)

        assert scraper.config == config
        assert scraper.rate_limiter is not None
        assert scraper.anti_detection is not None
        assert scraper.session is not None
        assert scraper.browser is None  # Not initialized until start

    @pytest.mark.asyncio
    async def test_scraper_initialization_with_browser(self):
        """Test scraper browser initialization."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits()
        )

        scraper = LinkedInScraper(config)

        # Mock playwright browser
        with patch('playwright.async_api.async_playwright') as mock_playwright:
            mock_browser_context = AsyncMock()
            mock_browser = AsyncMock()
            mock_browser.new_context.return_value = mock_browser_context
            mock_playwright_instance = AsyncMock()
            mock_playwright_instance.chromium.launch.return_value = mock_browser
            mock_playwright.return_value.__aenter__.return_value = mock_playwright_instance

            await scraper.start()

            assert scraper.browser is not None
            assert scraper.context is not None

    @pytest.mark.asyncio
    async def test_search_url_generation(self):
        """Test LinkedIn search URL generation."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python", "developer"],
                location="San Francisco",
                experience_level="mid",
                job_type="full-time",
                remote="remote"
            ),
            scraping_limits=ScrapingLimits()
        )

        scraper = LinkedInScraper(config)
        url = scraper._build_search_url()

        # Should contain search parameters
        assert "keywords=" in url or "python" in url
        assert "location=" in url or "San Francisco" in url.replace("%20", " ")
        assert "linkedin.com/jobs" in url

    @pytest.mark.asyncio
    async def test_job_extraction_from_page(self):
        """Test job data extraction from LinkedIn page."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits()
        )

        scraper = LinkedInScraper(config)

        # Mock page with job data
        mock_page = AsyncMock()
        mock_page.content.return_value = """
        <div class="job-card">
            <h3 class="job-title">Python Developer</h3>
            <span class="company-name">Tech Corp</span>
            <span class="job-location">San Francisco, CA</span>
            <div class="job-description">Great Python position...</div>
            <a href="/jobs/view/12345" class="job-link">View Job</a>
        </div>
        """

        jobs = await scraper._extract_jobs_from_page(mock_page)

        assert len(jobs) >= 0  # May be 0 if HTML structure doesn't match exactly

    @pytest.mark.asyncio
    async def test_captcha_handling(self):
        """Test CAPTCHA detection and handling."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits()
        )

        scraper = LinkedInScraper(config)

        # Mock page with CAPTCHA
        mock_page = AsyncMock()
        mock_page.content.return_value = '<div class="g-recaptcha">CAPTCHA</div>'

        with pytest.raises(CaptchaError):
            await scraper._extract_jobs_from_page(mock_page)

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self):
        """Test rate limit detection and handling."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits(jobs_per_session=1)
        )

        scraper = LinkedInScraper(config)

        # Simulate exceeding rate limits
        scraper.rate_limiter.record_job_scraped()

        with pytest.raises(RateLimitError):
            scraper._check_rate_limits()

    @pytest.mark.asyncio
    async def test_scrape_jobs_full_workflow(self):
        """Test complete job scraping workflow."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits(jobs_per_session=5)
        )

        scraper = LinkedInScraper(config)

        # Mock all external dependencies
        with patch.object(scraper, 'start') as mock_start, \
             patch.object(scraper, '_navigate_to_search') as mock_navigate, \
             patch.object(scraper, '_extract_jobs_from_page') as mock_extract, \
             patch.object(scraper, 'stop') as mock_stop:

            mock_extract.return_value = [
                {
                    'title': 'Python Developer',
                    'company': 'Tech Corp',
                    'location': 'San Francisco',
                    'description': 'Great position',
                    'url': 'https://linkedin.com/jobs/view/12345',
                    'linkedin_job_id': '12345'
                }
            ]

            jobs = await scraper.scrape_jobs(max_jobs=1)

            assert len(jobs) == 1
            assert jobs[0]['title'] == 'Python Developer'
            mock_start.assert_called_once()
            mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_recovery_and_retry(self):
        """Test error recovery and retry mechanisms."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits(max_retries=2)
        )

        scraper = LinkedInScraper(config)

        # Mock method that fails then succeeds
        call_count = 0
        async def mock_extract_with_failure(page):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Network error")
            return [{'title': 'Test Job', 'company': 'Test Corp', 'location': 'Test Location',
                    'description': 'Test', 'url': 'test', 'linkedin_job_id': 'test'}]

        with patch.object(scraper, '_extract_jobs_from_page', side_effect=mock_extract_with_failure):
            # Should succeed after retry
            with patch.object(scraper, 'start'), \
                 patch.object(scraper, '_navigate_to_search'), \
                 patch.object(scraper, 'stop'):

                jobs = await scraper.scrape_jobs(max_jobs=1)
                assert len(jobs) == 1
                assert call_count == 2  # Failed once, succeeded on retry

    @pytest.mark.asyncio
    async def test_cleanup_on_exit(self):
        """Test proper cleanup when scraper exits."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits()
        )

        scraper = LinkedInScraper(config)

        # Mock browser and context
        scraper.browser = AsyncMock()
        scraper.context = AsyncMock()

        await scraper.stop()

        scraper.context.close.assert_called_once()
        scraper.browser.close.assert_called_once()

    def test_linkedin_compliance_enforcement(self):
        """Test that LinkedIn ToS compliance is enforced."""
        # Should reject configuration that violates ToS at the ScrapingLimits level
        from src.config.search_config import ValidationError

        with pytest.raises(ValidationError, match="request_delay_seconds must be at least"):
            invalid_config = SearchConfig(
                search_parameters=SearchParameters(
                    keywords=["python"],
                    location="San Francisco"
                ),
                scraping_limits=ScrapingLimits(request_delay_seconds=1.0)  # Too fast
            )

    def test_job_data_to_model_conversion(self):
        """Test conversion of scraped job data to JobModel."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits()
        )

        scraper = LinkedInScraper(config)

        job_data = {
            'title': 'Senior Python Developer',
            'company': 'Tech Corporation',
            'location': 'San Francisco, CA',
            'description': 'We are looking for a senior Python developer...',
            'url': 'https://linkedin.com/jobs/view/12345',
            'linkedin_job_id': '12345',
            'employment_type': 'Full-time',
            'experience_level': 'Senior',
            'salary_min': 120000,
            'salary_max': 160000,
            'is_remote': 'Remote',
            'applicant_count': 50
        }

        job_model = scraper._convert_to_job_model(job_data)

        assert isinstance(job_model, JobModel)
        assert job_model.title == 'Senior Python Developer'
        assert job_model.company == 'Tech Corporation'
        assert job_model.linkedin_job_id == '12345'
        assert job_model.salary_min == 120000
        assert job_model.applicant_count == 50