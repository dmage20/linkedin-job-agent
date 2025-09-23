"""Comprehensive job analysis engine orchestrating all analysis services."""

import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field

from .claude_client import ClaudeClient, ClaudeConfig
from .repository import AnalysisRepository
from .models import UserProfileModel
from .services import (
    JobQualityService,
    CompetitionAnalysisService,
    JobMatchingService
)
from ..database.models import JobModel
from ..database.repository import JobRepository


logger = logging.getLogger(__name__)


@dataclass
class EngineConfig:
    """Configuration for the analysis engine."""

    enable_quality_analysis: bool = True
    enable_competition_analysis: bool = True
    enable_job_matching: bool = True
    batch_size: int = 5
    max_concurrent_jobs: int = 10
    claude_config: Optional[ClaudeConfig] = None
    cost_throttle_threshold: float = 0.9  # Throttle at 90% of cost limit

    def __post_init__(self):
        """Validate configuration."""
        if not 1 <= self.batch_size <= 100:
            raise ValueError("batch_size must be between 1 and 100")

        if not 1 <= self.max_concurrent_jobs <= 50:
            raise ValueError("max_concurrent_jobs must be between 1 and 50")

        if not 0.1 <= self.cost_throttle_threshold <= 1.0:
            raise ValueError("cost_throttle_threshold must be between 0.1 and 1.0")


