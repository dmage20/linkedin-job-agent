/**
 * Ollama Agent - Local LLM-powered Job Application Agent using MCP Server
 * Uses local Ollama instance for zero-cost testing
 */

import { Ollama } from 'ollama';
import { MCP_BROWSER_TOOLS, MCPBrowserToolExecutor } from './mcpBrowserTools.js';

export class OllamaJobAgent {
  constructor(mcpClient, userProfile) {
    this.mcp = mcpClient;
    this.userProfile = userProfile;
    this.ollama = new Ollama({ host: 'http://localhost:11434' });
    this.executor = new MCPBrowserToolExecutor(mcpClient, userProfile);
    this.conversationHistory = [];
    this.maxIterations = 50;
    this.totalInputTokens = 0;
    this.totalOutputTokens = 0;
  }

  /**
   * Create the system prompt (same as Claude agent)
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
6. **BATCH FILL FIELDS** - When you see multiple fields, use batch_fill_fields to fill them ALL AT ONCE (much faster!)
7. Click "Next" or "Review" (using ref from snapshot)
8. Repeat steps 5-7 until you reach the review/submit page
9. ASK USER FOR CONFIRMATION before final submit
10. Click submit after confirmation
11. Call task_complete

**CRITICAL**: ALWAYS take a snapshot BEFORE scrolling. The snapshot shows you what's on the page - don't scroll blindly!

**EFFICIENCY TIP #1**: Use batch_fill_fields instead of type_text when you have multiple fields!
- ✅ GOOD: batch_fill_fields with 5 fields = 1 operation
- ❌ SLOW: type_text 5 times = 5 operations (much slower and more expensive)

**EFFICIENCY TIP #2**: You DON'T need to take a snapshot after EVERY action!
SKIP snapshots after these actions (they're predictable and always work):
- ✅ batch_fill_fields → You know the fields were filled successfully
- ✅ type_text → You know the text was typed successfully
- ✅ select_option → You know the option was selected successfully
- ✅ wait → Just waiting, no need to verify

TAKE snapshots after these actions (they change page state):
- ❌ click → Buttons can trigger modals, navigation, page changes - you need to see what happened
- ❌ navigate → New page loaded, you need to see what's there
- ❌ scroll → Page content changed, you need to see what's now visible
- ❌ When unsure or if an error occurred

**Example efficient workflow**:
1. take_snapshot → see form with 5 fields
2. batch_fill_fields (all 5 fields) → skip snapshot, you know they're filled
3. click "Next" button → now take snapshot to see next page

This can reduce iterations from 18 → 10-12 (40% faster, 40% cheaper)!

TIPS:
- The snapshot shows the accessibility tree with refs embedded
- Look for patterns like: button "Text" [ref=X] or textbox "Label" [ref=Y]
- **MODALS/POPUPS**: After clicking "Easy Apply", a modal popup will appear with the form
- **The snapshot will automatically prioritize modal content** - focus on that!
- **BATCH OPERATIONS**: When you see a form with multiple fields, gather all refs and values, then use batch_fill_fields once
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
   * Convert MCP tools to Ollama tool format
   */
  getOllamaTools() {
    // Ollama uses a similar format to Anthropic, but we need to ensure compatibility
    return MCP_BROWSER_TOOLS.map(tool => ({
      type: 'function',
      function: {
        name: tool.name,
        description: tool.description,
        parameters: tool.input_schema
      }
    }));
  }

  /**
   * Run the agent
   */
  async applyToJob(jobUrl) {
    console.log('\n🧪 Ollama Agent Starting (LOCAL MODE)...\n');
    console.log('Model: llama3.1:8b');
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
        // Keep only the last 10 messages to prevent context bloat
        const recentHistory = this.conversationHistory.slice(-10);

        // Prepare messages for Ollama (include system prompt as first message)
        const messages = [
          {
            role: 'system',
            content: systemPrompt
          },
          ...recentHistory
        ];

        const response = await this.ollama.chat({
          model: 'llama3.1:8b',
          messages: messages,
          tools: this.getOllamaTools()
        });

        console.log(`💭 Ollama is thinking...`);

        // Ollama response format is different from Anthropic
        const { message } = response;

        // Track token usage (if available)
        if (response.prompt_eval_count) {
          this.totalInputTokens += response.prompt_eval_count;
        }
        if (response.eval_count) {
          this.totalOutputTokens += response.eval_count;
        }

        // Add assistant response to history
        this.conversationHistory.push({
          role: 'assistant',
          content: message.content || '',
          tool_calls: message.tool_calls
        });

        // Check if Ollama wants to use tools
        if (message.tool_calls && message.tool_calls.length > 0) {
          const toolResults = [];

          for (const toolCall of message.tool_calls) {
            const { function: func } = toolCall;
            const toolName = func.name;
            const toolInput = func.arguments;

            // Display any text content
            if (message.content) {
              console.log(`\n💬 Ollama: ${message.content}`);
            }

            if (toolName === 'task_complete') {
              taskComplete = true;
              finalResult = toolInput;
              toolResults.push({
                role: 'tool',
                content: JSON.stringify({ success: true, message: 'Task completed' })
              });
              continue;
            }

            const result = await this.executor.execute(toolName, toolInput);

            toolResults.push({
              role: 'tool',
              content: JSON.stringify(result)
            });
          }

          if (toolResults.length > 0 && !taskComplete) {
            // Add tool results to conversation
            this.conversationHistory.push(...toolResults);
          }
        } else {
          // No tool calls - just text response
          if (message.content) {
            console.log(`\n💬 Ollama: ${message.content}`);

            // Check if asking for confirmation
            if (message.content.toLowerCase().includes('confirm') ||
                message.content.toLowerCase().includes('ready to submit') ||
                message.content.toLowerCase().includes('proceed')) {

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
          console.error('Ollama Error:', error.response);
        }
        finalResult = { success: false, message: error.message };
        taskComplete = true;
      }
    }

    console.log('\n' + '='.repeat(80) + '\n');
    console.log('🏁 Agent Finished\n');

    // Display cost estimate (free for local!)
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
    console.log('💰 Cost Estimate (LOCAL):');
    console.log('─'.repeat(80));
    console.log(`   Iterations:     ${iterations}`);
    console.log(`   Input tokens:   ${this.totalInputTokens.toLocaleString()} (estimated)`);
    console.log(`   Output tokens:  ${this.totalOutputTokens.toLocaleString()} (estimated)`);
    console.log(`   Total tokens:   ${(this.totalInputTokens + this.totalOutputTokens).toLocaleString()}`);
    console.log('─'.repeat(80));
    console.log(`   TOTAL COST:     $0.0000 (FREE! 🎉)`);
    console.log('─'.repeat(80));
    console.log(`   Note: Running locally with Ollama - unlimited free usage!`);
    console.log('─'.repeat(80));
    console.log('');
  }

  getConversationHistory() {
    return this.conversationHistory;
  }
}
