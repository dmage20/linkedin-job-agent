"""Job Analysis Engine module for LinkedIn Job Agent.

This module provides comprehensive job analysis capabilities including:
- Claude API integration for AI-powered analysis
- Job quality scoring and assessment
- Competition analysis and market intelligence
- AI-powered job matching to user profiles
- Analysis results storage and retrieval
- Comprehensive analysis engine orchestrating all services

Key Components:
- claude_client: Claude API client with cost management and circuit breaker
- models: Database models for analysis data storage
- repository: Database operations for analysis data
- services: High-level business logic services
- analysis_engine: Comprehensive orchestration engine
"""

from .claude_client import ClaudeClient, ClaudeConfig, CircuitBreakerError
from .models import (
    JobAnalysisModel,
    CompetitionAnalysisModel,
    UserProfileModel,
    JobMatchModel,
    AnalysisStatus,
    AnalysisType
)
from .repository import AnalysisRepository, get_analysis_repository
from .analysis_engine import AnalysisEngine, AnalysisResult, EngineConfig
from .services import (
    JobQualityService,
    QualityMetrics,
    CompetitionAnalysisService,
    CompetitionMetrics,
    JobMatchingService,
    MatchingMetrics
)
from .factory import (
    create_analysis_engine,
    create_analysis_engine_from_env,
    validate_analysis_engine_requirements,
    get_analysis_engine_config_summary
)

__all__ = [
    # Claude API
    'ClaudeClient',
    'ClaudeConfig',
    'CircuitBreakerError',

    # Models
    'JobAnalysisModel',
    'CompetitionAnalysisModel',
    'UserProfileModel',
    'JobMatchModel',
    'AnalysisStatus',
    'AnalysisType',

    # Repository
    'AnalysisRepository',
    'get_analysis_repository',

    # Analysis Engine
    'AnalysisEngine',
    'AnalysisResult',
    'EngineConfig',

    # Services
    'JobQualityService',
    'QualityMetrics',
    'CompetitionAnalysisService',
    'CompetitionMetrics',
    'JobMatchingService',
    'MatchingMetrics',

    # Factory Functions
    'create_analysis_engine',
    'create_analysis_engine_from_env',
    'validate_analysis_engine_requirements',
    'get_analysis_engine_config_summary'
]