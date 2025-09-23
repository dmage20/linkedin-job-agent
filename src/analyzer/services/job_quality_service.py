"""Job quality scoring and analysis service."""

import re
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..claude_client import ClaudeClient
from ..repository import AnalysisRepository
from ..models import JobAnalysisModel, AnalysisStatus, AnalysisType
from ...database.models import JobModel


logger = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """Local quality metrics for job postings."""

    description_length: int
    has_salary_info: bool
    has_benefits_info: bool
    has_company_info: bool
    requirement_clarity_score: int  # 0-100
    responsibility_clarity_score: int  # 0-100
    keyword_density_score: int  # 0-100
    overall_local_score: int  # 0-100


class JobQualityService:
    """Service for analyzing and scoring job quality."""

    def __init__(
        self,
        claude_client: ClaudeClient,
        repository: AnalysisRepository,
        cache_ttl: int = 3600  # 1 hour cache
    ):
        """Initialize job quality service.

        Args:
            claude_client: Claude API client for analysis
            repository: Analysis repository for data persistence
            cache_ttl: Cache time-to-live in seconds
        """
        self.claude_client = claude_client
        self.repository = repository
        self.cache_ttl = cache_ttl

        # Quality keywords for analysis
        self.quality_keywords = {
            'requirements': [
                'required', 'must have', 'essential', 'necessary',
                'years of experience', 'bachelor', 'master', 'degree'
            ],
            'responsibilities': [
                'responsible for', 'will be', 'duties include',
                'you will', 'responsibilities', 'role involves'
            ],
            'benefits': [
                'health insurance', 'dental', 'vision', '401k', 'retirement',
                'pto', 'vacation', 'paid time off', 'sick leave',
                'flexible', 'remote', 'work from home', 'bonus'
            ],
            'company_culture': [
                'culture', 'team', 'collaborative', 'innovative',
                'growth opportunities', 'learning', 'development'
            ]
        }

        logger.info("JobQualityService initialized")

    async def analyze_job_quality(
        self,
        job: JobModel,
        force_refresh: bool = False,
        use_local_fallback: bool = False
    ) -> Dict[str, Any]:
        """Analyze job quality using Claude API with local metrics as backup.

        Args:
            job: Job model to analyze
            force_refresh: Force new analysis even if cached result exists
            use_local_fallback: Use local analysis if Claude API fails

        Returns:
            Dictionary with quality analysis results
        """
        try:
            # Check for existing analysis
            if not force_refresh:
                existing_analysis = await self._get_recent_analysis(job.id)
                if existing_analysis and self._should_use_cached_result(existing_analysis, force_refresh):
                    logger.info(f"Using cached quality analysis for job {job.id}")
                    return self._format_analysis_result(existing_analysis)

            # Create new analysis record
            analysis = self.repository.create_job_analysis(
                job_id=job.id,
                analysis_type=AnalysisType.QUALITY,
                status=AnalysisStatus.IN_PROGRESS
            )

            logger.info(f"Starting quality analysis for job {job.id}")

            try:
                # Get Claude analysis
                start_time = datetime.now()
                claude_result = await self.claude_client.analyze_job_quality(job)
                processing_time = (datetime.now() - start_time).total_seconds()

                # Calculate local metrics for enrichment
                local_metrics = self._calculate_local_metrics(job)

                # Combine Claude analysis with local metrics
                enriched_result = self._enrich_analysis_result(claude_result, local_metrics)

                # Update analysis record with success
                self.repository.update_job_analysis_status(
                    analysis.id,
                    AnalysisStatus.COMPLETED,
                    quality_score=enriched_result.get('quality_score'),
                    analysis_data=enriched_result,
                    processing_time_seconds=processing_time,
                    api_cost=self.claude_client.get_usage_stats().get('total_cost', 0)
                )

                logger.info(f"Quality analysis completed for job {job.id}, score: {enriched_result.get('quality_score')}")
                return enriched_result

            except Exception as e:
                logger.error(f"Claude API failed for job {job.id}: {str(e)}")

                if use_local_fallback:
                    # Fall back to local analysis
                    local_result = await self._perform_local_analysis(job)

                    self.repository.update_job_analysis_status(
                        analysis.id,
                        AnalysisStatus.COMPLETED,
                        quality_score=local_result.get('quality_score'),
                        analysis_data=local_result,
                        error_message=f"Used local fallback due to API error: {str(e)}"
                    )

                    return local_result
                else:
                    # Update analysis as failed
                    self.repository.update_job_analysis_status(
                        analysis.id,
                        AnalysisStatus.FAILED,
                        error_message=str(e)
                    )
                    raise

        except Exception as e:
            logger.error(f"Job quality analysis failed for job {job.id}: {str(e)}")
            raise

    async def batch_analyze_jobs(
        self,
        jobs: List[JobModel],
        batch_size: int = 5,
        use_local_fallback: bool = False
    ) -> List[Dict[str, Any]]:
        """Analyze multiple jobs in batches.

        Args:
            jobs: List of jobs to analyze
            batch_size: Number of jobs to process in parallel
            use_local_fallback: Use local analysis if Claude API fails

        Returns:
            List of analysis results
        """
        results = []

        for i in range(0, len(jobs), batch_size):
            batch = jobs[i:i + batch_size]
            batch_tasks = [
                self.analyze_job_quality(job, use_local_fallback=use_local_fallback)
                for job in batch
            ]

            # Process batch with error handling
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process results and handle exceptions
            for job, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch analysis failed for job {job.id}: {result}")
                    results.append({
                        "job_id": job.id,
                        "error": str(result),
                        "quality_score": None
                    })
                else:
                    result["job_id"] = job.id
                    results.append(result)

            # Add delay between batches to respect rate limits
            if i + batch_size < len(jobs):
                await asyncio.sleep(1)

        return results

    def get_quality_insights_summary(self, analyses: List[JobAnalysisModel]) -> Dict[str, Any]:
        """Generate insights summary from multiple quality analyses.

        Args:
            analyses: List of completed quality analyses

        Returns:
            Dictionary with summary insights
        """
        if not analyses:
            return {"message": "No analyses available"}

        # Calculate basic statistics
        scores = [a.quality_score for a in analyses if a.quality_score is not None]
        total_jobs = len(analyses)
        completed_jobs = len(scores)

        if not scores:
            return {"message": "No completed analyses with scores"}

        avg_score = sum(scores) / len(scores)

        # Analyze common patterns
        all_strengths = []
        all_weaknesses = []

        for analysis in analyses:
            if analysis.analysis_data:
                strengths = analysis.analysis_data.get('strengths', [])
                weaknesses = analysis.analysis_data.get('weaknesses', [])
                all_strengths.extend(strengths)
                all_weaknesses.extend(weaknesses)

        # Find common themes
        common_strengths = self._find_common_themes(all_strengths)
        common_weaknesses = self._find_common_themes(all_weaknesses)

        # Score distribution
        score_ranges = {
            "excellent": len([s for s in scores if s >= 90]),
            "good": len([s for s in scores if 80 <= s < 90]),
            "fair": len([s for s in scores if 70 <= s < 80]),
            "poor": len([s for s in scores if s < 70])
        }

        return {
            "total_jobs": total_jobs,
            "completed_analyses": completed_jobs,
            "average_score": round(avg_score, 2),
            "min_score": min(scores),
            "max_score": max(scores),
            "score_distribution": score_ranges,
            "common_strengths": common_strengths[:5],  # Top 5
            "common_weaknesses": common_weaknesses[:5],  # Top 5
            "recommendations": self._generate_quality_recommendations(avg_score, common_weaknesses)
        }

    async def _get_recent_analysis(self, job_id: int) -> Optional[JobAnalysisModel]:
        """Get most recent quality analysis for a job."""
        analyses = self.repository.get_job_analyses_for_job(
            job_id=job_id,
            analysis_type=AnalysisType.QUALITY
        )
        return analyses[0] if analyses else None

    def _should_use_cached_result(self, analysis: JobAnalysisModel, force_refresh: bool) -> bool:
        """Determine if cached analysis result should be used."""
        if force_refresh:
            return False

        if analysis.status != AnalysisStatus.COMPLETED:
            return False

        # Check if analysis is within cache TTL
        if analysis.created_at:
            age = datetime.now(timezone.utc) - analysis.created_at.replace(tzinfo=timezone.utc)
            return age.total_seconds() < self.cache_ttl

        return False

    def _format_analysis_result(self, analysis: JobAnalysisModel) -> Dict[str, Any]:
        """Format analysis model to result dictionary."""
        result = {
            "analysis_id": analysis.id,
            "job_id": analysis.job_id,
            "quality_score": analysis.quality_score,
            "status": analysis.status.value,
            "created_at": analysis.created_at.isoformat() if analysis.created_at else None
        }

        # Add analysis data if available
        if analysis.analysis_data:
            result.update(analysis.analysis_data)

        return result

    def _calculate_local_metrics(self, job: JobModel) -> QualityMetrics:
        """Calculate local quality metrics for a job."""
        description = job.description.lower() if job.description else ""

        # Basic metrics
        description_length = len(job.description) if job.description else 0
        has_salary_info = self._extract_salary_info(job.description or "")
        has_benefits_info = self._extract_benefits_info(description)
        has_company_info = bool(job.company and len(job.company.strip()) > 0)

        # Advanced metrics
        requirement_clarity = self._calculate_requirement_clarity(job.description or "")
        responsibility_clarity = self._calculate_responsibility_clarity(job.description or "")
        keyword_density = self._calculate_keyword_density(description)

        # Overall local score (weighted average)
        weights = {
            'length': 0.15,
            'salary': 0.20,
            'benefits': 0.15,
            'company': 0.10,
            'requirements': 0.20,
            'responsibilities': 0.15,
            'keywords': 0.05
        }

        length_score = min(100, (description_length / 1000) * 100)  # 1000+ chars = 100
        salary_score = 100 if has_salary_info else 0
        benefits_score = 100 if has_benefits_info else 0
        company_score = 100 if has_company_info else 0

        overall_score = (
            length_score * weights['length'] +
            salary_score * weights['salary'] +
            benefits_score * weights['benefits'] +
            company_score * weights['company'] +
            requirement_clarity * weights['requirements'] +
            responsibility_clarity * weights['responsibilities'] +
            keyword_density * weights['keywords']
        )

        return QualityMetrics(
            description_length=description_length,
            has_salary_info=has_salary_info,
            has_benefits_info=has_benefits_info,
            has_company_info=has_company_info,
            requirement_clarity_score=requirement_clarity,
            responsibility_clarity_score=responsibility_clarity,
            keyword_density_score=keyword_density,
            overall_local_score=int(overall_score)
        )

    def _extract_salary_info(self, description: str) -> bool:
        """Check if job description contains salary information."""
        salary_patterns = [
            r'\$[\d,]+\s*[-to]\s*\$[\d,]+',  # $80,000 - $120,000
            r'\$[\d,]+k?\s*[-to]\s*\$[\d,]+k?',  # $80k - $120k
            r'salary.*\$[\d,]+',  # salary: $100,000
            r'compensation.*\$[\d,]+',  # compensation $100,000
            r'\$[\d,]+\s*(?:per|\/)\s*(?:year|yr|annum)',  # $100,000 per year
        ]

        description_lower = description.lower()
        return any(re.search(pattern, description_lower) for pattern in salary_patterns)

    def _extract_benefits_info(self, description: str) -> bool:
        """Check if job description contains benefits information."""
        benefits_keywords = [
            'health insurance', 'dental', 'vision', 'medical',
            '401k', 'retirement', 'pension',
            'pto', 'paid time off', 'vacation', 'sick leave',
            'flexible', 'remote work', 'work from home',
            'bonus', 'stock options', 'equity'
        ]

        return any(keyword in description for keyword in benefits_keywords)

    def _calculate_requirement_clarity(self, description: str) -> int:
        """Calculate clarity score for job requirements (0-100)."""
        if not description:
            return 0

        description_lower = description.lower()

        # Look for requirement indicators
        requirement_indicators = [
            'requirements:', 'required:', 'must have:', 'qualifications:',
            'what you need:', 'prerequisites:', 'skills needed:'
        ]

        has_requirement_section = any(indicator in description_lower for indicator in requirement_indicators)

        # Look for specific experience mentions
        experience_patterns = [
            r'\d+\+?\s*years?\s*(?:of\s*)?experience',
            r'bachelor|master|phd|degree',
            r'certification|certified',
        ]

        experience_mentions = sum(1 for pattern in experience_patterns
                                if re.search(pattern, description_lower))

        # Look for technical skill specificity
        technical_keywords = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue',
            'sql', 'postgresql', 'mysql', 'mongodb',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes',
            'git', 'linux', 'agile', 'scrum'
        ]

        technical_mentions = sum(1 for keyword in technical_keywords
                               if keyword in description_lower)

        # Calculate score
        score = 0
        if has_requirement_section:
            score += 40
        score += min(30, experience_mentions * 15)  # Up to 30 points
        score += min(30, technical_mentions * 3)    # Up to 30 points

        return min(100, score)

    def _calculate_responsibility_clarity(self, description: str) -> int:
        """Calculate clarity score for job responsibilities (0-100)."""
        if not description:
            return 0

        description_lower = description.lower()

        # Look for responsibility indicators
        responsibility_indicators = [
            'responsibilities:', 'duties:', 'you will:', 'role involves:',
            'what you\'ll do:', 'day-to-day:', 'key tasks:'
        ]

        has_responsibility_section = any(indicator in description_lower
                                       for indicator in responsibility_indicators)

        # Count bullet points or numbered lists
        bullet_patterns = [r'^\s*[-•*]\s+', r'^\s*\d+\.\s+']
        bullet_count = 0
        for line in description.split('\n'):
            if any(re.match(pattern, line) for pattern in bullet_patterns):
                bullet_count += 1

        # Look for action verbs
        action_verbs = [
            'develop', 'build', 'create', 'design', 'implement',
            'manage', 'lead', 'coordinate', 'collaborate',
            'analyze', 'optimize', 'maintain', 'troubleshoot'
        ]

        action_verb_count = sum(1 for verb in action_verbs
                              if verb in description_lower)

        # Calculate score
        score = 0
        if has_responsibility_section:
            score += 50
        score += min(25, bullet_count * 5)      # Up to 25 points
        score += min(25, action_verb_count * 2) # Up to 25 points

        return min(100, score)

    def _calculate_keyword_density(self, description: str) -> int:
        """Calculate quality keyword density score (0-100)."""
        if not description:
            return 0

        total_keywords = sum(len(keywords) for keywords in self.quality_keywords.values())
        found_keywords = 0

        for category, keywords in self.quality_keywords.items():
            found_keywords += sum(1 for keyword in keywords if keyword in description)

        density = (found_keywords / total_keywords) * 100 if total_keywords > 0 else 0
        return min(100, int(density))

    def _enrich_analysis_result(self, claude_result: Dict[str, Any], local_metrics: QualityMetrics) -> Dict[str, Any]:
        """Enrich Claude analysis with local metrics."""
        enriched = claude_result.copy()

        # Add local metrics
        enriched["local_metrics"] = {
            "description_length": local_metrics.description_length,
            "has_salary_info": local_metrics.has_salary_info,
            "has_benefits_info": local_metrics.has_benefits_info,
            "requirement_clarity_score": local_metrics.requirement_clarity_score,
            "responsibility_clarity_score": local_metrics.responsibility_clarity_score,
            "overall_local_score": local_metrics.overall_local_score
        }

        # Adjust Claude score based on local metrics if significant discrepancy
        claude_score = claude_result.get('quality_score', 0)
        local_score = local_metrics.overall_local_score

        if abs(claude_score - local_score) > 20:
            # Weighted average favoring Claude but considering local
            adjusted_score = int(claude_score * 0.7 + local_score * 0.3)
            enriched["adjusted_quality_score"] = adjusted_score
            enriched["score_adjustment_reason"] = "Adjusted based on local metrics analysis"

        return enriched

    async def _perform_local_analysis(self, job: JobModel) -> Dict[str, Any]:
        """Perform local analysis when Claude API is unavailable."""
        local_metrics = self._calculate_local_metrics(job)

        # Generate basic insights based on local metrics
        strengths = []
        weaknesses = []

        if local_metrics.has_salary_info:
            strengths.append("Salary information provided")
        else:
            weaknesses.append("No salary information")

        if local_metrics.has_benefits_info:
            strengths.append("Benefits information included")
        else:
            weaknesses.append("Benefits not clearly outlined")

        if local_metrics.requirement_clarity_score > 70:
            strengths.append("Clear requirements specification")
        else:
            weaknesses.append("Requirements could be more specific")

        if local_metrics.description_length > 500:
            strengths.append("Comprehensive job description")
        else:
            weaknesses.append("Job description could be more detailed")

        return {
            "quality_score": local_metrics.overall_local_score,
            "reasoning": f"Local analysis based on description structure and content. Score: {local_metrics.overall_local_score}/100",
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": "Consider reviewing job posting for missing information and clarity improvements.",
            "analysis_type": "local_fallback",
            "local_metrics": {
                "description_length": local_metrics.description_length,
                "has_salary_info": local_metrics.has_salary_info,
                "has_benefits_info": local_metrics.has_benefits_info,
                "requirement_clarity_score": local_metrics.requirement_clarity_score,
                "responsibility_clarity_score": local_metrics.responsibility_clarity_score
            }
        }

    def _find_common_themes(self, items: List[str]) -> List[str]:
        """Find common themes in a list of strings."""
        if not items:
            return []

        # Simple frequency counting
        from collections import Counter

        # Split items into words and count frequency
        all_words = []
        for item in items:
            words = re.findall(r'\b\w+\b', item.lower())
            all_words.extend(words)

        # Filter out common words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'a', 'an'}
        filtered_words = [word for word in all_words if word not in stop_words and len(word) > 3]

        # Get most common words
        counter = Counter(filtered_words)
        return [word for word, count in counter.most_common(10)]

    def _generate_quality_recommendations(self, avg_score: float, common_weaknesses: List[str]) -> List[str]:
        """Generate recommendations based on analysis results."""
        recommendations = []

        if avg_score < 70:
            recommendations.append("Focus on improving job description quality and clarity")

        if 'salary' in ' '.join(common_weaknesses).lower():
            recommendations.append("Consider adding salary ranges to increase transparency")

        if 'benefit' in ' '.join(common_weaknesses).lower():
            recommendations.append("Highlight benefits and perks more clearly")

        if 'requirement' in ' '.join(common_weaknesses).lower():
            recommendations.append("Provide more specific and clear requirements")

        if not recommendations:
            recommendations.append("Job postings are generally of good quality, continue current practices")

        return recommendations