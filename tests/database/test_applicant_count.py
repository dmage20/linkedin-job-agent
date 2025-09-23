"""Tests for applicant count functionality in JobModel and JobRepository."""

import pytest
from src.database.models import JobModel
from src.database.repository import JobRepository
from src.database.connection import get_db_session, initialize_database


class TestApplicantCount:
    """Test cases for applicant count functionality."""

    @pytest.fixture(autouse=True)
    def setup_database(self):
        """Set up test database before each test."""
        initialize_database("sqlite:///:memory:")  # Use in-memory SQLite for tests

    def test_job_model_with_applicant_count(self):
        """Test that JobModel can store and retrieve applicant count."""
        # Create job with applicant count
        job_data = {
            "title": "Software Engineer",
            "company": "Tech Corp",
            "location": "San Francisco, CA",
            "description": "Great software engineering role",
            "url": "https://linkedin.com/jobs/view/123",
            "linkedin_job_id": "123",
            "applicant_count": 25
        }

        job = JobModel(**job_data)
        assert job.applicant_count == 25

        # Test to_dict includes applicant_count
        job_dict = job.to_dict()
        assert "applicant_count" in job_dict
        assert job_dict["applicant_count"] == 25

    def test_job_model_without_applicant_count(self):
        """Test that JobModel works when applicant_count is None."""
        job_data = {
            "title": "Software Engineer",
            "company": "Tech Corp",
            "location": "San Francisco, CA",
            "description": "Great software engineering role",
            "url": "https://linkedin.com/jobs/view/124",
            "linkedin_job_id": "124"
            # No applicant_count provided
        }

        job = JobModel(**job_data)
        assert job.applicant_count is None

        job_dict = job.to_dict()
        assert job_dict["applicant_count"] is None

    @pytest.fixture
    def repository_with_test_data(self):
        """Create repository with test data for competition analysis."""
        with next(get_db_session()) as session:
            repo = JobRepository(session)

            # Create test jobs with different applicant counts
            test_jobs = [
                {
                    "title": "Entry Level Developer",
                    "company": "StartupCorp",
                    "location": "Remote",
                    "description": "Entry level position",
                    "url": "https://linkedin.com/jobs/view/201",
                    "linkedin_job_id": "201",
                    "applicant_count": 5  # Low competition
                },
                {
                    "title": "Senior Developer",
                    "company": "BigTech",
                    "location": "Seattle, WA",
                    "description": "Senior position",
                    "url": "https://linkedin.com/jobs/view/202",
                    "linkedin_job_id": "202",
                    "applicant_count": 25  # Medium competition
                },
                {
                    "title": "Principal Engineer",
                    "company": "FAANG",
                    "location": "Mountain View, CA",
                    "description": "Principal level role",
                    "url": "https://linkedin.com/jobs/view/203",
                    "linkedin_job_id": "203",
                    "applicant_count": 75  # High competition
                },
                {
                    "title": "Backend Developer",
                    "company": "MidSize",
                    "location": "Austin, TX",
                    "description": "Backend role",
                    "url": "https://linkedin.com/jobs/view/204",
                    "linkedin_job_id": "204"
                    # No applicant_count (unknown competition)
                }
            ]

            for job_data in test_jobs:
                repo.create(**job_data)

            return repo

    def test_find_jobs_by_applicant_count(self, repository_with_test_data):
        """Test filtering jobs by applicant count ranges."""
        repo = repository_with_test_data

        # Find low competition jobs (≤10 applicants)
        low_competition = repo.find_jobs_by_applicant_count(max_applicants=10)
        assert len(low_competition) == 1
        assert low_competition[0].applicant_count == 5

        # Find medium competition jobs (11-50 applicants)
        medium_competition = repo.find_jobs_by_applicant_count(
            min_applicants=11, max_applicants=50
        )
        assert len(medium_competition) == 1
        assert medium_competition[0].applicant_count == 25

        # Find high competition jobs (>50 applicants)
        high_competition = repo.find_jobs_by_applicant_count(min_applicants=51)
        assert len(high_competition) == 1
        assert high_competition[0].applicant_count == 75

    def test_get_low_competition_jobs(self, repository_with_test_data):
        """Test getting low competition jobs for strategic targeting."""
        repo = repository_with_test_data

        low_comp_jobs = repo.get_low_competition_jobs(max_applicants=10)
        assert len(low_comp_jobs) == 1
        assert low_comp_jobs[0].title == "Entry Level Developer"
        assert low_comp_jobs[0].applicant_count == 5

    def test_competition_statistics(self, repository_with_test_data):
        """Test getting competition statistics for market intelligence."""
        repo = repository_with_test_data

        stats = repo.get_competition_statistics()

        # Should have data for 3 jobs (4th has no applicant_count)
        assert stats["total_jobs_with_data"] == 3

        # Average of 5, 25, 75 = 35
        assert stats["average_applicants"] == 35.0

        assert stats["min_applicants"] == 5
        assert stats["max_applicants"] == 75

        # Competition breakdown
        breakdown = stats["competition_breakdown"]
        assert breakdown["low_competition_jobs"] == 1  # ≤10 applicants
        assert breakdown["medium_competition_jobs"] == 1  # 11-50 applicants
        assert breakdown["high_competition_jobs"] == 1  # >50 applicants

    def test_order_by_competition(self, repository_with_test_data):
        """Test ordering jobs by competition level."""
        repo = repository_with_test_data

        # Order by ascending competition (easiest to apply first)
        jobs_asc = repo.find_jobs_by_applicant_count(order_by_competition="asc")
        applicant_counts_asc = [job.applicant_count for job in jobs_asc]
        assert applicant_counts_asc == [5, 25, 75]

        # Order by descending competition (most competitive first)
        jobs_desc = repo.find_jobs_by_applicant_count(order_by_competition="desc")
        applicant_counts_desc = [job.applicant_count for job in jobs_desc]
        assert applicant_counts_desc == [75, 25, 5]

    def test_competition_statistics_no_data(self):
        """Test competition statistics when no applicant count data is available."""
        with next(get_db_session()) as session:
            repo = JobRepository(session)

            # Create job without applicant count
            repo.create(
                title="Test Job",
                company="Test Corp",
                location="Test City",
                description="Test description",
                url="https://linkedin.com/jobs/view/999",
                linkedin_job_id="999"
            )

            stats = repo.get_competition_statistics()
            assert "message" in stats
            assert stats["message"] == "No applicant count data available"