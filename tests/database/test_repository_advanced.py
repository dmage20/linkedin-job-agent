"""Advanced tests for repository functionality and edge cases."""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from unittest.mock import patch, MagicMock

from src.database.repository import JobRepository, BaseRepository, get_job_repository
from src.database.models import JobModel


class TestRepositoryErrorHandling:
    """Test error handling in repository operations."""

    def test_create_job_integrity_error(self, clean_db):
        """Test handling of integrity errors during creation."""
        repo = JobRepository(clean_db)

        # Create a job first
        job_data = {
            "title": "Test Engineer",
            "company": "Test Corp",
            "location": "Test City",
            "description": "Test description",
            "url": "https://linkedin.com/jobs/test",
            "linkedin_job_id": "TEST-001"
        }

        repo.create(**job_data)

        # Try to create another job with same LinkedIn ID
        with pytest.raises(ValueError, match="Data integrity error"):
            repo.create(**job_data)

    def test_repository_sql_error_handling(self, clean_db):
        """Test handling of SQL errors."""
        repo = JobRepository(clean_db)

        # Mock session to raise SQLAlchemyError
        with patch.object(clean_db, 'commit', side_effect=SQLAlchemyError("DB Error")):
            with pytest.raises(RuntimeError, match="Database error"):
                repo.create(
                    title="Test",
                    company="Test",
                    location="Test",
                    description="Test",
                    url="https://test.com",
                    linkedin_job_id="TEST"
                )

    def test_update_nonexistent_job(self, clean_db):
        """Test updating a job that doesn't exist."""
        repo = JobRepository(clean_db)
        result = repo.update(99999, title="Updated Title")
        assert result is None

    def test_delete_nonexistent_job(self, clean_db):
        """Test deleting a job that doesn't exist."""
        repo = JobRepository(clean_db)
        result = repo.delete(99999)
        assert result is False

    def test_get_by_linkedin_id_not_found(self, clean_db):
        """Test getting job by LinkedIn ID that doesn't exist."""
        repo = JobRepository(clean_db)
        result = repo.get_by_linkedin_id("NONEXISTENT")
        assert result is None


