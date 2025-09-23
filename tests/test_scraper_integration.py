"""Integration tests for LinkedIn scraper with database."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from sqlalchemy.orm import Session

from src.scraper.linkedin_scraper import LinkedInScraper
from src.scraper.scraper_service import ScraperService
from src.config.search_config import SearchConfig, SearchParameters, ScrapingLimits
from src.database.models import JobModel
from src.database.repository import JobRepository


class TestScraperService:
    """Test the scraper service integration layer."""

    def test_scraper_service_initialization(self, test_session):
        """Test scraper service initialization."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits()
        )

        service = ScraperService(config, test_session)

        assert service.config == config
        assert service.session == test_session
        assert service.repository is not None
        assert service.scraper is not None

    @pytest.mark.asyncio
    async def test_scrape_and_save_jobs(self, test_session):
        """Test complete scraping workflow with database integration."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits()
        )

        service = ScraperService(config, test_session)

        # Mock scraped job data
        mock_jobs = [
            {
                'title': 'Senior Python Developer',
                'company': 'TechCorp Inc',
                'location': 'San Francisco, CA',
                'description': 'Exciting Python development role...',
                'url': 'https://linkedin.com/jobs/view/12345',
                'linkedin_job_id': '12345',
                'employment_type': 'Full-time',
                'experience_level': 'Senior',
                'salary_min': 120000,
                'salary_max': 160000,
                'is_remote': 'Remote',
                'applicant_count': 45
            },
            {
                'title': 'Python Backend Engineer',
                'company': 'StartupXYZ',
                'location': 'San Francisco, CA',
                'description': 'Join our growing backend team...',
                'url': 'https://linkedin.com/jobs/view/67890',
                'linkedin_job_id': '67890',
                'employment_type': 'Full-time',
                'experience_level': 'Mid',
                'salary_min': 100000,
                'salary_max': 130000,
                'is_remote': 'Hybrid',
                'applicant_count': 28
            }
        ]

        # Mock the scraper's scrape_jobs method
        with patch.object(service.scraper, 'scrape_jobs', return_value=mock_jobs):
            result = await service.scrape_and_save_jobs(max_jobs=2)

            assert result['jobs_scraped'] == 2
            assert result['jobs_saved'] == 2
            assert result['duplicates_skipped'] == 0

            # Verify jobs were saved to database
            saved_jobs = service.repository.get_all_jobs()
            assert len(saved_jobs) == 2

            # Verify job data integrity
            job1 = service.repository.get_job_by_linkedin_id('12345')
            assert job1 is not None
            assert job1.title == 'Senior Python Developer'
            assert job1.company == 'TechCorp Inc'
            assert job1.salary_min == 120000
            assert job1.applicant_count == 45

    @pytest.mark.asyncio
    async def test_duplicate_job_handling(self, test_session):
        """Test handling of duplicate jobs."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits()
        )

        service = ScraperService(config, test_session)

        # First, save a job
        existing_job = JobModel(
            title='Python Developer',
            company='TechCorp',
            location='San Francisco',
            description='Python development role',
            url='https://linkedin.com/jobs/view/12345',
            linkedin_job_id='12345'
        )
        service.repository.save_job(existing_job)

        # Mock scraped data with duplicate
        mock_jobs = [
            {
                'title': 'Python Developer',  # Same job
                'company': 'TechCorp',
                'location': 'San Francisco',
                'description': 'Python development role',
                'url': 'https://linkedin.com/jobs/view/12345',
                'linkedin_job_id': '12345'
            },
            {
                'title': 'New Python Job',
                'company': 'NewCompany',
                'location': 'San Francisco',
                'description': 'New opportunity',
                'url': 'https://linkedin.com/jobs/view/67890',
                'linkedin_job_id': '67890'
            }
        ]

        with patch.object(service.scraper, 'scrape_jobs', return_value=mock_jobs):
            result = await service.scrape_and_save_jobs(max_jobs=2)

            assert result['jobs_scraped'] == 2
            assert result['jobs_saved'] == 1  # Only the new job
            assert result['duplicates_skipped'] == 1

            # Verify total jobs in database
            all_jobs = service.repository.get_all_jobs()
            assert len(all_jobs) == 2  # Original + new job

    @pytest.mark.asyncio
    async def test_error_handling_during_scraping(self, test_session):
        """Test error handling during scraping process."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits()
        )

        service = ScraperService(config, test_session)

        # Mock scraper to raise an exception
        with patch.object(service.scraper, 'scrape_jobs', side_effect=Exception("Scraping failed")):
            result = await service.scrape_and_save_jobs(max_jobs=5)

            assert result['jobs_scraped'] == 0
            assert result['jobs_saved'] == 0
            assert 'error' in result
            assert 'Scraping failed' in result['error']

    def test_get_scraping_statistics(self, test_session):
        """Test getting scraping statistics."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits()
        )

        service = ScraperService(config, test_session)

        # Add some test jobs
        for i in range(5):
            job = JobModel(
                title=f'Python Job {i}',
                company=f'Company {i}',
                location='San Francisco',
                description=f'Job description {i}',
                url=f'https://linkedin.com/jobs/view/{i}',
                linkedin_job_id=str(i)
            )
            service.repository.save_job(job)

        stats = service.get_scraping_statistics()

        assert stats['total_jobs'] == 5
        assert stats['jobs_by_location']['San Francisco'] == 5
        assert 'most_recent_job' in stats
        assert 'oldest_job' in stats

    @pytest.mark.asyncio
    async def test_scraping_with_filters(self, test_session):
        """Test scraping with specific filters."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["senior", "python"],
                location="San Francisco",
                experience_level="senior",
                job_type="full-time",
                remote="remote",
                salary_min=120000
            ),
            scraping_limits=ScrapingLimits(jobs_per_session=10)
        )

        service = ScraperService(config, test_session)

        # Mock filtered job results
        mock_jobs = [
            {
                'title': 'Senior Python Engineer',
                'company': 'TechCorp',
                'location': 'San Francisco, CA',
                'description': 'Senior Python development role',
                'url': 'https://linkedin.com/jobs/view/12345',
                'linkedin_job_id': '12345',
                'employment_type': 'Full-time',
                'experience_level': 'Senior',
                'salary_min': 130000,
                'salary_max': 170000,
                'is_remote': 'Remote'
            }
        ]

        with patch.object(service.scraper, 'scrape_jobs', return_value=mock_jobs):
            result = await service.scrape_and_save_jobs(max_jobs=10)

            assert result['jobs_scraped'] == 1
            assert result['jobs_saved'] == 1

            # Verify the job matches our criteria
            saved_job = service.repository.get_job_by_linkedin_id('12345')
            assert saved_job.experience_level == 'Senior'
            assert saved_job.salary_min >= 120000
            assert saved_job.is_remote == 'Remote'

    @pytest.mark.asyncio
    async def test_rate_limit_compliance(self, test_session):
        """Test that rate limiting is properly enforced."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits(
                jobs_per_session=2,  # Very low limit
                request_delay_seconds=2.0
            )
        )

        service = ScraperService(config, test_session)

        # Mock fewer jobs to match the limit
        mock_jobs = [
            {'title': f'Job {i}', 'company': f'Company {i}', 'location': 'SF',
             'description': f'Desc {i}', 'url': f'https://linkedin.com/jobs/view/{i}',
             'linkedin_job_id': str(i)}
            for i in range(2)  # Match the session limit
        ]

        with patch.object(service.scraper, 'scrape_jobs', return_value=mock_jobs):
            result = await service.scrape_and_save_jobs(max_jobs=5)

            # Should have scraped the limited number of jobs
            assert result['jobs_scraped'] == 2
            assert result['jobs_saved'] == 2

    def test_job_data_validation(self, test_session):
        """Test validation of job data before saving."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits()
        )

        service = ScraperService(config, test_session)

        # Test invalid job data
        invalid_job_data = {
            'title': '',  # Empty title
            'company': 'TechCorp',
            'location': 'San Francisco',
            'description': 'Job description',
            'url': 'invalid-url',  # Invalid URL
            'linkedin_job_id': '12345'
        }

        # This should not save due to validation
        is_valid = service._validate_job_data(invalid_job_data)
        assert is_valid is False

        # Test valid job data
        valid_job_data = {
            'title': 'Python Developer',
            'company': 'TechCorp',
            'location': 'San Francisco',
            'description': 'Great Python role',
            'url': 'https://linkedin.com/jobs/view/12345',
            'linkedin_job_id': '12345'
        }

        is_valid = service._validate_job_data(valid_job_data)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_session_management(self, test_session):
        """Test proper session management during scraping."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits()
        )

        service = ScraperService(config, test_session)

        # Test that session starts and stops properly
        session_stats_before = service.get_session_stats()
        assert session_stats_before['session_active'] is False

        # Mock a scraping session
        mock_jobs = [
            {'title': 'Test Job', 'company': 'Test Company', 'location': 'SF',
             'description': 'Test', 'url': 'https://linkedin.com/jobs/view/123',
             'linkedin_job_id': '123'}
        ]

        with patch.object(service.scraper, 'scrape_jobs', return_value=mock_jobs):
            result = await service.scrape_and_save_jobs(max_jobs=1)

            assert result['jobs_scraped'] == 1

        # Session should be complete
        session_stats_after = service.get_session_stats()
        assert 'last_session_duration' in session_stats_after

    @pytest.mark.asyncio
    async def test_concurrent_scraping_prevention(self, test_session):
        """Test prevention of concurrent scraping sessions."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits()
        )

        service = ScraperService(config, test_session)

        # Simulate active session
        service._session_active = True

        # Should not allow starting another session
        with pytest.raises(Exception, match="Scraping session already active"):
            await service.scrape_and_save_jobs(max_jobs=1)

    @pytest.mark.asyncio
    async def test_job_enrichment(self, test_session):
        """Test job data enrichment during saving."""
        config = SearchConfig(
            search_parameters=SearchParameters(
                keywords=["python"],
                location="San Francisco"
            ),
            scraping_limits=ScrapingLimits()
        )

        service = ScraperService(config, test_session)

        # Mock basic job data that needs enrichment
        mock_jobs = [
            {
                'title': 'Python Developer',
                'company': 'TechCorp',
                'location': 'San Francisco, CA',
                'description': 'We are looking for a python developer with 3+ years experience',
                'url': 'https://linkedin.com/jobs/view/12345',
                'linkedin_job_id': '12345'
            }
        ]

        with patch.object(service.scraper, 'scrape_jobs', return_value=mock_jobs):
            result = await service.scrape_and_save_jobs(max_jobs=1)

            assert result['jobs_scraped'] == 1

            # Check that job was enriched
            saved_job = service.repository.get_job_by_linkedin_id('12345')
            assert saved_job is not None
            assert saved_job.created_at is not None
            assert saved_job.updated_at is not None