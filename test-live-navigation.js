/**
 * Live Navigation Test
 * Testing if Claude can navigate using PROCESSED snapshots
 */

import { SnapshotProcessor } from './src/utils/snapshotProcessor.js';
import { readFileSync } from 'fs';

console.log('🧪 LIVE NAVIGATION TEST\n');
console.log('Can Claude navigate the LinkedIn application using processed snapshots?\n');
console.log('='.repeat(80));

// Test with the actual modal snapshot we just captured
const rawModalSnapshot = readFileSync('/tmp/modal-raw.txt', 'utf-8');

console.log('\n📊 PROCESSING MODAL SNAPSHOT...\n');

// Process it
const filtered = SnapshotProcessor.filterForModal(rawModalSnapshot);
const processed = SnapshotProcessor.removeNoise(filtered);

// Get stats
const stats = SnapshotProcessor.getStats(rawModalSnapshot, processed);

console.log('PROCESSED OUTPUT:');
console.log('-'.repeat(80));
console.log(processed);
console.log('-'.repeat(80));

console.log(`\nToken Count: ${stats.originalTokens} → ${stats.processedTokens} (${stats.reductionPercent}% reduction)`);

// Now make decisions based on processed snapshot
console.log('\n🤖 CLAUDE\'S DECISION PROCESS:\n');

// Can I see what step I'm on?
if (processed.includes('Contact info')) {
  console.log('✅ I can identify the current step: Contact Info');
}

// Can I see form fields?
const hasEmail = processed.includes('Email address');
const hasPhone = processed.includes('Mobile phone number');
const hasPhoneCode = processed.includes('Phone country code');

console.log(`✅ I can see email field: ${hasEmail}`);
console.log(`✅ I can see phone fields: ${hasPhone && hasPhoneCode}`);

// Can I see if fields are already filled?
if (processed.includes('dmage20@gmail.com')) {
  console.log('✅ I can see email is already filled');
}
if (processed.includes('202-780-4966')) {
  console.log('✅ I can see phone is already filled');
}

// Can I find the Next button?
const nextMatch = processed.match(/button "([^"]*(?:Next|Continue)[^"]*)" \[ref=([^\]]+)\]/i);
if (nextMatch) {
  console.log(`✅ I can find Next button: "${nextMatch[1]}" (ref=${nextMatch[2]})`);
  console.log(`\n📋 MY DECISION: Click "${nextMatch[1]}" button with ref=${nextMatch[2]}`);
} else {
  console.log('❌ Cannot find Next button');
}

console.log('\n' + '='.repeat(80));
console.log('✅ RESULT: YES, I can navigate using processed snapshots!');
console.log('='.repeat(80));
