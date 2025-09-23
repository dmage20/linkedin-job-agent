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
- Job posting records with analysis scores
- Application tracking and status
- User profile data for matching

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

## Development Notes

The project structure is currently scaffolded but implementation files are not yet created. When implementing:

1. Start with the database models to define the data schema
2. Implement the scraper for LinkedIn job search
3. Add the analyzer for job matching using Claude API
4. Build the applicator for automated applications
5. Create the main.py entry point referenced in the Makefile

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