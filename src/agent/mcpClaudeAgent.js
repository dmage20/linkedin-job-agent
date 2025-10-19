/**
 * Claude Agent - LLM-powered Job Application Agent using MCP Server
 * Uses Playwright MCP Server for robust browser automation
 */

import Anthropic from '@anthropic-ai/sdk';
import { MCP_BROWSER_TOOLS, MCPBrowserToolExecutor } from './mcpBrowserTools.js';

export class MCPClaudeJobAgent {
  constructor(mcpClient, userProfile, apiKey) {
    this.mcp = mcpClient;
    this.userProfile = userProfile;
    this.anthropic = new Anthropic({ apiKey });
    this.executor = new MCPBrowserToolExecutor(mcpClient, userProfile);
    this.conversationHistory = [];
    this.maxIterations = 50;
    this.totalInputTokens = 0;
    this.totalOutputTokens = 0;
  }

  /**
   * Create the system prompt
   */
  getSystemPrompt() {
    // Create a condensed version of the user profile to save tokens
    const condensedProfile = {
      name: `${this.userProfile.personalInfo?.firstName} ${this.userProfile.personalInfo?.lastName}`,
      email: this.userProfile.personalInfo?.email,
      phone: this.userProfile.personalInfo?.phone,
      location: this.userProfile.personalInfo?.location,
      resume: this.userProfile.documents?.resume,
      yearsExperience: this.userProfile.preferences?.yearsOfExperience,
      requiresSponsorship: this.userProfile.preferences?.requiresSponsorship
    };

    return `You are an intelligent job application agent. Your task is to apply to a job on LinkedIn using browser automation.

USER PROFILE (key info only - use reasonable defaults if fields not listed here):
${JSON.stringify(condensedProfile, null, 2)}

IMPORTANT - HOW TO USE THE BROWSER TOOLS:

1. **ALWAYS start by taking a snapshot** to see what's on the page
2. **The snapshot shows elements with [ref=X] markers** - these are reference IDs you MUST use
3. **To click or type, you MUST provide the ref from the snapshot**

Example workflow:
- take_snapshot → see: button "Easy Apply" [ref=5]
- click with ref="5" and description="Easy Apply button"
- take_snapshot → see: textbox "Phone number" [ref=10]
- type_text with ref="10", text="+1234567890", description="phone number"

CRITICAL RULES:
- You CANNOT click or type without a ref from a snapshot
- ALWAYS take a snapshot before each action
- Read the snapshot carefully to find the correct ref
- Use the EXACT ref string (e.g., "5", "10", "ref-5") shown in the snapshot
- The snapshot is your source of truth for what's available on the page

WORKFLOW (OPTIMIZED):
1. Navigate to the job URL
2. **IMMEDIATELY take snapshot** (DO NOT scroll first!)
3. Find "Easy Apply" button in the snapshot and click it using its ref
4. Wait 2 seconds for modal to load
5. Take snapshot → you'll see the modal form fields
6. Fill each field using its ref from the snapshot
7. Click "Next" or "Review" (using ref from snapshot)
8. Repeat steps 5-7 until you reach the review/submit page
9. ASK USER FOR CONFIRMATION before final submit
10. Click submit after confirmation
11. Call task_complete

**CRITICAL**: ALWAYS take a snapshot BEFORE scrolling. The snapshot shows you what's on the page - don't scroll blindly!

TIPS:
- The snapshot shows the accessibility tree with refs embedded
- Look for patterns like: button "Text" [ref=X] or textbox "Label" [ref=Y]
- **MODALS/POPUPS**: After clicking "Easy Apply", a modal popup will appear with the form
- **The snapshot will automatically prioritize modal content** - focus on that!
- If you can't find an element, scroll and take a new snapshot
- Wait briefly after actions (use wait tool) for page to update
- Multi-step forms: complete each step, click Next, repeat

SAFETY:
- NEVER submit without user confirmation
- If unsure, explain what you see and ask for help
- Handle errors gracefully - if a ref doesn't work, take a new snapshot

Your tools give you precise control over the browser. Use refs to target elements exactly.`;
  }

