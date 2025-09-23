"""Tests for database models using TDD approach."""

import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from src.database.models import Base, BaseModel, JobModel


class TestBaseModel:
    """Test cases for the base model functionality."""

    def test_base_model_has_id_field(self):
        """Test that base model has an id field."""
        assert hasattr(BaseModel, 'id')

    def test_base_model_has_timestamps(self):
        """Test that base model has created_at and updated_at timestamps."""
        assert hasattr(BaseModel, 'created_at')
        assert hasattr(BaseModel, 'updated_at')


class TestJobModel:
    """Test cases for the Job model following TDD approach."""

    def test_job_model_creation(self, clean_db):
        """Test basic job model creation."""
        job = JobModel(
            title="Software Engineer",
            company="TechCorp",
            location="San Francisco, CA",
            description="Great opportunity for a software engineer",
            url="https://linkedin.com/jobs/123",
            linkedin_job_id="123456"
        )

        clean_db.add(job)
        clean_db.commit()

        assert job.id is not None
        assert job.title == "Software Engineer"
        assert job.company == "TechCorp"
        assert job.created_at is not None
        assert job.updated_at is not None

    def test_job_model_required_fields(self, clean_db):
        """Test that job model enforces required fields."""
        # Should fail without required fields
        with pytest.raises(IntegrityError):
            job = JobModel()
            clean_db.add(job)
            clean_db.commit()

    def test_job_model_unique_linkedin_id(self, clean_db):
        """Test that LinkedIn job ID must be unique."""
        job1 = JobModel(
            title="Engineer 1",
            company="Company 1",
            location="Location 1",
            description="Description 1",
            url="https://linkedin.com/jobs/1",
            linkedin_job_id="123456"
        )

        job2 = JobModel(
            title="Engineer 2",
            company="Company 2",
            location="Location 2",
            description="Description 2",
            url="https://linkedin.com/jobs/2",
            linkedin_job_id="123456"  # Same LinkedIn ID
        )

        clean_db.add(job1)
        clean_db.commit()

        # Should fail due to unique constraint
        with pytest.raises(IntegrityError):
            clean_db.add(job2)
            clean_db.commit()

    def test_job_model_timestamps_auto_set(self, clean_db):
        """Test that timestamps are automatically set."""
        job = JobModel(
            title="Software Engineer",
            company="TechCorp",
            location="San Francisco, CA",
            description="Great opportunity",
            url="https://linkedin.com/jobs/123",
            linkedin_job_id="123456"
        )

        clean_db.add(job)
        clean_db.commit()

        # Timestamps should be set automatically
        assert job.created_at is not None
        assert job.updated_at is not None

        # Timestamps are set by SQLite and may not have timezone info in test env
        # But they should be datetime objects
        assert isinstance(job.created_at, datetime)
        assert isinstance(job.updated_at, datetime)

        # On creation, created_at and updated_at should be very close
        time_diff = abs((job.created_at - job.updated_at).total_seconds())
        assert time_diff < 1  # Less than 1 second difference

    def test_job_model_updated_at_changes(self, clean_db):
        """Test that updated_at changes when model is modified."""
        job = JobModel(
            title="Software Engineer",
            company="TechCorp",
            location="San Francisco, CA",
            description="Great opportunity",
            url="https://linkedin.com/jobs/123",
            linkedin_job_id="123456"
        )

        clean_db.add(job)
        clean_db.commit()

        original_updated_at = job.updated_at

        # Modify the job
        job.title = "Senior Software Engineer"
        clean_db.commit()

        assert job.updated_at > original_updated_at

    def test_job_model_indexing_performance(self, clean_db):
        """Test that job model has proper indexing for performance."""
        # This test will verify that indexes exist for performance
        # We'll implement the actual performance testing later
        pass