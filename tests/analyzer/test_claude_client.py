"""Tests for Claude API client."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.analyzer.claude_client import ClaudeClient, ClaudeConfig, CircuitBreakerError
from src.database.models import JobModel


class TestClaudeConfig:
    """Test ClaudeConfig configuration class."""

    def test_default_config_creation(self):
        """Test creating default configuration."""
        config = ClaudeConfig()
        assert config.model == "claude-3-haiku-20240307"
        assert config.max_tokens == 1000
        assert config.temperature == 0.3
        assert config.max_retries == 3
        assert config.timeout == 30
        assert config.cost_limit_per_hour == 10.0
        assert config.circuit_breaker_failure_threshold == 5
        assert config.circuit_breaker_timeout == 300

    def test_custom_config_creation(self):
        """Test creating custom configuration."""
        config = ClaudeConfig(
            model="claude-3-sonnet-20240229",
            max_tokens=2000,
            temperature=0.7,
            cost_limit_per_hour=50.0
        )
        assert config.model == "claude-3-sonnet-20240229"
        assert config.max_tokens == 2000
        assert config.temperature == 0.7
        assert config.cost_limit_per_hour == 50.0

    def test_config_validation(self):
        """Test configuration validation."""
        with pytest.raises(ValueError):
            ClaudeConfig(temperature=1.5)  # Too high

        with pytest.raises(ValueError):
            ClaudeConfig(temperature=-0.5)  # Too low

        with pytest.raises(ValueError):
            ClaudeConfig(max_tokens=0)  # Too low


class TestClaudeClient:
    """Test Claude API client functionality."""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock Anthropic client."""
        with patch('src.analyzer.claude_client.Anthropic') as mock:
            client_instance = Mock()
            mock.return_value = client_instance
            yield client_instance

    @pytest.fixture
    def claude_config(self):
        """Claude configuration for testing."""
        return ClaudeConfig(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            cost_limit_per_hour=5.0
        )

    @pytest.fixture
    def claude_client(self, claude_config, mock_anthropic_client):
        """Claude client instance for testing."""
        return ClaudeClient(api_key="test-key", config=claude_config)

    @pytest.fixture
    def sample_job(self):
        """Sample job for testing."""
        return JobModel(
            title="Senior Python Developer",
            company="TechCorp",
            location="Remote",
            description="We are looking for a senior Python developer with 5+ years of experience...",
            url="https://linkedin.com/jobs/123",
            linkedin_job_id="123456",
            employment_type="Full-time",
            experience_level="Senior",
            applicant_count=25
        )

    def test_client_initialization(self, claude_config):
        """Test client initialization."""
        with patch('src.analyzer.claude_client.Anthropic'):
            client = ClaudeClient(api_key="test-key", config=claude_config)
            assert client.config == claude_config
            assert client.api_key == "test-key"
            assert client._request_count == 0
            assert client._total_cost == 0.0

    def test_cost_tracking(self, claude_client):
        """Test cost tracking functionality."""
        claude_client._add_cost(2.5)
        assert claude_client._total_cost == 2.5

        claude_client._add_cost(1.5)
        assert claude_client._total_cost == 4.0

        # Test cost limit exceeded
        claude_client._add_cost(10.0)
        with pytest.raises(ValueError, match="Cost limit exceeded"):
            claude_client._check_cost_limit()

    def test_circuit_breaker_functionality(self, claude_client):
        """Test circuit breaker pattern."""
        # Simulate failures
        for _ in range(claude_client.config.circuit_breaker_failure_threshold):
            claude_client._circuit_breaker_failures += 1

        claude_client._circuit_breaker_last_failure = datetime.now()

        assert claude_client._is_circuit_breaker_open()

        with pytest.raises(CircuitBreakerError):
            claude_client._check_circuit_breaker()

    @pytest.mark.asyncio
    async def test_analyze_job_quality_success(self, claude_client, mock_anthropic_client, sample_job):
        """Test successful job quality analysis."""
        # Mock API response
        mock_response = Mock()
        mock_response.content = [Mock(text='{"quality_score": 85, "reasoning": "Strong technical requirements"}')]
        mock_anthropic_client.messages.create.return_value = mock_response

        result = await claude_client.analyze_job_quality(sample_job)

        assert result["quality_score"] == 85
        assert "reasoning" in result
        assert claude_client._request_count == 1
        assert claude_client._total_cost > 0

    @pytest.mark.asyncio
    async def test_analyze_job_quality_api_error(self, claude_client, mock_anthropic_client, sample_job):
        """Test job quality analysis with API error."""
        mock_anthropic_client.messages.create.side_effect = Exception("API Error")

        with pytest.raises(Exception):
            await claude_client.analyze_job_quality(sample_job)

        # Circuit breaker should record failure
        assert claude_client._circuit_breaker_failures == 1

    @pytest.mark.asyncio
    async def test_analyze_competition_success(self, claude_client, mock_anthropic_client, sample_job):
        """Test successful competition analysis."""
        mock_response = Mock()
        mock_response.content = [Mock(text='{"competition_level": "medium", "analysis": "Moderate competition"}')]
        mock_anthropic_client.messages.create.return_value = mock_response

        result = await claude_client.analyze_competition(sample_job)

        assert result["competition_level"] == "medium"
        assert "analysis" in result

    @pytest.mark.asyncio
    async def test_match_job_to_profile_success(self, claude_client, mock_anthropic_client, sample_job):
        """Test successful job matching."""
        user_profile = {
            "skills": ["Python", "Django", "REST API"],
            "experience_years": 6,
            "preferred_locations": ["Remote"],
            "desired_salary": 120000
        }

        mock_response = Mock()
        mock_response.content = [Mock(text='{"match_score": 92, "explanation": "Excellent match"}')]
        mock_anthropic_client.messages.create.return_value = mock_response

        result = await claude_client.match_job_to_profile(sample_job, user_profile)

        assert result["match_score"] == 92
        assert "explanation" in result

    def test_build_job_analysis_prompt(self, claude_client, sample_job):
        """Test prompt building for job analysis."""
        prompt = claude_client._build_job_analysis_prompt(sample_job)

        assert sample_job.title in prompt
        assert sample_job.company in prompt
        assert sample_job.description in prompt
        assert "quality_score" in prompt

    def test_build_competition_prompt(self, claude_client, sample_job):
        """Test prompt building for competition analysis."""
        prompt = claude_client._build_competition_prompt(sample_job)

        assert sample_job.title in prompt
        assert str(sample_job.applicant_count) in prompt
        assert "competition_level" in prompt

    def test_build_matching_prompt(self, claude_client, sample_job):
        """Test prompt building for job matching."""
        user_profile = {"skills": ["Python"], "experience_years": 5}
        prompt = claude_client._build_matching_prompt(sample_job, user_profile)

        assert sample_job.title in prompt
        assert "Python" in prompt
        assert "match_score" in prompt

    @pytest.mark.asyncio
    async def test_batch_analysis(self, claude_client, mock_anthropic_client):
        """Test batch job analysis."""
        jobs = [
            JobModel(title="Job 1", company="Co1", location="Loc1",
                    description="Desc1", url="url1", linkedin_job_id="1"),
            JobModel(title="Job 2", company="Co2", location="Loc2",
                    description="Desc2", url="url2", linkedin_job_id="2")
        ]

        mock_response = Mock()
        mock_response.content = [Mock(text='{"quality_score": 80, "reasoning": "Good"}')]
        mock_anthropic_client.messages.create.return_value = mock_response

        results = await claude_client.batch_analyze_jobs(jobs, "quality")

        assert len(results) == 2
        assert all("quality_score" in result for result in results)

    def test_get_usage_stats(self, claude_client):
        """Test usage statistics."""
        claude_client._request_count = 10
        claude_client._total_cost = 5.5

        stats = claude_client.get_usage_stats()

        assert stats["request_count"] == 10
        assert stats["total_cost"] == 5.5
        assert "cost_limit" in stats
        assert "circuit_breaker_failures" in stats

    def test_reset_circuit_breaker(self, claude_client):
        """Test circuit breaker reset."""
        claude_client._circuit_breaker_failures = 3
        claude_client._circuit_breaker_last_failure = datetime.now()

        claude_client.reset_circuit_breaker()

        assert claude_client._circuit_breaker_failures == 0
        assert claude_client._circuit_breaker_last_failure is None