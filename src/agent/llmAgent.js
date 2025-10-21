/**
 * LLM-driven LinkedIn Easy Apply Agent
 * Uses Claude API to make navigation decisions based on processed snapshots
 */

import Anthropic from '@anthropic-ai/sdk';
import { chromium } from 'playwright';
import { SnapshotProcessor } from '../utils/snapshotProcessor.js';
import { AgentPrompt } from '../prompts/agentPrompt.js';
import { writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';
import * as readline from 'readline';

export class LLMAgent {
  constructor(config) {
    this.anthropic = new Anthropic({ apiKey: config.apiKey });
    this.model = config.model === 'sonnet'
      ? 'claude-3-5-sonnet-20241022'
      : 'claude-3-5-haiku-20241022';
    this.userProfile = config.userProfile;
    this.browser = null;
    this.page = null;
    this.totalTokensIn = 0;
    this.totalTokensOut = 0;
    this.decisions = [];
    this.logDir = join(process.cwd(), 'logs');

    // Ensure logs directory exists
    try {
      mkdirSync(this.logDir, { recursive: true });
    } catch (err) {
      // Directory already exists
    }
  }

  /**
   * Initialize browser instance
   */
  async initialize() {
    console.log('🚀 Initializing browser...');
    this.browser = await chromium.launch({
      headless: false,
      slowMo: 100
    });
    this.page = await this.browser.newPage();
  }

  /**
   * Ensure user is authenticated on LinkedIn
   */
  async _ensureAuthenticated() {
    // Navigate to LinkedIn
    await this.page.goto('https://www.linkedin.com', { waitUntil: 'domcontentloaded' });
    await this._delay(2000);

    // Check if we're actually logged in by looking for profile elements
    const isLoggedIn = await this.page.evaluate(() => {
      // Look for common logged-in indicators
      const hasProfileButton = document.querySelector('[data-control-name="identity_profile_photo"]');
      const hasNavBar = document.querySelector('.global-nav');
      const hasSignInButton = document.querySelector('a[data-tracking-control-name="guest_homepage-basic_nav-header-signin"]');

      // If we have sign in button, we're NOT logged in
      if (hasSignInButton) return false;

      // If we have profile or nav bar, we ARE logged in
      return !!(hasProfileButton || hasNavBar);
    });

    if (!isLoggedIn) {
      console.log('\n🔐 LinkedIn login required');
      console.log('=' .repeat(80));
      console.log('Please log into LinkedIn in the browser window');
      console.log('Complete any 2FA/verification if needed');
      console.log('Once logged in, press Enter here to continue...');
      console.log('='.repeat(80) + '\n');

      await this._waitForEnter();
      console.log('✓ Proceeding with logged-in session\n');
    } else {
      console.log('✓ Already authenticated\n');
    }
  }

  /**
   * Main entry point: apply to a job
   */
  async applyToJob(jobUrl) {
    const startTime = Date.now();

    try {
      console.log(`\n${'='.repeat(80)}`);
      console.log(`🎯 Starting application to: ${jobUrl}`);
      console.log(`🤖 Using model: ${this.model}`);
      console.log(`${'='.repeat(80)}\n`);

      // Step 1: Ensure authenticated
      console.log('📍 Step 1: Checking LinkedIn authentication...');
      await this._ensureAuthenticated();

      // Step 2: Navigate to job page
      console.log('\n📍 Step 2: Navigating to job page...');
      await this.page.goto(jobUrl, { waitUntil: 'load' });
      await this._delay(5000); // Give page time to render fully

      // Step 3: Find and click Easy Apply
      console.log('\n📍 Step 3: Finding Easy Apply button...');
      const easyApplyClicked = await this._findAndClickEasyApply();
      if (!easyApplyClicked) {
        throw new Error('Could not find Easy Apply button - job may not be Easy Apply eligible');
      }

      console.log('✅ Easy Apply modal opened\n');
      await this._delay(1500);

      // Step 4: Navigate through multi-step form
      console.log('📍 Step 4: Navigating application form...\n');
      await this._navigateApplicationForm();

      // Success!
      const duration = ((Date.now() - startTime) / 1000).toFixed(1);
      console.log(`\n${'='.repeat(80)}`);
      console.log(`✅ Application completed successfully in ${duration}s`);
      console.log(`${'='.repeat(80)}\n`);

      this._printCostSummary();
      this._saveLog('success');

    } catch (error) {
      console.error(`\n❌ Error during application: ${error.message}`);
      await this._handleError(error);
      throw error;
    } finally {
      if (this.browser) {
        await this._delay(3000); // Keep browser open briefly
        await this.browser.close();
      }
    }
  }

  /**
   * Find Easy Apply button on job page and click it
   */
  async _findAndClickEasyApply() {
    // Get snapshot and process it
    const rawSnapshot = await this._getSnapshot();

    // Debug: Save raw snapshot to see what we're getting
    if (process.env.DEBUG) {
      const { writeFileSync } = await import('fs');
      writeFileSync('/tmp/debug-raw-snapshot.txt', rawSnapshot);
      console.log(`📝 Debug: Raw snapshot saved to /tmp/debug-raw-snapshot.txt`);
    }

    const filtered = SnapshotProcessor.filterForJobPage(rawSnapshot);
    const processed = SnapshotProcessor.removeNoise(filtered);

    console.log(`📊 Snapshot: ${SnapshotProcessor.estimateTokens(rawSnapshot)} → ${SnapshotProcessor.estimateTokens(processed)} tokens`);

    // Debug: Log first 500 chars of each
    if (processed.length === 0) {
      console.log(`⚠️  Processed snapshot is empty!`);
      console.log(`Raw snapshot preview (first 500 chars):\n${rawSnapshot.substring(0, 500)}`);
    }

    // Get decision from Claude
    const decision = await this._getDecision('job_page', processed);
    this._logDecision(decision, 'Job Page');

    if (decision.action !== 'click') {
      return false;
    }

    // Click Easy Apply using Playwright locator
    await this._clickElement(decision.element_description);
    return true;
  }

  /**
   * Navigate through multi-step application form
   */
  async _navigateApplicationForm() {
    let stepCount = 0;
    const maxSteps = 10; // Safety limit

    while (stepCount < maxSteps) {
      stepCount++;
      await this._delay(1500);

      // Get and process snapshot
      const rawSnapshot = await this._getSnapshot();
      const filtered = SnapshotProcessor.filterForModal(rawSnapshot);
      const processed = SnapshotProcessor.removeNoise(filtered);

      console.log(`\n📊 Step ${stepCount} - Snapshot: ${SnapshotProcessor.estimateTokens(processed)} tokens`);

      // Get decision from Claude
      const decision = await this._getDecision('modal', processed, stepCount > 1 ? this.decisions[this.decisions.length - 1] : null);
      this._logDecision(decision, `Step ${stepCount}`);

      // Execute decision
      if (decision.action === 'submit') {
        await this._handleSubmit(decision);
        break; // Application complete
      } else if (decision.action === 'click') {
        await this._clickElement(decision.element_description);
      } else if (decision.action === 'fill') {
        await this._fillFields(decision.fields);
        // After filling, click next
        await this._delay(1000);
        await this._clickElement('Next');
      } else if (decision.action === 'pause_for_manual') {
        await this._handlePause(decision);
      } else if (decision.action === 'error') {
        throw new Error(decision.error_message);
      }
    }

    if (stepCount >= maxSteps) {
      throw new Error('Exceeded maximum steps - possible infinite loop');
    }
  }

  /**
   * Get page snapshot from Playwright accessibility tree
   */
  async _getSnapshot() {
    const snapshot = await this.page.accessibility.snapshot();
    return this._formatSnapshot(snapshot);
  }

  /**
   * Format accessibility snapshot as YAML string
   */
  _formatSnapshot(node, indent = 0) {
    if (!node) return '';

    const prefix = '  '.repeat(indent) + '- ';
    let line = prefix;

    // Add role/type
    if (node.role) line += node.role;

    // Add name/label
    if (node.name) line += ` "${node.name}"`;

    // Add properties
    if (node.level) line += ` [level=${node.level}]`;
    if (node.checked) line += ' [checked]';
    if (node.selected) line += ' [selected]';
    if (node.value) line += `: ${node.value}`;

    let result = line + '\n';

    // Add children
    if (node.children) {
      for (const child of node.children) {
        result += this._formatSnapshot(child, indent + 1);
      }
    }

    return result;
  }

  /**
   * Get decision from Claude API
   */
  async _getDecision(pageType, processedSnapshot, previousAction = null) {
    const systemPrompt = AgentPrompt.getSystemPrompt();
    const userPrompt = AgentPrompt.getUserPrompt(
      pageType,
      processedSnapshot,
      this.userProfile,
      previousAction ? `${previousAction.action}: ${previousAction.reasoning}` : null
    );

    console.log('🤔 Asking Claude for decision...');

    const response = await this.anthropic.messages.create({
      model: this.model,
      max_tokens: 1024,
      system: systemPrompt,
      messages: [{ role: 'user', content: userPrompt }]
    });

    // Track token usage
    this.totalTokensIn += response.usage.input_tokens;
    this.totalTokensOut += response.usage.output_tokens;

    // Parse JSON response
    const jsonText = response.content[0].text;

    // Extract JSON from markdown code blocks if present
    let cleanJson = jsonText.trim();
    if (cleanJson.startsWith('```json')) {
      cleanJson = cleanJson.replace(/```json\n/, '').replace(/\n```$/, '');
    } else if (cleanJson.startsWith('```')) {
      cleanJson = cleanJson.replace(/```\n/, '').replace(/\n```$/, '');
    }

    // Extract just the JSON object (handle cases where Claude adds explanation text after)
    try {
      // Find the first { and extract from there
      const jsonStart = cleanJson.indexOf('{');
      if (jsonStart === -1) {
        throw new Error('No JSON object found in response');
      }

      // Parse incrementally to find where the JSON object ends
      let parsed = null;
      for (let i = jsonStart + 1; i <= cleanJson.length; i++) {
        try {
          const candidate = cleanJson.substring(jsonStart, i);
          parsed = JSON.parse(candidate);
          // If parse succeeded, we found the complete JSON object
          return parsed;
        } catch (e) {
          // Continue trying longer substrings
        }
      }

      throw new Error('Could not find valid JSON object');
    } catch (err) {
      console.error('Failed to parse Claude response as JSON:', jsonText);
      throw new Error(`Invalid JSON response from Claude: ${err.message}`);
    }
  }

  /**
   * Click element using Playwright locator
   */
  async _clickElement(description) {
    console.log(`👆 Clicking: "${description}"`);

    try {
      // Try multiple selector strategies
      const page = this.page;

      // Strategy 1: Try exact button text
      try {
        await page.getByRole('button', { name: description, exact: true }).click({ timeout: 3000 });
        return;
      } catch (e) {}

      // Strategy 2: Try partial match
      try {
        await page.getByRole('button', { name: new RegExp(description, 'i') }).click({ timeout: 3000 });
        return;
      } catch (e) {}

      // Strategy 3: Try as link
      try {
        await page.getByRole('link', { name: description }).click({ timeout: 3000 });
        return;
      } catch (e) {}

      // Strategy 4: Generic text search
      await page.getByText(description, { exact: false }).first().click({ timeout: 3000 });

    } catch (error) {
      throw new Error(`Could not click element "${description}": ${error.message}`);
    }
  }

  /**
   * Fill form fields
   */
  async _fillFields(fields) {
    console.log(`📝 Filling ${fields.length} field(s)...`);

    for (const field of fields) {
      console.log(`  - ${field.field_type}: "${field.value}"`);

      try {
        if (field.field_type === 'textbox') {
          await this.page.fill(`input[type="text"]`, field.value);
        } else if (field.field_type === 'combobox') {
          await this.page.selectOption('select', field.value);
        } else if (field.field_type === 'checkbox') {
          if (field.value === 'true' || field.value === true) {
            await this.page.check('input[type="checkbox"]');
          }
        }
      } catch (error) {
        console.warn(`  ⚠️  Could not fill field: ${error.message}`);
      }
    }
  }

  /**
   * Handle pause for manual input
   */
  async _handlePause(decision) {
    console.log(`\n⏸️  PAUSED FOR MANUAL INPUT`);
    console.log(`Reason: ${decision.pause_reason}`);
    if (decision.field_description) {
      console.log(`Field: ${decision.field_description}`);
    }
    console.log(`\nPlease complete the field manually in the browser.`);
    console.log(`Press Enter when ready to continue...\n`);

    await this._waitForEnter();
    console.log('▶️  Resuming...\n');
  }

  /**
   * Handle submit action (with user confirmation)
   */
  async _handleSubmit(decision) {
    console.log(`\n📋 READY TO SUBMIT APPLICATION`);
    console.log(`Reasoning: ${decision.reasoning}`);
    console.log(`\n⚠️  Final confirmation required.`);
    console.log(`Press Enter to SUBMIT the application, or Ctrl+C to cancel...\n`);

    await this._waitForEnter();

    console.log('📤 Submitting application...');
    await this._clickElement(decision.element_description);
    await this._delay(2000);

    // Take screenshot of confirmation
    const screenshotPath = join(this.logDir, `submission-${Date.now()}.png`);
    await this.page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`📸 Screenshot saved: ${screenshotPath}`);
  }

  /**
   * Handle errors (log and screenshot)
   */
  async _handleError(error) {
    console.error(`\n🚨 ERROR OCCURRED`);
    console.error(`Message: ${error.message}`);

    try {
      const timestamp = Date.now();

      // Save screenshot
      const screenshotPath = join(this.logDir, `error-${timestamp}.png`);
      await this.page.screenshot({ path: screenshotPath, fullPage: true });
      console.log(`📸 Error screenshot: ${screenshotPath}`);

      // Save error log
      this._saveLog('error', { error: error.message, stack: error.stack });

    } catch (e) {
      console.error('Could not save error artifacts:', e.message);
    }
  }

  /**
   * Wait for user to press Enter
   */
  async _waitForEnter() {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    return new Promise((resolve) => {
      rl.question('', () => {
        rl.close();
        resolve();
      });
    });
  }

  /**
   * Log decision for tracking
   */
  _logDecision(decision, context) {
    this.decisions.push({ ...decision, context, timestamp: Date.now() });

    console.log(`\n💡 Decision (${context}):`);
    console.log(`   Action: ${decision.action}`);
    console.log(`   Reasoning: ${decision.reasoning}`);
    if (decision.element_description) {
      console.log(`   Target: ${decision.element_description}`);
    }
  }

  /**
   * Print cost summary
   */
  _printCostSummary() {
    const inputCost = this.model.includes('sonnet') ? 0.003 : 0.0008;
    const outputCost = this.model.includes('sonnet') ? 0.015 : 0.004;

    const costIn = (this.totalTokensIn / 1000) * inputCost;
    const costOut = (this.totalTokensOut / 1000) * outputCost;
    const totalCost = costIn + costOut;

    console.log(`\n💰 Cost Summary:`);
    console.log(`   Input tokens: ${this.totalTokensIn.toLocaleString()}`);
    console.log(`   Output tokens: ${this.totalTokensOut.toLocaleString()}`);
    console.log(`   Total cost: $${totalCost.toFixed(4)}`);
  }

  /**
   * Save structured log
   */
  _saveLog(status, extra = {}) {
    const logData = {
      timestamp: new Date().toISOString(),
      status,
      model: this.model,
      tokens: {
        input: this.totalTokensIn,
        output: this.totalTokensOut
      },
      decisions: this.decisions,
      ...extra
    };

    const logPath = join(this.logDir, `application-${Date.now()}.json`);
    writeFileSync(logPath, JSON.stringify(logData, null, 2));
    console.log(`📄 Log saved: ${logPath}`);
  }

  /**
   * Helper: delay
   */
  async _delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
