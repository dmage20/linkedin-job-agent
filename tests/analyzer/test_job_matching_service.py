"""Tests for AI-powered job matching service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.database.models import JobModel
from src.analyzer.models import UserProfileModel, JobMatchModel
from src.analyzer.services.job_matching_service import JobMatchingService, MatchingMetrics
from src.analyzer.claude_client import ClaudeClient


class TestJobMatchingService:
    """Test JobMatchingService functionality."""

    @pytest.fixture
    def mock_claude_client(self):
        """Mock Claude client."""
        return Mock(spec=ClaudeClient)

    @pytest.fixture
    def mock_repository(self):
        """Mock analysis repository."""
        return Mock()

    @pytest.fixture
    def mock_job_repository(self):
        """Mock job repository."""
        return Mock()

    @pytest.fixture
    def matching_service(self, mock_claude_client, mock_repository, mock_job_repository):
        """Create matching service instance."""
        return JobMatchingService(
            claude_client=mock_claude_client,
            repository=mock_repository,
            job_repository=mock_job_repository
        )

    @pytest.fixture
    def sample_job(self):
        """Sample job for testing."""
        return JobModel(
            id=1,
            title="Senior Python Developer",
            company="TechCorp Inc.",
            location="Remote",
            description="""
We are looking for a Senior Python Developer with 5+ years of experience.

Requirements:
- 5+ years of Python development
- Experience with Django or Flask
- Knowledge of SQL databases
- AWS cloud experience preferred
- Strong problem-solving skills

Responsibilities:
- Develop web applications
- Write clean, maintainable code
- Collaborate with team
- Participate in code reviews

