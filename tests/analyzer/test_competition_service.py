"""Tests for competitive intelligence analysis service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.database.models import JobModel
from src.analyzer.models import CompetitionAnalysisModel
from src.analyzer.services.competition_service import CompetitionAnalysisService, CompetitionMetrics
from src.analyzer.claude_client import ClaudeClient


class TestCompetitionAnalysisService:
    """Test CompetitionAnalysisService functionality."""

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
    def competition_service(self, mock_claude_client, mock_repository, mock_job_repository):
        """Create competition service instance."""
        return CompetitionAnalysisService(
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
            location="San Francisco, CA",
            description="Looking for a senior Python developer with 5+ years experience...",
            url="https://linkedin.com/jobs/12345",
            linkedin_job_id="12345",
            employment_type="Full-time",
            experience_level="Senior",
            applicant_count=45
        )

    @pytest.fixture
    def claude_competition_response(self):
        """Mock Claude API response for competition analysis."""
        return {
            "competition_level": "high",
            "analysis": "High competition due to attractive salary and remote work option",
            "success_probability": 25,
            "strategic_advice": "Apply early and highlight unique skills",
            "application_timing": "within 24 hours",
            "differentiation_tips": [
                "Emphasize full-stack capabilities",
                "Show open source contributions",
                "Highlight leadership experience"
            ]
        }

    @pytest.fixture
    def similar_jobs(self):
        """Sample similar jobs for competition analysis."""
        return [
            JobModel(
                id=2, title="Python Developer", company="StartupCorp",
                location="San Francisco, CA", applicant_count=30,
                description="Python developer position", url="", linkedin_job_id="job2"
            ),
            JobModel(
                id=3, title="Senior Backend Developer", company="BigTech",
                location="San Francisco, CA", applicant_count=60,
                description="Backend development role", url="", linkedin_job_id="job3"
            ),
            JobModel(
                id=4, title="Full Stack Python Developer", company="MediumCorp",
                location="Remote", applicant_count=25,
                description="Full stack Python role", url="", linkedin_job_id="job4"
            )
        ]

    def test_service_initialization(self, mock_claude_client, mock_repository, mock_job_repository):
        """Test service initialization."""
        service = CompetitionAnalysisService(
            claude_client=mock_claude_client,
            repository=mock_repository,
            job_repository=mock_job_repository
        )

        assert service.claude_client == mock_claude_client
        assert service.repository == mock_repository
        assert service.job_repository == mock_job_repository

    @pytest.mark.asyncio
    async def test_analyze_competition_success(
        self,
        competition_service,
        sample_job,
        claude_competition_response,
        similar_jobs,
        mock_repository,
        mock_job_repository
    ):
        """Test successful competition analysis."""
        # Mock repository responses
        mock_repository.get_competition_analysis_for_job.return_value = None
        mock_analysis = Mock()
        mock_analysis.id = 1
        mock_repository.create_competition_analysis.return_value = mock_analysis
        mock_repository.update_competition_analysis.return_value = mock_analysis

        # Mock job repository for finding similar jobs
        mock_job_repository.search_jobs.return_value = similar_jobs

        # Mock Claude client response
        competition_service.claude_client.analyze_competition = AsyncMock(
            return_value=claude_competition_response
        )

        result = await competition_service.analyze_competition(sample_job)

        # Verify the result
        assert result["competition_level"] == "high"
        assert result["success_probability"] == 25
        assert "market_analysis" in result
        assert "similar_jobs_count" in result["market_analysis"]

        # Verify repository calls
        mock_repository.create_competition_analysis.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_competition_with_existing_analysis(
        self,
        competition_service,
        sample_job,
        mock_repository
    ):
        """Test competition analysis when recent analysis exists."""
        # Mock existing analysis
        existing_analysis = Mock()
        existing_analysis.created_at = datetime.now()
        existing_analysis.competition_level = "medium"
        existing_analysis.success_probability = 60
        existing_analysis.analysis_data = {"cached": True}

        mock_repository.get_competition_analysis_for_job.return_value = existing_analysis

        result = await competition_service.analyze_competition(sample_job, force_refresh=False)

        # Should return cached result
        assert result["competition_level"] == "medium"
        assert result["success_probability"] == 60
        assert "cached" in result

        # Should not call Claude API
        competition_service.claude_client.analyze_competition.assert_not_called()

    def test_calculate_market_metrics(
        self,
        competition_service,
        sample_job,
        similar_jobs,
        mock_job_repository
    ):
        """Test market metrics calculation."""
        mock_job_repository.search_jobs.return_value = similar_jobs

        metrics = competition_service._calculate_market_metrics(sample_job)

        assert isinstance(metrics, CompetitionMetrics)
        assert metrics.similar_jobs_count == 3
        assert metrics.average_applicant_count > 0
        assert metrics.position_in_market in ["low", "medium", "high"]
        assert metrics.market_saturation_score >= 0

    def test_find_similar_jobs(
        self,
        competition_service,
        sample_job,
        similar_jobs,
        mock_job_repository
    ):
        """Test finding similar jobs."""
        mock_job_repository.search_jobs.return_value = similar_jobs

        found_jobs = competition_service._find_similar_jobs(sample_job)

        # Should have called search multiple times for different criteria
        assert mock_job_repository.search_jobs.call_count >= 3
        assert len(found_jobs) == 3

    def test_classify_competition_level(self, competition_service):
        """Test competition level classification."""
        # Test different applicant counts
        assert competition_service._classify_competition_level(5) == "low"
        assert competition_service._classify_competition_level(25) == "medium"
        assert competition_service._classify_competition_level(75) == "high"

    def test_calculate_success_probability(self, competition_service):
        """Test success probability calculation."""
        # Test different scenarios
        prob_low = competition_service._calculate_success_probability(
            applicant_count=10,
            similar_jobs_count=2,
            market_position="low"
        )

        prob_high = competition_service._calculate_success_probability(
            applicant_count=100,
            similar_jobs_count=20,
            market_position="high"
        )

        assert prob_low > prob_high
        assert 0 <= prob_low <= 100
        assert 0 <= prob_high <= 100

    def test_generate_strategic_advice(self, competition_service):
        """Test strategic advice generation."""
        advice = competition_service._generate_strategic_advice(
            competition_level="high",
            applicant_count=50,
            market_metrics=CompetitionMetrics(
                similar_jobs_count=10,
                average_applicant_count=45,
                position_in_market="medium",
                market_saturation_score=75,
                keyword_match_scores=[0.5, 0.3, 0.8],
                location_competition_factor=1.2
            )
        )

        assert isinstance(advice, dict)
        assert "application_timing" in advice
        assert "differentiation_strategies" in advice
        assert "success_factors" in advice

    @pytest.mark.asyncio
    async def test_batch_analyze_competition(
        self,
        competition_service,
        similar_jobs,
        mock_repository,
        mock_job_repository
    ):
        """Test batch competition analysis."""
        # Mock repository responses
        mock_repository.get_competition_analysis_for_job.return_value = None
        mock_repository.create_competition_analysis.return_value = Mock(id=1)
        mock_job_repository.search_jobs.return_value = []

        # Mock Claude client
        competition_service.claude_client.analyze_competition = AsyncMock(
            return_value={"competition_level": "medium", "success_probability": 60}
        )

        results = await competition_service.batch_analyze_competition(similar_jobs)

        assert len(results) == 3
        assert all("competition_level" in result for result in results)

    def test_get_market_intelligence_summary(
        self,
        competition_service,
        mock_repository
    ):
        """Test market intelligence summary generation."""
        # Mock competition analyses
        analyses = [
            Mock(
                competition_level="high",
                success_probability=20,
                applicant_count=80,
                market_demand_score=90,
                analysis_data={"tips": ["Apply early"]}
            ),
            Mock(
                competition_level="medium",
                success_probability=50,
                applicant_count=30,
                market_demand_score=60,
                analysis_data={"tips": ["Highlight skills"]}
            ),
            Mock(
                competition_level="low",
                success_probability=90,
                applicant_count=5,
                market_demand_score=30,
                analysis_data={"tips": ["Good opportunity"]}
            )
        ]

        mock_repository.session.query.return_value.all.return_value = analyses

        summary = competition_service.get_market_intelligence_summary()

        assert "total_jobs_analyzed" in summary
        assert "competition_distribution" in summary
        assert "average_success_probability" in summary
        assert "market_insights" in summary

    def test_should_use_cached_analysis(self, competition_service):
        """Test cache decision logic."""
        # Recent analysis - should use cache
        recent_analysis = Mock()
        recent_analysis.created_at = datetime.now()

        assert competition_service._should_use_cached_analysis(recent_analysis, force_refresh=False) is True
        assert competition_service._should_use_cached_analysis(recent_analysis, force_refresh=True) is False

        # Old analysis - should not use cache
        old_analysis = Mock()
        old_analysis.created_at = datetime(2023, 1, 1)

        assert competition_service._should_use_cached_analysis(old_analysis, force_refresh=False) is False

    def test_extract_job_keywords(self, competition_service):
        """Test keyword extraction from job descriptions."""
        job = JobModel(
            title="Senior Python Developer",
            description="Python, Django, REST API, PostgreSQL, AWS, Docker",
            location="",
            company="",
            url="",
            linkedin_job_id=""
        )

        keywords = competition_service._extract_job_keywords(job)

        assert "python" in keywords
        assert "django" in keywords
        assert "aws" in keywords
        assert len(keywords) > 3

    def test_calculate_keyword_overlap(self, competition_service):
        """Test keyword overlap calculation."""
        job1_keywords = {"python", "django", "postgresql", "aws"}
        job2_keywords = {"python", "flask", "mysql", "aws"}

        overlap = competition_service._calculate_keyword_overlap(job1_keywords, job2_keywords)

        # 2 intersection / 6 union = 0.33...
        assert overlap == pytest.approx(0.333, abs=0.01)

    def test_enrich_with_market_analysis(self, competition_service):
        """Test enriching Claude analysis with market data."""
        claude_result = {
            "competition_level": "high",
            "success_probability": 30
        }

        market_metrics = CompetitionMetrics(
            similar_jobs_count=15,
            average_applicant_count=45,
            position_in_market="high",
            market_saturation_score=80,
            keyword_match_scores=[0.6, 0.4, 0.9],
            location_competition_factor=1.3
        )

        enriched = competition_service._enrich_with_market_analysis(claude_result, market_metrics)

        assert "market_analysis" in enriched
        assert enriched["market_analysis"]["similar_jobs_count"] == 15
        assert enriched["market_analysis"]["average_applicant_count"] == 45

    @pytest.mark.asyncio
    async def test_analyze_competition_api_error(
        self,
        competition_service,
        sample_job,
        mock_repository,
        mock_job_repository
    ):
        """Test handling of Claude API errors."""
        mock_repository.get_competition_analysis_for_job.return_value = None
        mock_analysis = Mock(id=1)
        mock_repository.create_competition_analysis.return_value = mock_analysis
        mock_job_repository.search_jobs.return_value = []

        # Mock API error
        competition_service.claude_client.analyze_competition = AsyncMock(
            side_effect=Exception("API Error")
        )

        # Should fall back to local analysis
        result = await competition_service.analyze_competition(
            sample_job,
            use_local_fallback=True
        )

        assert "competition_level" in result
        assert "analysis_type" in result
        assert result["analysis_type"] == "local_fallback"