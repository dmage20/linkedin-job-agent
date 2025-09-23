# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LinkedIn Job Agent - an automated system for searching, analyzing, and applying to jobs on LinkedIn. The project uses Python with Playwright for browser automation, Anthropic's Claude API for job analysis, and SQLAlchemy for data persistence.

## Architecture

The application follows a modular architecture with these core components:

- **Scraper Module** (`src/scraper/`): Handles LinkedIn job search automation using Playwright
- **Analyzer Module** (`src/analyzer/`): Uses Anthropic API to analyze job postings and match against user profiles
- **Applicator Module** (`src/applicator/`): Automates the job application process
- **Database Module** (`src/database/`): SQLAlchemy models and database operations
- **Utils Module** (`src/utils/`): Shared utilities and helpers

The system is designed to run as a background service with configurable intervals for job searching and application limits.

## Development Commands

### Initial Setup
```bash
make install    # Install dependencies and Playwright browsers
make setup      # Create .env file and initialize database
```

### Running the Application
```bash
make start      # Start in background
make stop       # Stop background process
make restart    # Restart the application
make run        # Run in interactive/foreground mode
make status     # Check if running
```

### Monitoring and Debugging
```bash
make logs       # Follow live logs
make logs-recent # View recent log entries
```

### Testing and Maintenance
```bash
make test       # Run pytest test suite
make clean      # Clean data and logs (interactive prompt)
```

## Configuration

### Environment Variables (.env)
- `ANTHROPIC_API_KEY`: Required for job analysis
- `LINKEDIN_EMAIL/PASSWORD`: Optional, will prompt if not provided
- `MAX_APPLICATIONS_PER_DAY`: Rate limiting (default: 10)
- `SEARCH_INTERVAL_MINUTES`: How often to search (default: 60)
- `HEADLESS_MODE`: Browser visibility (default: false for debugging)

### Application Settings (config/settings.yaml)
- Search criteria: keywords, locations, experience levels
- Matching algorithm weights and thresholds
- Rate limiting and browser timeout settings
- Notification preferences

## Database Structure

Uses SQLite database stored in `data/db/jobs.db`. The application expects:
- Job posting records with analysis scores and competitive intelligence
- Application tracking and status management
- User profile data for matching algorithms
- Applicant count data for strategic job targeting

### Job Model Schema
The JobModel includes comprehensive fields for job analysis:
- **Core Fields**: title, company, location, description, LinkedIn job ID
- **Enhanced Data**: employment_type, experience_level, industry, salary range
- **Competitive Intelligence**: applicant_count for strategic targeting
- **Metadata**: posting dates, remote work status, company size
- **Performance**: Indexed fields for efficient querying and filtering

## Data Directories

- `data/db/`: SQLite database files
- `data/resume/`: User resume files
- `data/cover_letters/`: Generated cover letters
- `logs/`: Application log files

## Key Dependencies

- **Playwright**: Browser automation for LinkedIn interaction
- **Anthropic**: Claude API for intelligent job analysis
- **SQLAlchemy**: Database ORM
- **FastAPI**: Web interface (if implemented)
- **APScheduler**: Background job scheduling
- **Cryptography**: Credential security

## Competitive Intelligence Features

The database system includes advanced competitive analysis capabilities:

### Strategic Job Targeting
- **Low Competition Jobs**: Identify opportunities with ≤10 applicants for higher success rates
- **Competition Filtering**: Filter jobs by applicant count ranges (min/max thresholds)
- **Market Intelligence**: Get statistical analysis of job competition landscape
- **Success Optimization**: Focus application efforts on winnable opportunities

### Repository Methods
- `find_jobs_by_applicant_count()`: Advanced filtering with competition ordering
- `get_low_competition_jobs()`: Strategic targeting for maximum success probability
- `get_competition_statistics()`: Market analytics with competition breakdown
- **Performance**: All queries optimized with database indexing for sub-millisecond response

### Business Value
- **Data-Driven Strategy**: Make application decisions based on real competition data
- **Resource Efficiency**: Optimize time and effort by targeting strategic opportunities
- **Competitive Advantage**: Gain insights into job market competition levels
- **Success Metrics**: Track and improve application success rates through strategic targeting

## Development Notes

### Current Implementation Status

✅ **Database Foundation Complete**:
- Full JobModel with competitive intelligence capabilities
- Repository pattern with advanced querying and analytics
- Comprehensive test coverage (95%+) with performance validation
- Production-ready with indexing and optimization

### Next Development Steps

When continuing implementation:
1. ✅ **Database models and schema** - COMPLETED
2. **LinkedIn scraper** for job search automation
3. **Analyzer module** for job matching using Claude API
4. **Applicator module** for automated applications
5. **Main application** entry point and orchestration

### Database Features Ready

The implemented database system supports:
- Complete job data storage with LinkedIn integration
- Salary range tracking and currency support
- Remote work status classification (Remote/Hybrid/On-site)
- Competitive intelligence with applicant count analysis
- Strategic job targeting and market analytics

The application is designed to be privacy-conscious with local data storage and optional credential handling.

## Agile Development Team

This project includes a complete Agile development team simulation using specialized Claude Code agents. The team follows Test-Driven Development (TDD) and delivers software incrementally with continuous stakeholder feedback.

### Team Agents

Located in `.claude/agents/`, each agent has specialized expertise:

- **Product Owner**: Requirements gathering, user story creation, backlog management
- **Scrum Master**: Process facilitation, sprint planning, impediment removal
- **Technical Lead**: Architecture decisions, code reviews, technical guidance
- **Developer**: TDD implementation, feature development, code quality
- **QA/Tester**: Test strategy, quality validation, automation
- **DevOps**: CI/CD, infrastructure, deployment, monitoring

### Usage Pattern

1. **Start with Product Owner**: Break requirements into user stories
2. **Sprint Planning with Scrum Master**: Plan incremental delivery
3. **Technical Guidance**: Get architecture direction from Technical Lead
4. **TDD Implementation**: Developer implements with test-first approach
5. **Quality Validation**: QA/Tester ensures acceptance criteria met
6. **Deployment**: DevOps handles staging and production deployment

### Key Files

- `.claude/README.md`: Complete team overview and roles
- `.claude/USAGE_GUIDE.md`: Step-by-step guide for working with agents
- `.claude/workflows/agile-process.md`: Detailed Agile workflow
- `.claude/workflows/ticket-management.md`: Sprint and ticket tracking
- `.claude/templates/`: User story and sprint templates
- `.claude/sprints/`: Sprint tracking and progress

### Incremental Delivery

The team delivers working software in small increments that can be:
- **Demonstrated**: Show functional features
- **Tested**: Validate against acceptance criteria
- **Reviewed**: Get stakeholder feedback
- **Approved**: Sign off for next increment

### Change Management

When requirements evolve:
1. Product Owner updates user stories
2. Scrum Master assesses sprint impact
3. Team re-estimates and adjusts plan
4. Development continues with new requirements

This approach ensures you maintain control over the development process while getting incremental value and the ability to course-correct based on working software demonstrations.