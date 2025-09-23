"""Search configuration classes for LinkedIn job scraping."""

import json
import yaml
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
from enum import Enum


# LinkedIn ToS compliance constants
LINKEDIN_MIN_REQUEST_DELAY = 2.0  # Minimum seconds between requests
LINKEDIN_MAX_JOBS_PER_SESSION = 50  # Maximum jobs per session
LINKEDIN_MAX_JOBS_PER_DAY = 200  # Maximum jobs per day
LINKEDIN_MAX_SESSION_DURATION = 30  # Maximum session duration in minutes


class ValidationError(Exception):
    """Exception raised for configuration validation errors."""
    pass


class ExperienceLevel(Enum):
    """Valid experience levels for job search."""
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    EXECUTIVE = "executive"


class JobType(Enum):
    """Valid job types for job search."""
    FULL_TIME = "full-time"
    PART_TIME = "part-time"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"


class RemoteOption(Enum):
    """Valid remote work options."""
    REMOTE = "remote"
    HYBRID = "hybrid"
    ON_SITE = "on-site"


class OutputFormat(Enum):
    """Valid output formats for scraped data."""
    JSON = "json"
    CSV = "csv"
    YAML = "yaml"


class DatePosted(Enum):
    """Valid date posted filters."""
    ANY = "any"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class CompanySize(Enum):
    """Valid company size filters."""
    STARTUP = "startup"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"


@dataclass
class SearchParameters:
    """Configuration for job search parameters."""

    keywords: List[str]
    location: str
    experience_level: Optional[Union[str, ExperienceLevel]] = None
    job_type: Optional[Union[str, JobType]] = None
    remote: Optional[Union[str, RemoteOption]] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    company_size: Optional[Union[str, CompanySize]] = None
    date_posted: Optional[Union[str, DatePosted]] = None

    def __post_init__(self):
        """Validate search parameters after initialization."""
        self._validate()

    def _validate(self):
        """Validate search parameters."""
        # Validate keywords
        if not self.keywords or len(self.keywords) == 0:
            raise ValidationError("Keywords cannot be empty")

        # Validate location
        if not self.location or self.location.strip() == "":
            raise ValidationError("Location cannot be empty")

        # Validate experience level
        if self.experience_level is not None:
            valid_values = [e.value for e in ExperienceLevel]
            if (isinstance(self.experience_level, str) and
                self.experience_level not in valid_values):
                raise ValidationError(f"Invalid experience_level: {self.experience_level}. "
                                    f"Must be one of: {valid_values}")

        # Validate job type
        if self.job_type is not None:
            valid_values = [e.value for e in JobType]
            if (isinstance(self.job_type, str) and
                self.job_type not in valid_values):
                raise ValidationError(f"Invalid job_type: {self.job_type}. "
                                    f"Must be one of: {valid_values}")

        # Validate remote option
        if self.remote is not None:
            valid_values = [e.value for e in RemoteOption]
            if (isinstance(self.remote, str) and
                self.remote not in valid_values):
                raise ValidationError(f"Invalid remote: {self.remote}. "
                                    f"Must be one of: {valid_values}")

        # Validate company size
        if self.company_size is not None:
            valid_values = [e.value for e in CompanySize]
            if (isinstance(self.company_size, str) and
                self.company_size not in valid_values):
                raise ValidationError(f"Invalid company_size: {self.company_size}. "
                                    f"Must be one of: {valid_values}")

        # Validate date posted
        if self.date_posted is not None:
            valid_values = [e.value for e in DatePosted]
            if (isinstance(self.date_posted, str) and
                self.date_posted not in valid_values):
                raise ValidationError(f"Invalid date_posted: {self.date_posted}. "
                                    f"Must be one of: {valid_values}")

        # Validate salary range
        if (self.salary_min is not None and self.salary_max is not None and
            self.salary_min > self.salary_max):
            raise ValidationError("salary_min cannot be greater than salary_max")


@dataclass
class ScrapingLimits:
    """Configuration for scraping limits and LinkedIn ToS compliance."""

    jobs_per_session: int = LINKEDIN_MAX_JOBS_PER_SESSION
    jobs_per_day: int = LINKEDIN_MAX_JOBS_PER_DAY
    session_duration_minutes: int = LINKEDIN_MAX_SESSION_DURATION
    request_delay_seconds: float = LINKEDIN_MIN_REQUEST_DELAY
    max_retries: int = 3
    retry_delay_seconds: float = 5.0

    def __post_init__(self):
        """Validate scraping limits after initialization."""
        self._validate()

    def _validate(self):
        """Validate scraping limits for LinkedIn ToS compliance."""
        if not (1 <= self.jobs_per_session <= 100):
            raise ValidationError("jobs_per_session must be between 1 and 100")

        if not (1 <= self.jobs_per_day <= 500):
            raise ValidationError("jobs_per_day must be between 1 and 500")

        if not (1 <= self.session_duration_minutes <= 60):
            raise ValidationError("session_duration_minutes must be between 1 and 60")

        if self.request_delay_seconds < LINKEDIN_MIN_REQUEST_DELAY:
            raise ValidationError(f"request_delay_seconds must be at least {LINKEDIN_MIN_REQUEST_DELAY} "
                                "for LinkedIn ToS compliance")

        if self.max_retries < 0:
            raise ValidationError("max_retries must be non-negative")

        if self.retry_delay_seconds < 0:
            raise ValidationError("retry_delay_seconds must be non-negative")


