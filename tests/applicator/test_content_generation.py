"""Tests for content generation service."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch

from src.applicator.content_generation import (
    ContentGenerationService,
    ContentGenerationConfig,
    GeneratedContent
)
from src.applicator.models import ContentType
from src.applicator.repository import ApplicationRepository
from src.analyzer.claude_client import ClaudeClient, ClaudeConfig


class TestContentGenerationConfig:
    """Test cases for ContentGenerationConfig."""

    def test_config_creation(self):
        """Test creating content generation config."""
        claude_config = ClaudeConfig()
        config = ContentGenerationConfig(claude_config=claude_config)

        assert config.claude_config == claude_config
        assert config.min_quality_score == 70
        assert config.max_retry_attempts == 3
        assert config.use_fallback_templates is True

    def test_config_validation(self):
        """Test config validation."""
        claude_config = ClaudeConfig()

        # Valid config
        config = ContentGenerationConfig(
            claude_config=claude_config,
            min_quality_score=80,
            max_retry_attempts=2
        )
        assert config.min_quality_score == 80

        # Invalid quality score
        with pytest.raises(ValueError):
            ContentGenerationConfig(
                claude_config=claude_config,
                min_quality_score=101
            )

        # Invalid retry attempts
        with pytest.raises(ValueError):
            ContentGenerationConfig(
                claude_config=claude_config,
                max_retry_attempts=0
            )

        # Invalid claude config
        with pytest.raises(ValueError):
            ContentGenerationConfig(claude_config="not_a_config")


class TestContentGenerationService:
    """Test cases for ContentGenerationService."""

    @pytest.fixture
    def content_config(self):
        """Create content generation config."""
        claude_config = ClaudeConfig(model="claude-3-haiku-20240307")
        return ContentGenerationConfig(
            claude_config=claude_config,
            min_quality_score=75
        )

    @pytest.fixture
    def mock_claude_client(self):
        """Create mock Claude client."""
        mock_client = Mock(spec=ClaudeClient)
        mock_client.generate_content = AsyncMock()
        mock_client.get_stats = AsyncMock()
        return mock_client

    @pytest.fixture
    def app_repo(self, test_session):
        """Create application repository."""
        return ApplicationRepository(test_session)

    @pytest.fixture
    def content_service(self, content_config, app_repo, mock_claude_client):
        """Create content generation service."""
        return ContentGenerationService(content_config, app_repo, mock_claude_client)

    @pytest.mark.asyncio
    async def test_generate_cover_letter_success(self, content_service, sample_job, sample_user_profile):
        """Test successful cover letter generation."""
        # Mock Claude response
        claude_response = json.dumps({
            "cover_letter": "Dear Hiring Manager,\n\nI am excited to apply for the Senior Software Engineer position...",
            "quality_score": 85,
            "key_strengths_highlighted": ["Python", "5 years experience", "AWS"],
            "personalization_elements": ["Company-specific tech stack", "Role requirements"],
            "tone_analysis": "Professional and enthusiastic",
            "word_count": 287
        })

        content_service.claude.generate_content.return_value = claude_response
        content_service.claude.get_stats.side_effect = [
            {"total_cost": 0.10},  # Before
            {"total_cost": 0.15}   # After
        ]

        result = await content_service.generate_cover_letter(sample_job, sample_user_profile)

        assert isinstance(result, GeneratedContent)
        assert result.content_type == ContentType.COVER_LETTER
        assert result.quality_score == 85
        assert abs(result.generation_cost - 0.05) < 0.001  # Handle floating point precision
        assert "Senior Software Engineer" in result.content_text
        assert len(result.generation_metadata["key_strengths"]) == 3

    @pytest.mark.asyncio
    async def test_generate_cover_letter_with_custom_instructions(self, content_service, sample_job, sample_user_profile):
        """Test cover letter generation with custom instructions."""
        custom_instructions = "Emphasize remote work experience and team leadership"

        claude_response = json.dumps({
            "cover_letter": "Dear Hiring Manager,\n\nWith extensive remote work experience...",
            "quality_score": 88,
            "key_strengths_highlighted": ["Remote work", "Team leadership", "Python"],
            "personalization_elements": ["Remote work emphasis", "Leadership experience"],
            "tone_analysis": "Professional with leadership focus",
            "word_count": 295
        })

        content_service.claude.generate_content.return_value = claude_response
        content_service.claude.get_stats.side_effect = [
            {"total_cost": 0.20},
            {"total_cost": 0.25}
        ]

        result = await content_service.generate_cover_letter(
            sample_job,
            sample_user_profile,
            custom_instructions=custom_instructions
        )

        assert result.quality_score == 88
        assert "remote work" in result.content_text.lower()

        # Verify the prompt included custom instructions
        call_args = content_service.claude.generate_content.call_args[1]['prompt']
        assert custom_instructions in call_args

    @pytest.mark.asyncio
    async def test_generate_cover_letter_low_quality_retry(self, content_service, sample_job, sample_user_profile):
        """Test cover letter generation with low quality score triggering retry."""
        # Configure for retry
        content_service.config.min_quality_score = 80
        content_service.config.max_retry_attempts = 2

        # First response - low quality
        low_quality_response = json.dumps({
            "cover_letter": "Basic cover letter",
            "quality_score": 65,
            "key_strengths_highlighted": ["Python"],
            "personalization_elements": [],
            "tone_analysis": "Basic",
            "word_count": 50
        })

        # Second response - better quality
        high_quality_response = json.dumps({
            "cover_letter": "Excellent personalized cover letter...",
            "quality_score": 90,
            "key_strengths_highlighted": ["Python", "AWS", "Experience"],
            "personalization_elements": ["Company research", "Role-specific skills"],
            "tone_analysis": "Professional and engaging",
            "word_count": 320
        })

        content_service.claude.generate_content.side_effect = [
            low_quality_response,
            high_quality_response
        ]
        content_service.claude.get_stats.side_effect = [
            {"total_cost": 0.0}, {"total_cost": 0.05},  # First call
            {"total_cost": 0.05}, {"total_cost": 0.10}  # Second call
        ]

        result = await content_service.generate_cover_letter(sample_job, sample_user_profile)

        assert result.quality_score == 90
        assert content_service.claude.generate_content.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_cover_letter_fallback_on_error(self, content_service, sample_job, sample_user_profile):
        """Test cover letter generation fallback when Claude fails."""
        content_service.claude.generate_content.side_effect = Exception("Claude API error")

        result = await content_service.generate_cover_letter(sample_job, sample_user_profile)

        assert isinstance(result, GeneratedContent)
        assert result.content_type == ContentType.COVER_LETTER
        assert result.quality_score == 65  # Fallback quality score
        assert result.generation_metadata.get("fallback") is True
        assert sample_job.title in result.content_text
        assert sample_job.company in result.content_text

    @pytest.mark.asyncio
    async def test_generate_linkedin_message_application(self, content_service, sample_job, sample_user_profile):
        """Test LinkedIn application message generation."""
        claude_response = json.dumps({
            "message": "Hi, I'm interested in the Senior Software Engineer role at Tech Corp. With my 5 years of Python experience, I believe I'd be a great fit. Would love to connect!",
            "quality_score": 82,
            "tone": "Professional yet personable",
            "call_to_action": "Would love to connect",
            "word_count": 28
        })

        content_service.claude.generate_content.return_value = claude_response
        content_service.claude.get_stats.side_effect = [
            {"total_cost": 0.0},
            {"total_cost": 0.03}
        ]

        result = await content_service.generate_linkedin_message(
            sample_job,
            sample_user_profile,
            message_type="application"
        )

        assert result.content_type == ContentType.LINKEDIN_MESSAGE
        assert result.quality_score == 82
        assert result.generation_cost == 0.03
        assert sample_job.title in result.content_text
        assert sample_job.company in result.content_text

    @pytest.mark.asyncio
    async def test_generate_linkedin_message_connection(self, content_service, sample_job, sample_user_profile):
        """Test LinkedIn connection message generation."""
        claude_response = json.dumps({
            "message": "Hi, I'd like to connect regarding the Senior Software Engineer position. My background in Python and AWS aligns well with the role.",
            "quality_score": 80,
            "tone": "Professional networking",
            "call_to_action": "Connect to discuss opportunity",
            "word_count": 24
        })

        content_service.claude.generate_content.return_value = claude_response
        content_service.claude.get_stats.side_effect = [
            {"total_cost": 0.0},
            {"total_cost": 0.02}
        ]

        result = await content_service.generate_linkedin_message(
            sample_job,
            sample_user_profile,
            message_type="connection"
        )

        assert result.content_type == ContentType.LINKEDIN_MESSAGE
        assert result.generation_cost == 0.02
        assert "connect" in result.content_text.lower()

    @pytest.mark.asyncio
    async def test_store_generated_content(self, content_service, app_repo, sample_job, sample_user_profile):
        """Test storing generated content in database."""
        # Create application first
        application = app_repo.create_application(
            job_id=sample_job.id,
            user_profile_id=sample_user_profile.id
        )

        claude_response = json.dumps({
            "cover_letter": "Test cover letter content",
            "quality_score": 80,
            "key_strengths_highlighted": ["Python"],
            "personalization_elements": ["Custom element"],
            "tone_analysis": "Professional",
            "word_count": 150
        })

        content_service.claude.generate_content.return_value = claude_response
        content_service.claude.get_stats.side_effect = [
            {"total_cost": 0.0},
            {"total_cost": 0.04}
        ]

        result = await content_service.generate_cover_letter(
            sample_job,
            sample_user_profile,
            application_id=application.id
        )

        # Verify content was stored
        stored_content = app_repo.get_application_content(application.id, ContentType.COVER_LETTER)
        assert len(stored_content) == 1
        assert stored_content[0].content_text == "Test cover letter content"
        assert stored_content[0].quality_score == 80
        assert stored_content[0].generation_cost == 0.04

    @pytest.mark.asyncio
    async def test_skill_overlap_analysis(self, content_service, sample_job, sample_user_profile):
        """Test skill overlap analysis functionality."""
        # Update job description to include some of user's skills
        sample_job.description = "We are looking for a Python developer with React and AWS experience. SQL knowledge is a plus."

        overlap = content_service._analyze_skill_overlap(sample_job, sample_user_profile)

        # User has Python, JavaScript, React, SQL, AWS in profile
        assert "python" in overlap["matching"]
        assert "react" in overlap["matching"]
        assert "sql" in overlap["matching"]
        assert "aws" in overlap["matching"]

    def test_infer_company_tone(self, content_service, sample_job):
        """Test company tone inference."""
        # Test startup tone
        sample_job.description = "Join our fast-paced startup disrupting the industry with innovative solutions"
        tone = content_service._infer_company_tone(sample_job)
        assert tone == "dynamic and innovative"

        # Test corporate tone
        sample_job.description = "Established Fortune 500 enterprise seeks experienced professional"
        tone = content_service._infer_company_tone(sample_job)
        assert tone == "professional and formal"

        # Test creative tone
        sample_job.description = "Creative marketing team looking for brand design expert"
        tone = content_service._infer_company_tone(sample_job)
        assert tone == "creative and engaging"

        # Test default tone
        sample_job.description = "Software engineer needed for development work"
        tone = content_service._infer_company_tone(sample_job)
        assert tone == "professional and enthusiastic"

    @pytest.mark.asyncio
    async def test_get_generation_statistics(self, content_service, app_repo):
        """Test getting generation statistics."""
        # Mock repository stats
        with patch.object(app_repo, 'get_content_generation_stats') as mock_stats:
            mock_stats.return_value = {
                "total_content_generated": 10,
                "approved_content": 8,
                "approval_rate": 80.0,
                "cover_letter_count": 6,
                "linkedin_message_count": 4
            }

            stats = await content_service.get_generation_statistics()

            assert stats["total_content_generated"] == 10
            assert stats["approval_rate"] == 80.0
            assert "service_config" in stats
            assert stats["service_config"]["min_quality_score"] == 75
            assert stats["claude_model"] == "claude-3-haiku-20240307"

    def test_build_cover_letter_prompt(self, content_service, sample_job, sample_user_profile):
        """Test cover letter prompt building."""
        prompt = content_service._build_cover_letter_prompt(sample_job, sample_user_profile)

        # Check that all required elements are in prompt
        assert sample_job.title in prompt
        assert sample_job.company in prompt
        assert sample_job.location in prompt
        assert str(sample_user_profile.experience_years) in prompt
        assert "JSON" in prompt  # Response format instruction
        assert "cover_letter" in prompt
        assert "quality_score" in prompt

    def test_build_linkedin_message_prompt(self, content_service, sample_job, sample_user_profile):
        """Test LinkedIn message prompt building."""
        prompt = content_service._build_linkedin_message_prompt(
            sample_job, sample_user_profile, "application", None
        )

        assert sample_job.title in prompt
        assert sample_job.company in prompt
        assert "applying for the position" in prompt
        assert "JSON" in prompt
        assert "message" in prompt

    @pytest.mark.asyncio
    async def test_helper_generate_with_claude(self, content_service):
        """Test the helper method for Claude generation."""
        content_service.claude.generate_content.return_value = "Test response"
        content_service.claude.get_stats.side_effect = [
            {"total_cost": 1.0},
            {"total_cost": 1.25}
        ]

        response, cost = await content_service._generate_with_claude("Test prompt")

        assert response == "Test response"
        assert cost == 0.25
        content_service.claude.generate_content.assert_called_once_with(
            prompt="Test prompt",
            max_tokens=content_service.config.claude_config.max_tokens,
            temperature=content_service.config.claude_config.temperature
        )