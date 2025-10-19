/**
 * Claude Agent - LLM-powered Job Application Agent
 * Uses Claude API with tool use to intelligently navigate and fill job applications
 */

import Anthropic from '@anthropic-ai/sdk';
import { BROWSER_TOOLS, BrowserToolExecutor } from './browserTools.js';

export class ClaudeJobAgent {
  constructor(page, userProfile, apiKey) {
    this.page = page;
    this.userProfile = userProfile;
    this.anthropic = new Anthropic({ apiKey });
    this.executor = new BrowserToolExecutor(page, userProfile);
    this.conversationHistory = [];
    this.maxIterations = 50; // Prevent infinite loops
  }

  /**
   * Create the system prompt for the job application agent
   */
  getSystemPrompt() {
    return `You are an intelligent job application agent. Your task is to help apply to a job on LinkedIn.

USER PROFILE:
${JSON.stringify(this.userProfile, null, 2)}

INSTRUCTIONS:
1. ALWAYS start by taking a snapshot to see what's on the page
2. The snapshot will show you all visible buttons and input fields with their labels
3. Navigate through the LinkedIn job application process step by step
4. Fill out all form fields using the user's profile information
5. Handle multi-step forms by clicking "Next" or "Continue" buttons
6. Upload the resume when you see a file upload field
7. IMPORTANT: Before clicking the final "Submit" button, describe what you're about to submit and ask for confirmation
8. After the user confirms, submit the application
9. Use task_complete when done

HOW TO USE TOOLS:
- click tool: Use the EXACT text you see on buttons (e.g., "Easy Apply", "Next", "Submit application")
- type_text tool: Use the label/placeholder you see on input fields (e.g., "Phone number", "Email", "First name")
- The tools are smart and will find elements automatically - just provide the visible text
- DON'T try to guess CSS selectors or element IDs

WORKFLOW:
1. Take snapshot → see what buttons and fields are available
2. Click "Easy Apply" to start the application
3. Take snapshot → see the form fields
4. Fill each field with data from the user profile
5. Click "Next" if it's a multi-step form
6. Repeat until you reach the final submit button
7. Ask for user confirmation
8. Click "Submit application"
9. Call task_complete

TIPS:
- Always take a snapshot after navigation or clicks to see the new state
- Read the snapshot carefully to see exactly what buttons/fields are available
- If a button or field is not visible, scroll or check if you need to complete a previous step
- Be patient - wait a moment after actions for the page to update
- If you can't find something after trying, explain what you see and ask for help

SAFETY:
- NEVER submit without user confirmation
- If unsure about a field, skip it or use a reasonable value from the profile
- If you see CAPTCHAs or security challenges, inform the user

You have access to browser automation tools. The snapshot tool shows you everything you need to know.`;
  }

  /**
   * Run the agent to complete a job application
   */
  async applyToJob(jobUrl) {
    console.log('\n🤖 Claude Agent Starting...\n');
    console.log('Job URL:', jobUrl);
    console.log('\n' + '='.repeat(80) + '\n');

    // Initialize conversation with system prompt
    const systemPrompt = this.getSystemPrompt();

    // Start the conversation
    const initialMessage = `Please apply to this job: ${jobUrl}

Start by navigating to the job URL and taking a snapshot to see the page.`;

    this.conversationHistory.push({
      role: 'user',
      content: initialMessage
    });

    let iteration = 0;
    let taskComplete = false;
    let finalResult = null;

    while (!taskComplete && iteration < this.maxIterations) {
      iteration++;
      console.log(`\n--- Iteration ${iteration} ---\n`);

      try {
        // Call Claude API with tools
        const response = await this.anthropic.messages.create({
          model: 'claude-3-7-sonnet-20250219',
          max_tokens: 4096,
          system: systemPrompt,
          messages: this.conversationHistory,
          tools: BROWSER_TOOLS
        });

        console.log(`💭 Claude is thinking...`);

        // Process the response
        const { content, stop_reason } = response;

        // Add assistant response to history
        this.conversationHistory.push({
          role: 'assistant',
          content: content
        });

        // Check if Claude wants to use tools
        if (stop_reason === 'tool_use') {
          const toolResults = [];

          for (const block of content) {
            if (block.type === 'text') {
              console.log(`\n💬 Claude: ${block.text}`);
            } else if (block.type === 'tool_use') {
              const { id, name, input } = block;

              // Check for task completion
              if (name === 'task_complete') {
                taskComplete = true;
                finalResult = input;
                toolResults.push({
                  type: 'tool_result',
                  tool_use_id: id,
                  content: JSON.stringify({ success: true, message: 'Task completed' })
                });
                continue;
              }

              // Execute the tool
              const result = await this.executor.execute(name, input);

              // Add result to conversation
              toolResults.push({
                type: 'tool_result',
                tool_use_id: id,
                content: JSON.stringify(result)
              });
            }
          }

          // If we have tool results, add them to the conversation
          if (toolResults.length > 0 && !taskComplete) {
            this.conversationHistory.push({
              role: 'user',
              content: toolResults
            });
          }
        } else if (stop_reason === 'end_turn') {
          // Claude responded without using tools - might be asking for confirmation
          for (const block of content) {
            if (block.type === 'text') {
              console.log(`\n💬 Claude: ${block.text}`);

              // Check if Claude is asking for confirmation
              if (block.text.toLowerCase().includes('confirm') ||
                  block.text.toLowerCase().includes('ready to submit') ||
                  block.text.toLowerCase().includes('press enter')) {

                console.log('\n⏸️  Waiting for your confirmation...');
                console.log('Press Enter to proceed, or Ctrl+C to cancel: ');

                await this.waitForUserInput();

                // User confirmed, tell Claude to proceed
                this.conversationHistory.push({
                  role: 'user',
                  content: 'Confirmed. Please proceed with the submission.'
                });
              }
            }
          }
        }

        // Safety check for max iterations
        if (iteration >= this.maxIterations) {
          console.log('\n⚠️  Max iterations reached. Stopping agent.');
          finalResult = {
            success: false,
            message: 'Max iterations reached without completion'
          };
          taskComplete = true;
        }

      } catch (error) {
        console.error('\n❌ Error in agent loop:', error.message);
        if (error.response) {
          console.error('API Error:', error.response.data);
        }
        finalResult = { success: false, message: error.message };
        taskComplete = true;
      }
    }

    console.log('\n' + '='.repeat(80) + '\n');
    console.log('🏁 Agent Finished\n');

    return finalResult;
  }

  /**
   * Wait for user to press Enter
   */
  async waitForUserInput() {
    return new Promise((resolve) => {
      const stdin = process.stdin;
      stdin.setRawMode(true);
      stdin.resume();
      stdin.setEncoding('utf8');

      const onData = (key) => {
        if (key === '\r' || key === '\n') {
          stdin.setRawMode(false);
          stdin.pause();
          stdin.removeListener('data', onData);
          console.log('✓ Confirmed\n');
          resolve();
        } else if (key === '\u0003') {
          // Ctrl+C
          console.log('\n\n❌ Cancelled by user');
          process.exit(0);
        }
      };

      stdin.on('data', onData);
    });
  }

  /**
   * Get conversation history (useful for debugging)
   */
  getConversationHistory() {
    return this.conversationHistory;
  }
}
