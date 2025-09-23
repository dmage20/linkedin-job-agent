"""Additional tests for database models to increase coverage."""

import pytest
from src.database.models import JobModel


class TestJobModelMethods:
    """Test JobModel methods and functionality."""

    def test_job_model_repr(self, clean_db):
        """Test JobModel string representation."""
        job = JobModel(
            title="Test Engineer",
            company="Test Corp",
            location="Test City",
            description="Test description",
            url="https://linkedin.com/jobs/repr",
            linkedin_job_id="REPR-001"
        )

        clean_db.add(job)
        clean_db.commit()

        repr_str = repr(job)
        assert "JobModel" in repr_str
        assert str(job.id) in repr_str
        assert "Test Engineer" in repr_str
        assert "Test Corp" in repr_str

    def test_job_model_to_dict(self, clean_db):
        """Test JobModel to_dict method."""
        from datetime import datetime

        job = JobModel(
            title="Dict Test Engineer",
            company="Dict Test Corp",
            location="Dict Test City",
            description="Dict test description",
            url="https://linkedin.com/jobs/dict",
            linkedin_job_id="DICT-001",
            employment_type="Full-time",
            experience_level="Senior",
            industry="Technology",
            salary_min=100000,
            salary_max=150000,
            salary_currency="USD",
            is_remote="Remote",
            company_size="Large",
            date_posted=datetime.now()
        )

        clean_db.add(job)
        clean_db.commit()

        job_dict = job.to_dict()

        # Verify all fields are present
        assert job_dict["id"] == job.id
        assert job_dict["title"] == "Dict Test Engineer"
        assert job_dict["company"] == "Dict Test Corp"
        assert job_dict["location"] == "Dict Test City"
        assert job_dict["description"] == "Dict test description"
        assert job_dict["url"] == "https://linkedin.com/jobs/dict"
        assert job_dict["linkedin_job_id"] == "DICT-001"
        assert job_dict["employment_type"] == "Full-time"
        assert job_dict["experience_level"] == "Senior"
        assert job_dict["industry"] == "Technology"
        assert job_dict["salary_min"] == 100000
        assert job_dict["salary_max"] == 150000
        assert job_dict["salary_currency"] == "USD"
        assert job_dict["is_remote"] == "Remote"
        assert job_dict["company_size"] == "Large"

        # Verify datetime fields are properly serialized
        assert isinstance(job_dict["date_posted"], str)
        assert isinstance(job_dict["created_at"], str)
        assert isinstance(job_dict["updated_at"], str)

    def test_job_model_to_dict_null_fields(self, clean_db):
        """Test JobModel to_dict with null fields."""
        job = JobModel(
            title="Null Test Engineer",
            company="Null Test Corp",
            location="Null Test City",
            description="Null test description",
            url="https://linkedin.com/jobs/null",
            linkedin_job_id="NULL-001"
            # All optional fields left as None
        )

        clean_db.add(job)
        clean_db.commit()

        job_dict = job.to_dict()

        # Verify null fields are properly handled
        assert job_dict["employment_type"] is None
        assert job_dict["experience_level"] is None
        assert job_dict["industry"] is None
        assert job_dict["salary_min"] is None
        assert job_dict["salary_max"] is None
        assert job_dict["date_posted"] is None
        assert job_dict["is_remote"] is None
        assert job_dict["company_size"] is None

        # But required fields should still be present
        assert job_dict["title"] == "Null Test Engineer"
        assert job_dict["created_at"] is not None
        assert job_dict["updated_at"] is not None