We offer competitive salary ($120,000-$150,000), health benefits, and remote work.
            """,
            url="https://linkedin.com/jobs/12345",
            linkedin_job_id="12345",
            employment_type="Full-time",
            experience_level="Senior",
            salary_min=120000,
            salary_max=150000
        )

    @pytest.fixture
    def sample_profile(self):
        """Sample user profile for testing."""
        return UserProfileModel(
            id=1,
            user_id="user123",
            skills=["Python", "Django", "PostgreSQL", "JavaScript", "React"],
            experience_years=6,
            desired_roles=["Senior Python Developer", "Full Stack Developer"],
            preferred_locations=["Remote", "San Francisco"],
            salary_expectations={"min": 110000, "max": 140000, "currency": "USD"},
            work_schedule_preference="full-time",
            remote_preference="remote",
            education_level="Bachelor's",
            certifications=["AWS Solutions Architect"]
        )

    @pytest.fixture
    def claude_matching_response(self):
        """Mock Claude API response for job matching."""
        return {
            "match_score": 88,
            "explanation": "Excellent match with strong skill alignment and experience level compatibility",
            "skill_alignment": {
                "matched_skills": ["Python", "Django", "PostgreSQL"],
                "missing_skills": ["Flask"],
                "transferable_skills": ["JavaScript", "React"]
            },
            "experience_fit": "Strong match - candidate has 6 years vs 5+ required",
            "location_preference": "Perfect match - both remote",
            "salary_expectation": "Good alignment within expected range",
            "growth_potential": "Strong potential for career growth in this role",
            "recommendation": "strong_match"
        }

    def test_service_initialization(self, mock_claude_client, mock_repository, mock_job_repository):
        """Test service initialization."""
        service = JobMatchingService(
            claude_client=mock_claude_client,
            repository=mock_repository,
            job_repository=mock_job_repository
        )

        assert service.claude_client == mock_claude_client
        assert service.repository == mock_repository
        assert service.job_repository == mock_job_repository

    @pytest.mark.asyncio
    async def test_match_job_to_profile_success(
        self,
        matching_service,
        sample_job,
        sample_profile,
        claude_matching_response,
        mock_repository
    ):
        """Test successful job-to-profile matching."""
        # Mock repository responses
        mock_repository.get_job_match.return_value = None  # No existing match
        mock_match = Mock()
        mock_match.id = 1
        mock_repository.create_job_match.return_value = mock_match

        # Mock Claude client response
        matching_service.claude_client.match_job_to_profile = AsyncMock(
            return_value=claude_matching_response
        )

        result = await matching_service.match_job_to_profile(sample_job, sample_profile)

        # Verify the result
        assert result["match_score"] == 88
        assert result["recommendation"] == "strong_match"
        assert "skill_alignment" in result
        assert "local_metrics" in result

        # Verify repository calls
        mock_repository.create_job_match.assert_called_once()

    @pytest.mark.asyncio
    async def test_match_job_to_profile_with_existing_match(
        self,
        matching_service,
        sample_job,
        sample_profile,
        mock_repository
    ):
        """Test job matching when existing match exists."""
        # Mock existing match
        existing_match = Mock()
        existing_match.created_at = datetime.now()
        existing_match.match_score = 75
        existing_match.recommendation = "consider"
        existing_match.match_data = {"cached": True}

        mock_repository.get_job_match.return_value = existing_match

        result = await matching_service.match_job_to_profile(
            sample_job, sample_profile, force_refresh=False
        )

        # Should return cached result
        assert result["match_score"] == 75
        assert result["recommendation"] == "consider"
        assert "cached" in result

        # Should not call Claude API
        matching_service.claude_client.match_job_to_profile.assert_not_called()

    def test_calculate_local_matching_metrics(
        self,
        matching_service,
        sample_job,
        sample_profile
    ):
        """Test local matching metrics calculation."""
        metrics = matching_service._calculate_local_matching_metrics(sample_job, sample_profile)

        assert isinstance(metrics, MatchingMetrics)
        assert metrics.skill_match_score >= 0
        assert metrics.experience_match_score >= 0
        assert metrics.location_match_score >= 0
        assert metrics.salary_match_score >= 0
        assert metrics.overall_local_score >= 0

    def test_calculate_skill_match(self, matching_service, sample_job, sample_profile):
        """Test skill matching calculation."""
        score = matching_service._calculate_skill_match(sample_job, sample_profile)

        assert 0 <= score <= 100
        assert score > 30  # Should have reasonable match given sample data

    def test_calculate_experience_match(self, matching_service, sample_job, sample_profile):
        """Test experience matching calculation."""
        # Test exact match
        score = matching_service._calculate_experience_match(
            required_years=5,
            candidate_years=6
        )
        assert score >= 90

        # Test under-qualified
        score_low = matching_service._calculate_experience_match(
            required_years=10,
            candidate_years=3
        )
        assert score_low < 50

        # Test over-qualified
        score_high = matching_service._calculate_experience_match(
            required_years=3,
            candidate_years=15
        )
        assert 50 <= score_high <= 85  # Penalized but not too much

    def test_calculate_location_match(self, matching_service):
        """Test location matching calculation."""
        # Perfect remote match
        score = matching_service._calculate_location_match(
            job_location="Remote",
            preferred_locations=["Remote", "San Francisco"]
        )
        assert score == 100

        # City match
        score_city = matching_service._calculate_location_match(
            job_location="San Francisco, CA",
            preferred_locations=["San Francisco", "Remote"]
        )
        assert score_city >= 80

        # No match
        score_no_match = matching_service._calculate_location_match(
            job_location="New York, NY",
            preferred_locations=["Los Angeles", "Remote"]
        )
        assert score_no_match < 50

    def test_calculate_salary_match(self, matching_service):
        """Test salary matching calculation."""
        # Perfect match within range
        score = matching_service._calculate_salary_match(
            job_min=120000,
            job_max=150000,
            expected_min=110000,
            expected_max=140000
        )
        assert score >= 80

        # Below expectations
        score_low = matching_service._calculate_salary_match(
            job_min=80000,
            job_max=100000,
            expected_min=120000,
            expected_max=150000
        )
        assert score_low < 70  # Should be lower for below expectations

        # No salary info
        score_unknown = matching_service._calculate_salary_match(
            job_min=None,
            job_max=None,
            expected_min=100000,
            expected_max=130000
        )
        assert score_unknown == 50  # Neutral score

    def test_extract_required_years_from_job(self, matching_service):
        """Test extracting required years from job description."""
        # Test clear requirement
        description = "Looking for candidate with 5+ years of Python experience"
        years = matching_service._extract_required_years_from_job(description, "Senior")
        assert years == 5

        # Test experience level fallback
        years_fallback = matching_service._extract_required_years_from_job("", "Senior")
        assert years_fallback == 5  # Senior level default

        # Test junior level
        years_junior = matching_service._extract_required_years_from_job("", "Entry")
        assert years_junior == 0

    def test_extract_job_skills(self, matching_service, sample_job):
        """Test skill extraction from job description."""
        skills = matching_service._extract_job_skills(sample_job)

        assert "python" in skills
        assert "django" in skills
        assert "sql" in skills
        assert "aws" in skills

    @pytest.mark.asyncio
    async def test_find_matching_jobs_for_profile(
        self,
        matching_service,
        sample_profile,
        mock_job_repository
    ):
        """Test finding matching jobs for a user profile."""
        # Mock jobs returned by search
        matching_jobs = [
            JobModel(
                id=1, title="Python Developer", company="TechCorp",
                location="Remote", description="Python role", url="", linkedin_job_id="1"
            ),
            JobModel(
                id=2, title="Full Stack Developer", company="WebCorp",
                location="San Francisco", description="Full stack role", url="", linkedin_job_id="2"
            )
        ]

        mock_job_repository.search_jobs.return_value = matching_jobs

        jobs = await matching_service.find_matching_jobs_for_profile(sample_profile)

        # Should have called search multiple times for different criteria
        assert mock_job_repository.search_jobs.call_count >= 2
        assert len(jobs) <= 50  # Max limit

    @pytest.mark.asyncio
    async def test_batch_match_jobs_to_profile(
        self,
        matching_service,
        sample_profile,
        claude_matching_response,
        mock_repository
    ):
        """Test batch matching jobs to profile."""
        jobs = [
            JobModel(
                id=i, title=f"Job {i}", company=f"Company {i}",
                location="Remote", description=f"Job {i} description",
                url="", linkedin_job_id=str(i)
            )
            for i in range(1, 4)
        ]

        # Mock repository
        mock_repository.get_job_match.return_value = None
        mock_repository.create_job_match.return_value = Mock(id=1)

        # Mock Claude client
        matching_service.claude_client.match_job_to_profile = AsyncMock(
            return_value=claude_matching_response
        )

        results = await matching_service.batch_match_jobs_to_profile(sample_profile, jobs)

        assert len(results) == 3
        assert all("match_score" in result for result in results)

    def test_get_profile_matching_summary(
        self,
        matching_service,
        mock_repository
    ):
        """Test profile matching summary generation."""
        # Mock job matches
        matches = [
            Mock(
                match_score=90,
                recommendation="strong_match",
                skill_match_score=85,
                experience_match_score=95,
                location_match_score=100,
                salary_match_score=80
            ),
            Mock(
                match_score=75,
                recommendation="consider",
                skill_match_score=70,
                experience_match_score=80,
                location_match_score=60,
                salary_match_score=70
            ),
            Mock(
                match_score=60,
                recommendation="skip",
                skill_match_score=55,
                experience_match_score=65,
                location_match_score=40,
                salary_match_score=50
            )
        ]

        mock_repository.get_job_matches_for_profile.return_value = matches

        summary = matching_service.get_profile_matching_summary(123)

        assert "total_matches" in summary
        assert "average_match_score" in summary
        assert "recommendation_breakdown" in summary
        assert "skill_insights" in summary

    def test_should_use_cached_match(self, matching_service):
        """Test cache decision logic."""
        # Recent match - should use cache
        recent_match = Mock()
        recent_match.created_at = datetime.now()

        assert matching_service._should_use_cached_match(recent_match, force_refresh=False) is True
        assert matching_service._should_use_cached_match(recent_match, force_refresh=True) is False

        # Old match - should not use cache
        old_match = Mock()
        old_match.created_at = datetime(2023, 1, 1)

        assert matching_service._should_use_cached_match(old_match, force_refresh=False) is False

    def test_enrich_match_result(self, matching_service, sample_job, sample_profile):
        """Test enriching Claude match with local metrics."""
        claude_result = {
            "match_score": 85,
            "recommendation": "strong_match"
        }

        local_metrics = MatchingMetrics(
            skill_match_score=80,
            experience_match_score=90,
            location_match_score=100,
            salary_match_score=75,
            overall_local_score=86
        )

        enriched = matching_service._enrich_match_result(claude_result, local_metrics)

        assert "local_metrics" in enriched
        assert enriched["local_metrics"]["skill_match_score"] == 80
        assert enriched["local_metrics"]["overall_local_score"] == 86

    @pytest.mark.asyncio
    async def test_match_with_local_fallback(
        self,
        matching_service,
        sample_job,
        sample_profile,
        mock_repository
    ):
        """Test fallback to local matching when Claude API fails."""
        mock_repository.get_job_match.return_value = None
        mock_repository.create_job_match.return_value = Mock(id=1)

        # Mock API failure
        matching_service.claude_client.match_job_to_profile = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await matching_service.match_job_to_profile(
            sample_job, sample_profile, use_local_fallback=True
        )

        # Should return local analysis
        assert "match_score" in result
        assert "analysis_type" in result
        assert result["analysis_type"] == "local_fallback"

    def test_generate_match_recommendation(self, matching_service):
        """Test match recommendation generation."""
        # Strong match
        rec = matching_service._generate_match_recommendation(90)
        assert rec == "strong_match"

        # Good match
        rec_good = matching_service._generate_match_recommendation(75)
        assert rec_good == "apply"

        # Consider
        rec_consider = matching_service._generate_match_recommendation(60)
        assert rec_consider == "consider"

        # Skip
        rec_skip = matching_service._generate_match_recommendation(30)
        assert rec_skip == "skip"