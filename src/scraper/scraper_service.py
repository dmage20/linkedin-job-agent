"""Integration service for LinkedIn scraper with database operations."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict
from sqlalchemy.orm import Session
from urllib.parse import urlparse

from src.scraper.linkedin_scraper import LinkedInScraper
from src.scraper.error_handler import ErrorHandler
from src.config.search_config import SearchConfig
from src.database.models import JobModel
from src.database.repository import JobRepository


class ScraperService:
    """Service that integrates LinkedIn scraper with database operations."""

    def __init__(self, config: SearchConfig, session: Session):
        """Initialize scraper service with configuration and database session."""
        self.config = config
        self.session = session
        self.repository = JobRepository(session)
        self.scraper = LinkedInScraper(config)
        self.error_handler = ErrorHandler(
            max_retries=config.scraping_limits.max_retries,
            initial_delay=config.scraping_limits.retry_delay_seconds
        )

        self.logger = logging.getLogger(__name__)
        self._session_active = False
        self._session_start_time = None
        self._last_session_stats = {}

    async def scrape_and_save_jobs(self, max_jobs: int = 50) -> Dict[str, Any]:
        """Complete workflow: scrape jobs and save to database."""
        if self._session_active:
            raise Exception("Scraping session already active")

        self._session_active = True
        self._session_start_time = datetime.now()

        stats = {
            'jobs_scraped': 0,
            'jobs_saved': 0,
            'duplicates_skipped': 0,
            'validation_failures': 0,
            'errors': []
        }

        try:
            self.logger.info(f"Starting scraping session for max {max_jobs} jobs")

            # Use error handler for resilient scraping
            async def scraping_operation():
                return await self.scraper.scrape_jobs(max_jobs=max_jobs)

            scraped_jobs = await self.error_handler.handle_with_retry(scraping_operation)
            stats['jobs_scraped'] = len(scraped_jobs)

            self.logger.info(f"Scraped {len(scraped_jobs)} jobs")

            # Process and save each job
            for job_data in scraped_jobs:
                try:
                    if self._validate_job_data(job_data):
                        # Check for duplicates
                        existing_job = self.repository.get_job_by_linkedin_id(
                            job_data['linkedin_job_id']
                        )

                        if existing_job:
                            stats['duplicates_skipped'] += 1
                            self.logger.debug(f"Skipping duplicate job: {job_data['linkedin_job_id']}")
                            continue

                        # Convert to JobModel and save
                        job_model = self._convert_to_job_model(job_data)
                        self.repository.save_job(job_model)
                        stats['jobs_saved'] += 1

                        self.logger.debug(f"Saved job: {job_model.title} at {job_model.company}")

                    else:
                        stats['validation_failures'] += 1
                        self.logger.warning(f"Job data validation failed: {job_data.get('title', 'Unknown')}")

                except Exception as e:
                    stats['errors'].append(str(e))
                    self.logger.error(f"Error processing job: {e}")

            # Commit all changes
            self.session.commit()

            self.logger.info(f"Session complete: {stats['jobs_saved']} jobs saved, "
                           f"{stats['duplicates_skipped']} duplicates skipped")

        except Exception as e:
            self.session.rollback()
            error_msg = f"Scraping session failed: {e}"
            self.logger.error(error_msg)
            stats['error'] = error_msg

        finally:
            self._session_active = False
            self._record_session_stats(stats)

        return stats

    def _validate_job_data(self, job_data: Dict[str, Any]) -> bool:
        """Validate job data before saving to database."""
        required_fields = ['title', 'company', 'location', 'description', 'url', 'linkedin_job_id']

        # Check required fields
        for field in required_fields:
            if not job_data.get(field) or str(job_data[field]).strip() == '':
                self.logger.warning(f"Missing or empty required field: {field}")
                return False

        # Validate URL format
        try:
            parsed_url = urlparse(job_data['url'])
            if not parsed_url.scheme or not parsed_url.netloc:
                self.logger.warning(f"Invalid URL format: {job_data['url']}")
                return False
        except Exception:
            return False

        # Validate LinkedIn job ID format
        linkedin_id = job_data['linkedin_job_id']
        if not isinstance(linkedin_id, str) or len(linkedin_id) == 0:
            self.logger.warning(f"Invalid LinkedIn job ID: {linkedin_id}")
            return False

        # Validate salary range if provided
        salary_min = job_data.get('salary_min')
        salary_max = job_data.get('salary_max')
        if salary_min and salary_max and salary_min > salary_max:
            self.logger.warning("Invalid salary range: min > max")
            return False

        return True

    def _convert_to_job_model(self, job_data: Dict[str, Any]) -> JobModel:
        """Convert scraped job data to JobModel with enrichment."""
        # Basic required fields
        job_model = JobModel(
            title=job_data['title'].strip(),
            company=job_data['company'].strip(),
            location=job_data['location'].strip(),
            description=job_data['description'].strip(),
            url=job_data['url'].strip(),
            linkedin_job_id=job_data['linkedin_job_id'].strip()
        )

        # Optional fields
        if job_data.get('employment_type'):
            job_model.employment_type = job_data['employment_type']

        if job_data.get('experience_level'):
            job_model.experience_level = job_data['experience_level']

        if job_data.get('industry'):
            job_model.industry = job_data['industry']

        if job_data.get('salary_min') is not None:
            job_model.salary_min = int(job_data['salary_min'])

        if job_data.get('salary_max') is not None:
            job_model.salary_max = int(job_data['salary_max'])

        if job_data.get('salary_currency'):
            job_model.salary_currency = job_data['salary_currency']

        if job_data.get('is_remote'):
            job_model.is_remote = job_data['is_remote']

        if job_data.get('company_size'):
            job_model.company_size = job_data['company_size']

        if job_data.get('applicant_count') is not None:
            job_model.applicant_count = int(job_data['applicant_count'])

        if job_data.get('date_posted'):
            if isinstance(job_data['date_posted'], str):
                try:
                    job_model.date_posted = datetime.fromisoformat(job_data['date_posted'])
                except ValueError:
                    pass
            elif isinstance(job_data['date_posted'], datetime):
                job_model.date_posted = job_data['date_posted']

        return job_model

    def get_scraping_statistics(self) -> Dict[str, Any]:
        """Get comprehensive scraping and database statistics."""
        stats = {}

        # Database statistics
        total_jobs = self.repository.get_total_job_count()
        stats['total_jobs'] = total_jobs

        if total_jobs > 0:
            # Jobs by location
            jobs_by_location = defaultdict(int)
            all_jobs = self.repository.get_all_jobs()
            for job in all_jobs:
                jobs_by_location[job.location] += 1
            stats['jobs_by_location'] = dict(jobs_by_location)

            # Jobs by company
            jobs_by_company = defaultdict(int)
            for job in all_jobs:
                jobs_by_company[job.company] += 1
            stats['jobs_by_company'] = dict(sorted(jobs_by_company.items(),
                                                  key=lambda x: x[1], reverse=True)[:10])

            # Recent jobs
            recent_jobs = self.repository.get_recent_jobs(limit=5)
            stats['most_recent_job'] = recent_jobs[0].created_at if recent_jobs else None

            # Oldest job
            oldest_jobs = self.repository.get_jobs_by_date_range(limit=1, ascending=True)
            stats['oldest_job'] = oldest_jobs[0].created_at if oldest_jobs else None

            # Salary statistics
            salary_stats = self._calculate_salary_statistics(all_jobs)
            stats.update(salary_stats)

        # Error handler statistics
        error_summary = self.error_handler.get_error_summary()
        stats['error_statistics'] = error_summary

        return stats

    def _calculate_salary_statistics(self, jobs: List[JobModel]) -> Dict[str, Any]:
        """Calculate salary-related statistics."""
        salaries_min = [job.salary_min for job in jobs if job.salary_min is not None]
        salaries_max = [job.salary_max for job in jobs if job.salary_max is not None]

        stats = {}

        if salaries_min:
            stats['avg_salary_min'] = sum(salaries_min) / len(salaries_min)
            stats['min_salary_min'] = min(salaries_min)
            stats['max_salary_min'] = max(salaries_min)

        if salaries_max:
            stats['avg_salary_max'] = sum(salaries_max) / len(salaries_max)
            stats['min_salary_max'] = min(salaries_max)
            stats['max_salary_max'] = max(salaries_max)

        # Remote work statistics
        remote_jobs = len([job for job in jobs if job.is_remote == 'Remote'])
        hybrid_jobs = len([job for job in jobs if job.is_remote == 'Hybrid'])
        onsite_jobs = len([job for job in jobs if job.is_remote == 'On-site'])

        stats['remote_work_distribution'] = {
            'remote': remote_jobs,
            'hybrid': hybrid_jobs,
            'onsite': onsite_jobs
        }

        return stats

    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics."""
        stats = {
            'session_active': self._session_active,
            'session_start_time': self._session_start_time
        }

        if self._session_active and self._session_start_time:
            elapsed = datetime.now() - self._session_start_time
            stats['session_duration'] = elapsed.total_seconds()

        if self._last_session_stats:
            stats.update(self._last_session_stats)

        return stats

    def _record_session_stats(self, session_stats: Dict[str, Any]):
        """Record statistics from completed session."""
        if self._session_start_time:
            duration = datetime.now() - self._session_start_time
            self._last_session_stats = {
                'last_session_duration': duration.total_seconds(),
                'last_session_completed': datetime.now(),
                'last_session_stats': session_stats
            }

    async def cleanup(self):
        """Cleanup resources and connections."""
        try:
            if hasattr(self.scraper, 'stop'):
                await self.scraper.stop()
        except Exception as e:
            self.logger.error(f"Error during scraper cleanup: {e}")

        self._session_active = False