"""AI-powered job matching service."""

import re
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

from ..claude_client import ClaudeClient
from ..repository import AnalysisRepository
from ..models import UserProfileModel, JobMatchModel
from ...database.models import JobModel
from ...database.repository import JobRepository


logger = logging.getLogger(__name__)


@dataclass
class MatchingMetrics:
    """Local matching metrics for job-profile compatibility."""

    skill_match_score: int  # 0-100
    experience_match_score: int  # 0-100
    location_match_score: int  # 0-100
    salary_match_score: int  # 0-100
    overall_local_score: int  # 0-100


class JobMatchingService:
    """Service for AI-powered job matching to user profiles."""

    def __init__(
        self,
        claude_client: ClaudeClient,
        repository: AnalysisRepository,
        job_repository: JobRepository,
        cache_ttl: int = 1800  # 30 minutes cache for matching data
    ):
        """Initialize job matching service.

        Args:
            claude_client: Claude API client for analysis
            repository: Analysis repository for data persistence
            job_repository: Job repository for finding candidates
            cache_ttl: Cache time-to-live in seconds
        """
        self.claude_client = claude_client
        self.repository = repository
        self.job_repository = job_repository
        self.cache_ttl = cache_ttl

        # Skill keywords and categories
        self.skill_categories = {
            'python': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy'],
            'javascript': ['javascript', 'js', 'react', 'angular', 'vue', 'node', 'express'],
            'java': ['java', 'spring', 'hibernate', 'maven', 'gradle'],
            'database': ['sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform'],
            'web': ['html', 'css', 'rest', 'api', 'graphql', 'microservices'],
            'data': ['data science', 'machine learning', 'ai', 'analytics', 'etl', 'spark'],
            'devops': ['devops', 'ci/cd', 'jenkins', 'github actions', 'linux', 'bash']
        }

        # Experience level mappings
        self.experience_levels = {
            'entry': 0,
            'junior': 1,
            'mid': 3,
            'senior': 5,
            'lead': 8,
            'principal': 10,
            'executive': 15
        }

        logger.info("JobMatchingService initialized")

    async def match_job_to_profile(
        self,
        job: JobModel,
        profile: UserProfileModel,
        force_refresh: bool = False,
        use_local_fallback: bool = True
    ) -> Dict[str, Any]:
        """Match a job to a user profile using AI analysis.

        Args:
            job: Job model to match
            profile: User profile to match against
            force_refresh: Force new analysis even if cached result exists
            use_local_fallback: Use local analysis if Claude API fails

        Returns:
            Dictionary with matching analysis results
        """
        try:
            # Check for existing match
            if not force_refresh:
                existing_match = self.repository.get_job_match(job.id, profile.id)
                if existing_match and self._should_use_cached_match(existing_match, force_refresh):
                    logger.info(f"Using cached match for job {job.id} and profile {profile.id}")
                    return self._format_match_result(existing_match)

            logger.info(f"Starting job matching for job {job.id} and profile {profile.id}")

            # Calculate local matching metrics
            local_metrics = self._calculate_local_matching_metrics(job, profile)

            try:
                # Get Claude analysis
                start_time = datetime.now()
                claude_result = await self.claude_client.match_job_to_profile(
                    job,
                    profile.to_dict()
                )
                processing_time = (datetime.now() - start_time).total_seconds()

                # Enrich Claude analysis with local metrics
                enriched_result = self._enrich_match_result(claude_result, local_metrics)

                # Store match result
                match_data = {
                    "job_id": job.id,
                    "user_profile_id": profile.id,
                    "match_score": enriched_result.get("match_score", 0),
                    "recommendation": enriched_result.get("recommendation", "consider"),
                    "skill_match_score": local_metrics.skill_match_score,
                    "experience_match_score": local_metrics.experience_match_score,
                    "location_match_score": local_metrics.location_match_score,
                    "salary_match_score": local_metrics.salary_match_score,
                    "match_data": enriched_result
                }

                self.repository.create_job_match(**match_data)

                logger.info(f"Job matching completed for job {job.id}, score: {enriched_result.get('match_score')}")
                return enriched_result

            except Exception as e:
                logger.error(f"Claude API failed for job matching: {str(e)}")

                if use_local_fallback:
                    # Fall back to local analysis
                    local_result = await self._perform_local_matching(job, profile, local_metrics)

                    # Store local result
                    match_data = {
                        "job_id": job.id,
                        "user_profile_id": profile.id,
                        "match_score": local_result.get("match_score", 0),
                        "recommendation": local_result.get("recommendation", "consider"),
                        "skill_match_score": local_metrics.skill_match_score,
                        "experience_match_score": local_metrics.experience_match_score,
                        "location_match_score": local_metrics.location_match_score,
                        "salary_match_score": local_metrics.salary_match_score,
                        "match_data": local_result
                    }

                    self.repository.create_job_match(**match_data)
                    return local_result
                else:
                    raise

        except Exception as e:
            logger.error(f"Job matching failed for job {job.id}: {str(e)}")
            raise

    async def batch_match_jobs_to_profile(
        self,
        profile: UserProfileModel,
        jobs: List[JobModel],
        batch_size: int = 5,
        use_local_fallback: bool = True
    ) -> List[Dict[str, Any]]:
        """Match multiple jobs to a user profile in batches.

        Args:
            profile: User profile to match against
            jobs: List of jobs to match
            batch_size: Number of jobs to process in parallel
            use_local_fallback: Use local analysis if Claude API fails

        Returns:
            List of matching results
        """
        results = []

        for i in range(0, len(jobs), batch_size):
            batch = jobs[i:i + batch_size]
            batch_tasks = [
                self.match_job_to_profile(job, profile, use_local_fallback=use_local_fallback)
                for job in batch
            ]

            # Process batch with error handling
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process results and handle exceptions
            for job, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch matching failed for job {job.id}: {result}")
                    results.append({
                        "job_id": job.id,
                        "error": str(result),
                        "match_score": None
                    })
                else:
                    result["job_id"] = job.id
                    results.append(result)

            # Add delay between batches
            if i + batch_size < len(jobs):
                await asyncio.sleep(1)

        return results

    async def find_matching_jobs_for_profile(
        self,
        profile: UserProfileModel,
        max_results: int = 50
    ) -> List[JobModel]:
        """Find jobs that match a user profile.

        Args:
            profile: User profile to find matches for
            max_results: Maximum number of jobs to return

        Returns:
            List of potentially matching jobs
        """
        matching_jobs = []

        # Search by desired roles
        if profile.desired_roles:
            for role in profile.desired_roles[:3]:  # Top 3 desired roles
                role_jobs = self.job_repository.search_jobs(
                    title=role,
                    limit=20
                )
                matching_jobs.extend(role_jobs)

        # Search by skills
        if profile.skills:
            main_skills = profile.skills[:5]  # Top 5 skills
            for skill in main_skills:
                skill_jobs = self.job_repository.search_jobs(
                    title=skill,
                    limit=15
                )
                matching_jobs.extend(skill_jobs)

        # Search by location preferences
        if profile.preferred_locations:
            for location in profile.preferred_locations[:2]:  # Top 2 locations
                location_jobs = self.job_repository.search_jobs(
                    location=location,
                    limit=20
                )
                matching_jobs.extend(location_jobs)

        # Search by experience level
        experience_level = self._map_experience_years_to_level(profile.experience_years or 0)
        if experience_level:
            exp_jobs = self.job_repository.search_jobs(
                experience_level=experience_level,
                limit=25
            )
            matching_jobs.extend(exp_jobs)

        # Remove duplicates
        unique_jobs = []
        seen_ids = set()
        for job in matching_jobs:
            if job.id not in seen_ids:
                unique_jobs.append(job)
                seen_ids.add(job.id)

        # Sort by relevance and return top matches
        profile_keywords = set(skill.lower() for skill in (profile.skills or []))
        for job in unique_jobs:
            job_keywords = self._extract_job_skills(job)
            overlap = len(profile_keywords.intersection(job_keywords))
            job._relevance_score = overlap

        unique_jobs.sort(key=lambda j: getattr(j, '_relevance_score', 0), reverse=True)
        return unique_jobs[:max_results]

    def get_profile_matching_summary(self, user_profile_id: int) -> Dict[str, Any]:
        """Get comprehensive matching summary for a user profile.

        Args:
            user_profile_id: ID of user profile

        Returns:
            Dictionary with matching insights and statistics
        """
        try:
            # Get all matches for profile
            matches = self.repository.get_job_matches_for_profile(user_profile_id, limit=1000)

            if not matches:
                return {"message": "No matches found for this profile"}

            total_matches = len(matches)

            # Score statistics
            scores = [m.match_score for m in matches if m.match_score is not None]
            avg_score = sum(scores) / len(scores) if scores else 0

            # Recommendation breakdown
            recommendations = {}
            for match in matches:
                rec = match.recommendation or "unknown"
                recommendations[rec] = recommendations.get(rec, 0) + 1

            # Component score averages
            skill_scores = [m.skill_match_score for m in matches if m.skill_match_score is not None]
            exp_scores = [m.experience_match_score for m in matches if m.experience_match_score is not None]
            location_scores = [m.location_match_score for m in matches if m.location_match_score is not None]
            salary_scores = [m.salary_match_score for m in matches if m.salary_match_score is not None]

            avg_skill = sum(skill_scores) / len(skill_scores) if skill_scores else 0
            avg_exp = sum(exp_scores) / len(exp_scores) if exp_scores else 0
            avg_location = sum(location_scores) / len(location_scores) if location_scores else 0
            avg_salary = sum(salary_scores) / len(salary_scores) if salary_scores else 0

            # Top matches
            top_matches = sorted(matches, key=lambda m: m.match_score or 0, reverse=True)[:5]

            # Generate insights
            insights = self._generate_profile_insights(
                avg_score, avg_skill, avg_exp, avg_location, avg_salary, recommendations
            )

            return {
                "total_matches": total_matches,
                "average_match_score": round(avg_score, 2),
                "recommendation_breakdown": recommendations,
                "component_scores": {
                    "skill_alignment": round(avg_skill, 2),
                    "experience_fit": round(avg_exp, 2),
                    "location_compatibility": round(avg_location, 2),
                    "salary_alignment": round(avg_salary, 2)
                },
                "top_matches": [
                    {
                        "job_id": match.job_id,
                        "match_score": match.match_score,
                        "recommendation": match.recommendation
                    }
                    for match in top_matches
                ],
                "skill_insights": insights,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to generate profile matching summary: {str(e)}")
            raise

    def _calculate_local_matching_metrics(self, job: JobModel, profile: UserProfileModel) -> MatchingMetrics:
        """Calculate comprehensive local matching metrics."""
        # Skill matching
        skill_score = self._calculate_skill_match(job, profile)

        # Experience matching
        required_years = self._extract_required_years_from_job(
            job.description or "",
            job.experience_level or ""
        )
        experience_score = self._calculate_experience_match(
            required_years,
            profile.experience_years or 0
        )

        # Location matching
        location_score = self._calculate_location_match(
            job.location or "",
            profile.preferred_locations or []
        )

        # Salary matching
        salary_expectations = profile.salary_expectations or {}
        salary_score = self._calculate_salary_match(
            job.salary_min,
            job.salary_max,
            salary_expectations.get("min"),
            salary_expectations.get("max")
        )

        # Overall score (weighted average)
        weights = {
            'skill': 0.35,
            'experience': 0.25,
            'location': 0.20,
            'salary': 0.20
        }

        overall_score = (
            skill_score * weights['skill'] +
            experience_score * weights['experience'] +
            location_score * weights['location'] +
            salary_score * weights['salary']
        )

        return MatchingMetrics(
            skill_match_score=skill_score,
            experience_match_score=experience_score,
            location_match_score=location_score,
            salary_match_score=salary_score,
            overall_local_score=int(overall_score)
        )

    def _calculate_skill_match(self, job: JobModel, profile: UserProfileModel) -> int:
        """Calculate skill matching score (0-100)."""
        if not profile.skills:
            return 0

        job_skills = self._extract_job_skills(job)
        profile_skills = set(skill.lower() for skill in profile.skills)

        if not job_skills:
            return 50  # Neutral score if no skills detected

        # Direct skill matches
        direct_matches = job_skills.intersection(profile_skills)
        direct_score = (len(direct_matches) / len(job_skills)) * 100 if job_skills else 0

        # Category-based matches (related skills)
        category_matches = 0
        for job_skill in job_skills:
            for profile_skill in profile_skills:
                if self._are_related_skills(job_skill, profile_skill):
                    category_matches += 1
                    break

        category_score = (category_matches / len(job_skills)) * 60 if job_skills else 0

        # Combined score (favor direct matches)
        final_score = max(direct_score, category_score)
        return min(100, int(final_score))

    def _calculate_experience_match(self, required_years: int, candidate_years: int) -> int:
        """Calculate experience matching score (0-100)."""
        if required_years == 0:
            return 100  # Any experience is fine

        diff = candidate_years - required_years

        if diff >= 0:
            # Meets or exceeds requirements
            if diff <= 2:
                return 100  # Perfect match
            elif diff <= 5:
                return 90   # Slightly over-qualified
            else:
                return max(70, 100 - (diff - 5) * 5)  # Over-qualified penalty
        else:
            # Under-qualified
            shortage = abs(diff)
            if shortage == 1:
                return 75
            elif shortage == 2:
                return 50
            else:
                return max(10, 50 - shortage * 10)

    def _calculate_location_match(self, job_location: str, preferred_locations: List[str]) -> int:
        """Calculate location matching score (0-100)."""
        if not preferred_locations:
            return 50  # Neutral if no preferences

        job_location_lower = job_location.lower()

        for pref_location in preferred_locations:
            pref_lower = pref_location.lower()

            # Exact match or contains
            if pref_lower == job_location_lower or pref_lower in job_location_lower:
                return 100

            # Remote work matching
            if "remote" in pref_lower and "remote" in job_location_lower:
                return 100

            # City/state partial matching
            if self._locations_match(job_location_lower, pref_lower):
                return 80

        return 20  # No location match

    def _calculate_salary_match(
        self,
        job_min: Optional[int],
        job_max: Optional[int],
        expected_min: Optional[int],
        expected_max: Optional[int]
    ) -> int:
        """Calculate salary matching score (0-100)."""
        # If no salary information available
        if not job_min and not job_max:
            return 50  # Neutral score

        if not expected_min and not expected_max:
            return 50  # Neutral if no expectations

        # Use job max and expected min for primary comparison
        job_salary = job_max or job_min or 0
        expected_salary = expected_min or expected_max or 0

        if expected_salary == 0:
            return 50

        ratio = job_salary / expected_salary

        if ratio >= 1.0:
            # Meets or exceeds expectations
            if ratio <= 1.2:
                return 100  # Perfect range
            else:
                return 90   # Exceeds expectations
        else:
            # Below expectations
            if ratio >= 0.9:
                return 80   # Close to expectations
            elif ratio >= 0.8:
                return 60   # Somewhat below
            elif ratio >= 0.7:
                return 40   # Significantly below
            else:
                return 20   # Far below expectations

    def _extract_required_years_from_job(self, description: str, experience_level: str) -> int:
        """Extract required years of experience from job description."""
        # Look for explicit year requirements
        year_patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'minimum\s*(?:of\s*)?(\d+)\s*years?',
            r'at\s*least\s*(\d+)\s*years?',
        ]

        for pattern in year_patterns:
            match = re.search(pattern, description.lower())
            if match:
                return int(match.group(1))

        # Fall back to experience level mapping
        level_lower = experience_level.lower()
        for level, years in self.experience_levels.items():
            if level in level_lower:
                return years

        return 3  # Default middle experience

    def _extract_job_skills(self, job: JobModel) -> Set[str]:
        """Extract relevant skills from job title and description."""
        text = f"{job.title} {job.description or ''}".lower()

        found_skills = set()

        # Extract from all skill categories
        for category, skills in self.skill_categories.items():
            for skill in skills:
                if skill in text:
                    found_skills.add(skill)

        # Also look for common skills not in categories
        additional_skills = [
            'git', 'linux', 'agile', 'scrum', 'testing', 'debugging',
            'architecture', 'design patterns', 'algorithms', 'data structures'
        ]

        for skill in additional_skills:
            if skill in text:
                found_skills.add(skill)

        return found_skills

    def _are_related_skills(self, skill1: str, skill2: str) -> bool:
        """Check if two skills are related within the same category."""
        for category, skills in self.skill_categories.items():
            if skill1 in skills and skill2 in skills:
                return True
        return False

    def _locations_match(self, location1: str, location2: str) -> bool:
        """Check if two location strings match."""
        # Split by comma and check parts
        parts1 = [part.strip() for part in location1.split(',')]
        parts2 = [part.strip() for part in location2.split(',')]

        # Check for any overlap
        for part1 in parts1:
            for part2 in parts2:
                if part1 in part2 or part2 in part1:
                    return True

        return False

    def _map_experience_years_to_level(self, years: int) -> str:
        """Map years of experience to experience level."""
        if years == 0:
            return "entry"
        elif years <= 2:
            return "junior"
        elif years <= 5:
            return "mid"
        elif years <= 8:
            return "senior"
        elif years <= 12:
            return "lead"
        else:
            return "principal"

    def _enrich_match_result(self, claude_result: Dict[str, Any], local_metrics: MatchingMetrics) -> Dict[str, Any]:
        """Enrich Claude match result with local metrics."""
        enriched = claude_result.copy()

        # Add local metrics
        enriched["local_metrics"] = {
            "skill_match_score": local_metrics.skill_match_score,
            "experience_match_score": local_metrics.experience_match_score,
            "location_match_score": local_metrics.location_match_score,
            "salary_match_score": local_metrics.salary_match_score,
            "overall_local_score": local_metrics.overall_local_score
        }

        # Adjust Claude score if there's significant discrepancy
        claude_score = claude_result.get("match_score", 50)
        local_score = local_metrics.overall_local_score

        if abs(claude_score - local_score) > 15:
            adjusted_score = int(claude_score * 0.6 + local_score * 0.4)
            enriched["adjusted_match_score"] = adjusted_score
            enriched["score_adjustment_reason"] = "Adjusted based on local compatibility analysis"

        return enriched

    async def _perform_local_matching(
        self,
        job: JobModel,
        profile: UserProfileModel,
        local_metrics: MatchingMetrics
    ) -> Dict[str, Any]:
        """Perform local matching analysis when Claude API is unavailable."""
        match_score = local_metrics.overall_local_score
        recommendation = self._generate_match_recommendation(match_score)

        # Generate basic explanation
        explanations = []
        if local_metrics.skill_match_score >= 80:
            explanations.append("Strong skill alignment")
        elif local_metrics.skill_match_score >= 60:
            explanations.append("Good skill compatibility")
        else:
            explanations.append("Limited skill match")

        if local_metrics.experience_match_score >= 80:
            explanations.append("Experience level fits well")
        elif local_metrics.experience_match_score < 50:
            explanations.append("Experience level mismatch")

        if local_metrics.location_match_score >= 80:
            explanations.append("Location preferences align")

        if local_metrics.salary_match_score >= 80:
            explanations.append("Salary expectations met")

        return {
            "match_score": match_score,
            "recommendation": recommendation,
            "explanation": f"Local analysis: {', '.join(explanations)}",
            "skill_alignment": {
                "score": local_metrics.skill_match_score,
                "analysis": "Based on skill keyword matching"
            },
            "experience_fit": f"Experience compatibility: {local_metrics.experience_match_score}%",
            "location_preference": f"Location match: {local_metrics.location_match_score}%",
            "salary_expectation": f"Salary alignment: {local_metrics.salary_match_score}%",
            "analysis_type": "local_fallback",
            "local_metrics": {
                "skill_match_score": local_metrics.skill_match_score,
                "experience_match_score": local_metrics.experience_match_score,
                "location_match_score": local_metrics.location_match_score,
                "salary_match_score": local_metrics.salary_match_score
            }
        }

    def _generate_match_recommendation(self, match_score: int) -> str:
        """Generate recommendation based on match score."""
        if match_score >= 85:
            return "strong_match"
        elif match_score >= 70:
            return "apply"
        elif match_score >= 55:
            return "consider"
        else:
            return "skip"

    def _should_use_cached_match(self, match: JobMatchModel, force_refresh: bool) -> bool:
        """Determine if cached match result should be used."""
        if force_refresh:
            return False

        if not match.created_at:
            return False

        # Check if match is within cache TTL
        age = datetime.now(timezone.utc) - match.created_at.replace(tzinfo=timezone.utc)
        return age.total_seconds() < self.cache_ttl

    def _format_match_result(self, match: JobMatchModel) -> Dict[str, Any]:
        """Format match model to result dictionary."""
        result = {
            "match_id": match.id,
            "job_id": match.job_id,
            "user_profile_id": match.user_profile_id,
            "match_score": match.match_score,
            "recommendation": match.recommendation,
            "created_at": match.created_at.isoformat() if match.created_at else None
        }

        # Add match data if available
        if match.match_data:
            result.update(match.match_data)

        return result

    def _generate_profile_insights(
        self,
        avg_score: float,
        avg_skill: float,
        avg_exp: float,
        avg_location: float,
        avg_salary: float,
        recommendations: Dict[str, int]
    ) -> List[str]:
        """Generate insights for profile matching performance."""
        insights = []

        # Overall performance
        if avg_score >= 75:
            insights.append("Profile shows strong compatibility with available opportunities")
        elif avg_score >= 60:
            insights.append("Profile has good potential for matching roles")
        else:
            insights.append("Profile may need optimization for better job matching")

        # Component analysis
        if avg_skill < 60:
            insights.append("Consider expanding or highlighting relevant technical skills")

        if avg_exp < 60:
            insights.append("Experience level may be limiting opportunities - consider broader role categories")

        if avg_location < 50:
            insights.append("Location preferences may be restricting available opportunities")

        if avg_salary < 50:
            insights.append("Salary expectations may be above market range for target roles")

        # Recommendation patterns
        total_matches = sum(recommendations.values())
        if total_matches > 0:
            strong_matches = recommendations.get("strong_match", 0) + recommendations.get("apply", 0)
            strong_ratio = strong_matches / total_matches

            if strong_ratio > 0.6:
                insights.append("High proportion of strong matches indicates good profile-market fit")
            elif strong_ratio < 0.2:
                insights.append("Low proportion of strong matches suggests profile refinement needed")

        return insights