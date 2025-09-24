"""Test configuration and fixtures for the LinkedIn Job Agent project."""

import pytest
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from src.database.models import Base, JobModel
from src.analyzer.models import UserProfileModel
# Import application models to ensure they are registered with Base
from src.applicator.models import JobApplicationModel, GeneratedContentModel, SafetyEventModel


@pytest.fixture(scope="function")
def test_db_engine():
    """Create a temporary SQLite database for testing."""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    # Create engine with SQLite
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    # Create all tables
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    engine.dispose()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture(scope="function")
def test_session(test_db_engine) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def clean_db(test_session):
    """Provide a clean database for each test."""
    # Clear all tables before each test
    for table in reversed(Base.metadata.sorted_tables):
        test_session.execute(table.delete())
    test_session.commit()
    return test_session


@pytest.fixture
def sample_job(test_session):
    """Create a sample job for testing."""
    job = JobModel(
        title="Senior Software Engineer",
        company="Tech Corp",
        location="San Francisco, CA",
        description="Exciting opportunity for a senior software engineer to join our team...",
        url="https://linkedin.com/jobs/12345",
        linkedin_job_id="12345",
        employment_type="Full-time",
        experience_level="Mid-Senior level",
        industry="Technology",
        salary_min=120000,
        salary_max=180000,
        is_remote="Hybrid",
        applicant_count=25
    )
    test_session.add(job)
    test_session.commit()
    return job


@pytest.fixture
def sample_user_profile(test_session):
    """Create a sample user profile for testing."""
    profile = UserProfileModel(
        user_id="test_user_123",
        skills=["Python", "JavaScript", "React", "SQL", "AWS"],
        experience_years=5,
        desired_roles=["Software Engineer", "Full Stack Developer", "Backend Engineer"],
        preferred_locations=["San Francisco", "Remote"],
        salary_expectations={"min": 110000, "max": 170000, "currency": "USD"},
        work_schedule_preference="full-time",
        remote_preference="hybrid",
        education_level="Bachelor's Degree",
        certifications=["AWS Certified Developer"],
        industry_preferences=["Technology", "Fintech"],
        company_size_preference="medium",
        profile_data={"github": "https://github.com/testuser", "portfolio": "https://testuser.dev"}
    )
    test_session.add(profile)
    test_session.commit()
    return profile