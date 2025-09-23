"""Test CRUD operations and performance for the database system."""

import pytest
import time
from datetime import datetime, timezone
from typing import List

from src.database.models import JobModel
from src.database.repository import JobRepository


class TestJobCRUDOperations:
    """Test CRUD operations for Job model."""

    def test_create_job(self, clean_db):
        """Test creating a single job."""
        repo = JobRepository(clean_db)

        job_data = {
            "title": "Senior Software Engineer",
            "company": "TechCorp Inc.",
            "location": "San Francisco, CA",
            "description": "Exciting opportunity for a senior software engineer...",
            "url": "https://linkedin.com/jobs/12345",
            "linkedin_job_id": "12345",
            "employment_type": "Full-time",
            "experience_level": "Senior",
            "is_remote": "Hybrid"
        }

        job = repo.create(**job_data)

        assert job.id is not None
        assert job.title == job_data["title"]
        assert job.company == job_data["company"]
        assert job.linkedin_job_id == job_data["linkedin_job_id"]
        assert job.created_at is not None
        assert job.updated_at is not None

    def test_get_job_by_id(self, clean_db):
        """Test retrieving a job by ID."""
        repo = JobRepository(clean_db)

        # Create a job first
        job = repo.create(
            title="Data Scientist",
            company="DataCorp",
            location="New York, NY",
            description="Data science role",
            url="https://linkedin.com/jobs/67890",
            linkedin_job_id="67890"
        )

        # Retrieve the job
        retrieved_job = repo.get_by_id(job.id)

        assert retrieved_job is not None
        assert retrieved_job.id == job.id
        assert retrieved_job.title == "Data Scientist"
        assert retrieved_job.linkedin_job_id == "67890"

    def test_get_job_by_linkedin_id(self, clean_db):
        """Test retrieving a job by LinkedIn ID."""
        repo = JobRepository(clean_db)

        # Create a job
        job = repo.create(
            title="Product Manager",
            company="ProductCorp",
            location="Austin, TX",
            description="Product management role",
            url="https://linkedin.com/jobs/11111",
            linkedin_job_id="PM-11111"
        )

        # Retrieve by LinkedIn ID
        retrieved_job = repo.get_by_linkedin_id("PM-11111")

        assert retrieved_job is not None
        assert retrieved_job.id == job.id
        assert retrieved_job.title == "Product Manager"

    def test_update_job(self, clean_db):
        """Test updating a job."""
        repo = JobRepository(clean_db)

        # Create a job
        job = repo.create(
            title="DevOps Engineer",
            company="CloudCorp",
            location="Seattle, WA",
            description="DevOps role",
            url="https://linkedin.com/jobs/22222",
            linkedin_job_id="DO-22222"
        )

        original_updated_at = job.updated_at

        # Wait a brief moment to ensure timestamp difference
        time.sleep(0.1)

        # Update the job
        updated_job = repo.update(job.id, title="Senior DevOps Engineer", is_remote="Remote")

        assert updated_job is not None
        assert updated_job.title == "Senior DevOps Engineer"
        assert updated_job.is_remote == "Remote"
        assert updated_job.updated_at > original_updated_at

    def test_delete_job(self, clean_db):
        """Test deleting a job."""
        repo = JobRepository(clean_db)

        # Create a job
        job = repo.create(
            title="Frontend Developer",
            company="WebCorp",
            location="Los Angeles, CA",
            description="Frontend development role",
            url="https://linkedin.com/jobs/33333",
            linkedin_job_id="FE-33333"
        )

        job_id = job.id

        # Delete the job
        result = repo.delete(job_id)

        assert result is True

        # Verify job is deleted
        deleted_job = repo.get_by_id(job_id)
        assert deleted_job is None

    def test_search_jobs(self, clean_db):
        """Test searching jobs with filters."""
        repo = JobRepository(clean_db)

        # Create multiple jobs for searching
        jobs_data = [
            {
                "title": "Python Developer",
                "company": "Python Corp",
                "location": "Remote",
                "description": "Python development",
                "url": "https://linkedin.com/jobs/search1",
                "linkedin_job_id": "PY-001",
                "employment_type": "Full-time",
                "experience_level": "Mid",
                "is_remote": "Remote"
            },
            {
                "title": "Java Developer",
                "company": "Java Corp",
                "location": "New York, NY",
                "description": "Java development",
                "url": "https://linkedin.com/jobs/search2",
                "linkedin_job_id": "JAVA-001",
                "employment_type": "Full-time",
                "experience_level": "Senior",
                "is_remote": "On-site"
            },
            {
                "title": "React Developer",
                "company": "React Corp",
                "location": "San Francisco, CA",
                "description": "React development",
                "url": "https://linkedin.com/jobs/search3",
                "linkedin_job_id": "REACT-001",
                "employment_type": "Contract",
                "experience_level": "Mid",
                "is_remote": "Hybrid"
            }
        ]

        for job_data in jobs_data:
            repo.create(**job_data)

        # Test search by title
        python_jobs = repo.search_jobs(title="Python")
        assert len(python_jobs) == 1
        assert python_jobs[0].title == "Python Developer"

        # Test search by employment type
        fulltime_jobs = repo.search_jobs(employment_type="Full-time")
        assert len(fulltime_jobs) == 2

        # Test search by experience level
        mid_jobs = repo.search_jobs(experience_level="Mid")
        assert len(mid_jobs) == 2

        # Test search by remote status
        remote_jobs = repo.search_jobs(is_remote="Remote")
        assert len(remote_jobs) == 1

    def test_bulk_create_jobs(self, clean_db):
        """Test bulk creation of jobs."""
        repo = JobRepository(clean_db)

        jobs_data = [
            {
                "title": f"Engineer {i}",
                "company": f"Company {i}",
                "location": f"City {i}",
                "description": f"Description {i}",
                "url": f"https://linkedin.com/jobs/bulk{i}",
                "linkedin_job_id": f"BULK-{i:03d}"
            }
            for i in range(1, 6)  # Create 5 jobs
        ]

        created_jobs = repo.bulk_create(jobs_data)

        assert len(created_jobs) == 5
        for i, job in enumerate(created_jobs, 1):
            assert job.id is not None
            assert job.title == f"Engineer {i}"
            assert job.linkedin_job_id == f"BULK-{i:03d}"

    def test_upsert_job(self, clean_db):
        """Test upsert (create or update) operation."""
        repo = JobRepository(clean_db)

        job_data = {
            "title": "Upsert Engineer",
            "company": "Upsert Corp",
            "location": "Upsert City",
            "description": "Upsert description",
            "url": "https://linkedin.com/jobs/upsert",
            "linkedin_job_id": "UPSERT-001"
        }

        # First upsert should create
        job1 = repo.upsert_job(job_data)
        assert job1.id is not None
        assert job1.title == "Upsert Engineer"

        # Second upsert with same LinkedIn ID should update
        job_data["title"] = "Senior Upsert Engineer"
        job_data["experience_level"] = "Senior"

        job2 = repo.upsert_job(job_data)
        assert job2.id == job1.id  # Same job
        assert job2.title == "Senior Upsert Engineer"
        assert job2.experience_level == "Senior"

        # Verify only one job exists
        all_jobs = repo.get_all()
        upsert_jobs = [j for j in all_jobs if j.linkedin_job_id == "UPSERT-001"]
        assert len(upsert_jobs) == 1


