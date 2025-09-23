"""Tests for analysis database models."""

import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from src.database.models import JobModel
from src.analyzer.models import (
    JobAnalysisModel,
    CompetitionAnalysisModel,
    JobMatchModel,
    UserProfileModel,
    AnalysisStatus,
    AnalysisType
)


class TestJobAnalysisModel:
    """Test JobAnalysisModel functionality."""

    def test_create_job_analysis(self, test_session):
        """Test creating a job analysis record."""
        # Create a job first
        job = JobModel(
            title="Python Developer",
            company="TechCorp",
            location="Remote",
            description="Great job",
            url="https://example.com",
            linkedin_job_id="123"
        )
        test_session.add(job)
        test_session.commit()

        # Create analysis
        analysis = JobAnalysisModel(
            job_id=job.id,
            analysis_type=AnalysisType.QUALITY,
            quality_score=85,
            analysis_data={"reasoning": "Good job description"},
            status=AnalysisStatus.COMPLETED
        )
        test_session.add(analysis)
        test_session.commit()

        assert analysis.id is not None
        assert analysis.job_id == job.id
        assert analysis.quality_score == 85
        assert analysis.analysis_data["reasoning"] == "Good job description"
        assert analysis.status == AnalysisStatus.COMPLETED

    def test_job_analysis_relationship(self, test_session):
        """Test relationship between job and analysis."""
        # Create job
        job = JobModel(
            title="Data Scientist",
            company="DataCorp",
            location="NYC",
            description="Data role",
            url="https://example.com/job",
            linkedin_job_id="456"
        )
        test_session.add(job)
        test_session.commit()

        # Create analysis
        analysis = JobAnalysisModel(
            job_id=job.id,
            analysis_type=AnalysisType.QUALITY,
            quality_score=90
        )
        test_session.add(analysis)
        test_session.commit()

        # Test relationship
        assert analysis.job == job
        assert analysis in job.analyses

    def test_job_analysis_to_dict(self, test_session):
        """Test converting analysis to dictionary."""
        job = JobModel(
            title="ML Engineer",
            company="AI Corp",
            location="SF",
            description="ML role",
            url="https://example.com",
            linkedin_job_id="789"
        )
        test_session.add(job)
        test_session.commit()

        analysis = JobAnalysisModel(
            job_id=job.id,
            analysis_type=AnalysisType.MATCHING,
            match_score=75,
            analysis_data={"skills_match": ["Python", "ML"]},
            status=AnalysisStatus.COMPLETED,
            error_message=None
        )
        test_session.add(analysis)
        test_session.commit()

        result = analysis.to_dict()

        assert result["id"] == analysis.id
        assert result["job_id"] == job.id
        assert result["analysis_type"] == AnalysisType.MATCHING.value
        assert result["match_score"] == 75
        assert result["analysis_data"] == {"skills_match": ["Python", "ML"]}
        assert result["status"] == AnalysisStatus.COMPLETED.value

    def test_analysis_validation(self, test_session):
        """Test analysis model validation."""
        job = JobModel(
            title="Backend Dev",
            company="WebCorp",
            location="Remote",
            description="Backend role",
            url="https://example.com",
            linkedin_job_id="999"
        )
        test_session.add(job)
        test_session.commit()

        # Test invalid quality score
        analysis = JobAnalysisModel(
            job_id=job.id,
            analysis_type=AnalysisType.QUALITY,
            quality_score=150  # Invalid > 100
        )
        test_session.add(analysis)

        with pytest.raises(IntegrityError):
            test_session.commit()


class TestCompetitionAnalysisModel:
    """Test CompetitionAnalysisModel functionality."""

    def test_create_competition_analysis(self, test_session):
        """Test creating competition analysis."""
        job = JobModel(
            title="Frontend Developer",
            company="WebTech",
            location="LA",
            description="Frontend role",
            url="https://example.com",
            linkedin_job_id="comp123"
        )
        test_session.add(job)
        test_session.commit()

        analysis = CompetitionAnalysisModel(
            job_id=job.id,
            applicant_count=50,
            competition_level="high",
            success_probability=25,
            analysis_data={"market_insights": "High demand role"}
        )
        test_session.add(analysis)
        test_session.commit()

        assert analysis.applicant_count == 50
        assert analysis.competition_level == "high"
        assert analysis.success_probability == 25

    def test_competition_analysis_to_dict(self, test_session):
        """Test converting competition analysis to dict."""
        job = JobModel(
            title="DevOps Engineer",
            company="CloudCorp",
            location="Austin",
            description="DevOps role",
            url="https://example.com",
            linkedin_job_id="devops456"
        )
        test_session.add(job)
        test_session.commit()

        analysis = CompetitionAnalysisModel(
            job_id=job.id,
            applicant_count=15,
            competition_level="low",
            success_probability=80,
            analysis_data={"tips": ["Apply early", "Highlight DevOps experience"]}
        )
        test_session.add(analysis)
        test_session.commit()

        result = analysis.to_dict()

        assert result["applicant_count"] == 15
        assert result["competition_level"] == "low"
        assert result["success_probability"] == 80
        assert "tips" in result["analysis_data"]


