"""Edge case tests for repository functionality to achieve >95% coverage."""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError

from src.database.repository import JobRepository, BaseRepository
from src.database.models import JobModel


class TestRepositoryEdgeCases:
    """Test edge cases and error conditions in repository."""

    def test_base_repository_get_by_id_sql_error(self, clean_db):
        """Test BaseRepository get_by_id with SQL error."""
        repo = BaseRepository(clean_db, JobModel)

        with patch.object(clean_db, 'query', side_effect=SQLAlchemyError("Query error")):
            with pytest.raises(RuntimeError, match="Database error"):
                repo.get_by_id(1)

    def test_base_repository_get_all_sql_error(self, clean_db):
        """Test BaseRepository get_all with SQL error."""
        repo = BaseRepository(clean_db, JobModel)

        with patch.object(clean_db, 'query', side_effect=SQLAlchemyError("Query error")):
            with pytest.raises(RuntimeError, match="Database error"):
                repo.get_all()

    def test_base_repository_count_sql_error(self, clean_db):
        """Test BaseRepository count with SQL error."""
        repo = BaseRepository(clean_db, JobModel)

        with patch.object(clean_db, 'query', side_effect=SQLAlchemyError("Query error")):
            with pytest.raises(RuntimeError, match="Database error"):
                repo.count()

    def test_base_repository_update_sql_error(self, clean_db):
        """Test BaseRepository update with SQL error."""
        repo = BaseRepository(clean_db, JobModel)

        # Create a job first
        job = repo.create(
            title="Update Test",
            company="Update Corp",
            location="Update City",
            description="Update description",
            url="https://linkedin.com/jobs/update",
            linkedin_job_id="UPDATE-001"
        )

        # Mock commit to raise error
        with patch.object(clean_db, 'commit', side_effect=SQLAlchemyError("Commit error")):
            with pytest.raises(RuntimeError, match="Database error"):
                repo.update(job.id, title="Updated Title")

    def test_base_repository_delete_sql_error(self, clean_db):
        """Test BaseRepository delete with SQL error."""
        repo = BaseRepository(clean_db, JobModel)

        # Create a job first
        job = repo.create(
            title="Delete Test",
            company="Delete Corp",
            location="Delete City",
            description="Delete description",
            url="https://linkedin.com/jobs/delete",
            linkedin_job_id="DELETE-001"
        )

        # Mock commit to raise error
        with patch.object(clean_db, 'commit', side_effect=SQLAlchemyError("Commit error")):
            with pytest.raises(RuntimeError, match="Database error"):
                repo.delete(job.id)

    def test_job_repository_get_by_linkedin_id_sql_error(self, clean_db):
        """Test JobRepository get_by_linkedin_id with SQL error."""
        repo = JobRepository(clean_db)

        with patch.object(clean_db, 'query', side_effect=SQLAlchemyError("Query error")):
            with pytest.raises(RuntimeError, match="Database error"):
                repo.get_by_linkedin_id("TEST-001")

    def test_job_repository_search_jobs_sql_error(self, clean_db):
        """Test JobRepository search_jobs with SQL error."""
        repo = JobRepository(clean_db)

        with patch.object(clean_db, 'query', side_effect=SQLAlchemyError("Query error")):
            with pytest.raises(RuntimeError, match="Database error"):
                repo.search_jobs(title="Test")

    def test_job_repository_get_jobs_by_company_sql_error(self, clean_db):
        """Test JobRepository get_jobs_by_company with SQL error."""
        repo = JobRepository(clean_db)

        with patch.object(clean_db, 'query', side_effect=SQLAlchemyError("Query error")):
            with pytest.raises(RuntimeError, match="Database error"):
                repo.get_jobs_by_company("Test Corp")

    def test_job_repository_get_recent_jobs_sql_error(self, clean_db):
        """Test JobRepository get_recent_jobs with SQL error."""
        repo = JobRepository(clean_db)

        with patch.object(clean_db, 'query', side_effect=SQLAlchemyError("Query error")):
            with pytest.raises(RuntimeError, match="Database error"):
                repo.get_recent_jobs(days=7)

    def test_job_repository_get_jobs_stats_sql_error(self, clean_db):
        """Test JobRepository get_jobs_stats with SQL error."""
        repo = JobRepository(clean_db)

        with patch.object(repo, 'count', side_effect=SQLAlchemyError("Count error")):
            with pytest.raises(RuntimeError, match="Database error"):
                repo.get_jobs_stats()

    def test_job_repository_upsert_sql_error(self, clean_db):
        """Test JobRepository upsert with SQL error."""
        repo = JobRepository(clean_db)

        job_data = {
            "title": "Upsert Error Test",
            "company": "Upsert Error Corp",
            "location": "Upsert Error City",
            "description": "Upsert error description",
            "url": "https://linkedin.com/jobs/upsert-error",
            "linkedin_job_id": "UPSERT-ERROR-001"
        }

        with patch.object(clean_db, 'commit', side_effect=SQLAlchemyError("Upsert error")):
            with pytest.raises(RuntimeError, match="Database error"):
                repo.upsert_job(job_data)

    def test_search_jobs_all_filters(self, clean_db):
        """Test search_jobs with all possible filters to ensure coverage."""
        repo = JobRepository(clean_db)

        # Create a job with all fields
        job_data = {
            "title": "Full Filter Test Engineer",
            "company": "Full Filter Corp",
            "location": "Full Filter City",
            "description": "Full filter description",
            "url": "https://linkedin.com/jobs/full-filter",
            "linkedin_job_id": "FULL-FILTER-001",
            "employment_type": "Full-time",
            "experience_level": "Senior",
            "is_remote": "Hybrid"
        }

        repo.create(**job_data)

        # Test search with all filters
        results = repo.search_jobs(
            title="Full Filter",
            company="Full Filter",
            location="Full Filter",
            employment_type="Full-time",
            experience_level="Senior",
            is_remote="Hybrid",
            limit=10,
            offset=0,
            order_by="title",
            order_direction="asc"
        )

        assert len(results) == 1
        assert results[0].title == "Full Filter Test Engineer"

    def test_search_jobs_invalid_order_column(self, clean_db):
        """Test search_jobs with invalid order column falls back to default."""
        repo = JobRepository(clean_db)

        # Create a job
        repo.create(
            title="Order Test",
            company="Order Corp",
            location="Order City",
            description="Order description",
            url="https://linkedin.com/jobs/order",
            linkedin_job_id="ORDER-001"
        )

        # Search with invalid order column (should fall back to created_at)
        results = repo.search_jobs(
            title="Order",
            order_by="invalid_column",
            order_direction="desc"
        )

        assert len(results) == 1

    def test_get_jobs_stats_with_none_values(self, clean_db):
        """Test get_jobs_stats when some fields are None."""
        repo = JobRepository(clean_db)

        # Create jobs with some None values
        jobs_data = [
            {
                "title": "Stats Test 1",
                "company": "Stats Corp 1",
                "location": "Stats City 1",
                "description": "Stats description 1",
                "url": "https://linkedin.com/jobs/stats1",
                "linkedin_job_id": "STATS-001",
                "employment_type": None,  # None value
                "experience_level": "Senior",
                "is_remote": None  # None value
            },
            {
                "title": "Stats Test 2",
                "company": "Stats Corp 2",
                "location": "Stats City 2",
                "description": "Stats description 2",
                "url": "https://linkedin.com/jobs/stats2",
                "linkedin_job_id": "STATS-002",
                "employment_type": "Full-time",
                "experience_level": None,  # None value
                "is_remote": "Remote"
            }
        ]

        for job_data in jobs_data:
            repo.create(**job_data)

        stats = repo.get_jobs_stats()

        # Should handle None values gracefully
        assert stats["total_jobs"] == 2
        assert None in stats["employment_type_breakdown"]
        assert None in stats["experience_level_breakdown"]
        assert None in stats["remote_status_breakdown"]

    def test_repository_hasattr_edge_case(self, clean_db):
        """Test BaseRepository update with invalid attribute."""
        repo = BaseRepository(clean_db, JobModel)

        # Create a job
        job = repo.create(
            title="Hasattr Test",
            company="Hasattr Corp",
            location="Hasattr City",
            description="Hasattr description",
            url="https://linkedin.com/jobs/hasattr",
            linkedin_job_id="HASATTR-001"
        )

        # Try to update with invalid attribute (should be ignored)
        updated = repo.update(job.id, title="Updated Title", invalid_attr="Invalid")

        assert updated.title == "Updated Title"
        # Invalid attribute should be ignored without error