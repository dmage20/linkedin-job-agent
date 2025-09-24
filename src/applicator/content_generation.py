"""Personalized content generation service using Claude API."""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..analyzer.claude_client import ClaudeClient, ClaudeConfig
from ..database.models import JobModel
from ..analyzer.models import UserProfileModel
from .models import ContentType, GeneratedContentModel
from .repository import ApplicationRepository


logger = logging.getLogger(__name__)


@dataclass
class GeneratedContent:
    """Container for generated content and metadata."""
    content_type: ContentType
    content_text: str
    quality_score: int
    generation_metadata: Dict[str, Any]
    user_approved: bool = False
    generation_cost: float = 0.0
    generation_time_seconds: float = 0.0


@dataclass
class ContentGenerationConfig:
    """Configuration for content generation service."""

    # Claude API settings
    claude_config: ClaudeConfig

    # Content quality thresholds
    min_quality_score: int = 70
    max_retry_attempts: int = 3

    # Content length limits
    cover_letter_max_words: int = 400
    cover_letter_min_words: int = 200
    linkedin_message_max_words: int = 150
    linkedin_message_min_words: int = 50

    # Template settings
    use_fallback_templates: bool = True
    personalization_depth: str = "high"  # low, medium, high

    def __post_init__(self):
        """Validate configuration parameters."""
        if not isinstance(self.claude_config, ClaudeConfig):
            raise ValueError("claude_config must be a ClaudeConfig instance")

        if not 0 <= self.min_quality_score <= 100:
            raise ValueError("min_quality_score must be between 0 and 100")

        if self.max_retry_attempts < 1:
            raise ValueError("max_retry_attempts must be at least 1")


