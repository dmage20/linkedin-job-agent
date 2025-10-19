# LinkedIn Job Application Agent

An AI-powered agent that automates LinkedIn job applications using browser automation.

## Current Status: Phase 1 - MVP ✅

The Phase 1 MVP supports:
- ✅ LinkedIn authentication
- ✅ Automated form filling for Easy Apply jobs
- ✅ Resume upload
- ✅ Multi-step application handling
- ✅ Manual review before submission

## Prerequisites

- Node.js 18+ installed
- A LinkedIn account
- Your resume in PDF format

## Quick Start

### 1. Install Dependencies

```bash
cd linkedin-job-agent
npm install
```

This will install:
- Playwright (browser automation)
- dotenv (environment variables)

### 2. Configure LinkedIn Credentials

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your LinkedIn credentials:

```
LINKEDIN_EMAIL=your-email@example.com
LINKEDIN_PASSWORD=your-password-here
```

**⚠️ IMPORTANT:** Never commit your `.env` file to version control!

### 3. Set Up Your Profile

Create your user profile configuration:

```bash
cp src/config/user-profile.example.json src/config/user-profile.json
```

Edit `src/config/user-profile.json` with your information:
- Personal details (name, email, phone, location)
- Work experience
- Education
- Skills
- Path to your resume file
- Job preferences

### 4. Prepare Your Documents

Create a `documents` folder and add your resume:

```bash
mkdir -p documents
# Copy your resume to: documents/resume.pdf
```

Make sure the path in `user-profile.json` matches your resume location.

### 5. Create Screenshots Folder

```bash
mkdir -p screenshots
```

This is where confirmation screenshots will be saved.

### 6. Run the Agent

```bash
npm start <linkedin-job-url>
```

Example:

```bash
npm start https://www.linkedin.com/jobs/view/1234567890
```

## How It Works

1. **Launch**: The agent opens a browser window
2. **Login**: Automatically logs into LinkedIn with your credentials
3. **Navigate**: Goes to the specified job posting
4. **Easy Apply**: Clicks the "Easy Apply" button
5. **Auto-Fill**: Fills form fields with your profile data
6. **Upload**: Attaches your resume
7. **Review**: Pauses for you to review the application
8. **Submit**: Submits after you press Enter

## Features

### Smart Form Filling

The agent automatically detects and fills:
- Phone number
- Location/City
- Years of experience
- Visa sponsorship status
- Work authorization
- Text area responses (why this company, etc.)

### Multi-Step Support

LinkedIn Easy Apply forms often have multiple steps. The agent:
- Detects the current step
- Fills all fields in each step
- Clicks "Next" to proceed
- Continues until reaching the final submission

### Safety Features

- **Manual Review**: Always pauses before submission
- **Headless: false**: Browser is visible so you can monitor
- **Human-like Delays**: Random delays to avoid detection
- **Screenshot Confirmation**: Saves proof of application

## Project Structure

```
linkedin-job-agent/
├── src/
│   ├── index.js              # Main application
│   ├── browser/
│   │   └── auth.js           # LinkedIn authentication
│   ├── jobs/
│   │   └── formFiller.js     # Form detection & filling
│   └── config/
│       └── user-profile.json # Your profile data
├── documents/                # Your resume & docs
├── screenshots/              # Application confirmations
├── PROGRESS.md               # Project progress tracker
├── .env                      # Your credentials (DO NOT COMMIT)
└── package.json              # Dependencies
```

## Limitations (Phase 1)

- ✅ Only works with "Easy Apply" jobs
- ✅ Requires manual review before submission
- ✅ One job at a time (no batch processing yet)
- ✅ No AI-generated cover letters yet
- ✅ Basic form field detection

## Coming in Future Phases

### Phase 2 - AI Integration
- AI-generated cover letters tailored to each job
- Intelligent screening question answers
- Job description analysis
- Skills matching

### Phase 3 - Batch Processing
- Search for jobs by criteria
- Apply to multiple jobs automatically
- Application tracking database
- Success rate analytics

### Phase 4 - Polish
- Web-based dashboard
- Resume customization per job
- Company research integration
- Interview scheduling assistance

## Troubleshooting

### "Module not found" errors

Install dependencies:
```bash
npm install
```

### "User profile not found"

Create your profile:
```bash
cp src/config/user-profile.example.json src/config/user-profile.json
```

### "LinkedIn credentials not found"

Create `.env` file:
```bash
cp .env.example .env
# Then edit .env with your credentials
```

### 2FA / CAPTCHA Prompts

If you have 2-factor authentication enabled:
1. The agent will pause
2. Complete the 2FA challenge in the browser window
3. The agent will continue automatically

### "Easy Apply" button not found

Not all LinkedIn jobs have Easy Apply. The agent will skip jobs that require external application processes.

## Security Notes

- **Credentials**: Stored in `.env` (gitignored)
- **Local Only**: All data stays on your machine
- **No Cloud**: No data sent to external servers
- **Review Before Submit**: Always check before applications go out

## Development

Run in development mode with auto-reload:

```bash
npm run dev
```

## License

MIT

## Disclaimer

This tool is for educational purposes and to assist with job applications. Use responsibly and in accordance with LinkedIn's Terms of Service. The authors are not responsible for any account restrictions or bans resulting from use of this tool.

Always review applications before submission and ensure accuracy of information.
