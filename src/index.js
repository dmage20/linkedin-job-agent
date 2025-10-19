/**
 * LinkedIn Job Application Agent - Main Entry Point
 * Phase 1 MVP: Single job application automation
 */

import { chromium } from 'playwright';
import { config } from 'dotenv';
import { readFileSync } from 'fs';
import { LinkedInAuth } from './browser/auth.js';
import { FormFiller } from './jobs/formFiller.js';

// Load environment variables
config();

class JobApplicationAgent {
  constructor() {
    this.browser = null;
    this.page = null;
    this.auth = null;
    this.formFiller = null;
    this.userProfile = null;
  }

  /**
   * Initialize the agent
   */
  async init() {
    try {
      console.log('🤖 LinkedIn Job Application Agent - Phase 1 MVP\n');
      
      // Load user profile
      this.loadUserProfile();
      
      // Launch browser
      console.log('Launching browser...');
      this.browser = await chromium.launch({
        headless: false, // Show browser for Phase 1
        slowMo: 100 // Slow down actions to mimic human behavior
      });
      
      this.page = await this.browser.newPage();
      
      // Set viewport
      await this.page.setViewportSize({ width: 1280, height: 720 });
      
      // Initialize modules
      this.auth = new LinkedInAuth(this.page);
      this.formFiller = new FormFiller(this.page, this.userProfile);
      
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
   * Authenticate with LinkedIn
   */
  async authenticate() {
    const email = process.env.LINKEDIN_EMAIL;
    const password = process.env.LINKEDIN_PASSWORD;
    
    if (!email || !password) {
      console.error('❌ LinkedIn credentials not found in .env file');
      console.error('Please create a .env file with LINKEDIN_EMAIL and LINKEDIN_PASSWORD');
      process.exit(1);
    }
    
    console.log('Authenticating with LinkedIn...');
    const success = await this.auth.login(email, password);
    
    if (!success) {
      console.error('❌ Authentication failed');
      return false;
    }
    
    console.log('✓ Authentication successful\n');
    return true;
  }

  /**
   * Apply to a specific job
   * @param {string} jobUrl - LinkedIn job posting URL
   */
  async applyToJob(jobUrl) {
    try {
      console.log('\n📋 Applying to job: ' + jobUrl + '\n');
      
      // Navigate to job posting
      await this.page.goto(jobUrl, { waitUntil: 'networkidle' });
      await this.delay(2000);
      
      // Click "Easy Apply" button
      const easyApplyButton = this.page.locator('button:has-text("Easy Apply")').first();
      const hasEasyApply = await easyApplyButton.isVisible({ timeout: 5000 }).catch(() => false);
      
      if (!hasEasyApply) {
        console.log('❌ This job does not have Easy Apply - skipping');
        return false;
      }
      
      await easyApplyButton.click();
      console.log('✓ Clicked Easy Apply button\n');
      
      await this.delay(2000);
      
      // Handle multi-step application process
      let step = await this.formFiller.detectFormStep();
      console.log(step ? 'Step ' + step.current + ' of ' + step.total : 'Processing application form...');
      
      // Fill the form
      await this.formFiller.autoFillForm();
      
      // Upload resume if needed
      await this.formFiller.uploadResume();
      
      // Check if there are more steps
      let hasNextButton = true;
      while (hasNextButton) {
        await this.delay(1000);
        
        // Try to click next
        hasNextButton = await this.formFiller.clickNext();
        
        if (hasNextButton) {
          await this.delay(2000);
          
          // Fill next step
          step = await this.formFiller.detectFormStep();
          console.log(step ? '\nStep ' + step.current + ' of ' + step.total : '\nProcessing next step...');
          
          await this.formFiller.autoFillForm();
        }
      }
      
      // Review before submission
      console.log('\n⏸️  Ready to submit application');
      console.log('Please review the application in the browser window');
      console.log('Press Enter to submit, or Ctrl+C to cancel...');
      
      // Wait for user confirmation
      await this.waitForUserConfirmation();
      
      // Submit application
      const submitted = await this.formFiller.submitApplication();
      
      if (submitted) {
        console.log('\n✅ Application submitted successfully!');
        
        // Take screenshot of confirmation
        const timestamp = Date.now();
        await this.page.screenshot({ 
          path: './screenshots/application-' + timestamp + '.png' 
        });
        
        return true;
      } else {
        console.log('\n⚠️  Could not submit application - please submit manually');
        return false;
      }
      
    } catch (error) {
      console.error('❌ Error applying to job:', error.message);
      return false;
    }
  }

  /**
   * Wait for user to press Enter
   */
  async waitForUserConfirmation() {
    return new Promise((resolve) => {
      process.stdin.once('data', () => {
        resolve();
      });
    });
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

  /**
   * Utility: Delay function
   */
  async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * Main execution
 */
async function main() {
  const agent = new JobApplicationAgent();
  
  try {
    // Initialize
    await agent.init();
    
    // Authenticate
    const authenticated = await agent.authenticate();
    if (!authenticated) {
      throw new Error('Authentication failed');
    }
    
    // Get job URL from command line argument
    const jobUrl = process.argv[2];
    
    if (!jobUrl) {
      console.log('\n📖 Usage: npm start <job-url>');
      console.log('Example: npm start https://www.linkedin.com/jobs/view/1234567890\n');
      process.exit(0);
    }
    
    // Apply to the job
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
