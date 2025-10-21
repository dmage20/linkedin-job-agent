/**
 * Simple Job Agent
 * Minimal MCP-driven agent that replicates manual browser driving
 * No complex step detection - just linear flow
 */

export class SimpleJobAgent {
  constructor(mcpClient, userProfile) {
    this.mcp = mcpClient;
    this.profile = userProfile;
  }

  async applyToJob(jobUrl) {
    console.log('🚀 Starting simple job application\n');

    try {
      // Step 1: Navigate to job
      console.log('📍 Navigating to job...');
      await this.mcp.navigate(jobUrl);
      await this.wait(2000);

      // Step 2: Click Easy Apply
      console.log('📍 Looking for Easy Apply button...');
      let snapshot = await this.mcp.snapshot();
      const easyApplyBtn = this.findButton(snapshot, ['Easy Apply']);

      if (!easyApplyBtn) {
        throw new Error('Easy Apply button not found');
      }

      console.log('  ✓ Clicking Easy Apply');
      await this.mcp.click({
        element: easyApplyBtn.label,
        ref: easyApplyBtn.ref
      });
      await this.wait(2000);

      // Step 3: Loop through application steps
      for (let step = 1; step <= 10; step++) {
        console.log(`\n📍 Step ${step}: Processing form...`);

        snapshot = await this.mcp.snapshot();

        // Extract fields from snapshot
        const fields = this.extractFields(snapshot);

        // Fill form if fields exist
        if (fields.length > 0) {
          console.log(`  Found ${fields.length} field(s) to fill`);
          const mappedFields = this.mapFieldsToProfile(fields);

          if (mappedFields.length > 0) {
            try {
              await this.mcp.fillForm({ fields: mappedFields });
              console.log(`  ✓ Filled ${mappedFields.length} field(s)`);
            } catch (error) {
              console.log(`  ⚠️  Form fill error: ${error.message}`);
            }
          }
        } else {
          console.log('  No fields to fill');
        }

        await this.wait(1000);

        // Look for next button
        snapshot = await this.mcp.snapshot();
        const nextBtn = this.findButton(snapshot, [
          'Next',
          'Continue',
          'Review',
          'Submit application'
        ]);

        if (!nextBtn) {
          console.log('  ⚠️  No next button found - application may be complete');
          break;
        }

        // Check if it's submit button
        if (nextBtn.label.toLowerCase().includes('submit')) {
          console.log('  ⚠️  Found Submit button - stopping before final submission');
          console.log('\n✅ Application ready for review');
          break;
        }

        console.log(`  ➡️  Clicking: "${nextBtn.label}"`);
        await this.mcp.click({
          element: nextBtn.label,
          ref: nextBtn.ref
        });
        await this.wait(2000);
      }

      return { success: true, message: 'Application completed' };

    } catch (error) {
      console.error('\n❌ Error:', error.message);
      return { success: false, message: error.message };
    }
  }

  /**
   * Find a button in the snapshot by matching text
   */
  findButton(snapshot, buttonTexts) {
    const snapshotText = this.extractSnapshotText(snapshot);
    const lines = snapshotText.split('\n');

    for (const line of lines) {
      // Look for button lines: - button "Text" [ref=eXXX]
      if (!line.trim().startsWith('- button') && !line.trim().startsWith('- link')) {
        continue;
      }

      // Extract label (text in quotes)
      const labelMatch = line.match(/["']([^"']+)["']/);
      if (!labelMatch) continue;
      const label = labelMatch[1];

      // Extract ref
      const refMatch = line.match(/\[ref=([^\]]+)\]/);
      if (!refMatch) continue;
      const ref = refMatch[1];

      // Check if label matches any of our search texts
      for (const searchText of buttonTexts) {
        if (label.toLowerCase().includes(searchText.toLowerCase())) {
          return { label, ref };
        }
      }
    }

    return null;
  }

  /**
   * Extract form fields from snapshot
   */
  extractFields(snapshot) {
    const snapshotText = this.extractSnapshotText(snapshot);
    const lines = snapshotText.split('\n');
    const fields = [];

    for (const line of lines) {
      const trimmed = line.trim();

      // Extract textbox fields
      if (trimmed.startsWith('- textbox')) {
        const labelMatch = line.match(/["']([^"']+)["']/);
        const refMatch = line.match(/\[ref=([^\]]+)\]/);

        if (labelMatch && refMatch) {
          fields.push({
            type: 'textbox',
            name: labelMatch[1],
            ref: refMatch[1]
          });
        }
      }

      // Extract combobox fields
      if (trimmed.startsWith('- combobox')) {
        const labelMatch = line.match(/["']([^"']+)["']/);
        const refMatch = line.match(/\[ref=([^\]]+)\]/);

        if (labelMatch && refMatch) {
          fields.push({
            type: 'combobox',
            name: labelMatch[1],
            ref: refMatch[1]
          });
        }
      }

      // Extract textarea fields
      if (trimmed.startsWith('- textarea')) {
        const labelMatch = line.match(/["']([^"']+)["']/);
        const refMatch = line.match(/\[ref=([^\]]+)\]/);

        if (labelMatch && refMatch) {
          fields.push({
            type: 'textarea',
            name: labelMatch[1],
            ref: refMatch[1]
          });
        }
      }
    }

    return fields;
  }

  /**
   * Map extracted fields to user profile data
   */
  mapFieldsToProfile(fields) {
    const mapped = [];

    for (const field of fields) {
      const fieldName = field.name.toLowerCase();
      let value = null;

      // Phone number
      if (fieldName.includes('phone') || fieldName.includes('mobile')) {
        value = this.profile.personalInfo.phone;
      }
      // Email
      else if (fieldName.includes('email')) {
        value = this.profile.personalInfo.email;
      }
      // City
      else if (fieldName.includes('city')) {
        value = this.profile.personalInfo.location.city;
      }
      // Years of experience
      else if (fieldName.includes('years') && fieldName.includes('experience')) {
        value = String(this.profile.preferences.yearsOfExperience);
      }
      // Work authorization / sponsorship
      else if (fieldName.includes('sponsor') || fieldName.includes('authorization')) {
        value = this.profile.preferences.requiresSponsorship ? 'Yes' : 'No';
      }

      if (value) {
        mapped.push({
          name: field.name,
          ref: field.ref,
          type: field.type,
          value: value
        });
      }
    }

    return mapped;
  }

  /**
   * Extract text from MCP snapshot response
   */
  extractSnapshotText(snapshotResult) {
    if (typeof snapshotResult === 'string') {
      return snapshotResult;
    }

    if (snapshotResult && snapshotResult.content) {
      if (Array.isArray(snapshotResult.content)) {
        return snapshotResult.content
          .filter(item => item.type === 'text')
          .map(item => item.text)
          .join('\n');
      }
      if (typeof snapshotResult.content === 'string') {
        return snapshotResult.content;
      }
    }

    return '';
  }

  /**
   * Simple delay helper
   */
  async wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