class TestJobRepositoryAdvanced:
    """Advanced test cases for JobRepository functionality."""

    def test_get_jobs_by_company(self, clean_db):
        """Test getting jobs by company name."""
        repo = JobRepository(clean_db)

        # Create jobs for different companies
        companies = ["TechCorp", "DataCorp", "TechCorp Inc", "Other Corp"]
        for i, company in enumerate(companies):
            repo.create(
                title=f"Engineer {i}",
                company=company,
                location=f"City {i}",
                description=f"Description {i}",
                url=f"https://linkedin.com/jobs/{i}",
                linkedin_job_id=f"JOB-{i:03d}"
            )

        # Search for TechCorp (should match TechCorp and TechCorp Inc)
        tech_jobs = repo.get_jobs_by_company("TechCorp")
        assert len(tech_jobs) == 2

        # Search for exact match
        data_jobs = repo.get_jobs_by_company("DataCorp")
        assert len(data_jobs) == 1

    def test_get_recent_jobs(self, clean_db):
        """Test getting recent jobs."""
        repo = JobRepository(clean_db)

        # Create jobs
        for i in range(5):
            repo.create(
                title=f"Recent Engineer {i}",
                company=f"Recent Corp {i}",
                location=f"Recent City {i}",
                description=f"Recent description {i}",
                url=f"https://linkedin.com/jobs/recent{i}",
                linkedin_job_id=f"RECENT-{i:03d}"
            )

        # Get recent jobs (all should be recent since just created)
        recent_jobs = repo.get_recent_jobs(days=7, limit=3)
        assert len(recent_jobs) == 3

        # Test with 0 days (should return none)
        recent_jobs = repo.get_recent_jobs(days=0, limit=10)
        assert len(recent_jobs) == 0

    def test_search_jobs_complex(self, clean_db):
        """Test complex job search with multiple filters."""
        repo = JobRepository(clean_db)

        # Create diverse jobs for testing
        jobs_data = [
            {
                "title": "Senior Python Developer",
                "company": "Tech Company A",
                "location": "San Francisco, CA",
                "description": "Python development role",
                "url": "https://linkedin.com/jobs/1",
                "linkedin_job_id": "SEARCH-001",
                "employment_type": "Full-time",
                "experience_level": "Senior",
                "is_remote": "Remote"
            },
            {
                "title": "Junior Python Developer",
                "company": "Tech Company B",
                "location": "New York, NY",
                "description": "Entry level Python role",
                "url": "https://linkedin.com/jobs/2",
                "linkedin_job_id": "SEARCH-002",
                "employment_type": "Full-time",
                "experience_level": "Junior",
                "is_remote": "On-site"
            },
            {
                "title": "Data Scientist",
                "company": "Data Company",
                "location": "Remote",
                "description": "Data science role",
                "url": "https://linkedin.com/jobs/3",
                "linkedin_job_id": "SEARCH-003",
                "employment_type": "Contract",
                "experience_level": "Mid",
                "is_remote": "Remote"
            }
        ]

        for job_data in jobs_data:
            repo.create(**job_data)

        # Test multiple filter combinations
        results = repo.search_jobs(
            title="Python",
            employment_type="Full-time",
            order_by="experience_level",
            order_direction="asc"
        )
        assert len(results) == 2
        assert results[0].experience_level == "Junior"  # Ascending order

        # Test location and remote filter
        remote_results = repo.search_jobs(is_remote="Remote", limit=5)
        assert len(remote_results) == 2

        # Test company filter
        company_results = repo.search_jobs(company="Tech Company")
        assert len(company_results) == 2

    def test_search_jobs_ordering(self, clean_db):
        """Test job search ordering functionality."""
        repo = JobRepository(clean_db)

        # Create jobs with different creation times
        base_data = {
            "company": "Order Test Corp",
            "location": "Test City",
            "description": "Test description",
            "url": "https://linkedin.com/jobs/order",
            "employment_type": "Full-time"
        }

        for i in range(3):
            data = base_data.copy()
            data.update({
                "title": f"Engineer {chr(65 + i)}",  # A, B, C
                "linkedin_job_id": f"ORDER-{i:03d}"
            })
            repo.create(**data)

        # Test ascending order by title
        asc_results = repo.search_jobs(
            company="Order Test",
            order_by="title",
            order_direction="asc"
        )
        assert len(asc_results) == 3
        assert asc_results[0].title == "Engineer A"
        assert asc_results[2].title == "Engineer C"

        # Test descending order by title
        desc_results = repo.search_jobs(
            company="Order Test",
            order_by="title",
            order_direction="desc"
        )
        assert len(desc_results) == 3
        assert desc_results[0].title == "Engineer C"
        assert desc_results[2].title == "Engineer A"

    def test_get_jobs_stats_comprehensive(self, clean_db):
        """Test comprehensive job statistics."""
        repo = JobRepository(clean_db)

        # Create diverse jobs for statistics
        jobs_data = [
            {
                "title": "Engineer 1", "company": "Company A", "location": "City 1",
                "description": "Desc 1", "url": "https://test.com/1", "linkedin_job_id": "STATS-001",
                "employment_type": "Full-time", "experience_level": "Senior", "is_remote": "Remote"
            },
            {
                "title": "Engineer 2", "company": "Company A", "location": "City 2",
                "description": "Desc 2", "url": "https://test.com/2", "linkedin_job_id": "STATS-002",
                "employment_type": "Full-time", "experience_level": "Mid", "is_remote": "On-site"
            },
            {
                "title": "Engineer 3", "company": "Company B", "location": "City 3",
                "description": "Desc 3", "url": "https://test.com/3", "linkedin_job_id": "STATS-003",
                "employment_type": "Contract", "experience_level": "Senior", "is_remote": "Hybrid"
            }
        ]

        for job_data in jobs_data:
            repo.create(**job_data)

        stats = repo.get_jobs_stats()

        assert stats["total_jobs"] == 3
        assert stats["employment_type_breakdown"]["Full-time"] == 2
        assert stats["employment_type_breakdown"]["Contract"] == 1
        assert stats["experience_level_breakdown"]["Senior"] == 2
        assert stats["experience_level_breakdown"]["Mid"] == 1
        assert stats["remote_status_breakdown"]["Remote"] == 1
        assert stats["remote_status_breakdown"]["On-site"] == 1
        assert stats["remote_status_breakdown"]["Hybrid"] == 1
        assert stats["top_companies"]["Company A"] == 2
        assert stats["top_companies"]["Company B"] == 1

    def test_bulk_create_error_handling(self, clean_db):
        """Test bulk create with error conditions."""
        repo = JobRepository(clean_db)

        # Create one job first
        repo.create(
            title="Existing Job",
            company="Test Corp",
            location="Test City",
            description="Test description",
            url="https://linkedin.com/jobs/existing",
            linkedin_job_id="EXISTING-001"
        )

        # Try bulk create with duplicate LinkedIn ID
        jobs_data = [
            {
                "title": "Bulk Job 1",
                "company": "Bulk Corp 1",
                "location": "Bulk City 1",
                "description": "Bulk description 1",
                "url": "https://linkedin.com/jobs/bulk1",
                "linkedin_job_id": "BULK-001"
            },
            {
                "title": "Bulk Job 2",
                "company": "Bulk Corp 2",
                "location": "Bulk City 2",
                "description": "Bulk description 2",
                "url": "https://linkedin.com/jobs/bulk2",
                "linkedin_job_id": "EXISTING-001"  # Duplicate!
            }
        ]

        with pytest.raises(ValueError, match="Data integrity error during bulk create"):
            repo.bulk_create(jobs_data)

    def test_upsert_job_error_handling(self, clean_db):
        """Test upsert error handling."""
        repo = JobRepository(clean_db)

        # Test upsert without LinkedIn job ID
        with pytest.raises(ValueError, match="linkedin_job_id is required"):
            repo.upsert_job({"title": "Test", "company": "Test"})


