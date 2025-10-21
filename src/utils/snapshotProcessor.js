/**
 * Snapshot Processor
 * Filters and reduces MCP browser snapshots to minimize tokens before sending to LLM
 */

export class SnapshotProcessor {
  /**
   * Filter snapshot for job page (before Easy Apply clicked)
   * Goal: Find Easy Apply button only
   */
  static filterForJobPage(snapshot) {
    const lines = this.extractLines(snapshot)
    const filtered = []

    for (const line of lines) {
      const trimmed = line.trim()

      // Keep buttons and links that might be Easy Apply
      if ((trimmed.startsWith('- button') || trimmed.startsWith('- link')) &&
          line.toLowerCase().includes('easy apply')) {
        filtered.push(line)
      }
    }

    return filtered.join('\n')
  }

  /**
   * Filter snapshot for application modal (after Easy Apply clicked)
   * Goal: Extract iframe content (LinkedIn uses iframe for Easy Apply)
   */
  static filterForModal(snapshot) {
    const lines = this.extractLines(snapshot)
    const filtered = []
    let inIframe = false
    let iframeIndent = -1
    let inDialog = false
    let dialogIndent = -1

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]
      const currentIndent = line.search(/\S/)

      // Detect iframe start (LinkedIn Easy Apply uses iframe)
      if (line.includes('- iframe') && !inIframe) {
        inIframe = true
        iframeIndent = currentIndent
        filtered.push(line)
        continue
      }

      // If in iframe, keep everything
      if (inIframe) {
        // Check if we exited iframe (indent back to iframe level or less)
        if (currentIndent <= iframeIndent && line.trim().startsWith('-') && !line.includes('iframe')) {
          break
        }
        filtered.push(line)
      }

      // Also check for dialog elements (fallback if no iframe)
      if (!inIframe && line.includes('- dialog') && !inDialog) {
        inDialog = true
        dialogIndent = currentIndent
        filtered.push(line)
        continue
      }

      // If in dialog (and not in iframe), keep everything
      if (!inIframe && inDialog) {
        if (currentIndent <= dialogIndent && line.trim().startsWith('-') && !line.includes('dialog')) {
          break
        }
        filtered.push(line)
      }
    }

    // If no iframe or dialog found, return only form-related elements
    if (filtered.length === 0) {
      return snapshot.split('\n')
        .filter(line => {
          return (
            line.includes('- textbox') ||
            line.includes('- combobox') ||
            line.includes('- textarea') ||
            line.includes('- button') ||
            line.includes('- heading')
          )
        })
        .join('\n')
    }

    return filtered.join('\n')
  }

  /**
   * Remove noise elements
   */
  static removeNoise(snapshot) {
    return snapshot.split('\n')
      .filter(line => {
        const lower = line.toLowerCase()

        // Remove URLs (huge token wasters)
        if (line.includes('/url:')) return false

        // Remove premium/ad content
        if (lower.includes('premium') || lower.includes('reactivate')) return false

        // Remove global navigation (especially in iframes)
        if (lower.includes('navigation') || lower.includes('banner')) return false
        if (lower.includes('global navigation')) return false

        // Remove skip links and accessibility helpers
        if (lower.includes('skip to search') || lower.includes('skip to main')) return false
        if (lower.includes('keyboard shortcuts')) return false

        // Remove toast/notification messages
        if (lower.includes('toast message') || lower.includes('notifications total')) return false

        // Remove footer
        if (lower.includes('footer') || lower.includes('linkedin corporation')) return false

        // Remove header/nav items
        if (lower.includes('home, ') || lower.includes('my network,') || lower.includes('jobs, ')) return false
        if (lower.includes('messaging,') || lower.includes('notifications,')) return false

        return true
      })
      .join('\n')
  }

  /**
   * Helper: Extract text from MCP response
   */
  static extractLines(snapshotResult) {
    let text = ''

    if (typeof snapshotResult === 'string') {
      text = snapshotResult
    } else if (snapshotResult?.content) {
      if (Array.isArray(snapshotResult.content)) {
        text = snapshotResult.content
          .filter(item => item.type === 'text')
          .map(item => item.text)
          .join('\n')
      } else if (typeof snapshotResult.content === 'string') {
        text = snapshotResult.content
      }
    }

    return text.split('\n')
  }

  /**
   * Estimate token count (rough: 1 token ≈ 4 chars)
   */
  static estimateTokens(text) {
    return Math.ceil(text.length / 4)
  }

  /**
   * Get statistics
   */
  static getStats(original, processed) {
    const origTokens = this.estimateTokens(original)
    const procTokens = this.estimateTokens(processed)
    const reduction = ((1 - procTokens / origTokens) * 100).toFixed(1)

    return {
      originalChars: original.length,
      processedChars: processed.length,
      originalTokens: origTokens,
      processedTokens: procTokens,
      reductionPercent: reduction
    }
  }
}
