/**
 * Test script for SnapshotProcessor
 * Tests snapshot reduction and validates essential elements are preserved
 */

import { PlaywrightMCPClient } from './src/agent/mcpClient.js'
import { SnapshotProcessor } from './src/utils/snapshotProcessor.js'
import { writeFileSync } from 'fs'

/**
 * Validate job page snapshot contains required elements
 */
function validateJobPageSnapshot(processed) {
  const checks = {
    hasEasyApply: processed.includes('Easy Apply'),
    hasRef: processed.includes('[ref='),
    isSmall: SnapshotProcessor.estimateTokens(processed) < 1000
  }

  console.log('  Validation:', JSON.stringify(checks, null, 2))
  return checks.hasEasyApply && checks.hasRef && checks.isSmall
}

/**
 * Validate modal snapshot contains required elements
 */
function validateModalSnapshot(processed) {
  const checks = {
    hasDialog: processed.includes('dialog'),
    hasButton: processed.includes('- button'),
    hasFormField: processed.includes('textbox') || processed.includes('combobox'),
    isSmall: SnapshotProcessor.estimateTokens(processed) < 5000
  }

  console.log('  Validation:', JSON.stringify(checks, null, 2))
  return checks.hasDialog && checks.hasButton
}

async function testSnapshotProcessor() {
  console.log('🧪 Testing Snapshot Processor\n')

  const mcp = new PlaywrightMCPClient()
  await mcp.start()

  // Test 1: Job Page
  console.log('Test 1: Job Page (before Easy Apply)')
  console.log('=====================================')
  await mcp.navigate('https://www.linkedin.com/jobs/view/4313403580')
  await new Promise(r => setTimeout(r, 3000))

  const jobPageSnapshot = await mcp.snapshot()
  const jobPageOriginal = SnapshotProcessor.extractLines(jobPageSnapshot).join('\n')
  const jobPageFiltered = SnapshotProcessor.filterForJobPage(jobPageOriginal)
  const jobPageCleaned = SnapshotProcessor.removeNoise(jobPageFiltered)

  const jobStats = SnapshotProcessor.getStats(jobPageOriginal, jobPageCleaned)
  console.log('  Original:', jobStats.originalChars, 'chars,', jobStats.originalTokens, 'tokens')
  console.log('  Processed:', jobStats.processedChars, 'chars,', jobStats.processedTokens, 'tokens')
  console.log('  Reduction:', jobStats.reductionPercent + '%')

  // Save outputs for inspection
  writeFileSync('snapshots/job-page-original.txt', jobPageOriginal)
  writeFileSync('snapshots/job-page-processed.txt', jobPageCleaned)
  console.log('  ✓ Saved to snapshots/job-page-*.txt')

  const jobPageValid = validateJobPageSnapshot(jobPageCleaned)
  console.log('  Result:', jobPageValid ? '✅ PASS' : '❌ FAIL')
  console.log()

  // Test 2: Application Modal
  console.log('Test 2: Application Modal (after Easy Apply)')
  console.log('=============================================')

  // Click Easy Apply
  const easyApplySnapshot = await mcp.snapshot()
  const lines = SnapshotProcessor.extractLines(easyApplySnapshot).join('\n').split('\n')
  let easyApplyRef = null
  for (const line of lines) {
    if (line.includes('Easy Apply') && line.includes('[ref=')) {
      const match = line.match(/\[ref=([^\]]+)\]/)
      if (match) {
        easyApplyRef = match[1]
        console.log('  Found Easy Apply button, ref:', easyApplyRef)
        break
      }
    }
  }

  if (easyApplyRef) {
    await mcp.click({ element: 'Easy Apply', ref: easyApplyRef })
    console.log('  ✓ Clicked Easy Apply')
    console.log('  ⏳ Waiting 10 seconds for iframe to fully load...')
    await new Promise(r => setTimeout(r, 10000))

    // Take screenshot to see what's actually on screen
    console.log('  📸 Taking screenshot to verify modal state...')
    await mcp.takeScreenshot({ filename: 'snapshots/modal-screenshot.png', fullPage: false })
  } else {
    console.log('  ⚠️  Easy Apply button not found, skipping modal test')
    await mcp.close()
    return
  }

  const modalSnapshot = await mcp.snapshot()
  const modalOriginal = SnapshotProcessor.extractLines(modalSnapshot).join('\n')
  const modalFiltered = SnapshotProcessor.filterForModal(modalOriginal)
  const modalCleaned = SnapshotProcessor.removeNoise(modalFiltered)

  const modalStats = SnapshotProcessor.getStats(modalOriginal, modalCleaned)
  console.log('  Original:', modalStats.originalChars, 'chars,', modalStats.originalTokens, 'tokens')
  console.log('  Processed:', modalStats.processedChars, 'chars,', modalStats.processedTokens, 'tokens')
  console.log('  Reduction:', modalStats.reductionPercent + '%')

  // Save outputs
  writeFileSync('snapshots/modal-original.txt', modalOriginal)
  writeFileSync('snapshots/modal-processed.txt', modalCleaned)
  console.log('  ✓ Saved to snapshots/modal-*.txt')

  const modalValid = validateModalSnapshot(modalCleaned)
  console.log('  Result:', modalValid ? '✅ PASS' : '❌ FAIL')
  console.log()

  await mcp.close()

  // Summary
  console.log('📊 Summary')
  console.log('==========')
  console.log('Job page reduction:', jobStats.reductionPercent + '%', jobPageValid ? '✅' : '❌')
  console.log('Modal reduction:', modalStats.reductionPercent + '%', modalValid ? '✅' : '❌')
  console.log()
  console.log('Check snapshots/ directory for detailed output files')
}

testSnapshotProcessor().catch(console.error)
