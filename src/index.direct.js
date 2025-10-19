/**
 * LinkedIn Job Application Agent - LLM-Powered Version
 * Uses Claude API to intelligently navigate and fill job applications
 */

import { chromium } from 'playwright';
import { config } from 'dotenv';
import { readFileSync } from 'fs';
import { ClaudeJobAgent } from './agent/claudeAgent.js';

// Load environment variables
config();

class JobApplicationAgent {
  constructor() {
    this.browser = null;
    this.page = null;
    this.claudeAgent = null;
    this.userProfile = null;
  }

  /**
   * Initialize the agent
   */
  async init() {
    try {
      console.log('🤖 LinkedIn Job Application Agent - LLM-Powered\n');

      // Check for API key
      if (!process.env.ANTHROPIC_API_KEY) {
        console.error('❌ ANTHROPIC_API_KEY not found in .env file');
        console.error('Please add your Anthropic API key to the .env file');
        console.error('Get your API key from: https://console.anthropic.com/');
        process.exit(1);
      }

      // Load user profile
      this.loadUserProfile();

      // Launch browser
      console.log('Launching browser...');
      this.browser = await chromium.launch({
        headless: false, // Show browser so user can monitor
        slowMo: 50 // Slight delay for visibility
      });

      this.page = await this.browser.newPage();

      // Set viewport
      await this.page.setViewportSize({ width: 1280, height: 720 });

      // Initialize Claude agent
      this.claudeAgent = new ClaudeJobAgent(
        this.page,
        this.userProfile,
        process.env.ANTHROPIC_API_KEY
      );

      console.log('✓ Agent initialized\n');

      return true;
    } catch (error) {
      console.error('❌ Initialization error:', error.message);
      return false;
    }
  }

  /**
   * Load user profile from config file
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
   * Authenticate with LinkedIn (Manual Mode)
   */
  async authenticate() {
    console.log('🔐 Manual Login Mode\n');
    console.log('Opening LinkedIn...');

    // Navigate to LinkedIn
    await this.page.goto('https://www.linkedin.com', { waitUntil: 'domcontentloaded' });

    console.log('\n' + '='.repeat(80));
    console.log('👤 Please log into LinkedIn in the browser window');
    console.log('   Complete any 2FA/verification if needed');
    console.log('   Once logged in, press Enter here to continue...');
    console.log('='.repeat(80) + '\n');

    // Wait for user to press Enter
    await this.waitForUserInput();

    console.log('✓ Proceeding with logged-in session\n');
    return true;
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
   * Apply to a job using Claude agent
   */
  async applyToJob(jobUrl) {
    try {
      console.log('Starting LLM-powered job application...\n');

      // Let Claude take over and handle the application
      const result = await this.claudeAgent.applyToJob(jobUrl);

      if (result && result.success) {
        console.log('\n✅ Success:', result.message);

        // Take screenshot of final state
        const timestamp = Date.now();
        await this.page.screenshot({
          path: `./screenshots/application-${timestamp}.png`
        });
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
   * Cleanup and close browser
   */
  async cleanup() {
    console.log('\n🧹 Cleaning up...');

    if (this.browser) {
      await this.browser.close();
    }

    console.log('✓ Browser closed');
  }
}

/**
 * Main execution
 */
async function main() {
  const agent = new JobApplicationAgent();

  try {
    // Get job URL from command line argument
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

    // Apply to the job using Claude
    await agent.applyToJob(jobUrl);

  } catch (error) {
    console.error('\n❌ Fatal error:', error.message);
  } finally {
    // Cleanup
    await agent.cleanup();
    process.exit(0);
  }
}

// Run the agent
main();
