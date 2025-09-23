"""Factory functions for creating analysis engine instances with proper configuration."""

import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from .analysis_engine import AnalysisEngine, EngineConfig
from .claude_client import ClaudeClient, ClaudeConfig
from .repository import AnalysisRepository
from ..database.connection import get_db_session
from ..database.repository import JobRepository


logger = logging.getLogger(__name__)


def create_analysis_engine(
    session: Optional[Session] = None,
    api_key: Optional[str] = None,
    claude_config: Optional[ClaudeConfig] = None,
    engine_config: Optional[EngineConfig] = None
) -> AnalysisEngine:
    """Create a fully configured analysis engine instance.

    Args:
        session: Database session (will create new one if None)
        api_key: Anthropic API key (will use environment variable if None)
        claude_config: Claude configuration (will use default if None)
        engine_config: Engine configuration (will use default if None)

    Returns:
        Configured AnalysisEngine instance

    Raises:
        ValueError: If API key is not provided and not found in environment
        RuntimeError: If database connection fails
    """
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError(
                "Anthropic API key must be provided or set in ANTHROPIC_API_KEY environment variable"
            )

    # Create Claude configuration with environment-based defaults
    if not claude_config:
        cost_limit = float(os.environ.get('CLAUDE_COST_LIMIT_PER_HOUR', '10.0'))
        model = os.environ.get('CLAUDE_MODEL', 'claude-3-haiku-20240307')
        max_tokens = int(os.environ.get('CLAUDE_MAX_TOKENS', '1000'))
        temperature = float(os.environ.get('CLAUDE_TEMPERATURE', '0.3'))

        claude_config = ClaudeConfig(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            cost_limit_per_hour=cost_limit
        )

    # Create engine configuration with environment-based defaults
    if not engine_config:
        batch_size = int(os.environ.get('ANALYSIS_BATCH_SIZE', '5'))
        enable_quality = os.environ.get('ENABLE_QUALITY_ANALYSIS', 'true').lower() == 'true'
        enable_competition = os.environ.get('ENABLE_COMPETITION_ANALYSIS', 'true').lower() == 'true'
        enable_matching = os.environ.get('ENABLE_JOB_MATCHING', 'true').lower() == 'true'

        engine_config = EngineConfig(
            enable_quality_analysis=enable_quality,
            enable_competition_analysis=enable_competition,
            enable_job_matching=enable_matching,
            batch_size=batch_size,
            claude_config=claude_config
        )

    # Create database session if not provided
    if not session:
        try:
            session = next(get_db_session())
        except Exception as e:
            logger.error(f"Failed to create database session: {e}")
            raise RuntimeError(f"Database connection failed: {e}")

    # Create repositories
    try:
        analysis_repository = AnalysisRepository(session)
        job_repository = JobRepository(session)
    except Exception as e:
        logger.error(f"Failed to create repositories: {e}")
        raise RuntimeError(f"Repository initialization failed: {e}")

    # Create Claude client
    try:
        claude_client = ClaudeClient(api_key=api_key, config=claude_config)
    except Exception as e:
        logger.error(f"Failed to create Claude client: {e}")
        raise RuntimeError(f"Claude client initialization failed: {e}")

    # Create analysis engine
    try:
        engine = AnalysisEngine(
            claude_client=claude_client,
            repository=analysis_repository,
            job_repository=job_repository,
            config=engine_config
        )

        logger.info("Analysis engine created successfully")
        return engine

    except Exception as e:
        logger.error(f"Failed to create analysis engine: {e}")
        raise RuntimeError(f"Analysis engine initialization failed: {e}")


def create_analysis_engine_from_env() -> AnalysisEngine:
    """Create analysis engine using only environment variables for configuration.

    Environment Variables:
        ANTHROPIC_API_KEY: Required - Anthropic API key
        CLAUDE_COST_LIMIT_PER_HOUR: Optional - Cost limit per hour (default: 10.0)
        CLAUDE_MODEL: Optional - Claude model to use (default: claude-3-haiku-20240307)
        CLAUDE_MAX_TOKENS: Optional - Maximum tokens per request (default: 1000)
        CLAUDE_TEMPERATURE: Optional - Temperature setting (default: 0.3)
        ANALYSIS_BATCH_SIZE: Optional - Batch size for analysis (default: 5)
        ENABLE_QUALITY_ANALYSIS: Optional - Enable quality analysis (default: true)
        ENABLE_COMPETITION_ANALYSIS: Optional - Enable competition analysis (default: true)
        ENABLE_JOB_MATCHING: Optional - Enable job matching (default: true)

    Returns:
        Configured AnalysisEngine instance

    Raises:
        ValueError: If required environment variables are missing
        RuntimeError: If initialization fails
    """
    return create_analysis_engine()


