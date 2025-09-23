"""Competitive intelligence analysis service."""

import re
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from collections import Counter

from ..claude_client import ClaudeClient
from ..repository import AnalysisRepository
from ..models import CompetitionAnalysisModel
from ...database.models import JobModel
from ...database.repository import JobRepository


logger = logging.getLogger(__name__)


@dataclass
class CompetitionMetrics:
    """Market competition metrics for job analysis."""

    similar_jobs_count: int
    average_applicant_count: float
    position_in_market: str  # low, medium, high
    market_saturation_score: int  # 0-100
    keyword_match_scores: List[float]
    location_competition_factor: float


class CompetitionAnalysisService:
    """Service for analyzing job market competition and providing strategic insights."""

    def __init__(
        self,
        claude_client: ClaudeClient,
        repository: AnalysisRepository,
        job_repository: JobRepository,
        cache_ttl: int = 7200  # 2 hour cache for competition data
    ):
        """Initialize competition analysis service.

        Args:
            claude_client: Claude API client for analysis
            repository: Analysis repository for data persistence
            job_repository: Job repository for market research
            cache_ttl: Cache time-to-live in seconds
        """
        self.claude_client = claude_client
        self.repository = repository
        self.job_repository = job_repository
        self.cache_ttl = cache_ttl

        # Competition thresholds
        self.competition_thresholds = {
            "low": 20,      # < 20 applicants
            "medium": 50,   # 20-50 applicants
            "high": 50      # > 50 applicants
        }

        logger.info("CompetitionAnalysisService initialized")

    async def analyze_competition(
        self,
        job: JobModel,
        force_refresh: bool = False,
        use_local_fallback: bool = True
    ) -> Dict[str, Any]:
        """Analyze job competition and provide strategic insights.

        Args:
            job: Job model to analyze
            force_refresh: Force new analysis even if cached result exists
            use_local_fallback: Use local analysis if Claude API fails

        Returns:
            Dictionary with competition analysis results
        """
        try:
            # Check for existing analysis
            if not force_refresh:
                existing_analysis = self.repository.get_competition_analysis_for_job(job.id)
                if existing_analysis and self._should_use_cached_analysis(existing_analysis, force_refresh):
                    logger.info(f"Using cached competition analysis for job {job.id}")
                    return self._format_analysis_result(existing_analysis)

            logger.info(f"Starting competition analysis for job {job.id}")

            # Calculate market metrics
            market_metrics = self._calculate_market_metrics(job)

            try:
                # Get Claude analysis
                start_time = datetime.now()
                claude_result = await self.claude_client.analyze_competition(job)
                processing_time = (datetime.now() - start_time).total_seconds()

                # Enrich Claude analysis with market data
                enriched_result = self._enrich_with_market_analysis(claude_result, market_metrics)

                # Store analysis result
                analysis_data = {
                    "job_id": job.id,
                    "applicant_count": job.applicant_count,
                    "competition_level": enriched_result.get("competition_level"),
                    "success_probability": enriched_result.get("success_probability"),
                    "similar_jobs_count": market_metrics.similar_jobs_count,
                    "average_applicants_for_role": market_metrics.average_applicant_count,
                    "market_demand_score": market_metrics.market_saturation_score,
                    "analysis_data": enriched_result
                }

                self.repository.create_competition_analysis(**analysis_data)

                logger.info(f"Competition analysis completed for job {job.id}, level: {enriched_result.get('competition_level')}")
                return enriched_result

            except Exception as e:
                logger.error(f"Claude API failed for competition analysis of job {job.id}: {str(e)}")

                if use_local_fallback:
                    # Fall back to local analysis
                    local_result = await self._perform_local_competition_analysis(job, market_metrics)

                    # Store local analysis result
                    analysis_data = {
                        "job_id": job.id,
                        "applicant_count": job.applicant_count,
                        "competition_level": local_result.get("competition_level"),
                        "success_probability": local_result.get("success_probability"),
                        "similar_jobs_count": market_metrics.similar_jobs_count,
                        "average_applicants_for_role": market_metrics.average_applicant_count,
                        "market_demand_score": market_metrics.market_saturation_score,
                        "analysis_data": local_result
                    }

                    self.repository.create_competition_analysis(**analysis_data)
                    return local_result
                else:
                    raise

        except Exception as e:
            logger.error(f"Competition analysis failed for job {job.id}: {str(e)}")
            raise

    async def batch_analyze_competition(
        self,
        jobs: List[JobModel],
        batch_size: int = 3,  # Smaller batches for competition analysis
        use_local_fallback: bool = True
    ) -> List[Dict[str, Any]]:
        """Analyze competition for multiple jobs in batches.

        Args:
            jobs: List of jobs to analyze
            batch_size: Number of jobs to process in parallel
            use_local_fallback: Use local analysis if Claude API fails

        Returns:
            List of competition analysis results
        """
        results = []

        for i in range(0, len(jobs), batch_size):
            batch = jobs[i:i + batch_size]
            batch_tasks = [
                self.analyze_competition(job, use_local_fallback=use_local_fallback)
                for job in batch
            ]

            # Process batch with error handling
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process results and handle exceptions
            for job, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch competition analysis failed for job {job.id}: {result}")
                    results.append({
                        "job_id": job.id,
                        "error": str(result),
                        "competition_level": None
                    })
                else:
                    result["job_id"] = job.id
                    results.append(result)

            # Add delay between batches
            if i + batch_size < len(jobs):
                await asyncio.sleep(2)

        return results

    def get_market_intelligence_summary(self) -> Dict[str, Any]:
        """Generate comprehensive market intelligence summary.

        Returns:
            Dictionary with market insights and trends
        """
        try:
            # Get all competition analyses
            analyses = self.repository.session.query(CompetitionAnalysisModel).all()

            if not analyses:
                return {"message": "No competition analyses available"}

            total_jobs = len(analyses)

            # Competition level distribution
            competition_levels = [a.competition_level for a in analyses if a.competition_level]
            level_distribution = dict(Counter(competition_levels))

            # Success probability statistics
            success_probs = [a.success_probability for a in analyses if a.success_probability is not None]
            avg_success_prob = sum(success_probs) / len(success_probs) if success_probs else 0

            # Applicant count statistics
            applicant_counts = [a.applicant_count for a in analyses if a.applicant_count is not None]
            avg_applicants = sum(applicant_counts) / len(applicant_counts) if applicant_counts else 0

            # Market demand analysis
            demand_scores = [a.market_demand_score for a in analyses if a.market_demand_score is not None]
            avg_demand = sum(demand_scores) / len(demand_scores) if demand_scores else 0

            # Generate insights
            insights = self._generate_market_insights(
                level_distribution,
                avg_success_prob,
                avg_applicants,
                avg_demand
            )

            return {
                "total_jobs_analyzed": total_jobs,
                "competition_distribution": level_distribution,
                "average_success_probability": round(avg_success_prob, 2),
                "average_applicant_count": round(avg_applicants, 1),
                "average_market_demand": round(avg_demand, 1),
                "market_insights": insights,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to generate market intelligence summary: {str(e)}")
            raise

    def _calculate_market_metrics(self, job: JobModel) -> CompetitionMetrics:
        """Calculate comprehensive market metrics for a job."""
        # Find similar jobs for comparison
        similar_jobs = self._find_similar_jobs(job)

        # Calculate metrics
        similar_jobs_count = len(similar_jobs)

        # Calculate average applicant count
        applicant_counts = [j.applicant_count for j in similar_jobs if j.applicant_count is not None]
        avg_applicant_count = sum(applicant_counts) / len(applicant_counts) if applicant_counts else 0

        # Determine position in market
        job_applicant_count = job.applicant_count or 0
        position = self._determine_market_position(job_applicant_count, applicant_counts)

        # Calculate market saturation score
        saturation_score = self._calculate_market_saturation(similar_jobs_count, avg_applicant_count)

        # Calculate keyword match scores
        job_keywords = self._extract_job_keywords(job)
        keyword_scores = []
        for similar_job in similar_jobs[:10]:  # Top 10 for efficiency
            similar_keywords = self._extract_job_keywords(similar_job)
            overlap = self._calculate_keyword_overlap(job_keywords, similar_keywords)
            keyword_scores.append(overlap)

        # Location competition factor
        location_factor = self._calculate_location_competition_factor(job, similar_jobs)

        return CompetitionMetrics(
            similar_jobs_count=similar_jobs_count,
            average_applicant_count=avg_applicant_count,
            position_in_market=position,
            market_saturation_score=saturation_score,
            keyword_match_scores=keyword_scores,
            location_competition_factor=location_factor
        )

    def _find_similar_jobs(self, job: JobModel) -> List[JobModel]:
        """Find jobs similar to the given job for competition analysis."""
        all_similar = []

        # Search by similar title
        title_words = re.findall(r'\b\w+\b', job.title.lower())
        main_title_words = [word for word in title_words if word not in ['junior', 'senior', 'lead', 'principal', 'the', 'and', 'or']]

        for word in main_title_words[:3]:  # Top 3 keywords from title
            similar_by_title = self.job_repository.search_jobs(
                title=word,
                employment_type=job.employment_type,
                limit=20
            )
            all_similar.extend(similar_by_title)

        # Search by location
        if job.location and job.location.lower() not in ['remote', 'anywhere']:
            location_parts = job.location.split(',')
            if location_parts:
                main_location = location_parts[0].strip()
                similar_by_location = self.job_repository.search_jobs(
                    location=main_location,
                    experience_level=job.experience_level,
                    limit=15
                )
                all_similar.extend(similar_by_location)

        # Search by experience level and type
        similar_by_level = self.job_repository.search_jobs(
            experience_level=job.experience_level,
            employment_type=job.employment_type,
            limit=25
        )
        all_similar.extend(similar_by_level)

        # Remove duplicates and the job itself
        unique_similar = []
        seen_ids = {job.id}
        for similar_job in all_similar:
            if similar_job.id not in seen_ids:
                unique_similar.append(similar_job)
                seen_ids.add(similar_job.id)

        # Sort by relevance (keyword overlap and recency)
        job_keywords = self._extract_job_keywords(job)
        for similar_job in unique_similar:
            similar_keywords = self._extract_job_keywords(similar_job)
            similar_job._relevance_score = self._calculate_keyword_overlap(job_keywords, similar_keywords)

        unique_similar.sort(key=lambda j: getattr(j, '_relevance_score', 0), reverse=True)

        return unique_similar[:30]  # Top 30 most relevant

    def _extract_job_keywords(self, job: JobModel) -> Set[str]:
        """Extract relevant keywords from job title and description."""
        text = f"{job.title} {job.description or ''}".lower()

        # Common tech keywords to look for
        tech_keywords = {
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node',
            'sql', 'postgresql', 'mysql', 'mongodb', 'redis',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes',
            'django', 'flask', 'fastapi', 'spring', 'express',
            'git', 'linux', 'agile', 'scrum', 'devops', 'ci/cd',
            'api', 'rest', 'graphql', 'microservices',
            'machine learning', 'ai', 'data science', 'analytics'
        }

        # Extract keywords from text
        words = re.findall(r'\b\w+\b', text)
        found_keywords = set()

        for word in words:
            if word in tech_keywords:
                found_keywords.add(word)

        # Also extract multi-word phrases
        for phrase in tech_keywords:
            if ' ' in phrase and phrase in text:
                found_keywords.add(phrase)

        return found_keywords

    def _calculate_keyword_overlap(self, keywords1: Set[str], keywords2: Set[str]) -> float:
        """Calculate overlap percentage between two keyword sets."""
        if not keywords1 and not keywords2:
            return 0.0

        if not keywords1 or not keywords2:
            return 0.0

        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)

        return len(intersection) / len(union) if union else 0.0

    def _determine_market_position(self, job_applicants: int, market_applicants: List[int]) -> str:
        """Determine job's position in the market based on applicant counts."""
        if not market_applicants:
            return "unknown"

        market_applicants.sort()
        total = len(market_applicants)

        if total == 0:
            return "unknown"

        # Find percentile position
        position = 0
        for count in market_applicants:
            if job_applicants <= count:
                break
            position += 1

        percentile = position / total

        if percentile <= 0.33:
            return "low"
        elif percentile <= 0.66:
            return "medium"
        else:
            return "high"

    def _calculate_market_saturation(self, similar_jobs_count: int, avg_applicants: float) -> int:
        """Calculate market saturation score (0-100)."""
        # Base score on number of similar jobs
        job_score = min(50, (similar_jobs_count / 20) * 50)  # Max 50 points

        # Add applicant competition factor
        applicant_score = min(50, (avg_applicants / 100) * 50)  # Max 50 points

        return int(job_score + applicant_score)

    def _calculate_location_competition_factor(self, job: JobModel, similar_jobs: List[JobModel]) -> float:
        """Calculate competition factor based on location."""
        if not job.location:
            return 1.0

        job_location = job.location.lower()

        # Remote jobs face global competition
        if 'remote' in job_location:
            return 1.5

        # Count jobs in same location
        same_location_count = 0
        for similar_job in similar_jobs:
            if similar_job.location and job_location in similar_job.location.lower():
                same_location_count += 1

        # Higher factor means more competition
        location_density = same_location_count / max(len(similar_jobs), 1)
        return 1.0 + location_density

    def _classify_competition_level(self, applicant_count: Optional[int]) -> str:
        """Classify competition level based on applicant count."""
        if applicant_count is None:
            return "unknown"

        if applicant_count < self.competition_thresholds["low"]:
            return "low"
        elif applicant_count < self.competition_thresholds["medium"]:
            return "medium"
        else:
            return "high"

    def _calculate_success_probability(
        self,
        applicant_count: Optional[int],
        similar_jobs_count: int,
        market_position: str
    ) -> int:
        """Calculate success probability percentage (0-100)."""
        base_probability = 50

        # Adjust based on applicant count
        if applicant_count:
            if applicant_count < 10:
                base_probability += 30
            elif applicant_count < 25:
                base_probability += 10
            elif applicant_count < 50:
                base_probability -= 10
            else:
                base_probability -= 30

        # Adjust based on market saturation
        if similar_jobs_count > 20:
            base_probability -= 15
        elif similar_jobs_count < 5:
            base_probability += 15

        # Adjust based on market position
        if market_position == "low":
            base_probability += 20
        elif market_position == "high":
            base_probability -= 20

        return max(5, min(95, base_probability))

    def _generate_strategic_advice(
        self,
        competition_level: str,
        applicant_count: Optional[int],
        market_metrics: CompetitionMetrics
    ) -> Dict[str, Any]:
        """Generate strategic advice based on competition analysis."""
        advice = {
            "application_timing": "within 48 hours",
            "differentiation_strategies": [],
            "success_factors": [],
            "risk_factors": []
        }

        # Timing advice
        if competition_level == "high":
            advice["application_timing"] = "within 24 hours"
        elif competition_level == "low":
            advice["application_timing"] = "within 1 week"

        # Differentiation strategies
        if competition_level in ["medium", "high"]:
            advice["differentiation_strategies"] = [
                "Highlight unique skills and experiences",
                "Show quantifiable achievements",
                "Demonstrate cultural fit",
                "Provide portfolio or work samples"
            ]

        # Success factors
        advice["success_factors"] = [
            "Tailor resume to job requirements",
            "Write compelling cover letter",
            "Apply through multiple channels if possible"
        ]

        if market_metrics.location_competition_factor > 1.3:
            advice["success_factors"].append("Consider relocation flexibility")

        # Risk factors
        if applicant_count and applicant_count > 75:
            advice["risk_factors"].append("Very high competition")

        if market_metrics.market_saturation_score > 80:
            advice["risk_factors"].append("Saturated market for this role")

        return advice

    def _enrich_with_market_analysis(
        self,
        claude_result: Dict[str, Any],
        market_metrics: CompetitionMetrics
    ) -> Dict[str, Any]:
        """Enrich Claude analysis with local market data."""
        enriched = claude_result.copy()

        # Add market analysis section
        enriched["market_analysis"] = {
            "similar_jobs_count": market_metrics.similar_jobs_count,
            "average_applicant_count": round(market_metrics.average_applicant_count, 1),
            "market_position": market_metrics.position_in_market,
            "market_saturation_score": market_metrics.market_saturation_score,
            "location_competition_factor": round(market_metrics.location_competition_factor, 2),
            "keyword_relevance_scores": [round(score, 3) for score in market_metrics.keyword_match_scores[:5]]
        }

        # Adjust success probability if there's significant discrepancy
        claude_prob = claude_result.get("success_probability", 50)
        local_prob = self._calculate_success_probability(
            applicant_count=None,  # Will be derived from market data
            similar_jobs_count=market_metrics.similar_jobs_count,
            market_position=market_metrics.position_in_market
        )

        if abs(claude_prob - local_prob) > 20:
            adjusted_prob = int(claude_prob * 0.6 + local_prob * 0.4)
            enriched["adjusted_success_probability"] = adjusted_prob
            enriched["probability_adjustment_reason"] = "Adjusted based on market intelligence data"

        return enriched

    async def _perform_local_competition_analysis(
        self,
        job: JobModel,
        market_metrics: CompetitionMetrics
    ) -> Dict[str, Any]:
        """Perform local competition analysis when Claude API is unavailable."""
        applicant_count = job.applicant_count or 0
        competition_level = self._classify_competition_level(applicant_count)

        success_probability = self._calculate_success_probability(
            applicant_count,
            market_metrics.similar_jobs_count,
            market_metrics.position_in_market
        )

        strategic_advice = self._generate_strategic_advice(
            competition_level,
            applicant_count,
            market_metrics
        )

        return {
            "competition_level": competition_level,
            "analysis": f"Local analysis based on {applicant_count} applicants and {market_metrics.similar_jobs_count} similar jobs in market",
            "success_probability": success_probability,
            "strategic_advice": strategic_advice["success_factors"],
            "application_timing": strategic_advice["application_timing"],
            "differentiation_tips": strategic_advice["differentiation_strategies"],
            "market_analysis": {
                "similar_jobs_count": market_metrics.similar_jobs_count,
                "average_applicant_count": round(market_metrics.average_applicant_count, 1),
                "market_position": market_metrics.position_in_market,
                "market_saturation_score": market_metrics.market_saturation_score
            },
            "analysis_type": "local_fallback"
        }

    def _should_use_cached_analysis(self, analysis: CompetitionAnalysisModel, force_refresh: bool) -> bool:
        """Determine if cached competition analysis should be used."""
        if force_refresh:
            return False

        if not analysis.created_at:
            return False

        # Check if analysis is within cache TTL
        age = datetime.now(timezone.utc) - analysis.created_at.replace(tzinfo=timezone.utc)
        return age.total_seconds() < self.cache_ttl

    def _format_analysis_result(self, analysis: CompetitionAnalysisModel) -> Dict[str, Any]:
        """Format analysis model to result dictionary."""
        result = {
            "analysis_id": analysis.id,
            "job_id": analysis.job_id,
            "competition_level": analysis.competition_level,
            "success_probability": analysis.success_probability,
            "applicant_count": analysis.applicant_count,
            "created_at": analysis.created_at.isoformat() if analysis.created_at else None
        }

        # Add analysis data if available
        if analysis.analysis_data:
            result.update(analysis.analysis_data)

        return result

    def _generate_market_insights(
        self,
        level_distribution: Dict[str, int],
        avg_success_prob: float,
        avg_applicants: float,
        avg_demand: float
    ) -> List[str]:
        """Generate market insights from aggregated data."""
        insights = []

        # Competition level insights
        total_jobs = sum(level_distribution.values())
        if total_jobs > 0:
            high_comp_pct = (level_distribution.get("high", 0) / total_jobs) * 100
            if high_comp_pct > 50:
                insights.append(f"Market shows high competition with {high_comp_pct:.1f}% of jobs having intense competition")
            elif high_comp_pct < 25:
                insights.append("Market conditions are relatively favorable with lower competition levels")

        # Success probability insights
        if avg_success_prob > 60:
            insights.append("Overall market shows good opportunities with above-average success rates")
        elif avg_success_prob < 40:
            insights.append("Challenging market conditions with lower success probabilities")

        # Demand insights
        if avg_demand > 75:
            insights.append("High market demand indicates a competitive but active job market")
        elif avg_demand < 40:
            insights.append("Lower market demand suggests fewer opportunities but potentially less competition")

        return insights