class TestPerformance:
    """Test performance requirements for database operations."""

    def test_basic_crud_performance(self, clean_db):
        """Test that basic CRUD operations meet performance requirements (<50ms)."""
        repo = JobRepository(clean_db)

        job_data = {
            "title": "Performance Test Engineer",
            "company": "Performance Corp",
            "location": "Speed City",
            "description": "Performance testing role",
            "url": "https://linkedin.com/jobs/perf",
            "linkedin_job_id": "PERF-001"
        }

        # Test CREATE performance
        start_time = time.time()
        job = repo.create(**job_data)
        create_time = (time.time() - start_time) * 1000  # Convert to ms

        assert create_time < 50, f"Create operation took {create_time}ms, should be <50ms"

        # Test READ performance
        start_time = time.time()
        retrieved_job = repo.get_by_id(job.id)
        read_time = (time.time() - start_time) * 1000

        assert read_time < 50, f"Read operation took {read_time}ms, should be <50ms"

        # Test UPDATE performance
        start_time = time.time()
        updated_job = repo.update(job.id, title="Updated Performance Engineer")
        update_time = (time.time() - start_time) * 1000

        assert update_time < 50, f"Update operation took {update_time}ms, should be <50ms"

        # Test DELETE performance
        start_time = time.time()
        result = repo.delete(job.id)
        delete_time = (time.time() - start_time) * 1000

        assert delete_time < 50, f"Delete operation took {delete_time}ms, should be <50ms"

    def test_bulk_operations_performance(self, clean_db):
        """Test bulk operations performance for 100+ records."""
        repo = JobRepository(clean_db)

        # Create 100 job records
        jobs_data = [
            {
                "title": f"Bulk Engineer {i}",
                "company": f"Bulk Company {i}",
                "location": f"Bulk City {i}",
                "description": f"Bulk description {i}",
                "url": f"https://linkedin.com/jobs/bulk-perf-{i}",
                "linkedin_job_id": f"BULK-PERF-{i:03d}"
            }
            for i in range(1, 101)
        ]

        # Test bulk create performance
        start_time = time.time()
        created_jobs = repo.bulk_create(jobs_data)
        bulk_create_time = (time.time() - start_time) * 1000

        assert len(created_jobs) == 100
        assert bulk_create_time < 1000, f"Bulk create took {bulk_create_time}ms, should be <1000ms"

        # Test search performance on 100+ records
        start_time = time.time()
        search_results = repo.search_jobs(title="Bulk", limit=50)
        search_time = (time.time() - start_time) * 1000

        assert len(search_results) == 50  # Limited to 50
        assert search_time < 100, f"Search operation took {search_time}ms, should be <100ms"