  /**
   * Run the agent
   */
  async applyToJob(jobUrl) {
    console.log('\n🤖 Claude Agent Starting (MCP Mode)...\n');
    console.log('Job URL:', jobUrl);
    console.log('\n' + '='.repeat(80) + '\n');

    const systemPrompt = this.getSystemPrompt();

    const initialMessage = `Please apply to this job: ${jobUrl}

Start by navigating to the URL and taking a snapshot to see what's available.`;

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
        // Keep only the last 10 messages to prevent token bloat
        const recentHistory = this.conversationHistory.slice(-10);

        const response = await this.anthropic.messages.create({
          model: 'claude-3-7-sonnet-20250219',
          max_tokens: 2048, // Reduced from 4096 to save tokens
          system: systemPrompt,
          messages: recentHistory, // Use limited history
          tools: MCP_BROWSER_TOOLS
        });

        console.log(`💭 Claude is thinking...`);

        const { content, stop_reason, usage } = response;

        // Track token usage
        if (usage) {
          this.totalInputTokens += usage.input_tokens || 0;
          this.totalOutputTokens += usage.output_tokens || 0;
        }

        this.conversationHistory.push({
          role: 'assistant',
          content: content
        });

        if (stop_reason === 'tool_use') {
          const toolResults = [];

          for (const block of content) {
            if (block.type === 'text') {
              console.log(`\n💬 Claude: ${block.text}`);
            } else if (block.type === 'tool_use') {
              const { id, name, input } = block;

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

              const result = await this.executor.execute(name, input);

              toolResults.push({
                type: 'tool_result',
                tool_use_id: id,
                content: JSON.stringify(result)
              });
            }
          }

          if (toolResults.length > 0 && !taskComplete) {
            this.conversationHistory.push({
              role: 'user',
              content: toolResults
            });
          }
        } else if (stop_reason === 'end_turn') {
          for (const block of content) {
            if (block.type === 'text') {
              console.log(`\n💬 Claude: ${block.text}`);

              if (block.text.toLowerCase().includes('confirm') ||
                  block.text.toLowerCase().includes('ready to submit') ||
                  block.text.toLowerCase().includes('proceed')) {

                console.log('\n⏸️  Waiting for your confirmation...');
                console.log('Press Enter to proceed, or Ctrl+C to cancel: ');

                await this.waitForUserInput();

                this.conversationHistory.push({
                  role: 'user',
                  content: 'Confirmed. Please proceed with the submission.'
                });
              }
            }
          }
        }

        if (iteration >= this.maxIterations) {
          console.log('\n⚠️  Max iterations reached');
          finalResult = {
            success: false,
            message: 'Max iterations reached'
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

    // Display cost estimate
    this.displayCostEstimate(iteration);

    return finalResult;
  }

  /**
   * Wait for user input
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
          console.log('\n\n❌ Cancelled by user');
          process.exit(0);
        }
      };

      stdin.on('data', onData);
    });
  }

  /**
   * Display cost estimate for the run
   */
  displayCostEstimate(iterations) {
    // Claude 3.7 Sonnet pricing (as of January 2025)
    // Input: $3 per million tokens
    // Output: $15 per million tokens
    const inputCostPerMillion = 3.00;
    const outputCostPerMillion = 15.00;

    const inputCost = (this.totalInputTokens / 1_000_000) * inputCostPerMillion;
    const outputCost = (this.totalOutputTokens / 1_000_000) * outputCostPerMillion;
    const totalCost = inputCost + outputCost;

    console.log('💰 Cost Estimate:');
    console.log('─'.repeat(80));
    console.log(`   Iterations:     ${iterations}`);
    console.log(`   Input tokens:   ${this.totalInputTokens.toLocaleString()}`);
    console.log(`   Output tokens:  ${this.totalOutputTokens.toLocaleString()}`);
    console.log(`   Total tokens:   ${(this.totalInputTokens + this.totalOutputTokens).toLocaleString()}`);
    console.log('─'.repeat(80));
    console.log(`   Input cost:     $${inputCost.toFixed(4)} (${this.totalInputTokens.toLocaleString()} tokens @ $${inputCostPerMillion}/M)`);
    console.log(`   Output cost:    $${outputCost.toFixed(4)} (${this.totalOutputTokens.toLocaleString()} tokens @ $${outputCostPerMillion}/M)`);
    console.log('─'.repeat(80));
    console.log(`   TOTAL COST:     $${totalCost.toFixed(4)}`);
    console.log('─'.repeat(80));
    console.log('');
  }

  getConversationHistory() {
    return this.conversationHistory;
  }
}
