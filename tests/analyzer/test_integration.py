"""Integration tests for the job analysis engine."""

import pytest
import os
from unittest.mock import patch, Mock

from src.analyzer.factory import (
    create_analysis_engine,
    create_analysis_engine_from_env,
    validate_analysis_engine_requirements,
    get_analysis_engine_config_summary
)
from src.analyzer.analysis_engine import AnalysisEngine
from src.analyzer.claude_client import ClaudeConfig
from src.analyzer.analysis_engine import EngineConfig


class TestAnalysisEngineIntegration:
    """Test analysis engine integration and factory functions."""

    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'test-key-123',
        'CLAUDE_COST_LIMIT_PER_HOUR': '15.0',
        'CLAUDE_MODEL': 'claude-3-sonnet-20240229',
        'ANALYSIS_BATCH_SIZE': '3'
    })
    @patch('src.analyzer.factory.get_db_session')
    @patch('src.analyzer.factory.ClaudeClient')
    def test_create_analysis_engine_from_env(self, mock_claude_client, mock_get_db_session):
        """Test creating analysis engine from environment variables."""
        # Mock database session
        mock_session = Mock()
        mock_get_db_session.return_value = iter([mock_session])

        # Mock Claude client
        mock_claude_client.return_value = Mock()

        engine = create_analysis_engine_from_env()

        assert isinstance(engine, AnalysisEngine)

        # Verify Claude client was created with correct config
        call_args = mock_claude_client.call_args
        assert call_args[1]['api_key'] == 'test-key-123'

        claude_config = call_args[1]['config']
        assert claude_config.model == 'claude-3-sonnet-20240229'
        assert claude_config.cost_limit_per_hour == 15.0

    @patch('src.analyzer.factory.get_db_session')
    @patch('src.analyzer.factory.ClaudeClient')
    def test_create_analysis_engine_with_custom_config(self, mock_claude_client, mock_get_db_session):
        """Test creating analysis engine with custom configuration."""
        # Mock database session
        mock_session = Mock()
        mock_get_db_session.return_value = iter([mock_session])

        # Mock Claude client
        mock_claude_client.return_value = Mock()

        # Custom configurations
        claude_config = ClaudeConfig(
            model='claude-3-haiku-20240307',
            cost_limit_per_hour=5.0,
            max_tokens=500
        )

        engine_config = EngineConfig(
            enable_quality_analysis=True,
            enable_competition_analysis=False,
            enable_job_matching=True,
            batch_size=2
        )

        engine = create_analysis_engine(
            api_key='custom-key',
            claude_config=claude_config,
            engine_config=engine_config
        )

        assert isinstance(engine, AnalysisEngine)
        assert engine.config.batch_size == 2
        assert engine.config.enable_competition_analysis is False

    def test_create_analysis_engine_no_api_key(self):
        """Test error handling when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Anthropic API key must be provided"):
                create_analysis_engine()

    @patch('src.analyzer.factory.get_db_session')
    def test_create_analysis_engine_database_error(self, mock_get_db_session):
        """Test error handling when database connection fails."""
        # Mock database connection failure
        mock_get_db_session.side_effect = Exception("Database connection failed")

        with pytest.raises(RuntimeError, match="Database connection failed"):
            create_analysis_engine(api_key='test-key')

    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'test-key',
        'CLAUDE_COST_LIMIT_PER_HOUR': '20.0',
        'ENABLE_QUALITY_ANALYSIS': 'false'
    })
    def test_get_analysis_engine_config_summary(self):
        """Test getting configuration summary."""
        summary = get_analysis_engine_config_summary()

        assert summary['anthropic_api_key_set'] is True
        assert summary['claude_config']['cost_limit_per_hour'] == 20.0
        assert summary['engine_config']['enable_quality_analysis'] is False
        assert 'ANTHROPIC_API_KEY' in summary['environment_variables_used']

    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('src.analyzer.factory.get_db_session')
    def test_validate_analysis_engine_requirements_success(self, mock_get_db_session):
        """Test successful validation of requirements."""
        # Mock successful database connection
        mock_session = Mock()
        mock_get_db_session.return_value = iter([mock_session])

        validation = validate_analysis_engine_requirements()

        assert validation['valid'] is True
        assert len(validation['errors']) == 0
        assert len(validation['recommendations']) > 0

    @patch.dict(os.environ, {}, clear=True)
    def test_validate_analysis_engine_requirements_missing_api_key(self):
        """Test validation with missing API key."""
        validation = validate_analysis_engine_requirements()

        assert validation['valid'] is False
        assert any('ANTHROPIC_API_KEY' in error for error in validation['errors'])

    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('src.analyzer.factory.get_db_session')
    def test_validate_analysis_engine_requirements_database_error(self, mock_get_db_session):
        """Test validation with database connection error."""
        # Mock database connection failure
        mock_get_db_session.side_effect = Exception("DB connection failed")

        validation = validate_analysis_engine_requirements()

        assert validation['valid'] is False
        assert any('Database connection failed' in error for error in validation['errors'])

    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'test-key',
        'CLAUDE_MODEL': 'claude-3-haiku-20240307',
        'ANALYSIS_BATCH_SIZE': '10'
    })
    def test_environment_variable_parsing(self):
        """Test correct parsing of environment variables."""
        summary = get_analysis_engine_config_summary()

        # Test string values
        assert summary['claude_config']['model'] == 'claude-3-haiku-20240307'

        # Test integer values
        assert summary['engine_config']['batch_size'] == 10
        assert isinstance(summary['engine_config']['batch_size'], int)

        # Test float values
        assert isinstance(summary['claude_config']['temperature'], float)

        # Test boolean values
        assert isinstance(summary['engine_config']['enable_quality_analysis'], bool)

    @patch.dict(os.environ, {})
    def test_default_values_when_env_vars_missing(self):
        """Test that default values are used when environment variables are missing."""
        summary = get_analysis_engine_config_summary()

        # Test defaults
        assert summary['claude_config']['model'] == 'claude-3-haiku-20240307'
        assert summary['claude_config']['max_tokens'] == 1000
        assert summary['claude_config']['temperature'] == 0.3
        assert summary['claude_config']['cost_limit_per_hour'] == 10.0
        assert summary['engine_config']['batch_size'] == 5
        assert summary['engine_config']['enable_quality_analysis'] is True

    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'test-key',
        'ENABLE_QUALITY_ANALYSIS': 'false',
        'ENABLE_COMPETITION_ANALYSIS': 'false',
        'ENABLE_JOB_MATCHING': 'false'
    })
    @patch('src.analyzer.factory.get_db_session')
    @patch('src.analyzer.factory.ClaudeClient')
    def test_disabled_services(self, mock_claude_client, mock_get_db_session):
        """Test engine creation with all services disabled."""
        # Mock database session
        mock_session = Mock()
        mock_get_db_session.return_value = iter([mock_session])

        # Mock Claude client
        mock_claude_client.return_value = Mock()

        engine = create_analysis_engine_from_env()

        # All services should be disabled
        assert engine.quality_service is None
        assert engine.competition_service is None
        assert engine.matching_service is None

    def test_config_summary_structure(self):
        """Test that config summary has expected structure."""
        summary = get_analysis_engine_config_summary()

        # Test top-level keys
        expected_keys = ['anthropic_api_key_set', 'claude_config', 'engine_config', 'environment_variables_used']
        for key in expected_keys:
            assert key in summary

        # Test claude_config structure
        claude_keys = ['model', 'max_tokens', 'temperature', 'cost_limit_per_hour']
        for key in claude_keys:
            assert key in summary['claude_config']

        # Test engine_config structure
        engine_keys = ['batch_size', 'enable_quality_analysis', 'enable_competition_analysis', 'enable_job_matching']
        for key in engine_keys:
            assert key in summary['engine_config']

        # Test environment variables list
        assert isinstance(summary['environment_variables_used'], list)
        assert len(summary['environment_variables_used']) > 0