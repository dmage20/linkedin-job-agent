/**
 * Prompt templates for LLM-driven LinkedIn Easy Apply agent
 */

export class AgentPrompt {
  /**
   * System prompt that defines agent behavior
   */
  static getSystemPrompt() {
    return `You are an AI agent that navigates LinkedIn Easy Apply job applications.

Your role:
1. Analyze processed page snapshots (YAML format from accessibility tree)
2. Identify the current application step
3. Determine what action to take next
4. Return your decision as structured JSON

Key capabilities:
- Click buttons (Easy Apply, Next, Continue, Review, Submit)
- Fill form fields with user profile data
- Pause when encountering unclear fields (review + edit mode)
- Detect errors and report them

IMPORTANT RULES:
- You receive PROCESSED snapshots with 95-99% noise removed
- All interactive elements have a [ref=eXXXX] identifier - you MUST return this ref
- If a field is not in the user profile, use action "pause_for_manual"
- If you cannot find a button or are confused, use action "error"
- NEVER guess or make up information for form fields
- ALWAYS verify element refs exist in the snapshot before returning them

Response format:
You must return valid JSON with one of these action types:

1. CLICK (navigate to next step):
{
  "action": "click",
  "reasoning": "brief explanation of why you're clicking",
  "element_ref": "e1234",
  "element_description": "Continue to next step"
}

2. FILL (fill form fields):
{
  "action": "fill",
  "reasoning": "brief explanation of what you're filling",
  "fields": [
    {"ref": "e5678", "value": "Daniel Mage", "field_type": "textbox"},
    {"ref": "e5679", "value": "United States (+1)", "field_type": "combobox"}
  ]
}

3. PAUSE_FOR_MANUAL (unclear field, let user handle it):
{
  "action": "pause_for_manual",
  "reasoning": "why you need human help",
  "pause_reason": "Found field 'Are you authorized to work in US?' - not in user profile",
  "field_ref": "e9999",
  "field_description": "Work authorization checkbox"
}

4. SUBMIT (ready to submit application):
{
  "action": "submit",
  "reasoning": "why you're ready to submit",
  "element_ref": "e1234",
  "element_description": "Submit application"
}

5. ERROR (cannot proceed):
{
  "action": "error",
  "reasoning": "what went wrong",
  "error_message": "Could not find Next button on Contact Info step"
}

Field mapping guidance:
- "Email address" → userProfile.personalInfo.email
- "Phone country code" → userProfile.personalInfo.phone.countryCode
- "Mobile phone number" → userProfile.personalInfo.phone.number
- "City" → userProfile.personalInfo.location.city
- "Years of experience" → userProfile.preferences.yearsOfExperience
- "Require sponsorship" → userProfile.preferences.requiresSponsorship

Common application steps:
1. Job page: Click "Easy Apply" button
2. Contact Info: Usually pre-filled, just click Next
3. Resume: Verify resume selected, click Review
4. Additional questions: Fill from user profile or pause if unclear
5. Final Review: Click Submit (after user confirmation)`;
  }

  /**
   * User prompt for each iteration
   */
  static getUserPrompt(pageType, processedSnapshot, userProfile, previousAction = null) {
    let prompt = `Current page type: ${pageType}\n\n`;

    if (previousAction) {
      prompt += `Previous action: ${previousAction}\n\n`;
    }

    prompt += `Processed snapshot:\n${'='.repeat(80)}\n${processedSnapshot}\n${'='.repeat(80)}\n\n`;

    prompt += `User profile:\n${JSON.stringify(userProfile, null, 2)}\n\n`;

    prompt += `Analyze the snapshot and return your decision as JSON. What action should I take?`;

    return prompt;
  }

  /**
   * Example prompts for testing
   */
  static getExamples() {
    return {
      jobPage: {
        snapshot: `- link "Easy Apply" [ref=e470] [cursor=pointer]:
- link "Easy Apply" [ref=e525] [cursor=pointer]:`,
        expectedResponse: {
          action: 'click',
          reasoning: 'Found Easy Apply button on job page, clicking to open application modal',
          element_ref: 'e525',
          element_description: 'Easy Apply'
        }
      },

      contactInfo: {
        snapshot: `- dialog "Apply to primehire" [ref=e1158]:
  - heading "Contact info" [level=3] [ref=e1177]
  - combobox "Email address *" [ref=e1192]:
    - option "dmage20@gmail.com" [selected]
  - combobox "Phone country code *" [ref=e1200]:
    - option "United States (+1)" [selected]
  - textbox "Mobile phone number*" [ref=e1207]: 202-780-4966
  - button "Continue to next step" [ref=e1213] [cursor=pointer]:`,
        expectedResponse: {
          action: 'click',
          reasoning: 'Contact Info step - all fields already filled. Clicking Next to proceed.',
          element_ref: 'e1213',
          element_description: 'Continue to next step'
        }
      },

      resumeStep: {
        snapshot: `- dialog "Apply to primehire" [ref=e1158]:
  - region "Your job application progress is at 50 percent."
  - heading "Resume" [level=3] [ref=e1219]
  - generic "Selected" [ref=e1223]:
    - heading "STAR Resume.pdf" [level=3] [ref=e1225]
    - radio "Deselect resume STAR Resume.pdf" [checked]
  - button "Review your application" [ref=e1259] [cursor=pointer]:`,
        expectedResponse: {
          action: 'click',
          reasoning: 'Resume step - resume already selected (STAR Resume.pdf). Clicking Review to proceed.',
          element_ref: 'e1259',
          element_description: 'Review your application'
        }
      },

      unclearField: {
        snapshot: `- dialog "Apply to primehire" [ref=e1158]:
  - heading "Additional questions" [level=3]
  - checkbox "Are you legally authorized to work in the United States?" [ref=e1234]
  - button "Next" [ref=e1250] [cursor=pointer]:`,
        expectedResponse: {
          action: 'pause_for_manual',
          reasoning: 'Found work authorization question not in user profile. Pausing for manual input.',
          pause_reason: 'Work authorization checkbox - not specified in user profile',
          field_ref: 'e1234',
          field_description: 'Are you legally authorized to work in the United States?'
        }
      },

      finalReview: {
        snapshot: `- dialog "Apply to primehire" [ref=e1158]:
  - region "Your job application progress is at 100 percent."
  - heading "Review your application" [level=3]
  - heading "Contact info" [level=4]
  - heading "Resume" [level=4]
  - button "Submit application" [ref=e1321] [cursor=pointer]:`,
        expectedResponse: {
          action: 'submit',
          reasoning: 'Reached final review step (100% complete). Ready to submit application.',
          element_ref: 'e1321',
          element_description: 'Submit application'
        }
      }
    };
  }
}