class TestJobMatchModel:
    """Test JobMatchModel functionality."""

    def test_create_job_match(self, test_session):
        """Test creating job match record."""
        job = JobModel(
            title="Full Stack Developer",
            company="StartupCorp",
            location="Remote",
            description="Full stack role",
            url="https://example.com",
            linkedin_job_id="fullstack789"
        )
        test_session.add(job)
        test_session.commit()

        profile = UserProfileModel(
            user_id="user123",
            skills=["Python", "React", "Node.js"],
            experience_years=5,
            desired_roles=["Full Stack Developer", "Software Engineer"]
        )
        test_session.add(profile)
        test_session.commit()

        match = JobMatchModel(
            job_id=job.id,
            user_profile_id=profile.id,
            match_score=88,
            recommendation="strong_match",
            match_data={
                "skill_alignment": ["Python", "React"],
                "missing_skills": ["Docker"],
                "experience_fit": "good"
            }
        )
        test_session.add(match)
        test_session.commit()

        assert match.match_score == 88
        assert match.recommendation == "strong_match"
        assert "skill_alignment" in match.match_data

    def test_job_match_relationships(self, test_session):
        """Test job match relationships."""
        job = JobModel(
            title="Data Engineer",
            company="DataCorp",
            location="Seattle",
            description="Data engineering role",
            url="https://example.com",
            linkedin_job_id="data999"
        )
        test_session.add(job)
        test_session.commit()

        profile = UserProfileModel(
            user_id="user456",
            skills=["Python", "SQL", "Spark"],
            experience_years=4
        )
        test_session.add(profile)
        test_session.commit()

        match = JobMatchModel(
            job_id=job.id,
            user_profile_id=profile.id,
            match_score=75
        )
        test_session.add(match)
        test_session.commit()

        # Test relationships
        assert match.job == job
        assert match.user_profile == profile


class TestUserProfileModel:
    """Test UserProfileModel functionality."""

    def test_create_user_profile(self, test_session):
        """Test creating user profile."""
        profile = UserProfileModel(
            user_id="profile123",
            skills=["Java", "Spring", "MySQL"],
            experience_years=7,
            desired_roles=["Backend Developer", "Senior Java Developer"],
            preferred_locations=["Remote", "San Francisco"],
            salary_expectations={"min": 120000, "max": 160000, "currency": "USD"}
        )
        test_session.add(profile)
        test_session.commit()

        assert profile.user_id == "profile123"
        assert len(profile.skills) == 3
        assert profile.experience_years == 7
        assert profile.salary_expectations["min"] == 120000

    def test_user_profile_unique_user_id(self, test_session):
        """Test unique constraint on user_id."""
        profile1 = UserProfileModel(
            user_id="unique_user",
            skills=["Python"],
            experience_years=3
        )
        test_session.add(profile1)
        test_session.commit()

        # Try to create another profile with same user_id
        profile2 = UserProfileModel(
            user_id="unique_user",
            skills=["Java"],
            experience_years=5
        )
        test_session.add(profile2)

        with pytest.raises(IntegrityError):
            test_session.commit()

    def test_user_profile_to_dict(self, test_session):
        """Test converting user profile to dict."""
        profile = UserProfileModel(
            user_id="dict_user",
            skills=["React", "TypeScript", "Node.js"],
            experience_years=4,
            desired_roles=["Frontend Developer"],
            preferred_locations=["NYC", "Remote"],
            education_level="Bachelor's",
            certifications=["AWS Certified"]
        )
        test_session.add(profile)
        test_session.commit()

        result = profile.to_dict()

        assert result["user_id"] == "dict_user"
        assert result["skills"] == ["React", "TypeScript", "Node.js"]
        assert result["experience_years"] == 4
        assert result["education_level"] == "Bachelor's"


class TestEnums:
    """Test enum values."""

    def test_analysis_status_enum(self):
        """Test AnalysisStatus enum values."""
        assert AnalysisStatus.PENDING.value == "pending"
        assert AnalysisStatus.IN_PROGRESS.value == "in_progress"
        assert AnalysisStatus.COMPLETED.value == "completed"
        assert AnalysisStatus.FAILED.value == "failed"

    def test_analysis_type_enum(self):
        """Test AnalysisType enum values."""
        assert AnalysisType.QUALITY.value == "quality"
        assert AnalysisType.COMPETITION.value == "competition"
        assert AnalysisType.MATCHING.value == "matching"