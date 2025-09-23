"""Tests for the comprehensive analysis engine."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.database.models import JobModel
from src.analyzer.models import UserProfileModel
from src.analyzer.analysis_engine import AnalysisEngine, AnalysisResult, EngineConfig
from src.analyzer.claude_client import ClaudeClient, ClaudeConfig


class TestAnalysisEngine:
    """Test AnalysisEngine functionality."""

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
    def engine_config(self):
        """Engine configuration for testing."""
        return EngineConfig(
            enable_quality_analysis=True,
            enable_competition_analysis=True,
            enable_job_matching=True,
            batch_size=3,
            claude_config=ClaudeConfig(cost_limit_per_hour=5.0)
        )

    @pytest.fixture
    def analysis_engine(self, engine_config, mock_claude_client, mock_repository, mock_job_repository):
        """Create analysis engine instance."""
        with patch('src.analyzer.analysis_engine.JobQualityService') as mock_quality_service, \
             patch('src.analyzer.analysis_engine.CompetitionAnalysisService') as mock_competition_service, \
             patch('src.analyzer.analysis_engine.JobMatchingService') as mock_matching_service:

            engine = AnalysisEngine(
                claude_client=mock_claude_client,
                repository=mock_repository,
                job_repository=mock_job_repository,
                config=engine_config
            )

            engine.quality_service = mock_quality_service.return_value
            engine.competition_service = mock_competition_service.return_value
            engine.matching_service = mock_matching_service.return_value

            return engine

    @pytest.fixture
    def sample_job(self):
        """Sample job for testing."""
        return JobModel(
            id=1,
            title="Senior Python Developer",
            company="TechCorp Inc.",
            location="Remote",
            description="Python development role with 5+ years experience required",
            url="https://linkedin.com/jobs/12345",
            linkedin_job_id="12345",
            employment_type="Full-time",
            experience_level="Senior"
        )

    @pytest.fixture
    def sample_profile(self):
        """Sample user profile for testing."""
        return UserProfileModel(
            id=1,
            user_id="user123",
            skills=["Python", "Django", "PostgreSQL"],
            experience_years=6,
            desired_roles=["Senior Python Developer"],
            preferred_locations=["Remote"]
        )

    def test_engine_initialization(self, engine_config, mock_claude_client, mock_repository, mock_job_repository):
        """Test engine initialization."""
        with patch('src.analyzer.analysis_engine.JobQualityService') as mock_quality_service, \
             patch('src.analyzer.analysis_engine.CompetitionAnalysisService') as mock_competition_service, \
             patch('src.analyzer.analysis_engine.JobMatchingService') as mock_matching_service:

            engine = AnalysisEngine(
                claude_client=mock_claude_client,
                repository=mock_repository,
                job_repository=mock_job_repository,
                config=engine_config
            )

            assert engine.claude_client == mock_claude_client
            assert engine.repository == mock_repository
            assert engine.job_repository == mock_job_repository
            assert engine.config == engine_config

    @pytest.mark.asyncio
    async def test_analyze_job_comprehensive(
        self,
        analysis_engine,
        sample_job
    ):
        """Test comprehensive job analysis."""
        # Mock service responses
        analysis_engine.quality_service.analyze_job_quality = AsyncMock(
            return_value={"quality_score": 85, "reasoning": "Good job"}
        )
        analysis_engine.competition_service.analyze_competition = AsyncMock(
            return_value={"competition_level": "medium", "success_probability": 60}
        )

        result = await analysis_engine.analyze_job_comprehensive(sample_job)

        assert isinstance(result, AnalysisResult)
        assert result.job_id == 1
        assert result.quality_analysis is not None
        assert result.competition_analysis is not None
        assert result.success is True

        # Verify service calls
        analysis_engine.quality_service.analyze_job_quality.assert_called_once_with(
            sample_job, force_refresh=False
        )
        analysis_engine.competition_service.analyze_competition.assert_called_once_with(
            sample_job, force_refresh=False
        )

    @pytest.mark.asyncio
    async def test_analyze_job_comprehensive_with_profile(
        self,
        analysis_engine,
        sample_job,
        sample_profile
    ):
        """Test comprehensive job analysis with user profile matching."""
        # Mock service responses
        analysis_engine.quality_service.analyze_job_quality = AsyncMock(
            return_value={"quality_score": 85}
        )
        analysis_engine.competition_service.analyze_competition = AsyncMock(
            return_value={"competition_level": "medium"}
        )
        analysis_engine.matching_service.match_job_to_profile = AsyncMock(
            return_value={"match_score": 88, "recommendation": "strong_match"}
        )

        result = await analysis_engine.analyze_job_comprehensive(
            sample_job,
            user_profile=sample_profile
        )

        assert result.matching_analysis is not None
        assert result.matching_analysis["match_score"] == 88

        # Verify matching service called
        analysis_engine.matching_service.match_job_to_profile.assert_called_once_with(
            sample_job, sample_profile, force_refresh=False
        )

    @pytest.mark.asyncio
    async def test_analyze_job_selective_analysis(
        self,
        analysis_engine,
        sample_job
    ):
        """Test selective analysis (only quality)."""
        analysis_engine.quality_service.analyze_job_quality = AsyncMock(
            return_value={"quality_score": 85}
        )

        result = await analysis_engine.analyze_job_comprehensive(
            sample_job,
            include_quality=True,
            include_competition=False,
            include_matching=False
        )

        assert result.quality_analysis is not None
        assert result.competition_analysis is None
        assert result.matching_analysis is None

        # Verify only quality service called
        analysis_engine.quality_service.analyze_job_quality.assert_called_once()
        analysis_engine.competition_service.analyze_competition.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_analyze_jobs(
        self,
        analysis_engine,
        mock_job_repository
    ):
        """Test batch job analysis."""
        # Mock jobs
        jobs = [
            JobModel(id=i, title=f"Job {i}", company=f"Co {i}",
                    location="Remote", description=f"Desc {i}",
                    url="", linkedin_job_id=str(i))
            for i in range(1, 4)
        ]

        # Mock service responses
        analysis_engine.quality_service.batch_analyze_jobs = AsyncMock(
            return_value=[{"job_id": i, "quality_score": 80} for i in range(1, 4)]
        )
        analysis_engine.competition_service.batch_analyze_competition = AsyncMock(
            return_value=[{"job_id": i, "competition_level": "medium"} for i in range(1, 4)]
        )

        results = await analysis_engine.batch_analyze_jobs(jobs)

        assert len(results) == 3
        assert all(isinstance(result, AnalysisResult) for result in results)
        assert all(result.success for result in results)

    @pytest.mark.asyncio
    async def test_find_and_analyze_matching_jobs(
        self,
        analysis_engine,
        sample_profile
    ):
        """Test finding and analyzing matching jobs for a profile."""
        # Mock matching jobs
        matching_jobs = [
            JobModel(id=1, title="Python Dev", company="TechCorp",
                    location="Remote", description="Python role",
                    url="", linkedin_job_id="1"),
            JobModel(id=2, title="Senior Dev", company="WebCorp",
                    location="SF", description="Senior role",
                    url="", linkedin_job_id="2")
        ]

        analysis_engine.matching_service.find_matching_jobs_for_profile = AsyncMock(
            return_value=matching_jobs
        )
        analysis_engine.matching_service.batch_match_jobs_to_profile = AsyncMock(
            return_value=[
                {"job_id": 1, "match_score": 85},
                {"job_id": 2, "match_score": 75}
            ]
        )

        results = await analysis_engine.find_and_analyze_matching_jobs(
            sample_profile,
            max_jobs=10
        )

        assert len(results) == 2
        assert all("match_score" in result for result in results)

    def test_get_analysis_summary(
        self,
        analysis_engine,
        mock_repository
    ):
        """Test getting comprehensive analysis summary."""
        # Mock repository stats
        mock_repository.get_analysis_statistics.return_value = {
            "total_analyses": 100,
            "completed_analyses": 85,
            "average_scores": {"quality": 78.5}
        }

        # Mock repository session query for quality insights
        mock_repository.session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        analysis_engine.quality_service.get_quality_insights_summary = Mock(
            return_value={"average_score": 78.5}
        )
        analysis_engine.competition_service.get_market_intelligence_summary = Mock(
            return_value={"total_jobs_analyzed": 50}
        )

        # Mock Claude client usage stats
        analysis_engine.claude_client.get_usage_stats.return_value = {
            "total_cost": 5.0,
            "cost_limit": 10.0,
            "request_count": 25,
            "circuit_breaker_open": False
        }

        summary = analysis_engine.get_analysis_summary()

        assert "analysis_statistics" in summary
        assert "quality_insights" in summary
        assert "market_intelligence" in summary
        assert "generated_at" in summary

    @pytest.mark.asyncio
    async def test_analyze_job_with_error_handling(
        self,
        analysis_engine,
        sample_job
    ):
        """Test error handling in job analysis."""
        # Mock service error
        analysis_engine.quality_service.analyze_job_quality = AsyncMock(
            side_effect=Exception("API Error")
        )
        analysis_engine.competition_service.analyze_competition = AsyncMock(
            return_value={"competition_level": "medium"}
        )

        result = await analysis_engine.analyze_job_comprehensive(sample_job)

        # Should still return result with partial analysis
        assert isinstance(result, AnalysisResult)
        assert result.success is False
        assert result.quality_analysis is None  # Failed
        assert result.competition_analysis is not None  # Succeeded
        assert any("API Error" in error for error in result.errors)

    def test_config_validation(self):
        """Test engine configuration validation."""
        # Valid config
        config = EngineConfig(
            enable_quality_analysis=True,
            batch_size=5,
            claude_config=ClaudeConfig()
        )
        assert config.batch_size == 5

        # Invalid batch size
        with pytest.raises(ValueError):
            EngineConfig(batch_size=0)

        with pytest.raises(ValueError):
            EngineConfig(batch_size=101)

    def test_cost_management(self, analysis_engine):
        """Test cost management functionality."""
        # Mock Claude client stats
        analysis_engine.claude_client.get_usage_stats.return_value = {
            "total_cost": 8.5,
            "cost_limit": 10.0,
            "request_count": 50
        }

        stats = analysis_engine.get_cost_usage_stats()

        assert stats["total_cost"] == 8.5
        assert stats["cost_limit"] == 10.0
        assert stats["requests_remaining"] > 0

    def test_should_throttle_analysis(self, analysis_engine):
        """Test analysis throttling logic."""
        # Mock high cost usage
        analysis_engine.claude_client.get_usage_stats.return_value = {
            "total_cost": 9.8,
            "cost_limit": 10.0
        }

        assert analysis_engine._should_throttle_analysis() is True

        # Mock normal usage
        analysis_engine.claude_client.get_usage_stats.return_value = {
            "total_cost": 5.0,
            "cost_limit": 10.0
        }

        assert analysis_engine._should_throttle_analysis() is False

    @pytest.mark.asyncio
    async def test_throttled_analysis(
        self,
        analysis_engine,
        sample_job
    ):
        """Test analysis with throttling enabled."""
        # Mock high cost to trigger throttling
        analysis_engine.claude_client.get_usage_stats.return_value = {
            "total_cost": 9.9,
            "cost_limit": 10.0
        }

        result = await analysis_engine.analyze_job_comprehensive(sample_job)

        # Should return throttled result
        assert result.success is False
        assert "throttled" in result.errors[0].lower()

    def test_analysis_result_to_dict(self, sample_job):
        """Test converting analysis result to dictionary."""
        result = AnalysisResult(
            job_id=1,
            quality_analysis={"quality_score": 85},
            competition_analysis={"competition_level": "medium"},
            matching_analysis={"match_score": 88},
            success=True,
            processing_time_seconds=2.5
        )

        result_dict = result.to_dict()

        assert result_dict["job_id"] == 1
        assert result_dict["quality_analysis"]["quality_score"] == 85
        assert result_dict["success"] is True
        assert result_dict["processing_time_seconds"] == 2.5