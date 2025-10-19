# Quick Start - LLM-Powered Job Application Agent

## Setup (First Time)

### 1. Install Dependencies
```bash
npm install
npx playwright install chromium
```

### 2. Get Your Anthropic API Key
1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Create an API key
4. Copy the key (starts with `sk-ant-api03-...`)

### 3. Configure Environment Variables
```bash
cp .env.example .env
```

Edit `.env` and add:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password
```

### 4. Create Your Profile
```bash
cp src/config/user-profile.example.json src/config/user-profile.json
```

Edit `src/config/user-profile.json` with your actual information:
- Personal info (name, email, phone, location)
- Work experience
- Education
- Skills
- Resume path

### 5. Add Your Resume
```bash
cp /path/to/your/resume.pdf documents/resume.pdf
```

Make sure the path in `user-profile.json` matches:
```json
{
  "documents": {
    "resume": "documents/resume.pdf"
  }
}
```

## Usage

### Apply to a Single Job

1. Find a LinkedIn job with "Easy Apply"
2. Copy the job URL
3. Run:

```bash
npm start https://www.linkedin.com/jobs/view/XXXXXXXX
```

### What Happens

1. **Browser launches** - You'll see Chrome open
2. **Login** - Authenticate with LinkedIn (complete 2FA if prompted)
3. **Agent starts** - Claude takes over and:
   - Navigates to the job
   - Analyzes the application form
   - Fills out fields intelligently
   - Uploads your resume
   - Handles multi-step forms
4. **Confirmation** - Claude asks you to confirm before submitting
5. **Submit** - Press Enter to submit the application
6. **Screenshot** - Confirmation saved to `screenshots/`

## Example Run

```bash
$ npm start https://www.linkedin.com/jobs/view/4315500508

🤖 LinkedIn Job Application Agent - LLM-Powered

✓ User profile loaded
Launching browser...
✓ Agent initialized

Authenticating with LinkedIn...
✓ Authentication successful

Starting LLM-powered job application...

🤖 Claude Agent Starting...

--- Iteration 1 ---
💭 Claude is thinking...
🔧 Executing: navigate
   ✓ Navigated to: https://www.linkedin.com/jobs/view/4315500508

🔧 Executing: take_snapshot
   📸 Snapshot taken: Software Engineer - LinkedIn

--- Iteration 2 ---
💬 Claude: I can see the job posting. I'll click the Easy Apply button now.
🔧 Executing: click
   ✓ Clicked: Easy Apply button

--- Iteration 3 ---
🔧 Executing: take_snapshot
   📸 Snapshot taken: Apply to Amazon

💬 Claude: I see a multi-step application form. Step 1 of 3. I'll fill out the contact information fields.

🔧 Executing: type_text
   ✓ Typed into: Phone number field

🔧 Executing: type_text
   ✓ Typed into: City field

...

--- Iteration 8 ---
💬 Claude: I've completed all the form fields. Ready to submit your application to Amazon for the Software Engineer position.

Review the application in the browser window.
Would you like me to proceed with the submission?

⏸️  Waiting for your confirmation...
Press Enter to proceed, or Ctrl+C to cancel:

[User presses Enter]

✓ Confirmed

🔧 Executing: click
   ✓ Clicked: Submit application button

🔧 Executing: task_complete

🏁 Agent Finished

✅ Success: Application submitted successfully
📸 Screenshot saved: screenshots/application-1234567890.png

🧹 Cleaning up...
✓ Browser closed
```

## Tips

### For Best Results
- Use jobs with "Easy Apply" button (external applications not supported yet)
- Fill out your user profile completely
- Keep your resume PDF under 5MB
- Monitor the browser window during execution
- Cancel (Ctrl+C) if something looks wrong

### Cost Management
- Each application costs approximately $0.50-$2 in API costs
- Claude uses Sonnet 4.5 model (most capable)
- Page snapshots and conversation history consume tokens
- For budget-conscious users: consider implementing caching (future enhancement)

### Troubleshooting
- **"API key not found"**: Check your `.env` file
- **"Authentication failed"**: Verify LinkedIn credentials
- **"User profile not found"**: Create `src/config/user-profile.json`
- **Agent gets stuck**: Press Ctrl+C and try again
- **Form not filled correctly**: Update your user profile data

## What's Different from Scripted Version?

This is an **LLM-powered agent**, not a script:

| Old (Scripted) | New (LLM) |
|----------------|-----------|
| Hardcoded CSS selectors | Claude finds elements intelligently |
| Breaks on UI changes | Adapts to UI changes |
| Pre-programmed logic | Reasons about the page |
| Constant maintenance | Self-maintaining |

See `LLM-ARCHITECTURE.md` for technical details.

## Next Steps

After testing on a few jobs:
1. Review the screenshots to verify accuracy
2. Adjust your user profile if fields are incorrect
3. Consider batch processing (Phase 3 feature)
4. Provide feedback on what works/doesn't work

## Support

- Read `LLM-ARCHITECTURE.md` for architecture details
- Check `PROGRESS.md` for development status
- File issues if you encounter bugs

---

**Ready to go!** Find a LinkedIn job and run:
```bash
npm start <job-url>
```
