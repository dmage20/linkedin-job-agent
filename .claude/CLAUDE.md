# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Session Initialization

**CRITICAL:** At the start of EVERY session, read `PROGRESS.md` in the project root to understand:
- Current development phase and status
- What was completed in previous sessions
- Next steps and blockers
- Technical decisions made

## Project Overview

This is a LinkedIn Job Application Agent that automates job applications using browser automation. The project is built with Node.js and Playwright, following a phased development approach.

### Development Phases
1. **Phase 1 - MVP** (✅ COMPLETE): Single job application automation with manual review
2. **Phase 2 - AI Integration** (PLANNED): Claude API for cover letters and intelligent responses
3. **Phase 3 - Batch Processing** (PLANNED): Multi-job automation with SQLite tracking
4. **Phase 4 - Polish** (PLANNED): Web UI, advanced features, robustness improvements

## Core Architecture

### Module Structure

The application follows a modular architecture with three core components:

**JobApplicationAgent** (`src/index.js`)
- Main orchestrator class that coordinates the entire application flow
- Manages Playwright browser instance lifecycle
- Loads user profile from `src/config/user-profile.json`
- Coordinates authentication → navigation → form filling → submission
- Implements manual review checkpoint before final submission
- Captures screenshots of confirmations

**LinkedInAuth** (`src/browser/auth.js`)
- Handles LinkedIn login automation
- Detects and handles 2FA and CAPTCHA challenges (pauses for manual completion)
- Implements human-like delays between actions to avoid bot detection
- Verifies successful authentication before proceeding

**FormFiller** (`src/jobs/formFiller.js`)
- Detects all form field types (text inputs, dropdowns, checkboxes, file uploads, textareas)
- Auto-fills fields based on user profile data structure
- Handles multi-step LinkedIn Easy Apply forms
- Uploads resume from path specified in user profile
- Intelligently maps user data to common LinkedIn form fields (phone, location, experience, visa status)

### Data Flow

1. User provides LinkedIn job URL as command-line argument
2. Agent loads credentials from `.env` and profile from `src/config/user-profile.json`
3. Browser launched with `headless: false` and `slowMo: 100` for visibility and human-like behavior
4. Authentication module logs into LinkedIn
5. Navigation to job posting → click "Easy Apply"
6. Form filler detects all fields and auto-fills from profile
7. Multi-step forms handled by detecting step progress and clicking "Next"
8. **Manual review checkpoint**: User presses Enter to confirm submission
9. Screenshot saved to `screenshots/` directory with timestamp
10. Browser cleanup and exit

## Commands

### First-Time Setup
```bash
npm install                                    # Install Playwright and dependencies
cp .env.example .env                          # Create credentials file (must edit manually)
cp src/config/user-profile.example.json src/config/user-profile.json  # Create profile (must edit)
mkdir -p documents screenshots                # Create required directories
```

### Running the Agent
```bash
npm start <linkedin-job-url>                  # Apply to a single job
npm run dev <linkedin-job-url>                # Run with auto-reload (development)
```

Example:
```bash
npm start https://www.linkedin.com/jobs/view/1234567890
```

### Testing
```bash
npm test                                       # Run test suite (when tests exist)
```

## Configuration Files

### User Profile (`src/config/user-profile.json`)
Contains structured user data that maps to LinkedIn form fields:
- `personalInfo`: Name, email, phone, location (city, state, country, zip)
- `workExperience`: Array of job history objects
- `education`: Array of education objects
- `skills`: Array of skill strings
- `documents.resume`: Path to resume PDF file (relative or absolute)
- `preferences`: Job preferences including `yearsOfExperience`, `requiresSponsorship`, work arrangement, salary expectations
- `commonAnswers`: Pre-written responses to common application questions

### Environment Variables (`.env`)
```
LINKEDIN_EMAIL=your-email@example.com
LINKEDIN_PASSWORD=your-password
```

**Security Note:** The `.env` file is gitignored. Never commit credentials.

