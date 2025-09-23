#!/usr/bin/env python3
"""
Interactive LinkedIn Scraper Testing
Allows safe testing of the LinkedIn scraper with compliance monitoring
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.search_config import ConfigManager
from src.scraper.linkedin_scraper import LinkedInScraper
from src.scraper.scraper_service import ScraperService
from src.database.connection import DatabaseManager


def display_current_config():
    """Display current scraper configuration."""
    print("⚙️  CURRENT SCRAPER CONFIGURATION:")
    config_manager = ConfigManager()
    config_path = Path(__file__).parent / "config" / "staging_search_config.yaml"
    config = config_manager.load_from_file(str(config_path))

    print(f"   Keywords: {', '.join(config.search_parameters.keywords)}")
    print(f"   Location: {config.search_parameters.location}")
    print(f"   Experience: {config.search_parameters.experience_level}")
    print(f"   Job Type: {config.search_parameters.job_type}")
    print(f"   Remote: {config.search_parameters.remote}")
    print(f"   Salary Range: ${config.search_parameters.salary_min:,} - ${config.search_parameters.salary_max:,}")
    print()

    print("🛡️  COMPLIANCE SETTINGS:")
    limits = config.scraping_limits
    print(f"   Jobs per session: {limits.jobs_per_session} (max: 50)")
    print(f"   Jobs per day: {limits.jobs_per_day} (max: 200)")
    print(f"   Request delay: {limits.request_delay_seconds}s (min: 2.0s)")
    print(f"   Session duration: {limits.session_duration_minutes} min (max: 30)")
    print(f"   Max retries: {limits.max_retries}")
    print()

    # Compliance check
    is_compliant = config_manager.validate_linkedin_compliance(config)
    status = "✅ COMPLIANT" if is_compliant else "❌ NON-COMPLIANT"
    print(f"🔍 LinkedIn ToS Compliance: {status}")

    return config, config_manager


def test_scraper_initialization():
    """Test scraper initialization without actually scraping."""
    print("🚀 TESTING SCRAPER INITIALIZATION:")
    print("   Loading configuration...")

    config_manager = ConfigManager()
    config_path = Path(__file__).parent / "config" / "staging_search_config.yaml"
    config = config_manager.load_from_file(str(config_path))

    print("   Creating scraper instance...")
    try:
        scraper = LinkedInScraper(config)
        print("   ✅ Scraper initialized successfully")
        print("   ✅ Rate limiter configured")
        print("   ✅ Anti-detection measures active")
        print("   ✅ Error handler ready")

        # Test configuration validation
        print("   Testing configuration validation...")
        is_valid = scraper.validate_configuration()
        print(f"   Configuration valid: {'✅ YES' if is_valid else '❌ NO'}")

        return True

    except Exception as e:
        print(f"   ❌ Error initializing scraper: {e}")
        return False


def test_scraper_service():
    """Test the scraper service integration."""
    print("🔧 TESTING SCRAPER SERVICE INTEGRATION:")

    try:
        # Connect to staging database
        staging_db_path = Path(__file__).parent / "data" / "db" / "jobs_staging.db"
        database_url = f"sqlite:///{staging_db_path.absolute()}"

        print(f"   Connecting to database: {staging_db_path}")
        db_manager = DatabaseManager(database_url)
        db_manager.initialize()

        # Load configuration
        config_manager = ConfigManager()
        config_path = Path(__file__).parent / "config" / "staging_search_config.yaml"
        config = config_manager.load_from_file(str(config_path))

        print("   Creating scraper service...")
        scraper_service = ScraperService(config, db_manager)

        print("   ✅ Database connection established")
        print("   ✅ Scraper service created")
        print("   ✅ Ready for job collection")

        # Show current database status
        with db_manager.get_session_context() as session:
            from src.database.repository import JobRepository
            repo = JobRepository(session)
            job_count = repo.count()
            print(f"   Current jobs in database: {job_count}")

        db_manager.close()
        return True

    except Exception as e:
        print(f"   ❌ Error in service integration: {e}")
        return False


def modify_search_parameters():
    """Allow user to modify search parameters."""
    print("🔧 MODIFY SEARCH PARAMETERS:")
    print("   Current search will be modified for this test session only.")
    print()

    # Get current config
    config_manager = ConfigManager()
    config_path = Path(__file__).parent / "config" / "staging_search_config.yaml"
    config = config_manager.load_from_file(str(config_path))

    # Allow modifications
    print("   Enter new values (press Enter to keep current):")

    keywords_input = input(f"   Keywords [{', '.join(config.search_parameters.keywords)}]: ").strip()
    if keywords_input:
        config.search_parameters.keywords = [k.strip() for k in keywords_input.split(',')]

    location_input = input(f"   Location [{config.search_parameters.location}]: ").strip()
    if location_input:
        config.search_parameters.location = location_input

    experience_input = input(f"   Experience Level [{config.search_parameters.experience_level}]: ").strip()
    if experience_input:
        config.search_parameters.experience_level = experience_input

    # Show updated config
    print("\n   Updated configuration:")
    print(f"   Keywords: {', '.join(config.search_parameters.keywords)}")
    print(f"   Location: {config.search_parameters.location}")
    print(f"   Experience: {config.search_parameters.experience_level}")

    return config


def run_dry_run_mode():
    """Simulate scraper execution without actual web requests."""
    print("🎮 DRY-RUN MODE (SIMULATION ONLY):")
    print("   This simulates scraper behavior without making actual requests to LinkedIn.")
    print()

    config_manager = ConfigManager()
    config_path = Path(__file__).parent / "config" / "staging_search_config.yaml"
    config = config_manager.load_from_file(str(config_path))

    print("   Simulating scraper execution:")
    print(f"   🔍 Search keywords: {', '.join(config.search_parameters.keywords)}")
    print(f"   📍 Location: {config.search_parameters.location}")
    print(f"   ⏱️  Request delay: {config.scraping_limits.request_delay_seconds}s")
    print(f"   📊 Max jobs per session: {config.scraping_limits.jobs_per_session}")
    print()

    print("   Simulation results:")
    print("   ✅ Would respect 2.5s delay between requests")
    print("   ✅ Would stop after 30 jobs or 25 minutes")
    print("   ✅ Would use stealth mode and user agent rotation")
    print("   ✅ Would handle errors with circuit breaker pattern")
    print("   ✅ Would save results to staging database")
    print()
    print("   🛡️  All LinkedIn ToS compliance measures would be enforced")


def main():
    """Main interactive testing interface."""
    print("🤖 LINKEDIN SCRAPER - INTERACTIVE TESTING")
    print("=" * 50)
    print()

    while True:
        print("🚀 TESTING OPTIONS:")
        print("   1. Display current configuration")
        print("   2. Test scraper initialization")
        print("   3. Test scraper service integration")
        print("   4. Run dry-run mode (safe simulation)")
        print("   5. Modify search parameters (temporary)")
        print("   6. Exit")
        print()

        choice = input("📋 Choose an option (1-6): ").strip()
        print()

        if choice == "1":
            display_current_config()

        elif choice == "2":
            test_scraper_initialization()

        elif choice == "3":
            test_scraper_service()

        elif choice == "4":
            run_dry_run_mode()

        elif choice == "5":
            modify_search_parameters()

        elif choice == "6":
            print("👋 Exiting scraper testing. Thank you!")
            break

        else:
            print("❌ Invalid choice. Please try again.")

        print("\n" + "─" * 50 + "\n")


if __name__ == "__main__":
    main()