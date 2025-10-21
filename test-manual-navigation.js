/**
 * Manual test: Process snapshot from current browser state
 * Tests if processed snapshot has enough info for Claude to navigate
 */

import { SnapshotProcessor } from './src/utils/snapshotProcessor.js';

// This is the raw snapshot I just captured from the job page
const rawJobPageSnapshot = `- generic [ref=e2]:
  - heading "0 notifications" [level=2] [ref=e3]
  - generic [ref=e4]:
    - link "Easy Apply" [ref=e470] [cursor=pointer]:
    - link "Easy Apply" [ref=e525] [cursor=pointer]:`;

console.log('🧪 Testing: Can Claude navigate with processed snapshots?\n');
console.log('=' .repeat(70));
console.log('TEST 1: Job Page - Can I find Easy Apply button?');
console.log('='.repeat(70));

const processed = SnapshotProcessor.filterForJobPage(rawJobPageSnapshot);
const cleaned = SnapshotProcessor.removeNoise(processed);

console.log('\nPROCESSED SNAPSHOT:');
console.log(cleaned);

console.log('\n📋 DECISION:');
if (cleaned.includes('Easy Apply') && cleaned.includes('[ref=')) {
  const match = cleaned.match(/link "Easy Apply" \[ref=([^\]]+)\]/);
  if (match) {
    console.log(`✅ YES! I can find Easy Apply button`);
    console.log(`   Ref: ${match[1]}`);
    console.log(`   Action: Click element "Easy Apply" with ref=${match[1]}`);
  }
} else {
  console.log('❌ NO - Cannot find Easy Apply button');
}

const stats = SnapshotProcessor.getStats(rawJobPageSnapshot, cleaned);
console.log(`\nToken usage: ${stats.processedTokens} tokens`);