## Key Constraints & Design Decisions

### LinkedIn Easy Apply Only
Phase 1 only supports LinkedIn's "Easy Apply" feature. Jobs requiring external applications are automatically skipped.

### Manual Review Required
The agent ALWAYS pauses before final submission, requiring user to press Enter. This is a safety feature to prevent accidental applications.

### Browser Visibility
Browser runs with `headless: false` in Phase 1 so users can:
- Monitor the automation in real-time
- Manually complete 2FA/CAPTCHA challenges
- Review the application before submission

### Human-Like Behavior
All actions include delays (`slowMo: 100`, manual `delay()` calls) to mimic human behavior and avoid LinkedIn's anti-bot detection.

### Form Field Detection Strategy
The FormFiller uses multiple strategies to find fields:
- ID/name attribute matching (e.g., `input[id*="phoneNumber"]`)
- Label association via `for` attribute or parent label elements
- Common LinkedIn field patterns based on Easy Apply form structure

## Development Notes

### When Modifying Authentication (`src/browser/auth.js`)
- Test with accounts that have 2FA enabled
- Verify CAPTCHA detection and manual completion flow
- Ensure session verification works with both `/feed` and `/checkpoint` URLs

### When Modifying Form Filling (`src/jobs/formFiller.js`)
- LinkedIn's DOM structure may change; selectors might need updates
- Test with various job postings (different companies, different field combinations)
- Multi-step forms have varying numbers of steps; the detection logic must be robust
- File upload requires absolute paths; relative path conversion is handled in `uploadResume()`

### When Adding Features
- Update `project-config.json` to track feature status
- Update `PROGRESS.md` with implementation notes
- Phase 2+ features should be in separate modules (`src/ai/`, `src/data/`)

## LinkedIn DOM Patterns (Subject to Change)

These selectors were valid as of implementation but may need updates:

- Easy Apply button: `button:has-text("Easy Apply")`
- Form step progress: `[class*="artdeco-modal__header"]` containing text like "1 of 3"
- Next/Continue buttons: `button:has-text("Next")`, `button:has-text("Review")`, `button:has-text("Continue")`
- Submit button: `button:has-text("Submit application")`
- Phone field: `input[id*="phoneNumber"]`, `input[name*="phone"]`
- Location field: `input[id*="city"]`, `input[name*="location"]`

## Error Handling Philosophy

- Authentication failures: Log clear error messages, check for wrong password/email alerts
- Missing Easy Apply: Skip job gracefully with informative message
- Form field not found: Log as info (field may not be required), continue processing
- CAPTCHA/2FA: Pause execution, wait for manual completion, resume automatically
- Submission failure: Keep browser open, log error, allow manual completion

## Future Development

### Phase 2 Prerequisites
- Add `ANTHROPIC_API_KEY` to `.env.example` and configuration
- Create `src/ai/coverLetterGenerator.js` module
- Create `src/ai/questionAnswerer.js` module
- Update FormFiller to use AI modules for textarea fields

### Phase 3 Prerequisites
- Add SQLite dependency to package.json
- Create `src/data/tracker.js` with database schema
- Implement job search functionality in `src/jobs/searcher.js`
- Add batch processing logic to main orchestrator

## Troubleshooting Common Issues

### "Module not found" errors
- Run `npm install` to install dependencies
- Verify Node.js version is 18+

### "User profile not found"
- User must create `src/config/user-profile.json` from example template
- Check file permissions and JSON syntax

### "LinkedIn credentials not found"
- User must create `.env` file from `.env.example`
- Verify environment variables are correctly formatted

### Application not fully auto-filled
- Phase 1 handles common fields; some custom fields may require manual entry
- LinkedIn forms vary by company; selectors may need refinement
- Check console logs for "field not found" messages

### Bot detection / account restrictions
- Reduce application frequency
- Ensure delays are working (`slowMo` and manual delays)
- Consider session persistence to avoid repeated logins (future enhancement)
