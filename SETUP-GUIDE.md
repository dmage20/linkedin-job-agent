# Quick Setup Guide

Follow these steps to get the LinkedIn Job Application Agent running in under 5 minutes.

## Step-by-Step Setup

### 1. Install Dependencies (1 minute)

```bash
cd linkedin-job-agent
npm install
```

Wait for Playwright and other dependencies to download.

### 2. Configure Credentials (1 minute)

```bash
# Copy the template
cp .env.example .env

# Edit with your favorite editor
nano .env
```

Add your LinkedIn credentials:
```
LINKEDIN_EMAIL=your-email@example.com
LINKEDIN_PASSWORD=your-password
```

Save and exit (Ctrl+X, then Y, then Enter for nano).

### 3. Set Up Your Profile (2 minutes)

```bash
# Copy the template
cp src/config/user-profile.example.json src/config/user-profile.json

# Edit the profile
nano src/config/user-profile.json
```

Update these key fields:
- `personalInfo` - Your name, email, phone, location
- `documents.resume` - Path to your resume
- `preferences.yearsOfExperience` - How many years of experience you have
- `preferences.requiresSponsorship` - true/false for visa sponsorship

The rest can be updated later for better results.

### 4. Add Your Resume (30 seconds)

```bash
# Copy your resume to the documents folder
cp ~/path/to/your/resume.pdf documents/resume.pdf
```

Make sure the filename matches what you put in `user-profile.json`.

### 5. Test Run (1 minute)

Find a LinkedIn Easy Apply job you want to apply to, copy its URL, then run:

```bash
npm start https://www.linkedin.com/jobs/view/1234567890
```

Replace the URL with your actual job posting URL.

## What Happens Next

1. Browser window opens
2. Agent logs into LinkedIn
3. Navigates to the job
4. Clicks "Easy Apply"
5. Fills out the form
6. Pauses for your review
7. Press Enter to submit!

## First Time Tips

### Finding Easy Apply Jobs

On LinkedIn Jobs:
1. Search for jobs
2. Click "Easy Apply" filter on the left sidebar
3. Copy the URL of any job posting
4. Use that URL with the agent

### If Something Goes Wrong

**2FA Prompt**: Complete it in the browser, agent will wait

**CAPTCHA**: Complete it in the browser, agent will continue

**"Can't find Easy Apply"**: This job doesn't support it, try another

**Form not fully filled**: Phase 1 handles common fields, you can manually fill anything it misses

## Next Steps

After your first successful application:

1. **Update your profile**: Add more details to `user-profile.json` for better auto-fill
2. **Customize answers**: Edit `commonAnswers` section for text responses
3. **Try more jobs**: Apply to multiple positions
4. **Check screenshots**: Review confirmation screenshots in `screenshots/` folder

## Getting Help

Check `README.md` for full documentation and troubleshooting.

Check `PROGRESS.md` to see project status and upcoming features.

## Safety Reminders

✅ Always review before pressing Enter to submit
✅ Check that auto-filled information is correct
✅ Don't apply to jobs you're not actually interested in
✅ Keep your application rate reasonable (don't spam)

Happy job hunting! 🎯