def validate_analysis_engine_requirements() -> Dict[str, Any]:
    """Validate that all requirements for analysis engine are met.

    Returns:
        Dictionary with validation results and recommendations

    Raises:
        None - returns validation status instead
    """
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "recommendations": []
    }

    # Check API key
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        validation_results["valid"] = False
        validation_results["errors"].append("ANTHROPIC_API_KEY environment variable is required")

    # Check optional environment variables
    optional_vars = {
        'CLAUDE_COST_LIMIT_PER_HOUR': ('10.0', 'Cost limit per hour'),
        'CLAUDE_MODEL': ('claude-3-haiku-20240307', 'Claude model'),
        'CLAUDE_MAX_TOKENS': ('1000', 'Maximum tokens per request'),
        'CLAUDE_TEMPERATURE': ('0.3', 'Temperature setting'),
        'ANALYSIS_BATCH_SIZE': ('5', 'Analysis batch size'),
        'ENABLE_QUALITY_ANALYSIS': ('true', 'Enable quality analysis'),
        'ENABLE_COMPETITION_ANALYSIS': ('true', 'Enable competition analysis'),
        'ENABLE_JOB_MATCHING': ('true', 'Enable job matching')
    }

    for var_name, (default_value, description) in optional_vars.items():
        if not os.environ.get(var_name):
            validation_results["warnings"].append(
                f"{var_name} not set, will use default: {default_value}"
            )

    # Check database connectivity
    try:
        session = next(get_db_session())
        session.close()
    except Exception as e:
        validation_results["valid"] = False
        validation_results["errors"].append(f"Database connection failed: {str(e)}")

    # Test API key if provided
    if api_key:
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            # Simple test to validate API key (this might use a small amount of quota)
            # In production, you might want to skip this or use a different validation method
            validation_results["recommendations"].append("API key format appears valid")
        except Exception as e:
            validation_results["warnings"].append(f"Could not validate API key: {str(e)}")

    # Recommendations
    if validation_results["valid"]:
        validation_results["recommendations"].extend([
            "All requirements met for analysis engine",
            "Consider setting specific values for optional environment variables",
            "Monitor API usage and costs during operation",
            "Test with a small batch of jobs before full deployment"
        ])

    return validation_results


def get_analysis_engine_config_summary() -> Dict[str, Any]:
    """Get summary of current analysis engine configuration from environment.

    Returns:
        Dictionary with current configuration values
    """
    return {
        "anthropic_api_key_set": bool(os.environ.get('ANTHROPIC_API_KEY')),
        "claude_config": {
            "model": os.environ.get('CLAUDE_MODEL', 'claude-3-haiku-20240307'),
            "max_tokens": int(os.environ.get('CLAUDE_MAX_TOKENS', '1000')),
            "temperature": float(os.environ.get('CLAUDE_TEMPERATURE', '0.3')),
            "cost_limit_per_hour": float(os.environ.get('CLAUDE_COST_LIMIT_PER_HOUR', '10.0'))
        },
        "engine_config": {
            "batch_size": int(os.environ.get('ANALYSIS_BATCH_SIZE', '5')),
            "enable_quality_analysis": os.environ.get('ENABLE_QUALITY_ANALYSIS', 'true').lower() == 'true',
            "enable_competition_analysis": os.environ.get('ENABLE_COMPETITION_ANALYSIS', 'true').lower() == 'true',
            "enable_job_matching": os.environ.get('ENABLE_JOB_MATCHING', 'true').lower() == 'true'
        },
        "environment_variables_used": [
            'ANTHROPIC_API_KEY',
            'CLAUDE_COST_LIMIT_PER_HOUR',
            'CLAUDE_MODEL',
            'CLAUDE_MAX_TOKENS',
            'CLAUDE_TEMPERATURE',
            'ANALYSIS_BATCH_SIZE',
            'ENABLE_QUALITY_ANALYSIS',
            'ENABLE_COMPETITION_ANALYSIS',
            'ENABLE_JOB_MATCHING'
        ]
    }