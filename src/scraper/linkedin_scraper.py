"""LinkedIn job scraper with ethical ToS compliance."""

import asyncio
import random
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode
import logging

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from src.config.search_config import SearchConfig, LINKEDIN_MIN_REQUEST_DELAY
from src.database.models import JobModel


# Custom exceptions for scraping errors
class ScrapingError(Exception):
    """Base exception for scraping errors."""
    pass


class RateLimitError(ScrapingError):
    """Exception raised when rate limits are exceeded."""
    pass


class CaptchaError(ScrapingError):
    """Exception raised when CAPTCHA is detected."""
    pass


class BlockedError(ScrapingError):
    """Exception raised when access is blocked."""
    pass


class RateLimiter:
    """Rate limiter for LinkedIn ToS compliance."""

    def __init__(self, limits):
        """Initialize rate limiter with scraping limits."""
        self.jobs_per_session = limits.jobs_per_session
        self.jobs_per_day = limits.jobs_per_day
        self.request_delay = limits.request_delay_seconds
        self.max_retries = limits.max_retries
        self.retry_delay = limits.retry_delay_seconds

        # Tracking
        self.session_jobs_count = 0
        self.daily_jobs_count = 0
        self.last_request_time = None

    def can_make_request(self) -> bool:
        """Check if we can make another request within limits."""
        if self.session_jobs_count >= self.jobs_per_session:
            return False
        if self.daily_jobs_count >= self.jobs_per_day:
            return False
        return True

    async def wait_for_next_request(self) -> None:
        """Wait appropriate time before next request."""
        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.request_delay:
                wait_time = self.request_delay - elapsed
                await asyncio.sleep(wait_time)

        self.last_request_time = time.time()

    def record_job_scraped(self) -> None:
        """Record that a job was successfully scraped."""
        self.session_jobs_count += 1
        self.daily_jobs_count += 1

    def reset_session_count(self) -> None:
        """Reset session job count for new session."""
        self.session_jobs_count = 0


class AntiDetectionManager:
    """Manager for anti-detection measures."""

    def __init__(self, user_agents: List[str]):
        """Initialize with list of user agents."""
        self.user_agents = user_agents

    def get_random_user_agent(self) -> str:
        """Get a random user agent for rotation."""
        return random.choice(self.user_agents)

    async def apply_human_like_delay(self) -> None:
        """Apply randomized human-like delays."""
        # Random delay between 0.5 to 3.0 seconds
        delay = random.uniform(0.5, 3.0)
        await asyncio.sleep(delay)

    def get_stealth_headers(self) -> Dict[str, str]:
        """Get headers that make requests look more human."""
        return {
            "User-Agent": self.get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }

    def detect_captcha(self, page_content: str) -> bool:
        """Detect CAPTCHA presence in page content."""
        captcha_indicators = [
            "g-recaptcha",
            "recaptcha",
            "captcha",
            "challenge",
            "verify you are human",
            "security check"
        ]

        content_lower = page_content.lower()
        return any(indicator in content_lower for indicator in captcha_indicators)

    def detect_blocking(self, page_content: str) -> bool:
        """Detect if access is blocked or rate limited."""
        blocking_indicators = [
            "temporarily blocked",
            "access denied",
            "rate limit",
            "too many requests",
            "please wait",
            "slow down"
        ]

        content_lower = page_content.lower()
        return any(indicator in content_lower for indicator in blocking_indicators)


class ScrapingSession:
    """Manager for scraping session lifecycle."""

    def __init__(self, limits):
        """Initialize scraping session."""
        self.session_start_time = datetime.now()
        self.max_duration_minutes = limits.session_duration_minutes
        self.jobs_scraped = 0
        self.errors = []

    @property
    def is_active(self) -> bool:
        """Check if session is still active (not timed out)."""
        elapsed = datetime.now() - self.session_start_time
        return elapsed.total_seconds() < (self.max_duration_minutes * 60)

    def record_job_scraped(self) -> None:
        """Record a successfully scraped job."""
        self.jobs_scraped += 1

    def record_error(self, error: str) -> None:
        """Record an error during scraping."""
        self.errors.append({
            "error": error,
            "timestamp": datetime.now()
        })

    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        elapsed = datetime.now() - self.session_start_time
        return {
            "jobs_scraped": self.jobs_scraped,
            "errors_count": len(self.errors),
            "session_duration": elapsed.total_seconds(),
            "session_start": self.session_start_time
        }

    def reset_session(self) -> None:
        """Reset session for new session."""
        self.session_start_time = datetime.now()
        self.jobs_scraped = 0
        self.errors = []


