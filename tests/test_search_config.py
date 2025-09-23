"""Tests for the job search configuration system."""

import pytest
from pathlib import Path
import tempfile
import yaml
import json
from dataclasses import asdict

from src.config.search_config import (
    SearchConfig,
    SearchParameters,
    ScrapingLimits,
    ValidationError,
    ConfigManager
)


class TestSearchParameters:
    """Test the SearchParameters dataclass."""

    def test_valid_search_parameters(self):
        """Test creating valid search parameters."""
        params = SearchParameters(
            keywords=["python", "developer"],
            location="San Francisco",
            experience_level="mid",
            job_type="full-time",
            remote="remote",
            salary_min=100000,
            salary_max=150000,
            company_size="medium",
            date_posted="week"
        )

        assert params.keywords == ["python", "developer"]
        assert params.location == "San Francisco"
        assert params.experience_level == "mid"
        assert params.job_type == "full-time"
        assert params.remote == "remote"
        assert params.salary_min == 100000
        assert params.salary_max == 150000
        assert params.company_size == "medium"
        assert params.date_posted == "week"

    def test_invalid_experience_level(self):
        """Test that invalid experience level raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid experience_level"):
            SearchParameters(
                keywords=["python"],
                location="San Francisco",
                experience_level="invalid"
            )

    def test_invalid_job_type(self):
        """Test that invalid job type raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid job_type"):
            SearchParameters(
                keywords=["python"],
                location="San Francisco",
                job_type="invalid"
            )

    def test_invalid_remote_option(self):
        """Test that invalid remote option raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid remote"):
            SearchParameters(
                keywords=["python"],
                location="San Francisco",
                remote="invalid"
            )

    def test_invalid_salary_range(self):
        """Test that invalid salary range raises ValidationError."""
        with pytest.raises(ValidationError, match="salary_min cannot be greater than salary_max"):
            SearchParameters(
                keywords=["python"],
                location="San Francisco",
                salary_min=150000,
                salary_max=100000
            )

    def test_empty_keywords(self):
        """Test that empty keywords raises ValidationError."""
        with pytest.raises(ValidationError, match="Keywords cannot be empty"):
            SearchParameters(
                keywords=[],
                location="San Francisco"
            )

    def test_empty_location(self):
        """Test that empty location raises ValidationError."""
        with pytest.raises(ValidationError, match="Location cannot be empty"):
            SearchParameters(
                keywords=["python"],
                location=""
            )


class TestScrapingLimits:
    """Test the ScrapingLimits dataclass."""

    def test_valid_scraping_limits(self):
        """Test creating valid scraping limits."""
        limits = ScrapingLimits(
            jobs_per_session=50,
            jobs_per_day=200,
            session_duration_minutes=30,
            request_delay_seconds=2.5,
            max_retries=3,
            retry_delay_seconds=5.0
        )

        assert limits.jobs_per_session == 50
        assert limits.jobs_per_day == 200
        assert limits.session_duration_minutes == 30
        assert limits.request_delay_seconds == 2.5
        assert limits.max_retries == 3
        assert limits.retry_delay_seconds == 5.0

    def test_invalid_jobs_per_session(self):
        """Test that invalid jobs_per_session raises ValidationError."""
        with pytest.raises(ValidationError, match="jobs_per_session must be between 1 and 100"):
            ScrapingLimits(jobs_per_session=0)

    def test_invalid_jobs_per_day(self):
        """Test that invalid jobs_per_day raises ValidationError."""
        with pytest.raises(ValidationError, match="jobs_per_day must be between 1 and 500"):
            ScrapingLimits(jobs_per_day=600)

    def test_invalid_session_duration(self):
        """Test that invalid session duration raises ValidationError."""
        with pytest.raises(ValidationError, match="session_duration_minutes must be between 1 and 60"):
            ScrapingLimits(session_duration_minutes=70)

    def test_invalid_request_delay(self):
        """Test that invalid request delay raises ValidationError."""
        with pytest.raises(ValidationError, match="request_delay_seconds must be at least 2.0"):
            ScrapingLimits(request_delay_seconds=1.5)

    def test_linkedin_compliance_defaults(self):
        """Test that default limits comply with LinkedIn ToS."""
        limits = ScrapingLimits()

        # LinkedIn ToS compliance requirements
        assert limits.jobs_per_session <= 50
        assert limits.jobs_per_day <= 200
        assert limits.session_duration_minutes <= 30
        assert limits.request_delay_seconds >= 2.0


class TestSearchConfig:
    """Test the SearchConfig dataclass."""

    def test_valid_search_config(self):
        """Test creating valid search configuration."""
        params = SearchParameters(
            keywords=["python", "developer"],
            location="San Francisco"
        )
        limits = ScrapingLimits()

        config = SearchConfig(
            search_parameters=params,
            scraping_limits=limits,
            user_agents=[
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            ],
            enable_stealth_mode=True,
            output_format="json"
        )

        assert config.search_parameters == params
        assert config.scraping_limits == limits
        assert len(config.user_agents) == 2
        assert config.enable_stealth_mode is True
        assert config.output_format == "json"

    def test_invalid_output_format(self):
        """Test that invalid output format raises ValidationError."""
        params = SearchParameters(keywords=["python"], location="San Francisco")
        limits = ScrapingLimits()

        with pytest.raises(ValidationError, match="Invalid output_format"):
            SearchConfig(
                search_parameters=params,
                scraping_limits=limits,
                output_format="invalid"
            )

    def test_empty_user_agents(self):
        """Test that empty user agents raises ValidationError."""
        params = SearchParameters(keywords=["python"], location="San Francisco")
        limits = ScrapingLimits()

        with pytest.raises(ValidationError, match="At least one user agent must be provided"):
            SearchConfig(
                search_parameters=params,
                scraping_limits=limits,
                user_agents=[]
            )


class TestConfigManager:
    """Test the ConfigManager class."""

    def test_load_config_from_yaml(self):
        """Test loading configuration from YAML file."""
        config_data = {
            'search_parameters': {
                'keywords': ['python', 'developer'],
                'location': 'San Francisco',
                'experience_level': 'mid',
                'job_type': 'full-time',
                'remote': 'remote',
                'salary_min': 100000,
                'salary_max': 150000
            },
            'scraping_limits': {
                'jobs_per_session': 30,
                'jobs_per_day': 150,
                'request_delay_seconds': 3.0
            },
            'user_agents': [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            ],
            'enable_stealth_mode': True,
            'output_format': 'json'
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            manager = ConfigManager()
            config = manager.load_from_file(config_path)

            assert config.search_parameters.keywords == ['python', 'developer']
            assert config.search_parameters.location == 'San Francisco'
            assert config.scraping_limits.jobs_per_session == 30
            assert config.scraping_limits.request_delay_seconds == 3.0
            assert config.enable_stealth_mode is True
        finally:
            Path(config_path).unlink()

    def test_load_config_from_json(self):
        """Test loading configuration from JSON file."""
        config_data = {
            'search_parameters': {
                'keywords': ['javascript', 'frontend'],
                'location': 'New York',
                'job_type': 'contract'
            },
            'scraping_limits': {
                'jobs_per_session': 25,
                'request_delay_seconds': 2.5
            },
            'user_agents': [
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            ],
            'output_format': 'csv'
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            manager = ConfigManager()
            config = manager.load_from_file(config_path)

            assert config.search_parameters.keywords == ['javascript', 'frontend']
            assert config.search_parameters.location == 'New York'
            assert config.scraping_limits.jobs_per_session == 25
            assert config.output_format == 'csv'
        finally:
            Path(config_path).unlink()

    def test_save_config_to_yaml(self):
        """Test saving configuration to YAML file."""
        params = SearchParameters(
            keywords=['python', 'backend'],
            location='Seattle',
            experience_level='senior'
        )
        limits = ScrapingLimits(jobs_per_session=40)
        config = SearchConfig(
            search_parameters=params,
            scraping_limits=limits,
            output_format='yaml'
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_path = f.name

        try:
            manager = ConfigManager()
            manager.save_to_file(config, config_path)

            # Load back and verify
            loaded_config = manager.load_from_file(config_path)
            assert loaded_config.search_parameters.keywords == ['python', 'backend']
            assert loaded_config.search_parameters.location == 'Seattle'
            assert loaded_config.scraping_limits.jobs_per_session == 40
        finally:
            Path(config_path).unlink()

    def test_create_default_config(self):
        """Test creating default configuration."""
        manager = ConfigManager()
        config = manager.create_default_config()

        # Should have default values that comply with LinkedIn ToS
        assert config.scraping_limits.jobs_per_session <= 50
        assert config.scraping_limits.jobs_per_day <= 200
        assert config.scraping_limits.request_delay_seconds >= 2.0
        assert config.enable_stealth_mode is True
        assert len(config.user_agents) > 0

    def test_validate_linkedin_compliance(self):
        """Test LinkedIn ToS compliance validation."""
        manager = ConfigManager()

        # Valid configuration
        valid_config = SearchConfig(
            search_parameters=SearchParameters(keywords=['test'], location='test'),
            scraping_limits=ScrapingLimits(
                jobs_per_session=30,
                request_delay_seconds=2.5
            )
        )
        assert manager.validate_linkedin_compliance(valid_config) is True

        # Test that invalid configuration raises ValidationError during creation
        with pytest.raises(ValidationError, match="request_delay_seconds must be at least 2.0"):
            SearchConfig(
                search_parameters=SearchParameters(keywords=['test'], location='test'),
                scraping_limits=ScrapingLimits(
                    jobs_per_session=30,
                    request_delay_seconds=1.0  # Too fast
                )
            )

    def test_load_nonexistent_file(self):
        """Test loading from non-existent file raises appropriate error."""
        manager = ConfigManager()

        with pytest.raises(FileNotFoundError):
            manager.load_from_file('/nonexistent/config.yaml')

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML raises appropriate error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = f.name

        try:
            manager = ConfigManager()
            with pytest.raises(yaml.YAMLError):
                manager.load_from_file(config_path)
        finally:
            Path(config_path).unlink()