@dataclass
class SearchConfig:
    """Complete search configuration including parameters and limits."""

    search_parameters: SearchParameters
    scraping_limits: ScrapingLimits
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ])
    enable_stealth_mode: bool = True
    output_format: Union[str, OutputFormat] = "json"

    def __post_init__(self):
        """Validate search configuration after initialization."""
        self._validate()

    def _validate(self):
        """Validate search configuration."""
        if isinstance(self.output_format, str):
            valid_values = [e.value for e in OutputFormat]
            if self.output_format not in valid_values:
                raise ValidationError(f"Invalid output_format: {self.output_format}. "
                                    f"Must be one of: {valid_values}")

        if not self.user_agents or len(self.user_agents) == 0:
            raise ValidationError("At least one user agent must be provided")


class ConfigManager:
    """Manager for loading, saving, and validating search configurations."""

    def load_from_file(self, file_path: str) -> SearchConfig:
        """Load configuration from YAML or JSON file."""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        with open(file_path, 'r') as f:
            if file_path.lower().endswith(('.yaml', '.yml')):
                data = yaml.safe_load(f)
            elif file_path.lower().endswith('.json'):
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported file format. Use .yaml, .yml, or .json")

        return self._dict_to_config(data)

    def save_to_file(self, config: SearchConfig, file_path: str) -> None:
        """Save configuration to YAML or JSON file."""
        path = Path(file_path)
        data = self._config_to_dict(config)

        with open(file_path, 'w') as f:
            if file_path.lower().endswith(('.yaml', '.yml')):
                yaml.dump(data, f, default_flow_style=False, indent=2)
            elif file_path.lower().endswith('.json'):
                json.dump(data, f, indent=2)
            else:
                raise ValueError(f"Unsupported file format. Use .yaml, .yml, or .json")

    def create_default_config(self) -> SearchConfig:
        """Create a default configuration with LinkedIn ToS compliance."""
        params = SearchParameters(
            keywords=["python", "developer"],
            location="Remote",
            experience_level="mid",
            job_type="full-time",
            remote="remote"
        )

        limits = ScrapingLimits(
            jobs_per_session=30,
            jobs_per_day=150,
            session_duration_minutes=25,
            request_delay_seconds=2.5,
            max_retries=3,
            retry_delay_seconds=5.0
        )

        return SearchConfig(
            search_parameters=params,
            scraping_limits=limits,
            enable_stealth_mode=True,
            output_format="json"
        )

    def validate_linkedin_compliance(self, config: SearchConfig) -> bool:
        """Validate that configuration complies with LinkedIn ToS."""
        limits = config.scraping_limits

        # Check ToS compliance requirements
        if limits.request_delay_seconds < LINKEDIN_MIN_REQUEST_DELAY:
            return False

        if limits.jobs_per_session > LINKEDIN_MAX_JOBS_PER_SESSION:
            return False

        if limits.jobs_per_day > LINKEDIN_MAX_JOBS_PER_DAY:
            return False

        if limits.session_duration_minutes > LINKEDIN_MAX_SESSION_DURATION:
            return False

        return True

    def _dict_to_config(self, data: Dict[str, Any]) -> SearchConfig:
        """Convert dictionary to SearchConfig object."""
        # Extract search parameters
        search_params_data = data.get('search_parameters', {})
        search_params = SearchParameters(**search_params_data)

        # Extract scraping limits
        limits_data = data.get('scraping_limits', {})
        scraping_limits = ScrapingLimits(**limits_data)

        # Extract other config values
        user_agents = data.get('user_agents', [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ])
        enable_stealth_mode = data.get('enable_stealth_mode', True)
        output_format = data.get('output_format', 'json')

        return SearchConfig(
            search_parameters=search_params,
            scraping_limits=scraping_limits,
            user_agents=user_agents,
            enable_stealth_mode=enable_stealth_mode,
            output_format=output_format
        )

    def _config_to_dict(self, config: SearchConfig) -> Dict[str, Any]:
        """Convert SearchConfig object to dictionary."""
        return {
            'search_parameters': asdict(config.search_parameters),
            'scraping_limits': asdict(config.scraping_limits),
            'user_agents': config.user_agents,
            'enable_stealth_mode': config.enable_stealth_mode,
            'output_format': config.output_format
        }