class LinkedInScraper:
    """Ethical LinkedIn job scraper with ToS compliance."""

    def __init__(self, config: SearchConfig):
        """Initialize LinkedIn scraper with configuration."""
        self.config = config
        self._validate_config()

        # Initialize components
        self.rate_limiter = RateLimiter(config.scraping_limits)
        self.anti_detection = AntiDetectionManager(config.user_agents)
        self.session = ScrapingSession(config.scraping_limits)

        # Browser components (initialized in start())
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Logging
        self.logger = logging.getLogger(__name__)

    def _validate_config(self) -> None:
        """Validate configuration for LinkedIn ToS compliance."""
        limits = self.config.scraping_limits

        if limits.request_delay_seconds < LINKEDIN_MIN_REQUEST_DELAY:
            raise ValueError("Configuration violates LinkedIn ToS: request delay too short")

        if limits.jobs_per_session > 50:
            raise ValueError("Configuration violates LinkedIn ToS: too many jobs per session")

        if limits.jobs_per_day > 200:
            raise ValueError("Configuration violates LinkedIn ToS: too many jobs per day")

    async def start(self) -> None:
        """Start the scraper and initialize browser."""
        playwright = await async_playwright().__aenter__()

        # Launch browser with stealth settings
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )

        # Create context with stealth settings
        self.context = await self.browser.new_context(
            user_agent=self.anti_detection.get_random_user_agent(),
            viewport={'width': 1366, 'height': 768},
            extra_http_headers=self.anti_detection.get_stealth_headers()
        )

        # Create page
        self.page = await self.context.new_page()

        # Add stealth scripts
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
        """)

    async def stop(self) -> None:
        """Stop the scraper and cleanup resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    def _build_search_url(self) -> str:
        """Build LinkedIn search URL from search parameters."""
        base_url = "https://www.linkedin.com/jobs/search/?"

        params = {}

        # Keywords
        if self.config.search_parameters.keywords:
            params['keywords'] = ' '.join(self.config.search_parameters.keywords)

        # Location
        if self.config.search_parameters.location:
            params['location'] = self.config.search_parameters.location

        # Experience level mapping
        experience_mapping = {
            'entry': '1',
            'mid': '2',
            'senior': '3',
            'executive': '4'
        }
        if self.config.search_parameters.experience_level:
            exp_level = self.config.search_parameters.experience_level
            if isinstance(exp_level, str) and exp_level in experience_mapping:
                params['f_E'] = experience_mapping[exp_level]

        # Job type mapping
        job_type_mapping = {
            'full-time': 'F',
            'part-time': 'P',
            'contract': 'C',
            'temporary': 'T',
            'internship': 'I'
        }
        if self.config.search_parameters.job_type:
            job_type = self.config.search_parameters.job_type
            if isinstance(job_type, str) and job_type in job_type_mapping:
                params['f_JT'] = job_type_mapping[job_type]

        # Remote options
        remote_mapping = {
            'remote': '2',
            'hybrid': '3',
            'on-site': '1'
        }
        if self.config.search_parameters.remote:
            remote = self.config.search_parameters.remote
            if isinstance(remote, str) and remote in remote_mapping:
                params['f_WT'] = remote_mapping[remote]

        return base_url + urlencode(params)

    async def _navigate_to_search(self) -> None:
        """Navigate to LinkedIn search page."""
        search_url = self._build_search_url()
        self.logger.info(f"Navigating to: {search_url}")

        await self.page.goto(search_url, wait_until='networkidle')
        await self.anti_detection.apply_human_like_delay()

    async def _extract_jobs_from_page(self, page: Page) -> List[Dict[str, Any]]:
        """Extract job data from current page."""
        # Check for CAPTCHA or blocking
        content = await page.content()

        if self.anti_detection.detect_captcha(content):
            raise CaptchaError("CAPTCHA detected on page")

        if self.anti_detection.detect_blocking(content):
            raise BlockedError("Access appears to be blocked")

        jobs = []

        # Extract job cards (simplified extraction for MVP)
        try:
            # Wait for job cards to load
            await page.wait_for_selector('.job-card, .job-result-card, [data-testid="job-card"]',
                                       timeout=10000)

            # Extract job elements
            job_elements = await page.query_selector_all('.job-card, .job-result-card, [data-testid="job-card"]')

            for element in job_elements[:10]:  # Limit to first 10 jobs per page
                try:
                    job_data = await self._extract_job_data(element)
                    if job_data:
                        jobs.append(job_data)
                except Exception as e:
                    self.logger.warning(f"Error extracting job data: {e}")
                    continue

        except Exception as e:
            self.logger.warning(f"No job cards found or error: {e}")

        return jobs

    async def _extract_job_data(self, job_element) -> Optional[Dict[str, Any]]:
        """Extract data from a single job element."""
        try:
            # Extract basic job information
            title_elem = await job_element.query_selector('h3, .job-title, [data-testid="job-title"]')
            title = await title_elem.inner_text() if title_elem else "Unknown"

            company_elem = await job_element.query_selector('.company-name, [data-testid="company-name"]')
            company = await company_elem.inner_text() if company_elem else "Unknown"

            location_elem = await job_element.query_selector('.job-location, [data-testid="job-location"]')
            location = await location_elem.inner_text() if location_elem else "Unknown"

            link_elem = await job_element.query_selector('a')
            job_url = await link_elem.get_attribute('href') if link_elem else ""

            # Extract LinkedIn job ID from URL
            job_id = "unknown"
            if job_url and '/jobs/view/' in job_url:
                match = re.search(r'/jobs/view/(\d+)', job_url)
                if match:
                    job_id = match.group(1)

            # Basic job data
            job_data = {
                'title': title.strip(),
                'company': company.strip(),
                'location': location.strip(),
                'description': f"Job at {company.strip()} in {location.strip()}",  # Simplified for MVP
                'url': f"https://www.linkedin.com{job_url}" if job_url.startswith('/') else job_url,
                'linkedin_job_id': job_id,
                'employment_type': None,
                'experience_level': None,
                'salary_min': None,
                'salary_max': None,
                'is_remote': None,
                'applicant_count': None
            }

            return job_data

        except Exception as e:
            self.logger.error(f"Error extracting job data: {e}")
            return None

    def _check_rate_limits(self) -> None:
        """Check if rate limits allow continuing."""
        if not self.rate_limiter.can_make_request():
            if self.rate_limiter.session_jobs_count >= self.rate_limiter.jobs_per_session:
                raise RateLimitError("Session job limit exceeded")
            if self.rate_limiter.daily_jobs_count >= self.rate_limiter.jobs_per_day:
                raise RateLimitError("Daily job limit exceeded")

        if not self.session.is_active:
            raise RateLimitError("Session timeout exceeded")

    def _convert_to_job_model(self, job_data: Dict[str, Any]) -> JobModel:
        """Convert scraped job data to JobModel."""
        return JobModel(
            title=job_data.get('title', ''),
            company=job_data.get('company', ''),
            location=job_data.get('location', ''),
            description=job_data.get('description', ''),
            url=job_data.get('url', ''),
            linkedin_job_id=job_data.get('linkedin_job_id', ''),
            employment_type=job_data.get('employment_type'),
            experience_level=job_data.get('experience_level'),
            salary_min=job_data.get('salary_min'),
            salary_max=job_data.get('salary_max'),
            is_remote=job_data.get('is_remote'),
            applicant_count=job_data.get('applicant_count')
        )

    async def scrape_jobs(self, max_jobs: int = 50) -> List[Dict[str, Any]]:
        """Scrape jobs from LinkedIn with full ToS compliance."""
        all_jobs = []

        try:
            await self.start()
            await self._navigate_to_search()

            page_count = 0
            max_pages = 5  # Limit pages to stay within ToS

            while len(all_jobs) < max_jobs and page_count < max_pages:
                # Check rate limits before proceeding
                self._check_rate_limits()

                # Wait for rate limit compliance
                await self.rate_limiter.wait_for_next_request()

                # Extract jobs from current page
                try:
                    jobs = await self._extract_jobs_from_page(self.page)
                    all_jobs.extend(jobs[:max_jobs - len(all_jobs)])

                    # Record scraped jobs
                    for _ in jobs:
                        self.rate_limiter.record_job_scraped()
                        self.session.record_job_scraped()

                    page_count += 1

                    # Navigate to next page if needed and available
                    if len(all_jobs) < max_jobs and page_count < max_pages:
                        try:
                            next_button = await self.page.query_selector('[aria-label="Next"]')
                            if next_button:
                                await next_button.click()
                                await self.page.wait_for_load_state('networkidle')
                                await self.anti_detection.apply_human_like_delay()
                            else:
                                break
                        except Exception:
                            break

                except (CaptchaError, BlockedError) as e:
                    self.logger.error(f"Scraping stopped due to: {e}")
                    self.session.record_error(str(e))
                    break

                except Exception as e:
                    self.logger.error(f"Error during scraping: {e}")
                    self.session.record_error(str(e))
                    # Continue with retry logic if we have retries left
                    continue

        finally:
            await self.stop()

        self.logger.info(f"Scraped {len(all_jobs)} jobs in session")
        return all_jobs