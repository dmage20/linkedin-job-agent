# LinkedIn Job Application Agent

An intelligent agent that automates LinkedIn Easy Apply job applications using Claude AI and browser automation.

## Overview

This agent uses Claude's LLM to intelligently navigate LinkedIn Easy Apply forms, filling fields based on your profile and making context-aware decisions about form progression. It employs a ref-based element targeting system for precise field selection and robust form handling.

## Features

- **LLM-Driven Navigation**: Claude analyzes page state and makes intelligent decisions about what to fill and when to proceed
- **Ref-Based Element Targeting**: Unique identifiers for precise field selection, preventing infinite loops and duplicate fills
- **Multi-Field Type Support**: Handles textboxes, dropdowns, checkboxes, radio buttons, and textareas
- **Cost-Effective**: Choose between Haiku (~$0.001/application) or Sonnet (~$0.007/application) models
- **Manual Review**: Pause before final submission for human verification
- **Smart Matching**: Case-insensitive dropdown matching with partial text support

## Quick Start

### 1. Installation
```bash
npm install
```

### 2. Configuration
```bash
# Create credentials file
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Create user profile
cp src/config/user-profile.example.json src/config/user-profile.json
# Edit user-profile.json with your information

# Create required directories
mkdir -p documents screenshots logs
```

### 3. Run
```bash
# Apply to a job (default: Haiku model)
npm start https://www.linkedin.com/jobs/view/1234567890

# Use Sonnet model for more complex forms
npm start https://www.linkedin.com/jobs/view/1234567890 --model=sonnet
```

## How It Works

1. **Authentication**: Launches browser and waits for LinkedIn login (manual step)
2. **Page Analysis**: Captures accessibility tree snapshot of the page
3. **LLM Decision**: Claude analyzes snapshot and decides next action (fill/click/submit)
4. **Element Targeting**: Uses ref-based system to target specific form fields
5. **Form Progression**: Automatically advances through multi-step forms
6. **Manual Review**: Pauses before submission for user confirmation

## Architecture

### Core Components

- **LLMAgent** (`src/agent/llmAgent.js`): Main orchestrator with ref-based element tracking
- **AgentPrompt** (`src/prompts/agentPrompt.js`): System prompts that guide Claude's decisions
- **SnapshotProcessor** (`src/utils/snapshotProcessor.js`): Filters accessibility tree to reduce token usage

### Ref-Based Element System

Each interactive element receives a unique ref (e1, e2, e3...) that maps to:
- Element role (button, textbox, combobox, etc.)
- Element name/label
- Current value and state

This enables precise targeting: "Fill textbox e5 (Years of Ruby experience)" instead of "Fill first textbox"

## Configuration Files

### User Profile (`src/config/user-profile.json`)
Structured data containing:
- Personal information (name, email, phone, location)
- Work experience and education
- Skills and preferences
- Resume file path

### Environment Variables (`.env`)
```
ANTHROPIC_API_KEY=your-api-key-here
```

## Supported Features

✅ LinkedIn Easy Apply forms
✅ Multi-step form navigation
✅ Text inputs, dropdowns, checkboxes, radio buttons
✅ Resume upload
✅ Work authorization questions
✅ Technical experience questions

⚠️ Not supported: External application links, custom assessments, CAPTCHA (requires manual completion)

## Cost Optimization

- **Haiku model**: ~$0.001 per application (recommended for most jobs)
- **Sonnet model**: ~$0.007 per application (use for complex forms)
- Snapshot filtering reduces token usage by 95-99%
- Typical application uses 10k-30k input tokens, 1k-4k output tokens

## Logs

Application logs saved to `logs/` directory:
- `application-{timestamp}.json`: Decision history, token usage, cost summary
- `error-{timestamp}.png`: Screenshots on error
- `submission-{timestamp}.png`: Confirmation screenshots

## Safety Features

- Manual confirmation required before submission
- All actions logged for review
- Browser runs in visible mode for monitoring
- Graceful error handling with screenshots

## Development

```bash
# Run with auto-reload
npm run dev https://www.linkedin.com/jobs/view/1234567890

# Run tests
npm test
```

## Troubleshooting

**Module not found errors**: Run `npm install`

**ANTHROPIC_API_KEY not found**: Create `.env` file with your API key

**User profile not found**: Create `src/config/user-profile.json` from example template

**2FA/CAPTCHA prompts**: Complete manually in browser window, agent will continue automatically

**Easy Apply button not found**: Job may not be Easy Apply eligible, agent will skip

## License

MIT

## Disclaimer

This tool is for educational purposes and to assist with job applications. Use responsibly and in accordance with LinkedIn's Terms of Service. Always review applications before submission and ensure accuracy of information.
