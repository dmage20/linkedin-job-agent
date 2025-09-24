"""Claude API client for job analysis services."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

from anthropic import Anthropic
from anthropic.types import Message

from ..database.models import JobModel


logger = logging.getLogger(__name__)


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


@dataclass
class ClaudeConfig:
    """Configuration for Claude API client."""

    model: str = "claude-3-haiku-20240307"
    max_tokens: int = 1000
    temperature: float = 0.3
    max_retries: int = 3
    timeout: int = 30
    cost_limit_per_hour: float = 10.0
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: int = 300  # seconds

    def __post_init__(self):
        """Validate configuration parameters."""
        if not 0.0 <= self.temperature <= 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")

        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")


class ClaudeClient:
    """Claude API client with cost management and circuit breaker pattern."""

    def __init__(self, api_key: str, config: Optional[ClaudeConfig] = None):
        """Initialize Claude client with API key and configuration.

        Args:
            api_key: Anthropic API key
            config: Claude configuration, defaults to ClaudeConfig()
        """
        self.api_key = api_key
        self.config = config or ClaudeConfig()
        self.client = Anthropic(api_key=api_key)

        # Cost and usage tracking
        self._request_count = 0
        self._total_cost = 0.0
        self._hour_start = datetime.now()

        # Circuit breaker state
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure: Optional[datetime] = None

        logger.info(f"Claude client initialized with model {self.config.model}")

    async def analyze_job_quality(self, job: JobModel) -> Dict[str, Any]:
        """Analyze job quality and provide scoring.

        Args:
            job: Job model to analyze

        Returns:
            Dictionary containing quality_score (0-100) and detailed analysis

        Raises:
            CircuitBreakerError: If circuit breaker is open
            ValueError: If cost limit exceeded
        """
        self._check_circuit_breaker()
        self._check_cost_limit()

        try:
            prompt = self._build_job_analysis_prompt(job)
            response = await self._make_api_call(prompt)
            result = self._parse_json_response(response)

            # Reset circuit breaker failures on success
            self._circuit_breaker_failures = 0

            return result

        except Exception as e:
            self._circuit_breaker_failures += 1
            self._circuit_breaker_last_failure = datetime.now()
            logger.error(f"Job quality analysis failed: {str(e)}")
            raise

    async def analyze_competition(self, job: JobModel) -> Dict[str, Any]:
        """Analyze job competition level based on applicant data.

        Args:
            job: Job model to analyze

        Returns:
            Dictionary containing competition analysis and recommendations
        """
        self._check_circuit_breaker()
        self._check_cost_limit()

        try:
            prompt = self._build_competition_prompt(job)
            response = await self._make_api_call(prompt)
            result = self._parse_json_response(response)

            self._circuit_breaker_failures = 0
            return result

        except Exception as e:
            self._circuit_breaker_failures += 1
            self._circuit_breaker_last_failure = datetime.now()
            logger.error(f"Competition analysis failed: {str(e)}")
            raise

    async def match_job_to_profile(self, job: JobModel, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Match job to user profile and provide compatibility score.

        Args:
            job: Job model to analyze
            user_profile: User profile with skills, experience, preferences

        Returns:
            Dictionary containing match_score (0-100) and detailed explanation
        """
        self._check_circuit_breaker()
        self._check_cost_limit()

        try:
            prompt = self._build_matching_prompt(job, user_profile)
            response = await self._make_api_call(prompt)
            result = self._parse_json_response(response)

            self._circuit_breaker_failures = 0
            return result

        except Exception as e:
            self._circuit_breaker_failures += 1
            self._circuit_breaker_last_failure = datetime.now()
            logger.error(f"Job matching failed: {str(e)}")
            raise

    async def batch_analyze_jobs(
        self,
        jobs: List[JobModel],
        analysis_type: str = "quality",
        batch_size: int = 5
    ) -> List[Dict[str, Any]]:
        """Analyze multiple jobs in batches with rate limiting.

        Args:
            jobs: List of job models to analyze
            analysis_type: Type of analysis ("quality", "competition", "all")
            batch_size: Number of jobs to process in parallel

        Returns:
            List of analysis results corresponding to input jobs
        """
        results = []

        for i in range(0, len(jobs), batch_size):
            batch = jobs[i:i + batch_size]
            batch_tasks = []

            for job in batch:
                if analysis_type == "quality":
                    task = self.analyze_job_quality(job)
                elif analysis_type == "competition":
                    task = self.analyze_competition(job)
                else:
                    # For "all" type, we'll do quality analysis as default
                    task = self.analyze_job_quality(job)

                batch_tasks.append(task)

            # Process batch concurrently
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Handle exceptions in results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch analysis error: {result}")
                    results.append({"error": str(result)})
                else:
                    results.append(result)

            # Add delay between batches to respect rate limits
            if i + batch_size < len(jobs):
                await asyncio.sleep(1)

        return results

    def _build_job_analysis_prompt(self, job: JobModel) -> str:
        """Build prompt for job quality analysis."""
        return f"""Analyze this job posting and provide a comprehensive quality assessment.

Job Details:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Employment Type: {job.employment_type}
Experience Level: {job.experience_level}

Description:
{job.description}

Please analyze the following aspects:
1. Job description clarity and completeness
2. Required skills specificity and reasonableness
3. Company information and reputation factors
4. Compensation transparency (if mentioned)
5. Growth and learning opportunities
6. Work-life balance indicators
7. Overall job attractiveness

Provide your response as a JSON object with the following structure:
{{
    "quality_score": <integer from 0-100>,
    "reasoning": "<detailed explanation of the score>",
    "strengths": ["<list of job posting strengths>"],
    "weaknesses": ["<list of areas for improvement>"],
    "recommendations": "<advice for job seekers considering this position>"
}}"""

    def _build_competition_prompt(self, job: JobModel) -> str:
        """Build prompt for competition analysis."""
        applicant_info = f"Applicant count: {job.applicant_count}" if job.applicant_count else "Applicant count: Not available"

        return f"""Analyze the competition level for this job posting and provide strategic insights.

Job Details:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Experience Level: {job.experience_level}
{applicant_info}

Job Description:
{job.description[:500]}...

Based on the job details and applicant count (if available), provide competition analysis and strategic recommendations.

Respond with a JSON object:
{{
    "competition_level": "<low/medium/high>",
    "analysis": "<detailed competition analysis>",
    "success_probability": <integer 0-100>,
    "strategic_advice": "<recommendations for applicants>",
    "application_timing": "<best time to apply>",
    "differentiation_tips": ["<ways to stand out from other applicants>"]
}}"""

    def _build_matching_prompt(self, job: JobModel, user_profile: Dict[str, Any]) -> str:
        """Build prompt for job-profile matching."""
        profile_str = json.dumps(user_profile, indent=2)

        return f"""Analyze how well this job matches the user's profile and career goals.

Job Details:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Employment Type: {job.employment_type}
Experience Level: {job.experience_level}

Job Description:
{job.description[:800]}...

User Profile:
{profile_str}

Provide a comprehensive matching analysis comparing job requirements with user qualifications.

Respond with a JSON object:
{{
    "match_score": <integer from 0-100>,
    "explanation": "<detailed match analysis>",
    "skill_alignment": {{
        "matched_skills": ["<skills that match>"],
        "missing_skills": ["<required skills user lacks>"],
        "transferable_skills": ["<user skills applicable to role>"]
    }},
    "experience_fit": "<analysis of experience level match>",
    "location_preference": "<location compatibility analysis>",
    "salary_expectation": "<salary alignment if available>",
    "growth_potential": "<career growth opportunities>",
    "recommendation": "<apply/consider/skip with reasoning>"
}}"""

    async def _make_api_call(self, prompt: str) -> Message:
        """Make API call to Claude with retry logic and cost tracking."""
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self.client.messages.create(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )

                # Track usage and cost
                self._request_count += 1
                estimated_cost = self._estimate_cost(prompt, response)
                self._add_cost(estimated_cost)

                return response

            except Exception as e:
                if attempt == self.config.max_retries:
                    raise

                logger.warning(f"API call attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    def _parse_json_response(self, response: Message) -> Dict[str, Any]:
        """Parse JSON response from Claude API."""
        try:
            content = response.content[0].text
            return json.loads(content)
        except (json.JSONDecodeError, IndexError, AttributeError) as e:
            logger.error(f"Failed to parse API response: {str(e)}")
            return {"error": "Failed to parse API response", "raw_content": str(response.content)}

    def _estimate_cost(self, prompt: str, response: Message) -> float:
        """Estimate cost based on token usage."""
        # Simplified cost estimation (actual costs depend on model and token count)
        # Claude-3 Haiku: ~$0.25 per 1K input tokens, ~$1.25 per 1K output tokens
        input_tokens = len(prompt.split()) * 1.3  # Rough estimation
        output_tokens = len(str(response.content)) * 1.3

        if "haiku" in self.config.model:
            input_cost = (input_tokens / 1000) * 0.00025
            output_cost = (output_tokens / 1000) * 0.00125
        elif "sonnet" in self.config.model:
            input_cost = (input_tokens / 1000) * 0.003
            output_cost = (output_tokens / 1000) * 0.015
        else:
            # Default to Haiku pricing
            input_cost = (input_tokens / 1000) * 0.00025
            output_cost = (output_tokens / 1000) * 0.00125

        return input_cost + output_cost

    def _add_cost(self, cost: float):
        """Add cost to total and check if hour limit exceeded."""
        self._total_cost += cost

        # Reset hourly cost tracking
        if datetime.now() - self._hour_start > timedelta(hours=1):
            self._total_cost = cost
            self._hour_start = datetime.now()

    def _check_cost_limit(self):
        """Check if cost limit has been exceeded."""
        if self._total_cost > self.config.cost_limit_per_hour:
            raise ValueError(
                f"Cost limit exceeded: ${self._total_cost:.4f} > ${self.config.cost_limit_per_hour}"
            )

    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open."""
        if self._circuit_breaker_failures < self.config.circuit_breaker_failure_threshold:
            return False

        if not self._circuit_breaker_last_failure:
            return False

        # Check if timeout has passed
        time_since_failure = datetime.now() - self._circuit_breaker_last_failure
        return time_since_failure.seconds < self.config.circuit_breaker_timeout

    def _check_circuit_breaker(self):
        """Check circuit breaker and raise exception if open."""
        if self._is_circuit_breaker_open():
            raise CircuitBreakerError(
                f"Circuit breaker is open after {self._circuit_breaker_failures} failures. "
                f"Wait {self.config.circuit_breaker_timeout} seconds before retrying."
            )

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        return {
            "request_count": self._request_count,
            "total_cost": self._total_cost,
            "cost_limit": self.config.cost_limit_per_hour,
            "circuit_breaker_failures": self._circuit_breaker_failures,
            "circuit_breaker_open": self._is_circuit_breaker_open(),
            "hour_start": self._hour_start.isoformat()
        }

    def reset_circuit_breaker(self):
        """Manually reset circuit breaker state."""
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure = None
        logger.info("Circuit breaker manually reset")

    async def generate_content(self, prompt: str, max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> str:
        """Generate content using Claude API.

        Args:
            prompt: The prompt to send to Claude
            max_tokens: Maximum tokens to generate (overrides config)
            temperature: Temperature for generation (overrides config)

        Returns:
            Generated content as string

        Raises:
            CircuitBreakerError: If circuit breaker is open
            ValueError: If cost limit exceeded
        """
        self._check_circuit_breaker()
        self._check_cost_limit()

        try:
            # Use provided values or fall back to config
            tokens = max_tokens or self.config.max_tokens
            temp = temperature if temperature is not None else self.config.temperature

            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=tokens,
                temperature=temp,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Track request
            self._request_count += 1
            self._total_cost += self._calculate_cost(response)

            # Reset circuit breaker on success
            self._circuit_breaker_failures = 0

            return response.content[0].text

        except Exception as e:
            self._circuit_breaker_failures += 1
            self._circuit_breaker_last_failure = datetime.now()
            logger.error(f"Content generation failed: {str(e)}")
            raise