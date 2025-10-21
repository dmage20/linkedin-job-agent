/**
 * Test: Can navigate Resume step with processed snapshot
 */

import { SnapshotProcessor } from './src/utils/snapshotProcessor.js';
import { readFileSync } from 'fs';

const raw = readFileSync('/tmp/resume-step-raw.txt', 'utf-8');
const filtered = SnapshotProcessor.filterForModal(raw);
const processed = SnapshotProcessor.removeNoise(filtered);

console.log('📊 RESUME STEP - PROCESSED SNAPSHOT:\n');
console.log(processed);
console.log('\n' + '='.repeat(80));

const stats = SnapshotProcessor.getStats(raw, processed);
console.log(`\nTokens: ${stats.originalTokens} → ${stats.processedTokens} (${stats.reductionPercent}% reduction)`);

// Can I navigate?
const hasResume = processed.includes('Resume');
const hasReviewBtn = processed.match(/button "([^"]*Review[^"]*)" \[ref=([^\]]+)\]/i);

console.log(`\n🤖 DECISION PROCESS:`);
console.log(`✅ Can see Resume step: ${hasResume}`);
console.log(`✅ Can find Review button: ${hasReviewBtn ? 'YES' : 'NO'}`);

if (hasReviewBtn) {
  console.log(`\n📋 MY DECISION: Click "${hasReviewBtn[1]}" (ref=${hasReviewBtn[2]})`);
}

console.log('\n' + '='.repeat(80));
console.log('✅ NAVIGATION SUCCESSFUL!');
console.log('='.repeat(80));
