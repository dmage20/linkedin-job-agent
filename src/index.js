/**
 * LinkedIn Job Application Agent - MCP Version
 * Uses Playwright MCP Server for robust browser automation
 */

import { config } from 'dotenv';
import { readFileSync } from 'fs';
import { PlaywrightMCPClient } from './agent/mcpClient.js';
import { MCPClaudeJobAgent } from './agent/mcpClaudeAgent.js';
import { OllamaJobAgent } from './agent/ollamaJobAgent.js';

// Load environment variables
config();

class JobApplicationAgent {
  constructor() {
    this.mcpClient = null;
    this.claudeAgent = null;
    this.userProfile = null;
  }

  /**
   * Initialize the agent
   */
  async init() {
    try {
      const useLocalLLM = process.env.USE_LOCAL_LLM === 'true';

      console.log('🤖 LinkedIn Job Application Agent - MCP Powered\n');

      if (useLocalLLM) {
        console.log('🧪 Running in LOCAL MODE with Ollama');
        console.log('   Model: llama3.1:8b');
        console.log('   Cost: $0 (FREE!)\n');
      } else {
        console.log('🌐 Running in PRODUCTION MODE with Claude API');
        console.log('   Model: claude-3-7-sonnet-20250219\n');

        // Check for API key only in production mode
        if (!process.env.ANTHROPIC_API_KEY) {
          console.error('❌ ANTHROPIC_API_KEY not found in .env file');
          console.error('Please add your Anthropic API key to the .env file');
          console.error('Get your API key from: https://console.anthropic.com/');
          console.error('\nAlternatively, use local mode: USE_LOCAL_LLM=true npm start <job-url>');
          process.exit(1);
        }
      }

      // Load user profile
      this.loadUserProfile();

      // Start MCP client
      this.mcpClient = new PlaywrightMCPClient();
      await this.mcpClient.start();

      // Initialize appropriate agent based on mode
      if (useLocalLLM) {
        this.claudeAgent = new OllamaJobAgent(
          this.mcpClient,
          this.userProfile
        );
      } else {
        this.claudeAgent = new MCPClaudeJobAgent(
          this.mcpClient,
          this.userProfile,
          process.env.ANTHROPIC_API_KEY
        );
      }

      console.log('✓ Agent initialized\n');

      return true;
    } catch (error) {
      console.error('❌ Initialization error:', error.message);
      return false;
    }
  }

  /**
   * Load user profile
   */
  loadUserProfile() {
    try {
      const profilePath = './src/config/user-profile.json';
      const profileData = readFileSync(profilePath, 'utf-8');
      this.userProfile = JSON.parse(profileData);
      console.log('✓ User profile loaded\n');
    } catch (error) {
      console.error('❌ Could not load user profile');
      console.error('Please create src/config/user-profile.json from the example template');
      process.exit(1);
    }
  }

  /**
   * Manual login flow
   */
  async authenticate() {
    console.log('🔐 Manual Login Mode\n');
    console.log('Opening LinkedIn in browser...\n');

    try {
      // Navigate to LinkedIn - this should open the browser window
      const navResult = await this.mcpClient.navigate('https://www.linkedin.com');
      console.log('Navigation result:', navResult);

      // Wait a moment for page to load
      await new Promise(resolve => setTimeout(resolve, 3000));
    } catch (error) {
      console.error('Error during navigation:', error);
      throw error;
    }

    console.log('=' .repeat(80));
    console.log('👤 Please log into LinkedIn in the browser window');
    console.log('   Complete any 2FA/verification if needed');
    console.log('   Once logged in, press Enter here to continue...');
    console.log('='.repeat(80) + '\n');

    await this.waitForUserInput();

    console.log('✓ Proceeding with logged-in session\n');
    return true;
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
   * Apply to a job using Claude agent
   */
  async applyToJob(jobUrl) {
    try {
      console.log('Starting MCP-powered job application...\n');

      const result = await this.claudeAgent.applyToJob(jobUrl);

      if (result && result.success) {
        console.log('\n✅ Success:', result.message);

        // Take screenshot
        const timestamp = Date.now();
        await this.mcpClient.takeScreenshot(`screenshots/application-${timestamp}.png`);
        console.log(`📸 Screenshot saved: screenshots/application-${timestamp}.png`);

        return true;
      } else {
        console.log('\n⚠️  Application incomplete:', result?.message || 'Unknown error');
        return false;
      }

    } catch (error) {
      console.error('❌ Error applying to job:', error.message);
      return false;
    }
  }

  /**
   * Cleanup
   */
  async cleanup() {
    console.log('\n🧹 Cleaning up...');

    if (this.mcpClient) {
      await this.mcpClient.close();
    }

    console.log('✓ MCP Server closed');
  }
}

/**
 * Main execution
 */
async function main() {
  const agent = new JobApplicationAgent();

  try {
    const jobUrl = process.argv[2];

    if (!jobUrl) {
      console.log('\n📖 Usage: npm start <job-url>');
      console.log('Example: npm start https://www.linkedin.com/jobs/view/1234567890\n');
      process.exit(0);
    }

    // Initialize
    await agent.init();

    // Manual login
    await agent.authenticate();

    // Apply to the job
    await agent.applyToJob(jobUrl);

  } catch (error) {
    console.error('\n❌ Fatal error:', error.message);
    console.error(error.stack);
  } finally {
    await agent.cleanup();
    process.exit(0);
  }
}

// Run the agent
main();
