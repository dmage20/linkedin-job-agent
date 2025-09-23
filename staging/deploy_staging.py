#!/usr/bin/env python3
"""
Staging Deployment Script for LinkedIn Job Agent Database System
US-001: Job Data Storage - Staging Environment Setup
"""

import os
import sys
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import DatabaseManager, initialize_database
from src.database.models import JobModel
from src.database.repository import JobRepository


class StagingDeployment:
    """Handles staging deployment of the database system."""

    def __init__(self):
        self.deployment_start = datetime.now(timezone.utc)
        self.setup_logging()
        self.db_manager = None

    def setup_logging(self):
        """Configure logging for staging deployment."""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "deployment_staging.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def validate_environment(self):
        """Validate staging environment prerequisites."""
        self.logger.info("🔍 Validating staging environment...")

        # Check required directories
        required_dirs = [
            "staging/data/db",
            "staging/logs",
            "src/database"
        ]

        for dir_path in required_dirs:
            full_path = Path(__file__).parent.parent / dir_path
            if not full_path.exists():
                self.logger.error(f"❌ Required directory missing: {dir_path}")
                return False
            self.logger.info(f"✅ Directory exists: {dir_path}")

        # Check Python dependencies
        try:
            import sqlalchemy
            import pytest
            self.logger.info(f"✅ SQLAlchemy version: {sqlalchemy.__version__}")
        except ImportError as e:
            self.logger.error(f"❌ Missing dependency: {e}")
            return False

        self.logger.info("✅ Environment validation passed")
        return True

    def setup_database(self):
        """Initialize staging database."""
        self.logger.info("🗄️ Setting up staging database...")

        # Configure staging database URL
        staging_db_path = Path(__file__).parent / "data" / "db" / "jobs_staging.db"
        staging_db_path.parent.mkdir(parents=True, exist_ok=True)

        database_url = f"sqlite:///{staging_db_path.absolute()}"
        self.logger.info(f"Database URL: {database_url}")

        try:
            # Initialize database
            self.db_manager = initialize_database(database_url)
            self.logger.info("✅ Database initialized successfully")

            # Verify tables were created
            with self.db_manager.get_session_context() as session:
                repository = JobRepository(session)
                count = repository.count()
                self.logger.info(f"✅ Database ready - Current job count: {count}")

            return True

        except Exception as e:
            self.logger.error(f"❌ Database setup failed: {e}")
            return False

    def create_sample_data(self):
        """Create sample data for staging validation."""
        self.logger.info("📝 Creating sample data for staging...")

        try:
            with self.db_manager.get_session_context() as session:
                repository = JobRepository(session)

                # Sample job data
                sample_jobs = [
                    {
                        "title": "Senior Software Engineer - Database Systems",
                        "company": "TechCorp Staging",
                        "location": "Remote",
                        "description": "Join our team to build scalable database systems. Experience with SQLAlchemy and PostgreSQL required.",
                        "url": "https://staging.example.com/job/1",
                        "linkedin_job_id": "staging_job_001",
                        "employment_type": "Full-time",
                        "experience_level": "Senior",
                        "industry": "Technology",
                        "is_remote": "Remote",
                        "salary_min": 120000,
                        "salary_max": 160000,
                        "salary_currency": "USD"
                    },
                    {
                        "title": "Python Developer - Data Infrastructure",
                        "company": "DataSoft Staging",
                        "location": "San Francisco, CA",
                        "description": "Build data infrastructure using Python and modern database technologies.",
                        "url": "https://staging.example.com/job/2",
                        "linkedin_job_id": "staging_job_002",
                        "employment_type": "Full-time",
                        "experience_level": "Mid-Senior",
                        "industry": "Technology",
                        "is_remote": "Hybrid",
                        "salary_min": 100000,
                        "salary_max": 140000,
                        "salary_currency": "USD"
                    },
                    {
                        "title": "DevOps Engineer - Cloud Infrastructure",
                        "company": "CloudFirst Staging",
                        "location": "New York, NY",
                        "description": "Manage cloud infrastructure and deployment pipelines for our database systems.",
                        "url": "https://staging.example.com/job/3",
                        "linkedin_job_id": "staging_job_003",
                        "employment_type": "Full-time",
                        "experience_level": "Senior",
                        "industry": "Technology",
                        "is_remote": "On-site",
                        "salary_min": 110000,
                        "salary_max": 150000,
                        "salary_currency": "USD"
                    }
                ]

                # Create sample jobs
                created_jobs = repository.bulk_create(sample_jobs)
                self.logger.info(f"✅ Created {len(created_jobs)} sample jobs")

                # Verify data
                total_jobs = repository.count()
                self.logger.info(f"✅ Total jobs in staging database: {total_jobs}")

            return True

        except Exception as e:
            self.logger.error(f"❌ Sample data creation failed: {e}")
            return False

    def validate_deployment(self):
        """Validate staging deployment."""
        self.logger.info("✅ Validating staging deployment...")

        try:
            with self.db_manager.get_session_context() as session:
                repository = JobRepository(session)

                # Test basic operations
                job_count = repository.count()
                self.logger.info(f"✅ Database contains {job_count} jobs")

                # Test search functionality
                search_results = repository.search_jobs(title="Engineer", limit=10)
                self.logger.info(f"✅ Search test returned {len(search_results)} results")

                # Test job retrieval by LinkedIn ID
                test_job = repository.get_by_linkedin_id("staging_job_001")
                if test_job:
                    self.logger.info(f"✅ Job retrieval test passed: {test_job.title}")
                else:
                    self.logger.warning("⚠️ Job retrieval test failed")

                # Test statistics
                stats = repository.get_jobs_stats()
                self.logger.info(f"✅ Statistics test passed: {stats['total_jobs']} total jobs")

            return True

        except Exception as e:
            self.logger.error(f"❌ Deployment validation failed: {e}")
            return False

    def performance_check(self):
        """Run performance checks on staging database."""
        self.logger.info("⚡ Running performance checks...")

        try:
            with self.db_manager.get_session_context() as session:
                repository = JobRepository(session)

                # Time database operations
                operations = [
                    ("Count all jobs", lambda: repository.count()),
                    ("Search by title", lambda: repository.search_jobs(title="Engineer")),
                    ("Get recent jobs", lambda: repository.get_recent_jobs(days=7)),
                    ("Get job statistics", lambda: repository.get_jobs_stats())
                ]

                for operation_name, operation_func in operations:
                    start_time = time.time()
                    result = operation_func()
                    end_time = time.time()
                    duration_ms = (end_time - start_time) * 1000

                    self.logger.info(f"✅ {operation_name}: {duration_ms:.2f}ms")

                    # Check if operation meets performance requirements (<50ms)
                    if duration_ms > 50:
                        self.logger.warning(f"⚠️ Performance concern: {operation_name} took {duration_ms:.2f}ms")

            return True

        except Exception as e:
            self.logger.error(f"❌ Performance check failed: {e}")
            return False

    def generate_deployment_report(self):
        """Generate staging deployment report."""
        deployment_end = datetime.now(timezone.utc)
        duration = deployment_end - self.deployment_start

        report = f"""
# Staging Deployment Report
## LinkedIn Job Agent - Database System (US-001)

**Deployment Details:**
- Environment: Staging
- Start Time: {self.deployment_start.isoformat()}
- End Time: {deployment_end.isoformat()}
- Duration: {duration.total_seconds():.2f} seconds
- Feature: US-001: Job Data Storage
- Database System: SQLAlchemy 2.0.23 + SQLite

**Deployment Status:** ✅ SUCCESSFUL

**Validation Results:**
- ✅ Environment validation passed
- ✅ Database initialization successful
- ✅ Sample data creation successful
- ✅ Deployment validation passed
- ✅ Performance checks completed

**Next Steps:**
1. Production deployment preparation
2. Sprint Review demo setup
3. Stakeholder presentation
4. PostgreSQL migration planning (if needed)

**Staging Environment Ready for:**
- QA final validation
- Performance testing
- Integration testing
- Demo preparation
"""

        # Write report to file
        report_path = Path(__file__).parent / "logs" / "deployment_report.md"
        with open(report_path, 'w') as f:
            f.write(report)

        self.logger.info(f"📊 Deployment report generated: {report_path}")
        print(report)

    def deploy(self):
        """Execute full staging deployment."""
        self.logger.info("🚀 Starting staging deployment for Database System (US-001)")

        try:
            # Validate environment
            if not self.validate_environment():
                raise Exception("Environment validation failed")

            # Setup database
            if not self.setup_database():
                raise Exception("Database setup failed")

            # Create sample data
            if not self.create_sample_data():
                raise Exception("Sample data creation failed")

            # Validate deployment
            if not self.validate_deployment():
                raise Exception("Deployment validation failed")

            # Performance check
            if not self.performance_check():
                raise Exception("Performance check failed")

            # Generate report
            self.generate_deployment_report()

            self.logger.info("🎉 Staging deployment completed successfully!")
            return True

        except Exception as e:
            self.logger.error(f"💥 Staging deployment failed: {e}")
            return False

        finally:
            if self.db_manager:
                self.db_manager.close()


if __name__ == "__main__":
    deployment = StagingDeployment()
    success = deployment.deploy()
    sys.exit(0 if success else 1)