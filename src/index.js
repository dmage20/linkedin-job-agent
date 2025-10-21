/**
 * LinkedIn Job Application Agent - LLM-Driven Version
 * Uses Claude API to make intelligent navigation decisions
 */

import { config } from 'dotenv';
import { readFileSync } from 'fs';
import { LLMAgent } from './agent/llmAgent.js';

// Load environment variables
config();

/**
 * Parse command line arguments
 */
function parseArgs() {
  const args = process.argv.slice(2);

  let jobUrl = null;
  let model = 'haiku'; // Default to cheaper model

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg.startsWith('--model=')) {
      model = arg.split('=')[1];
    } else if (arg === '--model' && i + 1 < args.length) {
      model = args[i + 1];
      i++;
    } else if (!arg.startsWith('--')) {
      jobUrl = arg;
    }
  }

  return { jobUrl, model };
}

/**
 * Load user profile
 */
function loadUserProfile() {
  try {
    const profilePath = './src/config/user-profile.json';
    const profileData = readFileSync(profilePath, 'utf-8');
    return JSON.parse(profileData);
  } catch (error) {
    console.error('\n❌ Could not load user profile');
    console.error('Please create src/config/user-profile.json from the example template\n');
    process.exit(1);
  }
}

/**
 * Validate environment variables
 */
function validateEnv() {
  if (!process.env.ANTHROPIC_API_KEY) {
    console.error('\n❌ Missing ANTHROPIC_API_KEY environment variable');
    console.error('Please add ANTHROPIC_API_KEY to your .env file\n');
    process.exit(1);
  }
}

/**
 * Main execution
 */
async function main() {
  console.log('🤖 LinkedIn Job Application Agent - LLM-Driven Mode\n');

  // Parse arguments
  const { jobUrl, model } = parseArgs();

  if (!jobUrl) {
    console.log('📖 Usage: npm start <job-url> [--model=sonnet|haiku]\n');
    console.log('Examples:');
    console.log('  npm start https://www.linkedin.com/jobs/view/1234567890');
    console.log('  npm start https://www.linkedin.com/jobs/view/1234567890 --model=sonnet\n');
    console.log('Models:');
    console.log('  haiku  - Claude 3.5 Haiku (faster, cheaper, ~$0.001/application)');
    console.log('  sonnet - Claude 3.5 Sonnet (more capable, ~$0.007/application)\n');
    process.exit(0);
  }

  // Validate model
  if (!['haiku', 'sonnet'].includes(model)) {
    console.error(`\n❌ Invalid model: ${model}`);
    console.error('Valid models: haiku, sonnet\n');
    process.exit(1);
  }

  // Validate environment
  validateEnv();

  // Load user profile
  console.log('📋 Loading user profile...');
  const userProfile = loadUserProfile();
  console.log(`✓ Profile loaded: ${userProfile.personalInfo.name}\n`);

  // Create agent
  const agent = new LLMAgent({
    apiKey: process.env.ANTHROPIC_API_KEY,
    model,
    userProfile
  });

  try {
    // Initialize browser
    await agent.initialize();

    // Apply to job
    await agent.applyToJob(jobUrl);

    console.log('\n✅ Application process completed!\n');

  } catch (error) {
    console.error('\n❌ Fatal error:', error.message);
    if (process.env.DEBUG) {
      console.error(error.stack);
    }
    process.exit(1);
  }
}

// Run the agent
main();