class ContentGenerationService:
    """Service for generating personalized application content."""

    def __init__(self, config: ContentGenerationConfig, repository: ApplicationRepository, claude_client: ClaudeClient):
        self.config = config
        self.repository = repository
        self.claude = claude_client
        self.logger = logging.getLogger(__name__)

    async def _generate_with_claude(self, prompt: str, max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> tuple[str, float]:
        """Helper method to generate content with Claude and track costs."""
        # Get cost before request
        stats_before = await self.claude.get_stats()

        response = await self.claude.generate_content(
            prompt=prompt,
            max_tokens=max_tokens or self.config.claude_config.max_tokens,
            temperature=temperature if temperature is not None else self.config.claude_config.temperature
        )

        # Calculate generation cost
        stats_after = await self.claude.get_stats()
        generation_cost = stats_after["total_cost"] - stats_before["total_cost"]

        return response, generation_cost

    async def generate_cover_letter(
        self,
        job: JobModel,
        user_profile: UserProfileModel,
        application_id: Optional[int] = None,
        custom_instructions: Optional[str] = None
    ) -> GeneratedContent:
        """Generate personalized cover letter using Claude."""
        start_time = time.time()

        try:
            prompt = self._build_cover_letter_prompt(job, user_profile, custom_instructions)

            response, generation_cost = await self._generate_with_claude(prompt)

            content = self._parse_cover_letter_response(response)
            content.generation_cost = generation_cost

            # Validate content quality
            if content.quality_score < self.config.min_quality_score:
                self.logger.warning(f"Cover letter quality score {content.quality_score} below threshold {self.config.min_quality_score}")

                # Try to improve with retry
                if self.config.max_retry_attempts > 1:
                    return await self._retry_generation(
                        self.generate_cover_letter,
                        job, user_profile, application_id, custom_instructions,
                        "Cover letter quality too low"
                    )

            # Store generated content if application_id provided
            if application_id:
                await self._store_generated_content(
                    application_id, ContentType.COVER_LETTER, content
                )

            generation_time = time.time() - start_time
            content.generation_time_seconds = generation_time

            self.logger.info(f"Generated cover letter with quality score {content.quality_score} in {generation_time:.2f}s")
            return content

        except Exception as e:
            self.logger.error(f"Cover letter generation failed: {e}")

            if self.config.use_fallback_templates:
                return self._fallback_cover_letter(job, user_profile)
            else:
                raise

    async def generate_linkedin_message(
        self,
        job: JobModel,
        user_profile: UserProfileModel,
        application_id: Optional[int] = None,
        message_type: str = "application",  # "application", "connection", "follow_up"
        custom_instructions: Optional[str] = None
    ) -> GeneratedContent:
        """Generate personalized LinkedIn message using Claude."""
        start_time = time.time()

        try:
            prompt = self._build_linkedin_message_prompt(
                job, user_profile, message_type, custom_instructions
            )

            response, generation_cost = await self._generate_with_claude(
                prompt,
                max_tokens=min(800, self.config.claude_config.max_tokens)
            )

            content = self._parse_linkedin_message_response(response)
            content.generation_cost = generation_cost

            # Validate content quality and length
            word_count = len(content.content_text.split())
            if (word_count < self.config.linkedin_message_min_words or
                word_count > self.config.linkedin_message_max_words):

                self.logger.warning(f"LinkedIn message word count {word_count} outside acceptable range")

                if self.config.max_retry_attempts > 1:
                    return await self._retry_generation(
                        self.generate_linkedin_message,
                        job, user_profile, application_id, message_type, custom_instructions,
                        f"Word count {word_count} out of range"
                    )

            # Store generated content if application_id provided
            if application_id:
                await self._store_generated_content(
                    application_id, ContentType.LINKEDIN_MESSAGE, content
                )

            generation_time = time.time() - start_time
            content.generation_time_seconds = generation_time

            self.logger.info(f"Generated LinkedIn message with quality score {content.quality_score} in {generation_time:.2f}s")
            return content

        except Exception as e:
            self.logger.error(f"LinkedIn message generation failed: {e}")

            if self.config.use_fallback_templates:
                return self._fallback_linkedin_message(job, user_profile, message_type)
            else:
                raise

    async def generate_email_subject(
        self,
        job: JobModel,
        user_profile: UserProfileModel,
        application_id: Optional[int] = None,
        custom_instructions: Optional[str] = None
    ) -> GeneratedContent:
        """Generate personalized email subject line using Claude."""
        start_time = time.time()

        try:
            prompt = self._build_email_subject_prompt(job, user_profile, custom_instructions)

            response = await self.claude.generate_content(
                prompt=prompt,
                max_tokens=100,
                temperature=0.3  # Lower temperature for more focused subjects
            )

            content = self._parse_email_subject_response(response)

            # Store generated content if application_id provided
            if application_id:
                await self._store_generated_content(
                    application_id, ContentType.EMAIL_SUBJECT, content
                )

            generation_time = time.time() - start_time
            content.generation_time_seconds = generation_time

            self.logger.info(f"Generated email subject in {generation_time:.2f}s")
            return content

        except Exception as e:
            self.logger.error(f"Email subject generation failed: {e}")

            if self.config.use_fallback_templates:
                return self._fallback_email_subject(job, user_profile)
            else:
                raise

    async def generate_follow_up_message(
        self,
        job: JobModel,
        user_profile: UserProfileModel,
        application_id: Optional[int] = None,
        days_since_application: int = 7,
        custom_instructions: Optional[str] = None
    ) -> GeneratedContent:
        """Generate personalized follow-up message using Claude."""
        start_time = time.time()

        try:
            prompt = self._build_follow_up_prompt(
                job, user_profile, days_since_application, custom_instructions
            )

            response = await self.claude.generate_content(
                prompt=prompt,
                max_tokens=self.config.claude_config.max_tokens,
                temperature=self.config.claude_config.temperature
            )

            content = self._parse_follow_up_response(response)

            # Store generated content if application_id provided
            if application_id:
                await self._store_generated_content(
                    application_id, ContentType.FOLLOW_UP_MESSAGE, content
                )

            generation_time = time.time() - start_time
            content.generation_time_seconds = generation_time

            self.logger.info(f"Generated follow-up message in {generation_time:.2f}s")
            return content

        except Exception as e:
            self.logger.error(f"Follow-up message generation failed: {e}")

            if self.config.use_fallback_templates:
                return self._fallback_follow_up_message(job, user_profile, days_since_application)
            else:
                raise

    def _build_cover_letter_prompt(
        self,
        job: JobModel,
        user_profile: UserProfileModel,
        custom_instructions: Optional[str] = None
    ) -> str:
        """Build comprehensive prompt for cover letter generation."""

        # Analyze user skills match with job requirements
        skill_overlap = self._analyze_skill_overlap(job, user_profile)

        # Determine company culture tone
        company_tone = self._infer_company_tone(job)

        prompt = f"""Generate a professional, personalized cover letter for this job application.

JOB DETAILS:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Industry: {job.industry or 'Not specified'}
Employment Type: {job.employment_type or 'Not specified'}
Experience Level: {job.experience_level or 'Not specified'}
Company Size: {job.company_size or 'Not specified'}

Job Description (key excerpts):
{job.description[:1000]}{'...' if len(job.description) > 1000 else ''}

APPLICANT PROFILE:
Name: Professional (use placeholder - do not include actual name)
Experience: {user_profile.experience_years} years
Skills: {', '.join(user_profile.skills[:10]) if user_profile.skills else 'Not specified'}
Desired Roles: {', '.join(user_profile.desired_roles[:5]) if user_profile.desired_roles else 'Not specified'}
Education: {user_profile.education_level or 'Not specified'}
Certifications: {', '.join(user_profile.certifications[:5]) if user_profile.certifications else 'None listed'}

SKILL ANALYSIS:
Matching Skills: {skill_overlap['matching']}
Relevant Skills: {skill_overlap['relevant']}
Transferable Skills: {skill_overlap['transferable']}

COMPANY TONE: {company_tone}

PERSONALIZATION REQUIREMENTS:
1. Address specific job requirements mentioned in the description
2. Highlight {min(3, len(skill_overlap['matching']))} most relevant matching skills
3. Include specific examples of relevant experience (create realistic examples based on profile)
4. Match the {company_tone} tone while remaining professional
5. Show enthusiasm for the specific company and role
6. Address any experience level requirements
7. Keep to {self.config.cover_letter_min_words}-{self.config.cover_letter_max_words} words

CUSTOM INSTRUCTIONS:
{custom_instructions or 'None provided'}

RESPONSE FORMAT:
Respond with a JSON object containing:
{{
    "cover_letter": "<complete cover letter text>",
    "quality_score": <1-100 based on personalization and relevance>,
    "key_strengths_highlighted": ["<list of 3-5 key strengths emphasized>"],
    "personalization_elements": ["<specific personalizations made>"],
    "tone_analysis": "<description of tone used and why>",
    "word_count": <actual word count>
}}

Write the cover letter now:"""

        return prompt

    def _build_linkedin_message_prompt(
        self,
        job: JobModel,
        user_profile: UserProfileModel,
        message_type: str,
        custom_instructions: Optional[str] = None
    ) -> str:
        """Build prompt for LinkedIn message generation."""

        if message_type == "application":
            context = "applying for the position"
            action = "express interest and request consideration"
        elif message_type == "connection":
            context = "connecting regarding the position"
            action = "establish a professional connection"
        else:  # follow_up
            context = "following up on your application"
            action = "check on application status"

        prompt = f"""Generate a professional LinkedIn message for {context}.

JOB DETAILS:
Title: {job.title}
Company: {job.company}
Location: {job.location}

APPLICANT PROFILE:
Experience: {user_profile.experience_years} years
Key Skills: {', '.join(user_profile.skills[:5]) if user_profile.skills else 'Not specified'}
Background: {user_profile.education_level or 'Professional'}

MESSAGE REQUIREMENTS:
1. Professional but personable tone
2. Specific to the role and company
3. Highlight 1-2 most relevant qualifications
4. Clear call to action to {action}
5. Keep to {self.config.linkedin_message_min_words}-{self.config.linkedin_message_max_words} words
6. Include appropriate LinkedIn etiquette

CUSTOM INSTRUCTIONS:
{custom_instructions or 'None provided'}

RESPONSE FORMAT:
{{
    "message": "<complete LinkedIn message>",
    "quality_score": <1-100>,
    "tone": "<description of tone used>",
    "call_to_action": "<the specific call to action used>",
    "word_count": <actual word count>
}}

Generate the message:"""

        return prompt

    def _build_email_subject_prompt(
        self,
        job: JobModel,
        user_profile: UserProfileModel,
        custom_instructions: Optional[str] = None
    ) -> str:
        """Build prompt for email subject generation."""

        prompt = f"""Generate a compelling email subject line for a job application.

JOB: {job.title} at {job.company}
APPLICANT: {user_profile.experience_years} years experience in {user_profile.desired_roles[0] if user_profile.desired_roles else 'relevant field'}

REQUIREMENTS:
1. Professional and attention-grabbing
2. Include job title and/or company name
3. Highlight key qualification or unique value
4. 50-70 characters maximum
5. Avoid spam triggers

CUSTOM INSTRUCTIONS:
{custom_instructions or 'None provided'}

RESPONSE FORMAT:
{{
    "subject": "<email subject line>",
    "character_count": <actual character count>,
    "reasoning": "<why this subject is effective>"
}}

Generate the subject:"""

        return prompt

    def _build_follow_up_prompt(
        self,
        job: JobModel,
        user_profile: UserProfileModel,
        days_since_application: int,
        custom_instructions: Optional[str] = None
    ) -> str:
        """Build prompt for follow-up message generation."""

        prompt = f"""Generate a professional follow-up message for a job application.

JOB: {job.title} at {job.company}
TIMELINE: {days_since_application} days since application submitted
APPLICANT: {user_profile.experience_years} years experience

REQUIREMENTS:
1. Professional and polite tone
2. Reference the specific position and application date
3. Reiterate interest and key qualifications
4. Respectful inquiry about timeline
5. Keep to 150-300 words
6. Include offer to provide additional information

CUSTOM INSTRUCTIONS:
{custom_instructions or 'None provided'}

RESPONSE FORMAT:
{{
    "message": "<complete follow-up message>",
    "quality_score": <1-100>,
    "tone": "<professional/enthusiastic/patient>",
    "word_count": <actual word count>
}}

Generate the follow-up:"""

        return prompt

    def _parse_cover_letter_response(self, response: str) -> GeneratedContent:
        """Parse Claude's cover letter response."""
        try:
            data = json.loads(response)

            return GeneratedContent(
                content_type=ContentType.COVER_LETTER,
                content_text=data["cover_letter"],
                quality_score=int(data.get("quality_score", 75)),
                generation_metadata={
                    "key_strengths": data.get("key_strengths_highlighted", []),
                    "personalization_elements": data.get("personalization_elements", []),
                    "tone_analysis": data.get("tone_analysis", ""),
                    "word_count": data.get("word_count", 0),
                    "model_used": self.config.claude_config.model
                }
            )

        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Failed to parse cover letter response: {e}")
            # Fallback parsing
            return GeneratedContent(
                content_type=ContentType.COVER_LETTER,
                content_text=response,  # Use raw response
                quality_score=60,  # Lower score for unparsed response
                generation_metadata={"parsing_error": str(e)}
            )

    def _parse_linkedin_message_response(self, response: str) -> GeneratedContent:
        """Parse Claude's LinkedIn message response."""
        try:
            data = json.loads(response)

            return GeneratedContent(
                content_type=ContentType.LINKEDIN_MESSAGE,
                content_text=data["message"],
                quality_score=int(data.get("quality_score", 75)),
                generation_metadata={
                    "tone": data.get("tone", ""),
                    "call_to_action": data.get("call_to_action", ""),
                    "word_count": data.get("word_count", 0),
                    "model_used": self.config.claude_config.model
                }
            )

        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Failed to parse LinkedIn message response: {e}")
            return GeneratedContent(
                content_type=ContentType.LINKEDIN_MESSAGE,
                content_text=response,
                quality_score=60,
                generation_metadata={"parsing_error": str(e)}
            )

    def _parse_email_subject_response(self, response: str) -> GeneratedContent:
        """Parse Claude's email subject response."""
        try:
            data = json.loads(response)

            return GeneratedContent(
                content_type=ContentType.EMAIL_SUBJECT,
                content_text=data["subject"],
                quality_score=85,  # Email subjects are generally good quality
                generation_metadata={
                    "character_count": data.get("character_count", 0),
                    "reasoning": data.get("reasoning", ""),
                    "model_used": self.config.claude_config.model
                }
            )

        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Failed to parse email subject response: {e}")
            return GeneratedContent(
                content_type=ContentType.EMAIL_SUBJECT,
                content_text=response,
                quality_score=70,
                generation_metadata={"parsing_error": str(e)}
            )

    def _parse_follow_up_response(self, response: str) -> GeneratedContent:
        """Parse Claude's follow-up message response."""
        try:
            data = json.loads(response)

            return GeneratedContent(
                content_type=ContentType.FOLLOW_UP_MESSAGE,
                content_text=data["message"],
                quality_score=int(data.get("quality_score", 75)),
                generation_metadata={
                    "tone": data.get("tone", ""),
                    "word_count": data.get("word_count", 0),
                    "model_used": self.config.claude_config.model
                }
            )

        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Failed to parse follow-up response: {e}")
            return GeneratedContent(
                content_type=ContentType.FOLLOW_UP_MESSAGE,
                content_text=response,
                quality_score=60,
                generation_metadata={"parsing_error": str(e)}
            )

    def _analyze_skill_overlap(self, job: JobModel, user_profile: UserProfileModel) -> Dict[str, List[str]]:
        """Analyze skill overlap between job requirements and user profile."""
        if not user_profile.skills:
            return {"matching": [], "relevant": [], "transferable": []}

        user_skills = [skill.lower() for skill in user_profile.skills]
        job_text = (job.description + " " + (job.title or "")).lower()

        matching = []
        relevant = []
        transferable = []

        for skill in user_skills:
            if skill in job_text:
                matching.append(skill)
            elif any(related in job_text for related in self._get_related_skills(skill)):
                relevant.append(skill)
            else:
                transferable.append(skill)

        return {
            "matching": matching[:5],
            "relevant": relevant[:5],
            "transferable": transferable[:3]
        }

    def _get_related_skills(self, skill: str) -> List[str]:
        """Get related skills for a given skill."""
        skill_mapping = {
            "python": ["programming", "development", "coding", "software"],
            "javascript": ["js", "web", "frontend", "development"],
            "react": ["frontend", "ui", "javascript", "web"],
            "sql": ["database", "data", "query", "mysql", "postgresql"],
            "aws": ["cloud", "amazon", "infrastructure", "devops"],
            "docker": ["containers", "deployment", "devops"],
            "kubernetes": ["k8s", "orchestration", "containers", "devops"],
            "machine learning": ["ml", "ai", "data science", "analytics"],
            "project management": ["pm", "scrum", "agile", "coordination"],
            "communication": ["collaboration", "teamwork", "interpersonal"],
        }

        return skill_mapping.get(skill.lower(), [])

    def _infer_company_tone(self, job: JobModel) -> str:
        """Infer appropriate tone based on company and job description."""
        description = (job.description or "").lower()
        company = (job.company or "").lower()

        if any(word in description for word in ["startup", "fast-paced", "innovative", "disrupt"]):
            return "dynamic and innovative"
        elif any(word in description for word in ["enterprise", "corporate", "established", "fortune"]):
            return "professional and formal"
        elif any(word in description for word in ["creative", "design", "marketing", "brand"]):
            return "creative and engaging"
        elif any(word in description for word in ["healthcare", "medical", "patient", "clinical"]):
            return "professional and caring"
        elif any(word in description for word in ["finance", "banking", "investment", "financial"]):
            return "professional and analytical"
        else:
            return "professional and enthusiastic"

    async def _retry_generation(self, generation_method, *args, reason: str = "") -> GeneratedContent:
        """Retry content generation with improved prompt."""
        for attempt in range(self.config.max_retry_attempts - 1):
            self.logger.info(f"Retrying content generation (attempt {attempt + 2}): {reason}")
            try:
                await asyncio.sleep(1)  # Brief delay between retries
                result = await generation_method(*args)

                # Check if retry improved quality
                if result.quality_score >= self.config.min_quality_score:
                    return result

            except Exception as e:
                self.logger.warning(f"Retry attempt {attempt + 2} failed: {e}")

        # If all retries failed, return the last attempt or fallback
        self.logger.warning(f"All retry attempts failed for content generation")
        return await generation_method(*args)

    async def _store_generated_content(
        self,
        application_id: int,
        content_type: ContentType,
        content: GeneratedContent
    ) -> GeneratedContentModel:
        """Store generated content in database."""
        try:
            stored_content = self.repository.create_generated_content(
                application_id=application_id,
                content_type=content_type,
                content_text=content.content_text,
                generation_prompt="Generated via ContentGenerationService",
                claude_model_used=self.config.claude_config.model,
                generation_cost=content.generation_cost,
                generation_time_seconds=content.generation_time_seconds,
                quality_score=content.quality_score,
                user_approved=content.user_approved
            )

            self.logger.info(f"Stored {content_type.value} content for application {application_id}")
            return stored_content

        except Exception as e:
            self.logger.error(f"Failed to store generated content: {e}")
            raise

    # Fallback template methods
    def _fallback_cover_letter(self, job: JobModel, user_profile: UserProfileModel) -> GeneratedContent:
        """Generate fallback cover letter using templates."""
        content = f"""Dear Hiring Manager,

I am writing to express my strong interest in the {job.title} position at {job.company}. With {user_profile.experience_years} years of experience in {user_profile.desired_roles[0] if user_profile.desired_roles else 'the field'}, I am confident that my skills and background make me an excellent candidate for this role.

My expertise in {', '.join(user_profile.skills[:3]) if user_profile.skills else 'relevant technologies'} aligns well with the requirements outlined in your job posting. Throughout my career, I have consistently delivered high-quality results and am passionate about contributing to innovative teams like yours at {job.company}.

I would welcome the opportunity to discuss how my background and enthusiasm can contribute to your team's success. Thank you for considering my application.

Best regards,
[Your Name]"""

        return GeneratedContent(
            content_type=ContentType.COVER_LETTER,
            content_text=content,
            quality_score=65,  # Lower score for template
            generation_metadata={"fallback": True, "template_used": "basic_cover_letter"}
        )

    def _fallback_linkedin_message(self, job: JobModel, user_profile: UserProfileModel, message_type: str) -> GeneratedContent:
        """Generate fallback LinkedIn message using templates."""
        if message_type == "application":
            content = f"Hi, I noticed the {job.title} position at {job.company} and believe my {user_profile.experience_years} years of experience would be a great fit. I'd love to connect and discuss this opportunity further."
        elif message_type == "connection":
            content = f"Hi, I'm interested in the {job.title} role at {job.company}. With my background in {user_profile.desired_roles[0] if user_profile.desired_roles else 'the field'}, I'd appreciate connecting to learn more about the opportunity."
        else:  # follow_up
            content = f"Hi, I wanted to follow up on my application for the {job.title} position. I remain very interested and would appreciate any updates on the timeline. Thank you!"

        return GeneratedContent(
            content_type=ContentType.LINKEDIN_MESSAGE,
            content_text=content,
            quality_score=60,
            generation_metadata={"fallback": True, "template_used": f"basic_{message_type}"}
        )

    def _fallback_email_subject(self, job: JobModel, user_profile: UserProfileModel) -> GeneratedContent:
        """Generate fallback email subject using templates."""
        content = f"Application for {job.title} - {user_profile.experience_years} Years Experience"

        return GeneratedContent(
            content_type=ContentType.EMAIL_SUBJECT,
            content_text=content,
            quality_score=70,
            generation_metadata={"fallback": True, "template_used": "basic_subject"}
        )

    def _fallback_follow_up_message(self, job: JobModel, user_profile: UserProfileModel, days_since: int) -> GeneratedContent:
        """Generate fallback follow-up message using templates."""
        content = f"""Dear Hiring Manager,

I hope this message finds you well. I wanted to follow up on my application for the {job.title} position that I submitted {days_since} days ago.

I remain very interested in this opportunity and believe my {user_profile.experience_years} years of experience would be valuable to your team at {job.company}. If you need any additional information or have questions about my background, I would be happy to provide it.

Thank you for your time and consideration. I look forward to hearing about the next steps in the process.

Best regards,
[Your Name]"""

        return GeneratedContent(
            content_type=ContentType.FOLLOW_UP_MESSAGE,
            content_text=content,
            quality_score=65,
            generation_metadata={"fallback": True, "template_used": "basic_follow_up"}
        )

    async def get_generation_statistics(self) -> Dict[str, Any]:
        """Get content generation statistics."""
        try:
            stats = self.repository.get_content_generation_stats()

            # Add service-specific metrics
            stats.update({
                "service_config": {
                    "min_quality_score": self.config.min_quality_score,
                    "max_retry_attempts": self.config.max_retry_attempts,
                    "use_fallback_templates": self.config.use_fallback_templates
                },
                "claude_model": self.config.claude_config.model
            })

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get generation statistics: {e}")
            return {"error": str(e)}