@dataclass
class AnalysisResult:
    """Result of comprehensive job analysis."""

    job_id: int
    quality_analysis: Optional[Dict[str, Any]] = None
    competition_analysis: Optional[Dict[str, Any]] = None
    matching_analysis: Optional[Dict[str, Any]] = None
    success: bool = True
    errors: List[str] = field(default_factory=list)
    processing_time_seconds: float = 0.0
    api_cost: float = 0.0
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "job_id": self.job_id,
            "quality_analysis": self.quality_analysis,
            "competition_analysis": self.competition_analysis,
            "matching_analysis": self.matching_analysis,
            "success": self.success,
            "errors": self.errors,
            "processing_time_seconds": self.processing_time_seconds,
            "api_cost": self.api_cost,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AnalysisEngine:
    """Comprehensive job analysis engine combining quality, competition, and matching analysis."""

    def __init__(
        self,
        claude_client: ClaudeClient,
        repository: AnalysisRepository,
        job_repository: JobRepository,
        config: Optional[EngineConfig] = None
    ):
        """Initialize the analysis engine.

        Args:
            claude_client: Claude API client
            repository: Analysis repository for data persistence
            job_repository: Job repository for data access
            config: Engine configuration
        """
        self.claude_client = claude_client
        self.repository = repository
        self.job_repository = job_repository
        self.config = config or EngineConfig()

        # Initialize analysis services
        self.quality_service = JobQualityService(
            claude_client=claude_client,
            repository=repository
        ) if self.config.enable_quality_analysis else None

        self.competition_service = CompetitionAnalysisService(
            claude_client=claude_client,
            repository=repository,
            job_repository=job_repository
        ) if self.config.enable_competition_analysis else None

        self.matching_service = JobMatchingService(
            claude_client=claude_client,
            repository=repository,
            job_repository=job_repository
        ) if self.config.enable_job_matching else None

        logger.info("AnalysisEngine initialized with all services")

    async def analyze_job_comprehensive(
        self,
        job: JobModel,
        user_profile: Optional[UserProfileModel] = None,
        force_refresh: bool = False,
        include_quality: bool = True,
        include_competition: bool = True,
        include_matching: bool = True
    ) -> AnalysisResult:
        """Perform comprehensive analysis on a single job.

        Args:
            job: Job to analyze
            user_profile: Optional user profile for matching analysis
            force_refresh: Force fresh analysis even if cached results exist
            include_quality: Include quality analysis
            include_competition: Include competition analysis
            include_matching: Include job matching (requires user_profile)

        Returns:
            AnalysisResult with all requested analyses
        """
        start_time = datetime.now()
        result = AnalysisResult(job_id=job.id)

        # Check if analysis should be throttled
        if self._should_throttle_analysis():
            result.success = False
            result.errors.append("Analysis throttled due to cost limits")
            return result

        # Prepare analysis tasks
        tasks = []
        task_names = []

        # Quality analysis
        if include_quality and self.quality_service and self.config.enable_quality_analysis:
            tasks.append(self.quality_service.analyze_job_quality(job, force_refresh=force_refresh))
            task_names.append("quality")

        # Competition analysis
        if include_competition and self.competition_service and self.config.enable_competition_analysis:
            tasks.append(self.competition_service.analyze_competition(job, force_refresh=force_refresh))
            task_names.append("competition")

        # Job matching analysis
        if (include_matching and user_profile and self.matching_service and
            self.config.enable_job_matching):
            tasks.append(self.matching_service.match_job_to_profile(
                job, user_profile, force_refresh=force_refresh
            ))
            task_names.append("matching")

        # Execute analyses concurrently
        if tasks:
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                for task_name, task_result in zip(task_names, results):
                    if isinstance(task_result, Exception):
                        result.errors.append(f"{task_name} analysis failed: {str(task_result)}")
                        logger.error(f"{task_name} analysis failed for job {job.id}: {task_result}")
                    else:
                        if task_name == "quality":
                            result.quality_analysis = task_result
                        elif task_name == "competition":
                            result.competition_analysis = task_result
                        elif task_name == "matching":
                            result.matching_analysis = task_result

                # Set success status
                result.success = len(result.errors) == 0

            except Exception as e:
                result.success = False
                result.errors.append(f"Analysis execution failed: {str(e)}")
                logger.error(f"Analysis execution failed for job {job.id}: {e}")

        # Calculate processing time and cost
        result.processing_time_seconds = (datetime.now() - start_time).total_seconds()
        usage_stats = self.claude_client.get_usage_stats()
        result.api_cost = usage_stats.get("total_cost", 0.0)

        logger.info(f"Comprehensive analysis completed for job {job.id} in {result.processing_time_seconds:.2f}s")
        return result

    async def batch_analyze_jobs(
        self,
        jobs: List[JobModel],
        user_profile: Optional[UserProfileModel] = None,
        force_refresh: bool = False,
        include_quality: bool = True,
        include_competition: bool = True,
        include_matching: bool = True
    ) -> List[AnalysisResult]:
        """Perform batch analysis on multiple jobs.

        Args:
            jobs: List of jobs to analyze
            user_profile: Optional user profile for matching analysis
            force_refresh: Force fresh analysis
            include_quality: Include quality analysis
            include_competition: Include competition analysis
            include_matching: Include job matching

        Returns:
            List of AnalysisResult objects
        """
        if not jobs:
            return []

        # Use service batch methods for efficiency when possible
        results = []

        if self._should_throttle_analysis():
            logger.warning("Batch analysis throttled due to cost limits")
            return [
                AnalysisResult(
                    job_id=job.id,
                    success=False,
                    errors=["Analysis throttled due to cost limits"]
                )
                for job in jobs
            ]

        try:
            # Execute batch analyses
            quality_results = {}
            competition_results = {}
            matching_results = {}

            # Batch quality analysis
            if include_quality and self.quality_service:
                try:
                    quality_batch = await self.quality_service.batch_analyze_jobs(
                        jobs,
                        batch_size=self.config.batch_size
                    )
                    quality_results = {r.get("job_id"): r for r in quality_batch if "job_id" in r}
                except Exception as e:
                    logger.error(f"Batch quality analysis failed: {e}")

            # Batch competition analysis
            if include_competition and self.competition_service:
                try:
                    competition_batch = await self.competition_service.batch_analyze_competition(
                        jobs,
                        batch_size=self.config.batch_size
                    )
                    competition_results = {r.get("job_id"): r for r in competition_batch if "job_id" in r}
                except Exception as e:
                    logger.error(f"Batch competition analysis failed: {e}")

            # Batch matching analysis
            if include_matching and user_profile and self.matching_service:
                try:
                    matching_batch = await self.matching_service.batch_match_jobs_to_profile(
                        user_profile,
                        jobs,
                        batch_size=self.config.batch_size
                    )
                    matching_results = {r.get("job_id"): r for r in matching_batch if "job_id" in r}
                except Exception as e:
                    logger.error(f"Batch matching analysis failed: {e}")

            # Combine results
            for job in jobs:
                result = AnalysisResult(job_id=job.id)

                # Add quality results
                if job.id in quality_results:
                    quality_result = quality_results[job.id]
                    if "error" in quality_result:
                        result.errors.append(f"Quality analysis: {quality_result['error']}")
                    else:
                        result.quality_analysis = quality_result

                # Add competition results
                if job.id in competition_results:
                    competition_result = competition_results[job.id]
                    if "error" in competition_result:
                        result.errors.append(f"Competition analysis: {competition_result['error']}")
                    else:
                        result.competition_analysis = competition_result

                # Add matching results
                if job.id in matching_results:
                    matching_result = matching_results[job.id]
                    if "error" in matching_result:
                        result.errors.append(f"Matching analysis: {matching_result['error']}")
                    else:
                        result.matching_analysis = matching_result

                result.success = len(result.errors) == 0
                results.append(result)

            logger.info(f"Batch analysis completed for {len(jobs)} jobs")
            return results

        except Exception as e:
            logger.error(f"Batch analysis execution failed: {e}")
            return [
                AnalysisResult(
                    job_id=job.id,
                    success=False,
                    errors=[f"Batch analysis failed: {str(e)}"]
                )
                for job in jobs
            ]

    async def find_and_analyze_matching_jobs(
        self,
        user_profile: UserProfileModel,
        max_jobs: int = 50,
        include_quality: bool = True,
        include_competition: bool = True
    ) -> List[Dict[str, Any]]:
        """Find jobs matching a user profile and analyze them.

        Args:
            user_profile: User profile to find matches for
            max_jobs: Maximum number of jobs to analyze
            include_quality: Include quality analysis
            include_competition: Include competition analysis

        Returns:
            List of job analysis results with matching scores
        """
        if not self.matching_service:
            raise ValueError("Job matching service not enabled")

        try:
            # Find matching jobs
            matching_jobs = await self.matching_service.find_matching_jobs_for_profile(
                user_profile,
                max_results=max_jobs
            )

            if not matching_jobs:
                logger.info(f"No matching jobs found for profile {user_profile.user_id}")
                return []

            # Get matching scores
            matching_results = await self.matching_service.batch_match_jobs_to_profile(
                user_profile,
                matching_jobs,
                batch_size=self.config.batch_size
            )

            # Optionally add quality and competition analysis
            if include_quality or include_competition:
                analysis_results = await self.batch_analyze_jobs(
                    matching_jobs,
                    user_profile=user_profile,
                    include_quality=include_quality,
                    include_competition=include_competition,
                    include_matching=False  # Already have matching results
                )

                # Combine results
                analysis_by_job_id = {r.job_id: r for r in analysis_results}

                for match_result in matching_results:
                    job_id = match_result.get("job_id")
                    if job_id in analysis_by_job_id:
                        analysis = analysis_by_job_id[job_id]
                        match_result["quality_analysis"] = analysis.quality_analysis
                        match_result["competition_analysis"] = analysis.competition_analysis

            logger.info(f"Found and analyzed {len(matching_results)} matching jobs for profile {user_profile.user_id}")
            return matching_results

        except Exception as e:
            logger.error(f"Find and analyze matching jobs failed: {e}")
            raise

    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get comprehensive analysis summary across all services.

        Returns:
            Dictionary with analysis statistics and insights
        """
        try:
            summary = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "engine_config": {
                    "quality_enabled": self.config.enable_quality_analysis,
                    "competition_enabled": self.config.enable_competition_analysis,
                    "matching_enabled": self.config.enable_job_matching,
                    "batch_size": self.config.batch_size
                }
            }

            # Analysis statistics from repository
            summary["analysis_statistics"] = self.repository.get_analysis_statistics()

            # Quality insights
            if self.quality_service:
                try:
                    # Get recent quality analyses for summary
                    from .models import JobAnalysisModel, AnalysisType, AnalysisStatus
                    recent_quality = self.repository.session.query(JobAnalysisModel).filter(
                        JobAnalysisModel.analysis_type == AnalysisType.QUALITY,
                        JobAnalysisModel.status == AnalysisStatus.COMPLETED
                    ).order_by(JobAnalysisModel.created_at.desc()).limit(100).all()

                    summary["quality_insights"] = self.quality_service.get_quality_insights_summary(recent_quality)
                except Exception as e:
                    logger.error(f"Failed to get quality insights: {e}")
                    summary["quality_insights"] = {"error": str(e)}

            # Market intelligence
            if self.competition_service:
                try:
                    summary["market_intelligence"] = self.competition_service.get_market_intelligence_summary()
                except Exception as e:
                    logger.error(f"Failed to get market intelligence: {e}")
                    summary["market_intelligence"] = {"error": str(e)}

            # Cost and usage statistics
            summary["cost_usage"] = self.get_cost_usage_stats()

            return summary

        except Exception as e:
            logger.error(f"Failed to generate analysis summary: {e}")
            return {
                "error": str(e),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

    def get_cost_usage_stats(self) -> Dict[str, Any]:
        """Get current cost and usage statistics."""
        usage_stats = self.claude_client.get_usage_stats()

        cost_limit = usage_stats.get("cost_limit", 10.0)
        total_cost = usage_stats.get("total_cost", 0.0)
        cost_remaining = max(0, cost_limit - total_cost)
        cost_utilization = (total_cost / cost_limit) * 100 if cost_limit > 0 else 0

        return {
            "total_cost": total_cost,
            "cost_limit": cost_limit,
            "cost_remaining": cost_remaining,
            "cost_utilization_percent": round(cost_utilization, 2),
            "request_count": usage_stats.get("request_count", 0),
            "circuit_breaker_open": usage_stats.get("circuit_breaker_open", False),
            "requests_remaining": max(0, int(cost_remaining / 0.01)) if cost_remaining > 0 else 0  # Rough estimate
        }

    def reset_cost_tracking(self):
        """Reset Claude client cost tracking (for new billing period)."""
        try:
            self.claude_client.reset_circuit_breaker()
            logger.info("Cost tracking and circuit breaker reset")
        except Exception as e:
            logger.error(f"Failed to reset cost tracking: {e}")

    def _should_throttle_analysis(self) -> bool:
        """Check if analysis should be throttled due to cost limits."""
        try:
            usage_stats = self.claude_client.get_usage_stats()
            cost_limit = usage_stats.get("cost_limit", 10.0)
            total_cost = usage_stats.get("total_cost", 0.0)

            cost_ratio = total_cost / cost_limit if cost_limit > 0 else 0
            return cost_ratio >= self.config.cost_throttle_threshold

        except Exception as e:
            logger.error(f"Failed to check throttling status: {e}")
            return False  # Allow analysis if check fails

    def get_service_health_status(self) -> Dict[str, Any]:
        """Get health status of all analysis services."""
        status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_healthy": True,
            "services": {}
        }

        # Check Claude client
        try:
            usage_stats = self.claude_client.get_usage_stats()
            status["services"]["claude_client"] = {
                "healthy": not usage_stats.get("circuit_breaker_open", False),
                "usage_stats": usage_stats
            }
        except Exception as e:
            status["services"]["claude_client"] = {
                "healthy": False,
                "error": str(e)
            }
            status["overall_healthy"] = False

        # Check database connectivity
        try:
            # Simple query to test database
            self.repository.get_analysis_statistics()
            status["services"]["database"] = {"healthy": True}
        except Exception as e:
            status["services"]["database"] = {
                "healthy": False,
                "error": str(e)
            }
            status["overall_healthy"] = False

        # Check individual services
        services_to_check = [
            ("quality_service", self.quality_service),
            ("competition_service", self.competition_service),
            ("matching_service", self.matching_service)
        ]

        for service_name, service in services_to_check:
            if service:
                status["services"][service_name] = {"healthy": True, "enabled": True}
            else:
                status["services"][service_name] = {"healthy": True, "enabled": False}

        return status