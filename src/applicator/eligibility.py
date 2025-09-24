"""Application eligibility engine for determining job application viability."""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..database.models import JobModel
from ..analyzer.models import UserProfileModel, JobMatchModel
from .models import ApplicationStatus, JobApplicationModel
from .repository import ApplicationRepository
from ..analyzer.services.job_matching_service import JobMatchingService
from ..analyzer.services.job_quality_service import JobQualityService
from ..analyzer.services.competition_service import CompetitionAnalysisService


logger = logging.getLogger(__name__)


@dataclass
class EligibilityResult:
    """Result of eligibility evaluation."""
    eligible: bool
    confidence_score: int  # 0-100
    reasons: List[str]
    blocking_factors: List[str]
    recommendations: List[str]
    estimated_success_probability: float
    quality_score: Optional[int] = None
    match_score: Optional[int] = None
    competition_score: Optional[int] = None


@dataclass
class ApplicationRecommendation:
    """Strategic application recommendation."""
    should_apply: bool
    priority_level: str  # "high", "medium", "low"
    recommended_timing: str  # "immediate", "soon", "later", "monitor"
    application_strategy: str
    content_suggestions: List[str]
    risk_factors: List[str]
    success_indicators: List[str]


@dataclass
class EligibilityConfig:
    """Configuration for eligibility evaluation."""

    # Quality thresholds
    min_quality_score: int = 70
    min_match_score: int = 60
    max_competition_score: int = 80

    # Application history limits
    max_applications_per_company: int = 3
    min_days_between_applications: int = 30

    # User preference weights
    salary_weight: float = 0.2
    location_weight: float = 0.15
    experience_weight: float = 0.25
    skills_weight: float = 0.25
    company_weight: float = 0.15

    # Risk tolerances
    allow_stretch_applications: bool = True
    min_experience_match_threshold: float = 0.7
    allow_salary_below_expectations: bool = False

    def __post_init__(self):
        """Validate configuration parameters."""
        if not 0 <= self.min_quality_score <= 100:
            raise ValueError("min_quality_score must be between 0 and 100")

        if not 0 <= self.min_match_score <= 100:
            raise ValueError("min_match_score must be between 0 and 100")

        # Ensure weights sum to approximately 1.0
        total_weight = (self.salary_weight + self.location_weight +
                       self.experience_weight + self.skills_weight + self.company_weight)

        if abs(total_weight - 1.0) > 0.1:
            raise ValueError(f"Weights should sum to 1.0, got {total_weight}")


