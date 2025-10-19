# LLM-Powered Architecture

## Overview

This project has been upgraded from a **brittle scripted approach** to an **LLM-powered intelligent agent** using Claude API with tool use.

## Why LLM-Powered?

### Problems with Scripted Approach
- ❌ Hardcoded CSS selectors break when LinkedIn changes their UI
- ❌ Can't adapt to unexpected situations
- ❌ Requires constant maintenance and updates
- ❌ Limited to pre-programmed scenarios

### Benefits of LLM Approach
- ✅ **Adaptive**: Claude can reason about the page and find elements intelligently
- ✅ **Robust**: Works even when LinkedIn changes their UI
- ✅ **Intelligent**: Can handle unexpected situations and multi-step forms
- ✅ **Self-healing**: If one approach fails, Claude tries alternatives
- ✅ **Vision-capable**: Can understand page structure semantically

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Main Application                        │
│                    (src/index.js)                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Claude Job Agent                          │
│                (src/agent/claudeAgent.js)                   │
│                                                             │
│  ┌────────────────────────────────────────────────┐        │
│  │  Agent Loop:                                   │        │
│  │  1. Claude sees page snapshot                  │        │
│  │  2. Claude decides which tool to use           │        │
│  │  3. Execute tool (click, type, navigate, etc)  │        │
│  │  4. Return result to Claude                    │        │
│  │  5. Repeat until task complete                 │        │
│  └────────────────────────────────────────────────┘        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Browser Tools                             │
│              (src/agent/browserTools.js)                    │
│                                                             │
│  Tools available to Claude:                                │
│  - take_snapshot: See current page state                   │
│  - click: Click on elements                                │
│  - type_text: Fill input fields                            │
│  - navigate: Go to URLs                                    │
│  - select_option: Choose from dropdowns                    │
│  - upload_file: Upload resume                              │
│  - wait: Wait for page loads                               │
│  - scroll: Scroll page                                     │
│  - press_key: Press keyboard keys                          │
│  - task_complete: Signal completion                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Playwright                             │
│              (Actual Browser Automation)                    │
└─────────────────────────────────────────────────────────────┘
```

## How It Works

### 1. Initialization
- Load user profile (your resume data)
- Launch browser with Playwright
- Authenticate with LinkedIn
- Initialize Claude agent with API key

### 2. Agent Loop
Claude operates in an iterative loop:

```javascript
while (!taskComplete) {
  // 1. Claude sees the page
  snapshot = takeSnapshot()

  // 2. Claude thinks and decides what to do
  response = await claude.messages.create({
    messages: conversationHistory,
    tools: BROWSER_TOOLS
  })

  // 3. Execute the tool Claude chose
  if (response.tool_use) {
    result = execute(tool_name, tool_input)
    // Add result to conversation
  }

  // 4. Check if done
  if (tool_name === 'task_complete') {
    taskComplete = true
  }
}
```

### 3. Tool Execution
Each tool corresponds to a Playwright action:

- **take_snapshot** → `page.ariaSnapshot()` - Gets semantic page structure
- **click** → `page.locator(selector).click()` - Clicks elements
- **type_text** → `page.locator(selector).fill(text)` - Types text
- etc.

### 4. Safety & Confirmation
- Claude asks for user confirmation before submitting
- User presses Enter to confirm
- Application is submitted
- Screenshot is captured

## Configuration

### Required Environment Variables

```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-api03-...    # Get from console.anthropic.com
LINKEDIN_EMAIL=your@email.com
LINKEDIN_PASSWORD=your_password
```

### User Profile

The `src/config/user-profile.json` contains your information that Claude uses to fill forms:

```json
{
  "personalInfo": {
    "firstName": "John",
    "lastName": "Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    ...
  },
  "workExperience": [...],
  "education": [...],
  "documents": {
    "resume": "documents/resume.pdf"
  }
}
```

## Key Features

### 1. Adaptive Form Filling
Claude doesn't rely on hardcoded selectors. Instead:
- Takes a page snapshot to see available fields
- Reasons about which fields need which data
- Uses semantic understanding to match profile data to fields

### 2. Multi-Step Form Handling
- Automatically detects form steps (e.g., "Step 1 of 3")
- Completes each step methodically
- Clicks "Next" or "Continue" buttons intelligently

### 3. Error Recovery
If Claude encounters an error:
- It receives the error message
- Tries alternative approaches
- Adapts based on what worked/didn't work

### 4. Human-in-the-Loop
- Browser is visible (not headless)
- User can monitor progress in real-time
- Confirmation required before final submission
- Can intervene at any time (Ctrl+C)

## Comparison: Old vs New

| Feature | Scripted (Old) | LLM-Powered (New) |
|---------|---------------|-------------------|
| Adaptability | ❌ Breaks on UI changes | ✅ Adapts to changes |
| Intelligence | ❌ Pre-programmed only | ✅ Reasons about page |
| Maintenance | ❌ Constant updates needed | ✅ Self-maintaining |
| Error Handling | ❌ Hard crashes | ✅ Tries alternatives |
| Form Variety | ❌ Limited scenarios | ✅ Any form structure |
| Cost | ✅ Free | ⚠️ API costs (~$0.50-2/app) |

## Cost Estimates

Using Claude 3.5 Sonnet:
- Input: $3 per million tokens
- Output: $15 per million tokens

Estimated cost per job application:
- ~50-100k input tokens (page snapshots + conversation)
- ~5-10k output tokens (Claude's decisions)
- **Total: ~$0.50 - $2.00 per application**

For batch applications:
- 10 applications ≈ $5-20
- 100 applications ≈ $50-200

## Development

### Old Files (Backup)
The old scripted implementation is saved in:
- `src/index.old.js` - Old entry point
- `src/browser/auth.js` - Still used for initial LinkedIn login
- `src/jobs/formFiller.js` - Old form filler (not used anymore)

### New Files
- `src/index.js` - New LLM-powered entry point
- `src/agent/claudeAgent.js` - Claude agent orchestrator
- `src/agent/browserTools.js` - Tool definitions and executors

## Future Enhancements

### Phase 2 Ideas
- [ ] Add vision capability for CAPTCHA solving
- [ ] Batch processing with job queue
- [ ] Database tracking of applications
- [ ] Cover letter generation per job
- [ ] Smart question answering based on job description
- [ ] Application success rate analytics

### Potential Optimizations
- [ ] Cache common page patterns to reduce API calls
- [ ] Use Claude Haiku for simpler actions (cheaper)
- [ ] Implement retry logic with exponential backoff
- [ ] Add conversation compression for long sessions

## Troubleshooting

### "API key not found"
Add `ANTHROPIC_API_KEY` to your `.env` file. Get it from: https://console.anthropic.com/

### "Max iterations reached"
The agent hit the 50-iteration safety limit. This might happen if:
- The job application is unusually complex
- Claude gets stuck in a loop
- There's a bug in the form

Solution: Increase `maxIterations` in `src/agent/claudeAgent.js` or break the application into smaller steps.

### "Tool execution failed"
Check the console output to see which tool failed. Common issues:
- Selector not found (LinkedIn changed their UI)
- Network timeout
- File upload path incorrect

The agent will attempt to recover automatically.

## License

MIT
