"""Tests for analysis repository."""

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
from src.analyzer.repository import AnalysisRepository


class TestAnalysisRepository:
    """Test AnalysisRepository functionality."""

    @pytest.fixture
    def repository(self, test_session):
        """Create repository instance."""
        return AnalysisRepository(test_session)

    @pytest.fixture
    def sample_job(self, test_session):
        """Create a sample job for testing."""
        job = JobModel(
            title="Python Developer",
            company="TechCorp",
            location="Remote",
            description="Python development role",
            url="https://example.com/job",
            linkedin_job_id="test123"
        )
        test_session.add(job)
        test_session.commit()
        return job

    @pytest.fixture
    def sample_profile(self, test_session):
        """Create a sample user profile."""
        profile = UserProfileModel(
            user_id="testuser123",
            skills=["Python", "Django", "REST API"],
            experience_years=5
        )
        test_session.add(profile)
        test_session.commit()
        return profile

    def test_create_job_analysis(self, repository, sample_job):
        """Test creating job analysis."""
        analysis_data = {
            "job_id": sample_job.id,
            "analysis_type": AnalysisType.QUALITY,
            "quality_score": 85,
            "analysis_data": {"reasoning": "Strong job description"}
        }

        result = repository.create_job_analysis(**analysis_data)

        assert result.id is not None
        assert result.job_id == sample_job.id
        assert result.quality_score == 85
        assert result.status == AnalysisStatus.PENDING

    def test_get_job_analysis_by_id(self, repository, sample_job):
        """Test retrieving job analysis by ID."""
        analysis = JobAnalysisModel(
            job_id=sample_job.id,
            analysis_type=AnalysisType.QUALITY,
            quality_score=90
        )
        repository.session.add(analysis)
        repository.session.commit()

        result = repository.get_job_analysis(analysis.id)

        assert result is not None
        assert result.id == analysis.id
        assert result.quality_score == 90

    def test_get_job_analyses_for_job(self, repository, sample_job):
        """Test getting all analyses for a job."""
        # Create multiple analyses
        analysis1 = JobAnalysisModel(
            job_id=sample_job.id,
            analysis_type=AnalysisType.QUALITY,
            quality_score=85
        )
        analysis2 = JobAnalysisModel(
            job_id=sample_job.id,
            analysis_type=AnalysisType.COMPETITION,
            competition_score=70
        )
        repository.session.add_all([analysis1, analysis2])
        repository.session.commit()

        results = repository.get_job_analyses_for_job(sample_job.id)

        assert len(results) == 2
        assert any(a.analysis_type == AnalysisType.QUALITY for a in results)
        assert any(a.analysis_type == AnalysisType.COMPETITION for a in results)

    def test_update_job_analysis_status(self, repository, sample_job):
        """Test updating analysis status."""
        analysis = JobAnalysisModel(
            job_id=sample_job.id,
            analysis_type=AnalysisType.QUALITY,
            status=AnalysisStatus.PENDING
        )
        repository.session.add(analysis)
        repository.session.commit()

        repository.update_job_analysis_status(
            analysis.id,
            AnalysisStatus.COMPLETED,
            quality_score=88,
            analysis_data={"details": "Analysis complete"}
        )

        updated = repository.get_job_analysis(analysis.id)
        assert updated.status == AnalysisStatus.COMPLETED
        assert updated.quality_score == 88
        assert updated.analysis_data["details"] == "Analysis complete"

    def test_create_competition_analysis(self, repository, sample_job):
        """Test creating competition analysis."""
        comp_data = {
            "job_id": sample_job.id,
            "applicant_count": 25,
            "competition_level": "medium",
            "success_probability": 60,
            "analysis_data": {"insights": "Moderate competition"}
        }

        result = repository.create_competition_analysis(**comp_data)

        assert result.id is not None
        assert result.applicant_count == 25
        assert result.competition_level == "medium"
        assert result.success_probability == 60

    def test_get_competition_analysis_for_job(self, repository, sample_job):
        """Test getting competition analysis for a job."""
        comp = CompetitionAnalysisModel(
            job_id=sample_job.id,
            competition_level="high",
            success_probability=30
        )
        repository.session.add(comp)
        repository.session.commit()

        result = repository.get_competition_analysis_for_job(sample_job.id)

        assert result is not None
        assert result.competition_level == "high"
        assert result.success_probability == 30

    def test_create_user_profile(self, repository):
        """Test creating user profile."""
        profile_data = {
            "user_id": "newuser456",
            "skills": ["React", "TypeScript", "Node.js"],
            "experience_years": 3,
            "desired_roles": ["Frontend Developer"],
            "salary_expectations": {"min": 80000, "max": 120000, "currency": "USD"}
        }

        result = repository.create_user_profile(**profile_data)

        assert result.id is not None
        assert result.user_id == "newuser456"
        assert len(result.skills) == 3
        assert result.experience_years == 3

    def test_get_user_profile_by_user_id(self, repository, sample_profile):
        """Test getting user profile by user_id."""
        result = repository.get_user_profile_by_user_id(sample_profile.user_id)

        assert result is not None
        assert result.user_id == sample_profile.user_id
        assert result.experience_years == sample_profile.experience_years

    def test_update_user_profile(self, repository, sample_profile):
        """Test updating user profile."""
        updated_data = {
            "skills": ["Python", "Django", "REST API", "PostgreSQL"],
            "experience_years": 6,
            "certifications": ["AWS Certified Developer"]
        }

        result = repository.update_user_profile(sample_profile.id, **updated_data)

        assert result is not None
        assert len(result.skills) == 4
        assert result.experience_years == 6
        assert "AWS Certified Developer" in result.certifications

    def test_create_job_match(self, repository, sample_job, sample_profile):
        """Test creating job match."""
        match_data = {
            "job_id": sample_job.id,
            "user_profile_id": sample_profile.id,
            "match_score": 85,
            "recommendation": "apply",
            "skill_match_score": 90,
            "match_data": {"matched_skills": ["Python", "Django"]}
        }

        result = repository.create_job_match(**match_data)

        assert result.id is not None
        assert result.match_score == 85
        assert result.recommendation == "apply"
        assert result.skill_match_score == 90

    def test_get_job_matches_for_profile(self, repository, sample_job, sample_profile):
        """Test getting job matches for a profile."""
        match = JobMatchModel(
            job_id=sample_job.id,
            user_profile_id=sample_profile.id,
            match_score=88,
            recommendation="strong_match"
        )
        repository.session.add(match)
        repository.session.commit()

        results = repository.get_job_matches_for_profile(sample_profile.id)

        assert len(results) == 1
        assert results[0].match_score == 88
        assert results[0].recommendation == "strong_match"

    def test_get_top_matches_for_profile(self, repository, sample_profile, test_session):
        """Test getting top matches for a profile."""
        # Create multiple jobs and matches
        jobs = []
        for i in range(3):
            job = JobModel(
                title=f"Job {i}",
                company=f"Company {i}",
                location="Remote",
                description=f"Description {i}",
                url=f"https://example.com/job{i}",
                linkedin_job_id=f"job{i}"
            )
            test_session.add(job)
            jobs.append(job)
        test_session.commit()

        # Create matches with different scores
        matches = []
        scores = [95, 80, 70]
        for i, (job, score) in enumerate(zip(jobs, scores)):
            match = JobMatchModel(
                job_id=job.id,
                user_profile_id=sample_profile.id,
                match_score=score,
                recommendation="apply" if score > 85 else "consider"
            )
            repository.session.add(match)
            matches.append(match)
        repository.session.commit()

        # Get top 2 matches
        results = repository.get_top_matches_for_profile(sample_profile.id, limit=2)

        assert len(results) == 2
        assert results[0].match_score == 95  # Highest score first
        assert results[1].match_score == 80

    def test_update_match_user_interaction(self, repository, sample_job, sample_profile):
        """Test updating match user interactions."""
        match = JobMatchModel(
            job_id=sample_job.id,
            user_profile_id=sample_profile.id,
            match_score=75
        )
        repository.session.add(match)
        repository.session.commit()

        # Update as viewed
        repository.update_match_user_interaction(
            match.id,
            interaction_type="viewed"
        )

        updated = repository.session.get(JobMatchModel, match.id)
        assert updated.user_viewed is not None

        # Update as applied
        repository.update_match_user_interaction(
            match.id,
            interaction_type="applied"
        )

        updated = repository.session.get(JobMatchModel, match.id)
        assert updated.user_applied is not None

    def test_get_analysis_statistics(self, repository, sample_job):
        """Test getting analysis statistics."""
        # Create various analyses
        analyses = [
            JobAnalysisModel(
                job_id=sample_job.id,
                analysis_type=AnalysisType.QUALITY,
                status=AnalysisStatus.COMPLETED,
                quality_score=85
            ),
            JobAnalysisModel(
                job_id=sample_job.id,
                analysis_type=AnalysisType.COMPETITION,
                status=AnalysisStatus.COMPLETED,
                competition_score=70
            ),
            JobAnalysisModel(
                job_id=sample_job.id,
                analysis_type=AnalysisType.MATCHING,
                status=AnalysisStatus.FAILED
            )
        ]
        repository.session.add_all(analyses)
        repository.session.commit()

        stats = repository.get_analysis_statistics()

        assert stats["total_analyses"] == 3
        assert stats["completed_analyses"] == 2
        assert stats["failed_analyses"] == 1
        assert "analysis_by_type" in stats
        assert "analysis_by_status" in stats

    def test_bulk_create_job_analyses(self, repository, test_session):
        """Test bulk creating job analyses."""
        # Create multiple jobs
        jobs = []
        for i in range(3):
            job = JobModel(
                title=f"Job {i}",
                company=f"Company {i}",
                location="Remote",
                description=f"Description {i}",
                url=f"https://example.com/job{i}",
                linkedin_job_id=f"bulk{i}"
            )
            test_session.add(job)
            jobs.append(job)
        test_session.commit()

        # Bulk create analyses
        analyses_data = [
            {
                "job_id": job.id,
                "analysis_type": AnalysisType.QUALITY,
                "status": AnalysisStatus.PENDING
            }
            for job in jobs
        ]

        results = repository.bulk_create_job_analyses(analyses_data)

        assert len(results) == 3
        assert all(analysis.id is not None for analysis in results)
        assert all(analysis.analysis_type == AnalysisType.QUALITY for analysis in results)

    def test_find_analyses_for_retry(self, repository, sample_job):
        """Test finding analyses that need retry."""
        # Create a failed analysis with retry count
        analysis = JobAnalysisModel(
            job_id=sample_job.id,
            analysis_type=AnalysisType.QUALITY,
            status=AnalysisStatus.FAILED,
            retry_count=1,
            error_message="Temporary error"
        )
        repository.session.add(analysis)
        repository.session.commit()

        results = repository.find_analyses_for_retry(max_retries=3)

        assert len(results) == 1
        assert results[0].id == analysis.id
        assert results[0].status == AnalysisStatus.FAILED