class EligibilityEngine:
    """Determines job application eligibility based on multiple criteria."""

    def __init__(
        self,
        config: EligibilityConfig,
        repository: ApplicationRepository,
        job_matching_service: JobMatchingService,
        quality_service: JobQualityService,
        competition_service: CompetitionAnalysisService
    ):
        self.config = config
        self.repository = repository
        self.matching_service = job_matching_service
        self.quality_service = quality_service
        self.competition_service = competition_service
        self.logger = logging.getLogger(__name__)

    async def evaluate_eligibility(
        self,
        job: JobModel,
        user_profile: UserProfileModel
    ) -> EligibilityResult:
        """Comprehensive eligibility evaluation."""

        self.logger.info(f"Evaluating eligibility for job {job.id} ({job.title}) and user {user_profile.id}")

        reasons = []
        blocking_factors = []
        recommendations = []

        try:
            # 1. Basic requirements check
            basic_eligible, basic_reasons, basic_blocks = await self._check_basic_requirements(job, user_profile)
            reasons.extend(basic_reasons)
            blocking_factors.extend(basic_blocks)

            if not basic_eligible:
                return EligibilityResult(
                    eligible=False,
                    confidence_score=10,
                    reasons=reasons,
                    blocking_factors=blocking_factors,
                    recommendations=["Review basic requirements before applying"],
                    estimated_success_probability=0.0
                )

            # 2. Quality score analysis
            quality_score = await self._get_quality_score(job)
            if quality_score < self.config.min_quality_score:
                blocking_factors.append(f"Job quality score {quality_score} below threshold {self.config.min_quality_score}")
            else:
                reasons.append(f"Good job quality score: {quality_score}")

            # 3. Job matching analysis
            match_score = await self._get_match_score(job, user_profile)
            if match_score < self.config.min_match_score:
                blocking_factors.append(f"Job match score {match_score} below threshold {self.config.min_match_score}")
            else:
                reasons.append(f"Good job match score: {match_score}")

            # 4. Competition analysis
            competition_score = await self._get_competition_score(job)
            if competition_score > self.config.max_competition_score:
                blocking_factors.append(f"Competition level too high: {competition_score}")
            else:
                reasons.append(f"Manageable competition level: {competition_score}")

            # 5. User preferences alignment
            preference_match, pref_reasons = await self._check_user_preferences(job, user_profile)
            reasons.extend(pref_reasons)

            # 6. Application history check
            history_valid, history_reasons = await self._check_application_history(job, user_profile)
            if not history_valid:
                blocking_factors.extend(history_reasons)
            else:
                reasons.extend(history_reasons)

            # 7. Experience level compatibility
            experience_match, exp_reasons = await self._check_experience_compatibility(job, user_profile)
            reasons.extend(exp_reasons)

            # Calculate overall eligibility
            eligible = len(blocking_factors) == 0

            # Calculate confidence score
            confidence_score = await self._calculate_confidence_score(
                quality_score, match_score, competition_score, preference_match, experience_match
            )

            # Estimate success probability
            success_probability = await self._estimate_success_probability(
                quality_score, match_score, competition_score, user_profile.experience_years
            )

            # Generate recommendations
            recommendations = await self._generate_recommendations(
                job, user_profile, quality_score, match_score, competition_score
            )

            self.logger.info(f"Eligibility evaluation complete: eligible={eligible}, confidence={confidence_score}")

            return EligibilityResult(
                eligible=eligible,
                confidence_score=confidence_score,
                reasons=reasons,
                blocking_factors=blocking_factors,
                recommendations=recommendations,
                estimated_success_probability=success_probability,
                quality_score=quality_score,
                match_score=match_score,
                competition_score=competition_score
            )

        except Exception as e:
            self.logger.error(f"Error during eligibility evaluation: {e}")
            return EligibilityResult(
                eligible=False,
                confidence_score=0,
                reasons=[],
                blocking_factors=[f"Evaluation error: {str(e)}"],
                recommendations=["Manual review required"],
                estimated_success_probability=0.0
            )

    async def get_application_recommendation(
        self,
        job: JobModel,
        user_profile: UserProfileModel
    ) -> ApplicationRecommendation:
        """Generate strategic application recommendation."""

        eligibility = await self.evaluate_eligibility(job, user_profile)

        if not eligibility.eligible:
            return ApplicationRecommendation(
                should_apply=False,
                priority_level="low",
                recommended_timing="later",
                application_strategy="Address blocking factors first",
                content_suggestions=[],
                risk_factors=eligibility.blocking_factors,
                success_indicators=[]
            )

        # Determine priority level
        if eligibility.confidence_score >= 80:
            priority = "high"
        elif eligibility.confidence_score >= 60:
            priority = "medium"
        else:
            priority = "low"

        # Determine timing
        if eligibility.estimated_success_probability > 0.7:
            timing = "immediate"
        elif eligibility.estimated_success_probability > 0.5:
            timing = "soon"
        else:
            timing = "later"

        # Generate application strategy
        strategy = await self._generate_application_strategy(job, user_profile, eligibility)

        # Content suggestions
        content_suggestions = await self._generate_content_suggestions(job, user_profile, eligibility)

        # Risk factors
        risk_factors = await self._identify_risk_factors(job, user_profile, eligibility)

        # Success indicators
        success_indicators = await self._identify_success_indicators(job, user_profile, eligibility)

        return ApplicationRecommendation(
            should_apply=True,
            priority_level=priority,
            recommended_timing=timing,
            application_strategy=strategy,
            content_suggestions=content_suggestions,
            risk_factors=risk_factors,
            success_indicators=success_indicators
        )

    async def _check_basic_requirements(
        self,
        job: JobModel,
        user_profile: UserProfileModel
    ) -> tuple[bool, List[str], List[str]]:
        """Check basic job requirements."""

        reasons = []
        blocking_factors = []

        # Check if we have minimum required information
        if not job.title or not job.company:
            blocking_factors.append("Job missing essential information (title/company)")
            return False, reasons, blocking_factors

        if not user_profile.skills or not user_profile.experience_years:
            blocking_factors.append("User profile missing essential information")
            return False, reasons, blocking_factors

        # Check if job URL is accessible
        if not job.url or "linkedin.com" not in job.url:
            blocking_factors.append("Invalid or missing job URL")
            return False, reasons, blocking_factors

        reasons.append("Basic requirements satisfied")
        return True, reasons, blocking_factors

    async def _get_quality_score(self, job: JobModel) -> int:
        """Get job quality score from analysis service."""
        try:
            quality_analysis = await self.quality_service.analyze_job_quality(job)
            return quality_analysis.get("quality_score", 50)
        except Exception as e:
            self.logger.warning(f"Could not get quality score for job {job.id}: {e}")
            return 50  # Default score

    async def _get_match_score(self, job: JobModel, user_profile: UserProfileModel) -> int:
        """Get job match score from matching service."""
        try:
            match_result = await self.matching_service.match_job_to_profile(job, user_profile)
            return match_result.get("match_score", 50)
        except Exception as e:
            self.logger.warning(f"Could not get match score for job {job.id}: {e}")
            return 50  # Default score

    async def _get_competition_score(self, job: JobModel) -> int:
        """Get competition score from competition service."""
        try:
            competition_analysis = await self.competition_service.analyze_competition(job)
            return competition_analysis.get("competition_score", 50)
        except Exception as e:
            self.logger.warning(f"Could not get competition score for job {job.id}: {e}")
            return 50  # Default score

    async def _check_user_preferences(
        self,
        job: JobModel,
        user_profile: UserProfileModel
    ) -> tuple[float, List[str]]:
        """Check alignment with user preferences."""

        reasons = []
        total_score = 0.0
        total_weight = 0.0

        # Salary alignment
        if user_profile.salary_expectations and job.salary_min and job.salary_max:
            user_min = user_profile.salary_expectations.get("min", 0)
            user_max = user_profile.salary_expectations.get("max", float('inf'))

            if job.salary_max >= user_min and job.salary_min <= user_max:
                salary_score = 1.0
                reasons.append(f"Salary range aligns with expectations")
            elif job.salary_max < user_min:
                if self.config.allow_salary_below_expectations:
                    salary_score = 0.3
                    reasons.append("Salary below expectations but allowed")
                else:
                    salary_score = 0.0
                    reasons.append("Salary below minimum expectations")
            else:
                salary_score = 0.8
                reasons.append("Partial salary alignment")

            total_score += salary_score * self.config.salary_weight
            total_weight += self.config.salary_weight

        # Location alignment
        if user_profile.preferred_locations and job.location:
            location_match = any(
                pref_location.lower() in job.location.lower()
                for pref_location in user_profile.preferred_locations
            )

            remote_preference = user_profile.remote_preference
            is_remote = job.is_remote and "remote" in job.is_remote.lower()

            if location_match or (remote_preference == "remote" and is_remote):
                location_score = 1.0
                reasons.append("Location matches preferences")
            elif remote_preference in ["hybrid", "remote"] and job.is_remote:
                location_score = 0.8
                reasons.append("Partial location match")
            else:
                location_score = 0.4
                reasons.append("Location doesn't match preferences")

            total_score += location_score * self.config.location_weight
            total_weight += self.config.location_weight

        # Employment type alignment
        if user_profile.work_schedule_preference and job.employment_type:
            if user_profile.work_schedule_preference.lower() in job.employment_type.lower():
                reasons.append("Employment type matches preference")
            else:
                reasons.append("Employment type differs from preference")

        # Company size preference
        if user_profile.company_size_preference and job.company_size:
            if user_profile.company_size_preference.lower() in job.company_size.lower():
                reasons.append("Company size matches preference")

        preference_match = total_score / total_weight if total_weight > 0 else 0.5
        return preference_match, reasons

    async def _check_application_history(
        self,
        job: JobModel,
        user_profile: UserProfileModel
    ) -> tuple[bool, List[str]]:
        """Check application history for duplicates and limits."""

        reasons = []

        # Check for duplicate applications
        existing_app = self.repository.get_application_by_job_and_user(job.id, user_profile.id)
        if existing_app:
            return False, ["Already applied to this job"]

        # Check company application limits
        company_applications = []
        all_user_apps = self.repository.get_user_applications(user_profile.id)

        for app in all_user_apps:
            if app.job.company == job.company:
                company_applications.append(app)

        if len(company_applications) >= self.config.max_applications_per_company:
            return False, [f"Maximum applications to {job.company} reached ({self.config.max_applications_per_company})"]

        # Check timing between applications to same company
        if company_applications:
            latest_app = max(company_applications, key=lambda x: x.applied_at or x.created_at)
            time_since_last = datetime.now(timezone.utc) - (latest_app.applied_at or latest_app.created_at)

            if time_since_last.days < self.config.min_days_between_applications:
                return False, [f"Too soon to apply to {job.company} again (wait {self.config.min_days_between_applications - time_since_last.days} more days)"]

        reasons.append("Application history check passed")
        return True, reasons

    async def _check_experience_compatibility(
        self,
        job: JobModel,
        user_profile: UserProfileModel
    ) -> tuple[float, List[str]]:
        """Check experience level compatibility."""

        reasons = []

        if not job.experience_level or not user_profile.experience_years:
            return 0.5, ["Experience information incomplete"]

        experience_level = job.experience_level.lower()
        user_years = user_profile.experience_years

        # Define experience level mappings
        level_requirements = {
            "entry": (0, 2),
            "junior": (0, 3),
            "mid": (2, 7),
            "senior": (5, 15),
            "lead": (7, 20),
            "principal": (10, 25),
            "staff": (8, 20)
        }

        match_score = 0.5  # Default

        for level, (min_years, max_years) in level_requirements.items():
            if level in experience_level:
                if min_years <= user_years <= max_years:
                    match_score = 1.0
                    reasons.append(f"Experience ({user_years} years) perfectly matches {level} level")
                elif user_years < min_years:
                    if self.config.allow_stretch_applications:
                        gap = min_years - user_years
                        if gap <= 2:
                            match_score = 0.7
                            reasons.append(f"Slightly under-experienced but within stretch range")
                        else:
                            match_score = 0.3
                            reasons.append(f"Under-experienced by {gap} years")
                    else:
                        match_score = 0.2
                        reasons.append(f"Under-experienced for {level} level")
                elif user_years > max_years:
                    match_score = 0.8
                    reasons.append(f"Over-qualified for {level} level")
                break

        return match_score, reasons

    async def _calculate_confidence_score(
        self,
        quality_score: int,
        match_score: int,
        competition_score: int,
        preference_match: float,
        experience_match: float
    ) -> int:
        """Calculate overall confidence score."""

        # Normalize scores to 0-1 range
        quality_norm = quality_score / 100
        match_norm = match_score / 100
        competition_norm = 1 - (competition_score / 100)  # Lower competition is better

        # Weighted average
        confidence = (
            quality_norm * 0.25 +
            match_norm * 0.30 +
            competition_norm * 0.20 +
            preference_match * 0.15 +
            experience_match * 0.10
        )

        return int(confidence * 100)

    async def _estimate_success_probability(
        self,
        quality_score: int,
        match_score: int,
        competition_score: int,
        experience_years: int
    ) -> float:
        """Estimate probability of application success."""

        # Base probability based on scores
        base_prob = (quality_score + match_score) / 200

        # Adjust for competition
        competition_factor = 1 - (competition_score / 150)  # High competition reduces probability

        # Experience factor
        experience_factor = min(1.0, experience_years / 10)  # More experience helps

        # Combine factors
        probability = base_prob * competition_factor * (0.5 + 0.5 * experience_factor)

        return max(0.0, min(1.0, probability))

    async def _generate_recommendations(
        self,
        job: JobModel,
        user_profile: UserProfileModel,
        quality_score: int,
        match_score: int,
        competition_score: int
    ) -> List[str]:
        """Generate actionable recommendations."""

        recommendations = []

        if quality_score < 80:
            recommendations.append("Research the company thoroughly to understand if this opportunity aligns with your career goals")

        if match_score < 70:
            recommendations.append("Identify ways to strengthen your application by highlighting transferable skills")

        if competition_score > 70:
            recommendations.append("Apply early and ensure your application stands out with specific examples")

        if user_profile.experience_years < 3:
            recommendations.append("Focus on highlighting your learning agility and relevant projects")

        recommendations.append("Customize your cover letter to address specific job requirements")
        recommendations.append("Research the hiring manager and company culture")

        return recommendations

    async def _generate_application_strategy(
        self,
        job: JobModel,
        user_profile: UserProfileModel,
        eligibility: EligibilityResult
    ) -> str:
        """Generate application strategy."""

        if eligibility.match_score and eligibility.match_score > 80:
            return "Direct application with emphasis on skill alignment"
        elif eligibility.competition_score and eligibility.competition_score > 70:
            return "Differentiated application focusing on unique value proposition"
        elif eligibility.quality_score and eligibility.quality_score < 70:
            return "Cautious application with thorough company research"
        else:
            return "Standard application with personalized cover letter"

    async def _generate_content_suggestions(
        self,
        job: JobModel,
        user_profile: UserProfileModel,
        eligibility: EligibilityResult
    ) -> List[str]:
        """Generate content suggestions for application."""

        suggestions = []

        if user_profile.skills:
            matching_skills = []
            job_desc_lower = job.description.lower() if job.description else ""

            for skill in user_profile.skills[:5]:
                if skill.lower() in job_desc_lower:
                    matching_skills.append(skill)

            if matching_skills:
                suggestions.append(f"Highlight these matching skills: {', '.join(matching_skills)}")

        if job.company:
            suggestions.append(f"Research {job.company}'s recent news and company culture")

        if eligibility.estimated_success_probability < 0.6:
            suggestions.append("Include specific examples demonstrating your impact in previous roles")

        return suggestions

    async def _identify_risk_factors(
        self,
        job: JobModel,
        user_profile: UserProfileModel,
        eligibility: EligibilityResult
    ) -> List[str]:
        """Identify potential risk factors."""

        risks = []

        if eligibility.competition_score and eligibility.competition_score > 80:
            risks.append("High competition for this role")

        if eligibility.match_score and eligibility.match_score < 60:
            risks.append("Skills may not fully align with requirements")

        if job.applicant_count and job.applicant_count > 100:
            risks.append("Large number of applicants")

        return risks

    async def _identify_success_indicators(
        self,
        job: JobModel,
        user_profile: UserProfileModel,
        eligibility: EligibilityResult
    ) -> List[str]:
        """Identify positive success indicators."""

        indicators = []

        if eligibility.match_score and eligibility.match_score > 80:
            indicators.append("Strong skills alignment")

        if eligibility.quality_score and eligibility.quality_score > 80:
            indicators.append("High-quality job opportunity")

        if job.company and user_profile.industry_preferences:
            for industry in user_profile.industry_preferences:
                if industry.lower() in (job.industry or "").lower():
                    indicators.append("Industry preference match")
                    break

        return indicators

    async def batch_evaluate_eligibility(
        self,
        jobs: List[JobModel],
        user_profile: UserProfileModel
    ) -> List[tuple[JobModel, EligibilityResult]]:
        """Evaluate eligibility for multiple jobs efficiently."""

        results = []

        for job in jobs:
            try:
                eligibility = await self.evaluate_eligibility(job, user_profile)
                results.append((job, eligibility))
            except Exception as e:
                self.logger.error(f"Failed to evaluate eligibility for job {job.id}: {e}")
                # Add failed result
                failed_result = EligibilityResult(
                    eligible=False,
                    confidence_score=0,
                    reasons=[],
                    blocking_factors=[f"Evaluation failed: {str(e)}"],
                    recommendations=["Manual review required"],
                    estimated_success_probability=0.0
                )
                results.append((job, failed_result))

        return results

    async def get_eligible_jobs(
        self,
        jobs: List[JobModel],
        user_profile: UserProfileModel,
        min_confidence: int = 50
    ) -> List[tuple[JobModel, EligibilityResult]]:
        """Get only eligible jobs above confidence threshold."""

        all_results = await self.batch_evaluate_eligibility(jobs, user_profile)

        eligible_results = [
            (job, result) for job, result in all_results
            if result.eligible and result.confidence_score >= min_confidence
        ]

        # Sort by confidence score (highest first)
        eligible_results.sort(key=lambda x: x[1].confidence_score, reverse=True)

        return eligible_results