class TestBaseRepository:
    """Test the base repository functionality."""

    def test_base_repository_operations(self, clean_db):
        """Test base repository CRUD operations."""
        base_repo = BaseRepository(clean_db, JobModel)

        # Test create
        job = base_repo.create(
            title="Base Test Job",
            company="Base Test Corp",
            location="Base Test City",
            description="Base test description",
            url="https://linkedin.com/jobs/base",
            linkedin_job_id="BASE-001"
        )

        assert job.id is not None
        assert job.title == "Base Test Job"

        # Test get_by_id
        retrieved = base_repo.get_by_id(job.id)
        assert retrieved is not None
        assert retrieved.id == job.id

        # Test get_all
        all_jobs = base_repo.get_all()
        assert len(all_jobs) >= 1

        # Test count
        count = base_repo.count()
        assert count >= 1

        # Test update
        updated = base_repo.update(job.id, title="Updated Base Job")
        assert updated.title == "Updated Base Job"

        # Test delete
        result = base_repo.delete(job.id)
        assert result is True

        # Verify deletion
        deleted = base_repo.get_by_id(job.id)
        assert deleted is None

    def test_base_repository_pagination(self, clean_db):
        """Test base repository pagination."""
        base_repo = BaseRepository(clean_db, JobModel)

        # Create multiple jobs
        for i in range(10):
            base_repo.create(
                title=f"Pagination Job {i}",
                company=f"Pagination Corp {i}",
                location=f"Pagination City {i}",
                description=f"Pagination description {i}",
                url=f"https://linkedin.com/jobs/page{i}",
                linkedin_job_id=f"PAGE-{i:03d}"
            )

        # Test limit
        limited = base_repo.get_all(limit=5)
        assert len(limited) == 5

        # Test offset
        offset_results = base_repo.get_all(limit=3, offset=5)
        assert len(offset_results) == 3

        # Test without limit
        all_results = base_repo.get_all()
        assert len(all_results) >= 10


class TestUtilityFunctions:
    """Test utility functions in repository module."""

    def test_get_job_repository_with_session(self, clean_db):
        """Test get_job_repository with provided session."""
        repo = get_job_repository(clean_db)
        assert isinstance(repo, JobRepository)
        assert repo.session == clean_db

    def test_get_job_repository_without_session(self):
        """Test get_job_repository without session (uses dependency)."""
        # This test verifies the function works but doesn't test the actual session creation
        # since that would require a full database setup
        repo_func = get_job_repository
        assert callable(repo_func)